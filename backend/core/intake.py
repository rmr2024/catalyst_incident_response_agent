import asyncio
import json
import logging
import re

from core import bridges
from core.bus import make_emitter, publish, publish_global, set_status
from core.severity import classify
from db import crud
from db.models import SimilarRef, SmartAlert
from schemas import Alert, Recommendation
from settings import memory_enabled

log = logging.getLogger("intake")

RISKY = re.compile(r"restart|rollback|roll back|redeploy|failover|scale|delete|drop|flush|kill|purge", re.I)
_tasks: set[asyncio.Task] = set()


def spawn(coro) -> asyncio.Task:
    t = asyncio.get_running_loop().create_task(coro)
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)
    return t


def is_risky(step: str) -> bool:
    return bool(RISKY.search(step or ""))


def rebuild_actions(incident_id: str, steps: list[str]) -> None:
    crud.delete_actions(incident_id)
    for i, s in enumerate(steps):
        crud.add_action(incident_id, i, s, risky=is_risky(s))


async def ingest_alert(alert: Alert, source: str) -> dict:
    sev, reason = classify(alert)
    inc = crud.create_incident(
        service=alert.service, message=alert.message, severity=sev, severity_reason=reason, source=source,
        status="investigating", alert_json=alert.model_dump_json(), memory_used=memory_enabled(),
    )
    crud.add_audit(inc.id, "system", "alert_received", {"source": source, "severity": sev, "reason": reason})
    emit = make_emitter(inc.id)
    await emit("agent", "alert received", f"{alert.service}: {alert.message} [{sev}: {reason}]")
    publish_global("incident_created", crud.to_summary(inc))
    spawn(run_investigation(inc.id, alert))
    return {"incident_id": inc.id, "severity": sev, "severity_reason": reason, "status": inc.status}


def build_smart_alert(inc, rec: Recommendation) -> SmartAlert:
    top = rec.hypotheses[0] if rec.hypotheses else None
    if rec.is_novel or top is None:
        headline = f"[{inc.severity}] {inc.service}: novel incident, no confident match in memory"
    else:
        headline = f"[{inc.severity}] {inc.service}: likely {top.cause} ({round(top.confidence * 100)}%)"
    return SmartAlert(
        incident_id=inc.id, severity=inc.severity, severity_reason=inc.severity_reason, service=inc.service,
        headline=headline, likely_cause=top.cause if top else None, confidence=top.confidence if top else None,
        similar=[SimilarRef(incident_id=h.incident_id, outcome=h.outcome, score=h.score) for h in rec.similar],
        recommended_response=rec.runbook or (rec.steps[0] if rec.steps else None),
        avoid=rec.avoid, is_novel=rec.is_novel, needs_approval=rec.needs_approval,
    )


async def run_investigation(incident_id: str, alert: Alert) -> None:
    emit = make_emitter(incident_id)
    try:
        rec = await bridges.investigate(incident_id, alert, emit)
        if any(is_risky(s) for s in rec.steps):
            rec.needs_approval = True
        top = rec.hypotheses[0] if rec.hypotheses else None
        inc = crud.update_incident(
            incident_id, recommendation_json=rec.model_dump_json(), is_novel=rec.is_novel,
            top_hypothesis=top.cause if top else None, top_confidence=top.confidence if top else None,
        )
        rebuild_actions(incident_id, rec.steps)
        sa = build_smart_alert(inc, rec)
        crud.update_incident(incident_id, smart_alert_json=sa.model_dump_json())
        await emit("agent", "smart alert", sa.headline)
        publish(incident_id, "smart_alert", sa)
        publish_global("smart_alert", sa)
        set_status(incident_id, "awaiting_approval" if rec.needs_approval else "recommended")
        await emit("agent", "recommendation ready", f"{len(rec.steps)} steps; needs_approval={rec.needs_approval}")
    except Exception as e:
        log.exception("investigation failed for %s", incident_id)
        try:
            set_status(incident_id, "failed")
            await emit("agent", "error", str(e)[:200] or type(e).__name__)
            crud.add_audit(incident_id, "system", "investigation_failed", {"error": str(e)[:500]})
        except Exception:
            pass


def load_recommendation(inc) -> dict:
    try:
        return json.loads(inc.recommendation_json) if inc.recommendation_json else {}
    except Exception:
        return {}
