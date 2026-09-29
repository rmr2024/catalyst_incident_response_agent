"""
postmortem.py
-------------
Postmortem generation and retain-after-approval workflow.

Provides:
  draft_postmortem(incident_id) -> dict
    – generates a structured postmortem using LLM + incident data
    – does NOT automatically store it
    – postmortem must be explicitly approved before retention

  approve_postmortem(incident_id, postmortem) -> str
    – retains the approved postmortem via memory.service.retain_postmortem()
    – preserves the incident_id for traceability

The Postmortem schema reuses the existing schema from schemas.py:
  incident_id, summary, timeline, impact, root_cause, resolution, lessons

This module adds extended fields for the P1 full postmortem:
  evidence, actions_taken, successful_fixes, failed_fixes,
  lessons_learned, follow_up_actions
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from llm import call_llm
from settings import settings

log = logging.getLogger("postmortem")

# Module-level imports for testability (mock patching requires module-level names)
try:
    from db import crud
except Exception:  # pragma: no cover
    crud = None  # type: ignore

try:
    from memory.service import retain_postmortem
except Exception:  # pragma: no cover
    retain_postmortem = None  # type: ignore


_PM_SYSTEM_PROMPT = """You are an expert SRE writing a detailed incident postmortem.

Rules:
- Be factual and evidence-based.
- Only reference steps and actions that actually happened (provided in the incident context).
- Identify the root cause from the evidence available.
- Distinguish successful fixes from failed fixes.
- Lessons learned must be actionable.
- Do not fabricate information not present in the incident context.
- Respond with valid JSON only, no extra text."""


def _build_pm_prompt(incident_id: str, inc_data: dict, actions: list[dict], events: list[dict]) -> str:
    """Build the postmortem generation prompt."""
    service = inc_data.get("service", "unknown")
    message = inc_data.get("message", "")
    severity = inc_data.get("severity", "unknown")
    top_hypothesis = inc_data.get("top_hypothesis") or "Unknown"
    resolution = inc_data.get("resolution") or "Not yet determined"
    outcome = inc_data.get("outcome") or "unknown"
    created_at = inc_data.get("created_at") or ""
    resolved_at = inc_data.get("resolved_at") or ""
    ttr = inc_data.get("ttr_seconds")

    succeeded = [a for a in actions if a.get("status") == "succeeded"]
    failed = [a for a in actions if a.get("status") == "failed"]

    succeeded_steps = "; ".join(a.get("step", "") for a in succeeded) or "None"
    failed_steps = "; ".join(a.get("step", "") for a in failed) or "None"

    # Build a timeline from events
    timeline_items: list[str] = []
    for e in events[:20]:  # limit timeline length
        ts = str(e.get("ts", ""))[:19]
        step = e.get("step", "")
        detail = str(e.get("detail", ""))[:100]
        timeline_items.append(f"{ts}: [{e.get('kind','?')}] {step} – {detail}")

    timeline_str = "\n".join(f"  {t}" for t in timeline_items) if timeline_items else "  No timeline events recorded"
    ttr_str = f"{ttr} seconds" if ttr else "unknown"

    # Recommendation context
    rec_data = inc_data.get("recommendation_json") or "{}"
    try:
        rec = json.loads(rec_data) if isinstance(rec_data, str) else rec_data
    except Exception:
        rec = {}
    similar = rec.get("similar") or []
    similar_str = "; ".join(
        f"{s.get('incident_id','?')} (score={s.get('score',0):.2f})"
        for s in similar[:3]
    ) if similar else "None"

    prompt = f"""Generate a postmortem for the following incident.

INCIDENT DETAILS:
  Incident ID: {incident_id}
  Service: {service}
  Severity: {severity}
  Message: {message}
  Created: {created_at}
  Resolved: {resolved_at}
  Time to Resolve: {ttr_str}
  Outcome: {outcome}

ROOT CAUSE (from agent analysis):
  {top_hypothesis}

RESOLUTION:
  {resolution}

ACTIONS EXECUTED:
  Successful: {succeeded_steps}
  Failed: {failed_steps}

SIMILAR HISTORICAL INCIDENTS:
  {similar_str}

TIMELINE:
{timeline_str}

Generate a complete postmortem JSON with these fields:
{{
  "incident_id": "{incident_id}",
  "summary": "1-2 sentence summary",
  "timeline": ["timestamp: event 1", "timestamp: event 2"],
  "impact": "description of user/business impact",
  "root_cause": "detailed root cause analysis",
  "root_cause_confidence": 0.0,
  "evidence": ["evidence item 1"],
  "actions_taken": ["action 1", "action 2"],
  "successful_fixes": ["fix that worked"],
  "failed_fixes": ["fix that did not work"],
  "resolution": "how it was ultimately resolved",
  "lessons_learned": ["lesson 1", "lesson 2"],
  "follow_up_actions": ["follow-up 1"],
  "generated_at": "{datetime.now(timezone.utc).isoformat()}"
}}

