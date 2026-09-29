from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from db import crud
from db.crud import as_utc
from schemas import Postmortem

router = APIRouter(prefix="", tags=["postmortem"])


def _recorded(value) -> str:
	if isinstance(value, (dict, list)):
		return str(value)
	return str(value).strip() if value is not None else ""


@router.post("/incidents/{incident_id}/postmortem", response_model=Postmortem)
def create_postmortem(incident_id: str) -> Postmortem:
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
