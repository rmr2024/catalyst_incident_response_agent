"""
Simulated resolution verification.

check_metrics inspects which actions have been executed for a service against
the active scenario's expected outcomes and returns a structured verdict.
"""
from __future__ import annotations

import copy
from typing import Any

from . import state as _state_mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _midpoint(a: float, b: float) -> float:
    return round((a + b) / 2, 4)


def _blend_metrics(baseline: dict, peak: dict) -> dict:
    """Return metrics halfway between baseline and peak."""
    return {
        k: _midpoint(baseline.get(k, 0), peak.get(k, 0))
        for k in peak
    }


# ---------------------------------------------------------------------------
# Public verification function
# ---------------------------------------------------------------------------

def check_metrics(service: str) -> dict[str, Any]:
    """
    Return a simulated verification result for *service*.

    With an active scenario:
    - any harmful action executed           → worsened
    - all required actions executed         → resolved  (metrics = baseline)
    - some required or only partial actions → partial   (metrics midway)
    - nothing relevant executed             → not_resolved (metrics = peak)

    With no active scenario:
    - any recognised action executed        → resolved (generic note)
    - nothing executed                      → not_resolved

    Returns:
        {
          "service": str,
          "status": "resolved" | "partial" | "not_resolved" | "worsened",
          "resolved": bool,
          "error_rate": float,
          "p95_latency_ms": int,
          "note": str,          # non-empty readable sentence shown to users
        }
    """
    scenario = _state_mod.get_active_scenario(service)
    executed = set(_state_mod.executed_actions(service))

    if scenario is None:
        # No active scenario — use generic heuristic
        if executed:
            return {
                "service": service,
                "status": "resolved",
                "resolved": True,
                "error_rate": 0.01,
                "p95_latency_ms": 200,
                "note": (
                    f"Metrics for {service} have returned to normal levels after the "
                    f"executed actions ({', '.join(sorted(executed))})."
                ),
            }
        return {
            "service": service,
            "status": "not_resolved",
            "resolved": False,
            "error_rate": 0.25,
            "p95_latency_ms": 4000,
            "note": (
                f"No actions have been executed for {service}. Metrics remain elevated "
                f"and the incident is not yet resolved."
            ),
        }

    # Extract outcome sets from scenario
    outcomes = scenario.get("outcomes", {})
    required:  set[str] = set(outcomes.get("required_actions", []))
    partial_ok: set[str] = set(outcomes.get("partial_actions", []))
    harmful:    set[str] = set(outcomes.get("harmful_actions", []))

    ctx        = scenario.get("context", {})
    m_ctx      = ctx.get("metrics", {})
    baseline   = m_ctx.get("baseline", {"error_rate": 0.01, "p95_latency_ms": 200})
    peak       = m_ctx.get("peak",     {"error_rate": 0.30, "p95_latency_ms": 5000})

    b_err      = baseline.get("error_rate", 0.01)
    b_lat      = baseline.get("p95_latency_ms", 200)
    p_err      = peak.get("error_rate", 0.30)
    p_lat      = peak.get("p95_latency_ms", 5000)

    # 1 — harmful actions trump everything
    triggered_harmful = executed & harmful
    if triggered_harmful:
        worse_err = min(1.0, p_err * 1.5)
        worse_lat = int(p_lat * 1.4)
        return {
            "service": service,
            "status": "worsened",
            "resolved": False,
            "error_rate": round(worse_err, 4),
            "p95_latency_ms": worse_lat,
            "note": (
                f"Conditions for {service} have worsened after executing "
                f"{', '.join(sorted(triggered_harmful))}. "
                f"Error rate is now {round(worse_err * 100, 1)}% and p95 latency is "
                f"{worse_lat} ms. Revert the harmful action immediately."
            ),
        }

    # 2 — check required coverage
    if required and required.issubset(executed):
        return {
            "service": service,
            "status": "resolved",
            "resolved": True,
            "error_rate": b_err,
            "p95_latency_ms": int(b_lat),
            "note": (
                f"All required actions for {service} have been executed successfully. "
                f"Error rate has dropped to {round(b_err * 100, 1)}% and p95 latency "
                f"is back to {int(b_lat)} ms."
            ),
        }

    # 3 — partial: some required done, or only partial_ok actions executed
    executed_required = executed & required
    executed_partial  = executed & partial_ok
    missing_required  = required - executed

    if executed_required or executed_partial:
        mid_err = round(_midpoint(b_err, p_err), 4)
        mid_lat = int(_midpoint(b_lat, p_lat))
        missing_str = ", ".join(sorted(missing_required)) if missing_required else "none"
        return {
            "service": service,
            "status": "partial",
            "resolved": False,
            "error_rate": mid_err,
            "p95_latency_ms": mid_lat,
            "note": (
                f"{service} is partially recovered: error rate is {round(mid_err * 100, 1)}% "
                f"and p95 latency is {mid_lat} ms, but the incident is likely to recur. "
                f"Still required: {missing_str}."
            ),
        }

    # 4 — nothing relevant executed
    return {
        "service": service,
        "status": "not_resolved",
        "resolved": False,
        "error_rate": p_err,
        "p95_latency_ms": int(p_lat),
        "note": (
            f"No relevant actions have been applied to {service}. "
            f"Error rate remains at {round(p_err * 100, 1)}% and p95 latency is "
            f"{int(p_lat)} ms. The required actions are: {', '.join(sorted(required))}."
        ),
    }
