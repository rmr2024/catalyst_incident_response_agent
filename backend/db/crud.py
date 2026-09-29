import json
import threading
from collections import Counter
from datetime import datetime, timezone

from sqlmodel import delete, select

from db.models import (ActionOut, ActionRow, AuditLog, EventRow, Incident, IncidentDetail,
                       IncidentSummary, SmartAlert, utcnow)
from db.session import get_session
from schemas import AgentEvent

TERMINAL = {"resolved", "rejected", "failed"}
_id_lock = threading.Lock()


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _next_id(s) -> str:
    nums = []
    for i in s.exec(select(Incident.id)).all():
        tail = i.split("-")[-1]
        if i.startswith("INC-") and tail.isdigit() and int(tail) >= 1001:
            nums.append(int(tail))
    return f"INC-{max(nums) + 1 if nums else 1001}"


def create_incident(**fields) -> Incident:
    with _id_lock, get_session() as s:
        inc = Incident(id=fields.pop("id", None) or _next_id(s), **fields)
        s.add(inc)
        s.commit()
        s.refresh(inc)
        return inc


def get_incident(incident_id: str) -> Incident | None:
    with get_session() as s:
        return s.get(Incident, incident_id)


def list_incidents(status: str | None = None, service: str | None = None, severity: str | None = None,
                   limit: int = 50, active: bool | None = None) -> list[Incident]:
    with get_session() as s:
        q = select(Incident)
        if status:
            q = q.where(Incident.status == status)
        if service:
            q = q.where(Incident.service == service)
        if severity:
            q = q.where(Incident.severity == severity)
        if active is True:
            q = q.where(Incident.status.not_in(TERMINAL))
        elif active is False:
            q = q.where(Incident.status.in_(TERMINAL))
        return list(s.exec(q.order_by(Incident.created_at.desc()).limit(limit)).all())


def update_incident(incident_id: str, **fields) -> Incident | None:
    with get_session() as s:
        inc = s.get(Incident, incident_id)
        if not inc:
            return None
        for k, v in fields.items():
            setattr(inc, k, v)
        s.add(inc)
        s.commit()
        s.refresh(inc)
        return inc


def add_event(ev: AgentEvent) -> EventRow:
    with get_session() as s:
        row = EventRow(incident_id=ev.incident_id, kind=ev.kind, step=ev.step, detail=ev.detail, ts=ev.ts)
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def list_events(incident_id: str) -> list[AgentEvent]:
    with get_session() as s:
        rows = s.exec(select(EventRow).where(EventRow.incident_id == incident_id).order_by(EventRow.id)).all()
        return [AgentEvent(incident_id=r.incident_id, kind=r.kind, step=r.step, detail=r.detail, ts=as_utc(r.ts))
                for r in rows]


def add_action(incident_id: str, idx: int, step: str, risky: bool = False, status: str = "pending") -> ActionRow:
    with get_session() as s:
        row = ActionRow(incident_id=incident_id, idx=idx, step=step, risky=risky, status=status)
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def update_action(action_id: int, **fields) -> ActionRow | None:
    with get_session() as s:
        row = s.get(ActionRow, action_id)
        if not row:
            return None
        for k, v in fields.items():
            setattr(row, k, v)
        row.ts = utcnow()
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def list_actions(incident_id: str) -> list[ActionRow]:
    with get_session() as s:
        return list(s.exec(select(ActionRow).where(ActionRow.incident_id == incident_id).order_by(ActionRow.idx)).all())


def delete_actions(incident_id: str) -> None:
    with get_session() as s:
        s.exec(delete(ActionRow).where(ActionRow.incident_id == incident_id))
        s.commit()


