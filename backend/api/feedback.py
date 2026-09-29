import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.bus import make_emitter, set_status
from core.execution import execute_plan
from core.intake import load_recommendation, rebuild_actions, run_investigation, spawn
from core.outcomes import retain_outcome
from db import crud
from db.crud import as_utc
from db.models import IncidentDetail
from schemas import Alert

router = APIRouter(prefix="/incidents", tags=["feedback"])

ACTIONABLE = {"awaiting_approval", "recommended", "fix_failed"}
VERDICT = {"accept": "accepted", "edit": "edited", "reject": "rejected"}


class FeedbackIn(BaseModel):
    action: Literal["accept", "edit", "reject"]
    steps: list[str] | None = None
    comment: str | None = None
    actor: str = "engineer"
    retry: bool = False


class ResolveIn(BaseModel):
    outcome: Literal["worked", "failed", "partial"] = "worked"
    resolution: str | None = None
    actor: str | None = None


@router.post("/{incident_id}/feedback")
async def feedback(incident_id: str, body: FeedbackIn):
    inc = crud.get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "incident not found")
    if inc.status not in ACTIONABLE:
        raise HTTPException(409, f"cannot {body.action} while status is {inc.status}")
    if body.action == "edit" and not body.steps:
        raise HTTPException(422, "steps required for edit")
    emit = make_emitter(incident_id)
    crud.add_audit(incident_id, body.actor, f"feedback_{body.action}", body.model_dump())
    detail = f"{VERDICT[body.action]} by {body.actor}" + (f": {body.comment}" if body.comment else "")
    await emit("human", body.action, detail)
    crud.update_incident(incident_id, suggestion_verdict=VERDICT[body.action])
    rec = load_recommendation(inc)

    if body.action == "edit":
        rec["steps"] = body.steps
        crud.update_incident(incident_id, recommendation_json=json.dumps(rec))
        rebuild_actions(incident_id, body.steps)

    if body.action in ("accept", "edit"):
        if inc.status == "fix_failed" and body.action == "accept":
            rebuild_actions(incident_id, rec.get("steps") or [a.step for a in crud.list_actions(incident_id)])
        spawn(execute_plan(incident_id))
        return {"incident_id": incident_id, "status": "executing"}

    set_status(incident_id, "rejected")
    retain_outcome(incident_id, "failed", body.comment)
    if body.retry:
        alert = Alert.model_validate_json(inc.alert_json)
        prev = "; ".join(rec.get("steps") or [a.step for a in crud.list_actions(incident_id)])
        alert = alert.model_copy(update={
            "message": f"{alert.message} | Previously rejected/failed: {prev}. Reason: {body.comment or 'n/a'}"})
        crud.delete_actions(incident_id)
        set_status(incident_id, "investigating")
        await emit("agent", "retry", "re-investigating with rejection context")
        spawn(run_investigation(incident_id, alert))
        return {"incident_id": incident_id, "status": "investigating"}
    return {"incident_id": incident_id, "status": "rejected"}


@router.post("/{incident_id}/resolve", response_model=IncidentDetail)
async def resolve(incident_id: str, body: ResolveIn | None = None):
    body = body or ResolveIn()
    inc = crud.get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "incident not found")
    if inc.status == "resolved":
        raise HTTPException(409, "already resolved")
    actor = body.actor or "engineer"
    resolution = body.resolution
    if not resolution:
        acts = crud.list_actions(incident_id)
        ok = ", ".join(a.step for a in acts if a.status == "succeeded") or "none"
        bad = ", ".join(a.step for a in acts if a.status == "failed") or "none"
        ver = [e.detail for e in crud.list_events(incident_id) if e.step == "verification"]
        resolution = f"Resolved via: {ok}. Failed: {bad}. Verification: {ver[-1] if ver else 'n/a'}."
    now = datetime.now(timezone.utc)
    crud.update_incident(incident_id, resolved_at=now, outcome=body.outcome, resolution=resolution,
                         ttr_seconds=round((now - as_utc(inc.created_at)).total_seconds(), 1))
    set_status(incident_id, "resolved")
    await make_emitter(incident_id)("human", "resolved", f"resolved by {actor} (outcome={body.outcome}): {resolution}")
    crud.add_audit(incident_id, actor, "resolve", {"outcome": body.outcome, "resolution": resolution})
    retain_outcome(incident_id, body.outcome)
    return crud.to_detail(crud.get_incident(incident_id))
