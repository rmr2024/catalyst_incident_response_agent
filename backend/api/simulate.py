"""
Simulator API routes.

Two routes only (P2 owns /incidents/{id}/simulate):
  GET  /simulate/scenarios          list available scenarios
  POST /simulate/{scenario_id}      trigger a scenario
"""
from __future__ import annotations

import inspect
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

log = logging.getLogger("simulate")

router = APIRouter(prefix="/simulate", tags=["simulate"])


def _load_tools():
    """Lazy import tools to avoid import errors if tools/ isn't ready yet."""
    try:
        import tools  # noqa: PLC0415
        return tools
    except Exception as exc:
        log.warning("tools not available: %s", exc)
        return None


def _load_scenarios() -> list[dict]:
    """Load scenarios from tools state module or fall back to empty list."""
    try:
        from tools.state import _scenarios  # noqa: PLC0415
        return _scenarios()
    except Exception as exc:
        log.warning("could not load scenarios: %s", exc)
        return []


def _load_ingest():
    """Lazy import ingest_alert from core.intake."""
    try:
        from core.intake import ingest_alert  # noqa: PLC0415
        return ingest_alert
    except Exception as exc:
        log.warning("ingest_alert not available: %s", exc)
        return None


@router.get("/scenarios", summary="List all simulation scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    """Return a summary list of available simulation scenarios."""
    scenarios = _load_scenarios()
    return [
        {
            "id":               s.get("id"),
            "title":            s.get("title"),
            "service":          s.get("service"),
            "description":      s.get("description"),
            "expected_runbook": s.get("expected_runbook"),
            "is_novel":         s.get("is_novel", False),
        }
        for s in scenarios
    ]


@router.post("/{scenario_id}", summary="Trigger a scenario and start investigation")
async def run_scenario(scenario_id: str) -> dict[str, Any]:
    """
    Activate *scenario_id*, build an Alert from its template, and ingest it.

    Steps:
    1. Look up the scenario.
    2. Call tools.set_active_scenario so the context layer serves scenario data.
    3. Build a schemas.Alert from the alert_template (timestamp = now UTC).
    4. Call ingest_alert(alert, source="simulator").
    5. Return {scenario_id, incident_id, alert}.
    """
    scenarios = _load_scenarios()
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")

    service = scenario.get("service", "")

    # 1 — activate scenario so tools layer returns scenario context
    tools = _load_tools()
    if tools:
        try:
            tools.set_active_scenario(service, scenario_id)
        except Exception as exc:
            log.warning("set_active_scenario failed: %s", exc)

    # 2 — build Alert from template
    try:
        from schemas import Alert  # noqa: PLC0415
        tmpl: dict = dict(scenario.get("alert_template", {}))
        tmpl["timestamp"] = datetime.now(timezone.utc)
        # severity may be null in template
        if tmpl.get("severity") is None:
            tmpl.pop("severity", None)
        # metrics may be missing
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

    # 3 — ingest alert
    ingest_alert = _load_ingest()
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
        log.warning("ingest_alert not available; returning alert without incident_id")

    return {
        "scenario_id": scenario_id,
        "incident_id": incident_id,
        "alert": alert.model_dump(),
    }
