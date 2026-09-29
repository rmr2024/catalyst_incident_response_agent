"""
Simulator API routes.

  GET  /simulate/scenarios              list available scenarios
  POST /simulate/{scenario_id}          trigger a scenario (ingest alert + start investigation)
  POST /incidents/{id}/simulate         execute the approved action plan for an incident
"""
from __future__ import annotations

import inspect
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

log = logging.getLogger("simulate")

# Single router loaded by main.py as api.simulate.router.
# No shared prefix so we can host both /simulate/* and /incidents/{id}/simulate.
router = APIRouter(tags=["simulate"])


# ---------------------------------------------------------------------------
# Lazy helpers - keep startup safe if P1/P3 modules are not yet ready
# ---------------------------------------------------------------------------

def _tools():
    """Lazy-import tools package."""
    try:
        import tools  # noqa: PLC0415
        return tools
    except Exception as exc:
        log.warning("tools not available: %s", exc)
        return None


def _get_scenarios() -> list[dict]:
    """Load scenarios from tools.state, fall back to empty list."""
    try:
        from tools.state import _scenarios  # noqa: PLC0415
        return _scenarios()
    except Exception as exc:
        log.warning("could not load scenarios: %s", exc)
        return []


def _get_ingest():
    """Lazy-import ingest_alert from core.intake."""
    try:
        from core.intake import ingest_alert  # noqa: PLC0415
        return ingest_alert
    except Exception as exc:
        log.warning("ingest_alert not available: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Scenario routes  (P3 deliverable)
# ---------------------------------------------------------------------------

@router.get("/simulate/scenarios", summary="List all simulation scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    """Return a summary list of available simulation scenarios."""
    return [
        {
            "id":               s.get("id"),
            "title":            s.get("title"),
            "service":          s.get("service"),
            "description":      s.get("description"),
            "expected_runbook": s.get("expected_runbook"),
            "is_novel":         s.get("is_novel", False),
        }
        for s in _get_scenarios()
    ]


@router.post("/simulate/{scenario_id}", summary="Trigger a scenario and start investigation")
async def run_scenario(scenario_id: str) -> dict[str, Any]:
    """
    Activate *scenario_id*, build an Alert from its template, and ingest it.

    Steps
    -----
    1. Look up the scenario by ID (404 if not found).
    2. Call tools.set_active_scenario so context layer returns scenario data.
    3. Build schemas.Alert from alert_template with timestamp = now UTC.
    4. Call ingest_alert(alert, source='simulator') - starts investigation async.
    5. Return {scenario_id, incident_id, alert}.
    """
    scenarios = _get_scenarios()
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")

    service = scenario.get("service", "")

    # Step 1 - activate scenario so tools returns scenario-specific context
    t = _tools()
    if t:
        try:
            t.set_active_scenario(service, scenario_id)
        except Exception as exc:
            log.warning("set_active_scenario failed: %s", exc)

    # Step 2 - build Alert from the scenario alert_template
    try:
        from schemas import Alert  # noqa: PLC0415
        tmpl: dict = dict(scenario.get("alert_template", {}))
        tmpl["timestamp"] = datetime.now(timezone.utc)
        if tmpl.get("severity") is None:
            tmpl.pop("severity", None)
        tmpl.setdefault("metrics", {})
        alert = Alert(
            service=tmpl.get("service", service),
            message=tmpl.get("message", scenario.get("description", "")),
            severity=tmpl.get("severity"),
            metrics=tmpl.get("metrics", {}),
            timestamp=tmpl["timestamp"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build alert: {exc}") from exc

    # Step 3 - ingest alert; investigation spawns as background task
    ingest_alert = _get_ingest()
    incident_id: str | None = None
    if ingest_alert:
        try:
            result = ingest_alert(alert, source="simulator")
            if inspect.isawaitable(result):
                result = await result
            # extract incident_id defensively
            if isinstance(result, dict):
                incident_id = str(result.get("incident_id") or result.get("id") or "")
            elif hasattr(result, "incident_id"):
                incident_id = str(result.incident_id)
            elif hasattr(result, "id"):
                incident_id = str(result.id)
            else:
                incident_id = str(result)
        except Exception as exc:
            log.error("ingest_alert failed for scenario %s: %s", scenario_id, exc)
            return {
                "scenario_id": scenario_id,
                "incident_id": None,
                "alert": alert.model_dump(),
                "error": str(exc),
            }
    else:
        log.warning("ingest_alert unavailable; returning alert without incident_id")

    return {
        "scenario_id": scenario_id,
        "incident_id": incident_id,
        "alert": alert.model_dump(),
    }


# ---------------------------------------------------------------------------
# Incident simulation route  (P2 contract)
# ---------------------------------------------------------------------------

@router.post(
    "/incidents/{incident_id}/simulate",
    summary="Execute the approved remediation plan for an incident",
)
async def simulate_incident(incident_id: str) -> dict[str, Any]:
    """
    Execute the approved remediation plan for *incident_id*.

    - Incident must be in status: recommended, awaiting_approval, fix_failed, or mitigated.
    - Risky actions (needs_approval=True) require prior acceptance via
      POST /incidents/{id}/feedback before this endpoint allows execution.
    - Delegates to core.execution.execute_plan which iterates each action via
      tools.execute_action and verifies the outcome via tools.check_metrics.
    - Returns immediately with {"incident_id", "status": "executing"}.
      Live updates stream via GET /incidents/{id}/events (SSE).
    """
    try:
        from core.execution import execute_plan  # noqa: PLC0415
        from core.intake import spawn  # noqa: PLC0415
        from db import crud  # noqa: PLC0415
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Backend modules not ready: {exc}",
        ) from exc

    inc = crud.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="incident not found")

    simulatable = {"recommended", "awaiting_approval", "fix_failed", "mitigated"}
    if inc.status not in simulatable:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot simulate while status is '{inc.status}'. "
                f"Expected one of: {sorted(simulatable)}."
            ),
        )

    # Risky actions need human approval before execution
    if inc.status == "awaiting_approval" and inc.suggestion_verdict not in (
        "accepted",
        "edited",
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Risky actions require approval first. "
                "POST /incidents/{id}/feedback with action='accept' or 'edit'."
            ),
        )

    spawn(execute_plan(incident_id))
    return {"incident_id": incident_id, "status": "executing"}