Only include actions_taken that appear in the ACTIONS EXECUTED section above.
Respond with valid JSON ONLY."""

    return prompt


async def draft_postmortem(incident_id: str) -> dict:
    """
    Generate a structured postmortem for the given incident.

    Gathers incident data, actions and events from the DB.
    Calls the LLM to generate the postmortem.
    Returns a dict – does NOT store it (approval required first).

    Args:
        incident_id: The incident to generate a postmortem for.

    Returns:
        dict with postmortem fields (matches extended Postmortem schema).

    Raises:
        ValueError: if incident_id is not found in the database.
    """
    if not incident_id:
        raise ValueError("incident_id is required")

    # Load incident from DB
    inc_data: dict = {}
    actions: list[dict] = []
    events: list[dict] = []

    try:
        if crud is None:
            raise ImportError("crud module not available")
        inc = crud.get_incident(incident_id)
        if inc is None:
            raise ValueError(f"Incident {incident_id!r} not found")

        # Convert to dict, serialize datetimes
        inc_data = {
            "id": inc.id,
            "service": inc.service,
            "message": inc.message,
            "severity": inc.severity,
            "status": inc.status,
            "top_hypothesis": inc.top_hypothesis,
            "resolution": inc.resolution,
            "outcome": inc.outcome,
            "recommendation_json": inc.recommendation_json,
            "created_at": inc.created_at.isoformat() if inc.created_at else "",
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else "",
            "ttr_seconds": inc.ttr_seconds,
        }

        actions = [
            {"step": a.step, "status": a.status, "output": a.output}
            for a in crud.list_actions(incident_id)
        ]
        events = [
            {"kind": e.kind, "step": e.step, "detail": e.detail, "ts": e.ts.isoformat() if hasattr(e.ts, "isoformat") else str(e.ts)}
            for e in crud.list_events(incident_id)
        ]
    except ValueError:
        raise
    except Exception as e:
        log.warning("Could not load incident %s from DB: %s; generating with minimal context", incident_id, e)
        inc_data = {"id": incident_id, "service": "unknown", "message": "unknown", "severity": "unknown"}

    # Build and call LLM
    prompt = _build_pm_prompt(incident_id, inc_data, actions, events)

    raw = call_llm(
        prompt=prompt,
        system=_PM_SYSTEM_PROMPT,
        expect_json=True,
        cache_key=f"postmortem-{incident_id}",
    )

    # Ensure incident_id is always present and correct
    if isinstance(raw, dict):
        raw["incident_id"] = incident_id
        # Ensure required fields exist
        raw.setdefault("summary", f"Incident {incident_id} on {inc_data.get('service','unknown')} service")
        raw.setdefault("timeline", [e.get("step", "") for e in events[:10]])
        raw.setdefault("impact", "Impact not assessed")
        raw.setdefault("root_cause", inc_data.get("top_hypothesis") or "Unknown")
        raw.setdefault("evidence", [])
        raw.setdefault("actions_taken", [a["step"] for a in actions])
        raw.setdefault("successful_fixes", [a["step"] for a in actions if a.get("status") == "succeeded"])
        raw.setdefault("failed_fixes", [a["step"] for a in actions if a.get("status") == "failed"])
        raw.setdefault("resolution", inc_data.get("resolution") or "")
        raw.setdefault("lessons_learned", [])
        raw.setdefault("follow_up_actions", [])
        raw.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
        raw["_status"] = "draft"
        raw["_approved"] = False
        return raw

    # Fallback if LLM returned unexpected type
    return {
        "incident_id": incident_id,
        "summary": f"[FALLBACK] Incident {incident_id} on {inc_data.get('service','unknown')}",
        "timeline": [],
        "impact": "Not assessed",
        "root_cause": inc_data.get("top_hypothesis") or "Unknown",
        "evidence": [],
        "actions_taken": [a["step"] for a in actions],
        "successful_fixes": [a["step"] for a in actions if a.get("status") == "succeeded"],
        "failed_fixes": [a["step"] for a in actions if a.get("status") == "failed"],
        "resolution": inc_data.get("resolution") or "",
        "lessons_learned": [],
        "follow_up_actions": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "_status": "draft",
        "_approved": False,
    }


async def approve_postmortem(incident_id: str, postmortem: dict) -> str:
    """
    Approve and retain a postmortem to long-term memory.

    This is the retain-after-approval step.  The postmortem is only stored
    once explicitly approved by a human.

    Args:
        incident_id: The incident this postmortem belongs to.
        postmortem:  The postmortem dict (as returned by draft_postmortem).

    Returns:
        Confirmation string from memory.service.retain_postmortem.
    """
    if not incident_id:
        raise ValueError("incident_id is required")

    postmortem = dict(postmortem)
    postmortem["incident_id"] = incident_id
    postmortem["_approved"] = True
    postmortem["_approved_at"] = datetime.now(timezone.utc).isoformat()

    try:
        if retain_postmortem is None:
            raise ImportError("retain_postmortem not available")
        result = await retain_postmortem(postmortem)
        log.info("Postmortem for %s approved and retained: %s", incident_id, result)

        # Also update the incident audit log
        try:
            if crud is not None:
                crud.add_audit(incident_id, "system", "postmortem_retained", {"result": result})
        except Exception:
            pass

        return result
    except Exception as e:
        log.error("Failed to retain postmortem for %s: %s", incident_id, e)
        raise
