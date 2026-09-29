from fastapi import APIRouter, HTTPException

from core.bus import make_emitter, set_status
from core.execution import execute_plan
from core.intake import load_recommendation, run_investigation, spawn
from db import crud
from db.crud import as_utc
from db.models import IncidentDetail, IncidentSummary
from schemas import AgentEvent, Alert, MemoryHit

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentSummary])
def list_incidents(status: str | None = None, service: str | None = None, severity: str | None = None,
                   active: bool | None = None, limit: int = 50):
    return [crud.to_summary(i) for i in crud.list_incidents(status, service, severity, limit, active)]


@router.get("/stats")
def stats():
    return crud.stats()


def _get(incident_id: str):
    inc = crud.get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "incident not found")
    return inc


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str):
    return crud.to_detail(_get(incident_id))


@router.get("/{incident_id}/timeline")
def timeline(incident_id: str):
    _get(incident_id)
    items = [{"ts": e.ts, "source": "event", "kind": e.kind, "title": e.step, "detail": e.detail}
             for e in crud.list_events(incident_id)]
    items += [{"ts": as_utc(a.ts), "source": "action", "kind": a.status, "title": f"step {a.idx + 1}: {a.step}",
               "detail": a.output} for a in crud.list_actions(incident_id)]
    items += [{"ts": as_utc(a.ts), "source": "audit", "kind": a.actor, "title": a.action, "detail": a.payload_json}
              for a in crud.list_audit(incident_id)]
    return sorted(items, key=lambda x: x["ts"])


@router.get("/{incident_id}/memory-calls", response_model=list[AgentEvent])
def memory_calls(incident_id: str):
    _get(incident_id)
    return [e for e in crud.list_events(incident_id) if e.kind == "memory"]


@router.get("/{incident_id}/similar", response_model=list[MemoryHit])
def similar(incident_id: str):
    return load_recommendation(_get(incident_id)).get("similar") or []


@router.post("/{incident_id}/investigate")
async def investigate(incident_id: str):
    inc = _get(incident_id)
    if inc.status in ("investigating", "executing"):
        raise HTTPException(409, f"cannot investigate while status is {inc.status}")
    crud.delete_actions(incident_id)
    set_status(incident_id, "investigating")
    await make_emitter(incident_id)("agent", "re-investigate", "investigation restarted on request")
    spawn(run_investigation(incident_id, Alert.model_validate_json(inc.alert_json)))
    return {"incident_id": incident_id, "status": "investigating"}


@router.post("/{incident_id}/simulate")
async def simulate(incident_id: str):
    inc = _get(incident_id)
    approved = inc.suggestion_verdict in ("accepted", "edited")
    if inc.status not in ("recommended", "awaiting_approval", "fix_failed", "mitigated"):
        raise HTTPException(409, f"cannot simulate while status is {inc.status}")
    if inc.status != "recommended" and not approved:
        raise HTTPException(409, "risky actions need approval first (POST /incidents/{id}/feedback)")
    spawn(execute_plan(incident_id))
    return {"incident_id": incident_id, "status": "executing"}
