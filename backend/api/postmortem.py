"""
api/postmortem.py
-----------------
Postmortem endpoints.

P6 endpoint (synchronous, uses existing Postmortem schema from schemas.py):
  POST /incidents/{incident_id}/postmortem
    – build a postmortem from recorded DB data; no LLM required

P1 endpoints (LLM-assisted, async, draft → approve workflow):
  POST /incidents/{incident_id}/postmortem/draft
    – generate an LLM-assisted draft; NOT stored automatically

  POST /incidents/{incident_id}/postmortem/approve
    – approve the draft and retain it to long-term memory (Hindsight)

  GET  /incidents/{incident_id}/postmortem/status
    – check postmortem retention status
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import crud
from db.crud import as_utc
from schemas import Postmortem

router = APIRouter(prefix="", tags=["postmortem"])


# ---------------------------------------------------------------------------
# P6: synchronous postmortem from DB data (no LLM)
# ---------------------------------------------------------------------------

def _recorded(value) -> str:
	if isinstance(value, (dict, list)):
		return str(value)
	return str(value).strip() if value is not None else ""


@router.post("/incidents/{incident_id}/postmortem", response_model=Postmortem)
def create_postmortem(incident_id: str) -> Postmortem:
	"""Build a structured postmortem from recorded incident data. No LLM required."""
	incident = crud.get_incident(incident_id)
	if not incident:
		raise HTTPException(404, "incident not found")

	detail = crud.to_detail(incident)
	recommendation = detail.recommendation if isinstance(detail.recommendation, dict) else {}
	alert = detail.alert if isinstance(detail.alert, dict) else {}
	entries: list[tuple[datetime | None, str]] = []

	def add_entry(ts, source: str, label: str, description: str = "") -> None:
		timestamp = as_utc(ts)
		text = f"{timestamp.isoformat() if timestamp else 'time unavailable'} [{source}] {label}"
		if description:
			text += f": {description}"
		entries.append((timestamp, text))

	for event in detail.events:
		add_entry(event.ts, f"event/{event.kind}", event.step, event.detail)
	for action in detail.actions:
		description = action.output or ""
		add_entry(action.ts, f"action/{action.status}", f"step {action.idx + 1}: {action.step}", description)
	for audit in crud.list_audit(incident_id):
		payload = _recorded(audit.payload_json)
		add_entry(audit.ts, f"audit/{audit.actor}", audit.action, payload)
	timeline = [text for _, text in sorted(
		entries, key=lambda entry: entry[0] or datetime.min.replace(tzinfo=timezone.utc)
	)]

	service = _recorded(incident.service) or "unknown service"
	message = _recorded(incident.message)
	severity = _recorded(incident.severity)
	status = _recorded(incident.status)
	summary = f"{service}: {message}" if message else f"Incident {incident_id} for {service}."
	qualifiers = [value for value in (severity and f"severity {severity}", status and f"status {status}") if value]
	if qualifiers:
		summary += f" ({', '.join(qualifiers)})."

	metrics = alert.get("metrics")
	metric_text = "; ".join(f"{key}={value}" for key, value in sorted(metrics.items())) \
		if isinstance(metrics, dict) and metrics else ""
	impact = summary
	if metric_text:
		impact += f" Recorded metrics: {metric_text}."
	else:
		impact += " No alert metrics were recorded."

	hypotheses = recommendation.get("hypotheses")
	recommended_cause = ""
	if isinstance(hypotheses, list) and hypotheses and isinstance(hypotheses[0], dict):
		recommended_cause = _recorded(hypotheses[0].get("cause"))
	root_cause = (
		_recorded(incident.top_hypothesis)
		or recommended_cause
		or _recorded(detail.smart_alert.likely_cause if detail.smart_alert else None)
		or "No root cause was recorded."
	)

	resolution_parts = []
	if _recorded(incident.resolution):
		resolution_parts.append(_recorded(incident.resolution))
	if _recorded(incident.outcome):
		resolution_parts.append(f"Recorded outcome: {_recorded(incident.outcome)}.")
	if not resolution_parts and detail.actions:
		resolution_parts.extend(f"{action.step} ({action.status})" for action in detail.actions)
	resolution = " ".join(resolution_parts) or "No resolution details were recorded."

	lessons = []
	if _recorded(incident.suggestion_verdict):
		lessons.append(f"The recommendation was {_recorded(incident.suggestion_verdict)}.")
	if _recorded(incident.outcome):
		lessons.append(f"The recorded outcome was {_recorded(incident.outcome)}.")
	for action in detail.actions:
		if action.status in {"succeeded", "failed"}:
			lessons.append(f"Recorded action {action.step!r} as {action.status}.")
	steps = recommendation.get("steps")
	if isinstance(steps, list):
		lessons.extend(f"The recommendation included: {step}." for step in steps if _recorded(step))
	avoid = recommendation.get("avoid")
	if isinstance(avoid, list):
		lessons.extend(f"The recommendation flagged avoiding: {item}." for item in avoid if _recorded(item))
	if incident.is_novel:
		lessons.append("The incident was marked novel.")
	if not lessons:
		lessons.append("No additional lessons were recorded.")

	return Postmortem(
		incident_id=incident.id,
		summary=summary,
		timeline=timeline,
		impact=impact,
		root_cause=root_cause,
		resolution=resolution,
		lessons=lessons,
	)


# ---------------------------------------------------------------------------
# P1: LLM-assisted draft → approve workflow
# ---------------------------------------------------------------------------

class PostmortemApproveIn(BaseModel):
    postmortem: dict
    actor: str = "engineer"


@router.post("/incidents/{incident_id}/postmortem/draft")
async def draft_postmortem_endpoint(incident_id: str):
    """
    Generate an LLM-assisted draft postmortem.
    The draft is NOT stored until explicitly approved via /approve.
    """
    try:
        from postmortem import draft_postmortem
    except ImportError as e:
        raise HTTPException(503, f"postmortem service unavailable: {e}")
    try:
        pm = await draft_postmortem(incident_id)
        return pm
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"postmortem generation failed: {str(e)[:200]}")


@router.post("/incidents/{incident_id}/postmortem/approve")
async def approve_postmortem_endpoint(incident_id: str, body: PostmortemApproveIn):
    """
    Approve a draft postmortem and retain it permanently to long-term memory.
    Only call after human review of the draft.
    """
    try:
        from postmortem import approve_postmortem
    except ImportError as e:
        raise HTTPException(503, f"postmortem service unavailable: {e}")
    try:
        result = await approve_postmortem(incident_id, body.postmortem)
        try:
            crud.add_audit(incident_id, body.actor, "postmortem_approved", {"result": result})
        except Exception:
            pass
        return {"incident_id": incident_id, "status": "retained", "result": result}
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"postmortem retention failed: {str(e)[:200]}")


@router.get("/incidents/{incident_id}/postmortem/status")
async def get_postmortem_status(incident_id: str):
    """Check whether a postmortem has been approved and retained for this incident."""
    try:
        audit = crud.list_audit(incident_id)
        pm_events = [a for a in audit if a.action in ("postmortem_retained", "postmortem_approved")]
        if pm_events:
            import json as _json
            latest = pm_events[0]
            return {
                "incident_id": incident_id,
                "status": "retained",
                "retained_at": as_utc(latest.ts).isoformat() if as_utc(latest.ts) else None,
                "detail": _json.loads(latest.payload_json) if latest.payload_json else {},
            }
    except Exception:
        pass
    return {
        "incident_id": incident_id,
        "status": "not_retained",
        "detail": "No approved postmortem found. Use POST /incidents/{id}/postmortem/draft to generate one.",
    }