def add_audit(incident_id: str | None, actor: str, action: str, payload: dict | None = None) -> AuditLog:
    with get_session() as s:
        row = AuditLog(incident_id=incident_id, actor=actor, action=action,
                       payload_json=json.dumps(payload or {}, default=str))
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def list_audit(incident_id: str | None = None, limit: int = 200) -> list[AuditLog]:
    with get_session() as s:
        q = select(AuditLog)
        if incident_id:
            q = q.where(AuditLog.incident_id == incident_id)
        return list(s.exec(q.order_by(AuditLog.id.desc()).limit(limit)).all())


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def _distribution(values) -> dict[str, int]:
    counts = Counter(
        str(value) for value in values
        if value is not None and (not isinstance(value, str) or value.strip())
    )
    return dict(sorted(counts.items()))


def stats(include_analytics: bool = False) -> dict:
    with get_session() as s:
        incs = list(s.exec(select(Incident)).all())
    resolved = [i for i in incs if i.status == "resolved"]
    verdicts = [i.suggestion_verdict for i in incs if i.suggestion_verdict]
    result = {
        "total": len(incs),
        "active": sum(1 for i in incs if i.status not in TERMINAL),
        "resolved": len(resolved),
        "by_severity": dict(Counter(i.severity for i in incs)),
        "by_status": dict(Counter(i.status for i in incs)),
        "mttr_seconds": _avg([i.ttr_seconds for i in resolved]),
        "mttr_memory_on": _avg([i.ttr_seconds for i in resolved if i.memory_used]),
        "mttr_memory_off": _avg([i.ttr_seconds for i in resolved if not i.memory_used]),
        "novel_count": sum(1 for i in incs if i.is_novel),
        "acceptance_rate": round(sum(1 for v in verdicts if v == "accepted") / len(verdicts), 3) if verdicts else None,
    }
    if include_analytics:
        ttr_values = [i.ttr_seconds for i in incs if i.ttr_seconds is not None]
        result.update({
            "by_memory_used": _distribution(
                "enabled" if i.memory_used is True else
                "disabled" if i.memory_used is False else "unknown"
                for i in incs
            ),
            "ttr_seconds": {
                "count": len(ttr_values),
                "average": _avg(ttr_values),
                "min": round(min(ttr_values), 1) if ttr_values else None,
                "max": round(max(ttr_values), 1) if ttr_values else None,
            },
            "by_suggestion_verdict": _distribution(i.suggestion_verdict for i in incs),
            "by_outcome": _distribution(i.outcome for i in incs),
            "by_top_hypothesis": _distribution(i.top_hypothesis for i in incs),
        })
    return result


def reset_all() -> None:
    with get_session() as s:
        for m in (EventRow, ActionRow, AuditLog, Incident):
            s.exec(delete(m))
        s.commit()


def _loads(v):
    try:
        return json.loads(v) if v else None
    except Exception:
        return None


def to_summary(inc: Incident) -> IncidentSummary:
    sa = _loads(inc.smart_alert_json) or {}
    return IncidentSummary(
        id=inc.id, service=inc.service, message=inc.message, severity=inc.severity,
        severity_reason=inc.severity_reason, source=inc.source, status=inc.status, headline=sa.get("headline"),
        is_novel=inc.is_novel, memory_used=inc.memory_used, top_hypothesis=inc.top_hypothesis,
        top_confidence=inc.top_confidence, suggestion_verdict=inc.suggestion_verdict, outcome=inc.outcome,
        resolution=inc.resolution, created_at=as_utc(inc.created_at), resolved_at=as_utc(inc.resolved_at),
        ttr_seconds=inc.ttr_seconds,
    )


def to_action_out(a: ActionRow) -> ActionOut:
    return ActionOut(id=a.id, incident_id=a.incident_id, idx=a.idx, step=a.step, risky=a.risky,
                     status=a.status, output=a.output, ts=as_utc(a.ts))


def to_detail(inc: Incident) -> IncidentDetail:
    sa = _loads(inc.smart_alert_json)
    return IncidentDetail(
        **to_summary(inc).model_dump(),
        alert=_loads(inc.alert_json) or {},
        recommendation=_loads(inc.recommendation_json),
        smart_alert=SmartAlert(**sa) if sa else None,
        actions=[to_action_out(a) for a in list_actions(inc.id)],
        events=list_events(inc.id),
    )
