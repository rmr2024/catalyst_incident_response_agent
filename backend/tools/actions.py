"""
Simulated action execution layer.

Maps free-text remediation step descriptions to known action IDs via
case-insensitive keyword matching, then simulates each matched action
and records it in the scenario state.

Nothing here makes real system calls.
"""
from __future__ import annotations

import re
from typing import Any

from . import state as _state_mod

# ---------------------------------------------------------------------------
# Action registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, dict[str, Any]] = {
    "restart_service": {
        "description": "Restart all pods of the service to recover from transient failures.",
        "risky": True,
    },
    "rollback_deployment": {
        "description": "Roll back the service to the previous known-good release.",
        "risky": True,
    },
    "increase_db_pool": {
        "description": "Increase the database connection pool size to relieve pool exhaustion.",
        "risky": False,
    },
    "scale_out": {
        "description": "Add more replicas of the service to distribute load.",
        "risky": False,
    },
    "clear_cache": {
        "description": "Flush or invalidate the cache for the service.",
        "risky": True,
    },
    "enable_request_coalescing": {
        "description": "Enable single-flight request coalescing to prevent cache stampedes.",
        "risky": False,
    },
    "warm_cache": {
        "description": "Pre-load hot cache keys to prevent cold-start stampedes.",
        "risky": False,
    },
    "sync_clock": {
        "description": "Synchronise system time across nodes to fix clock-drift issues.",
        "risky": False,
    },
}

# ---------------------------------------------------------------------------
# Keyword → action mapping (checked in order; first match wins per keyword group)
# Each tuple: (compiled_regex, action_id)
# Order matters: more specific patterns come first.
# ---------------------------------------------------------------------------

_KEYWORD_MAP: list[tuple[re.Pattern, str]] = [
    # cache operations — most specific first
    (re.compile(r"clear|flush|purge|invalidate\s+cache", re.I), "clear_cache"),
    (re.compile(r"warm|prime|preload|pre-load", re.I),          "warm_cache"),
    (re.compile(r"coalesc|single.?flight|singleflight|request collapsi", re.I), "enable_request_coalescing"),
    # deployment
    (re.compile(r"roll.?back|revert", re.I),                    "rollback_deployment"),
    # database pool
    (re.compile(r"connection pool|pool size|pool capacity", re.I), "increase_db_pool"),
    # scaling
    (re.compile(r"scale out|scale up|add replicas|add instances|autoscal", re.I), "scale_out"),
    # clock sync
    (re.compile(r"ntp|clock|time sync|chrony|sync.{0,10}time", re.I), "sync_clock"),
    # restart — intentionally last so rollback takes priority over "restart after rollback"
    (re.compile(r"restart|reboot|bounce|recycle", re.I),        "restart_service"),
]


def _match_action_ids(step: str) -> list[str]:
    """
    Return all action IDs that match keywords in *step*.

    A single step may match multiple actions (e.g. "Increase pool capacity and restart").
    """
    matched: list[str] = []
    for pattern, action_id in _KEYWORD_MAP:
        if pattern.search(step) and action_id not in matched:
            matched.append(action_id)
    return matched


def execute_action(step: str, service: str) -> dict[str, Any]:
    """
    Simulate executing a remediation *step* against *service*.

    Matches *step* to known action IDs by keyword, records each matched action
    in the scenario state, and returns a result dict.

    Returns:
        {"ok": bool, "output": str}

    Never raises.
    """
    try:
        action_ids = _match_action_ids(step)
        if not action_ids:
            return {
                "ok": True,
                "output": "No simulated executor for this step; treated as a manual step.",
            }
        outputs: list[str] = []
        for action_id in action_ids:
            _state_mod.record_action(service, action_id)
            desc = _REGISTRY.get(action_id, {}).get("description", action_id)
            outputs.append(_format_output(action_id, service))
        return {"ok": True, "output": "; ".join(outputs)}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "output": f"Simulation error: {exc}"}


def _format_output(action_id: str, service: str) -> str:
    """Return a human-readable simulation output for *action_id* on *service*."""
    templates: dict[str, str] = {
        "restart_service":           f"Simulated: restarted 3 pods of {service}",
        "rollback_deployment":       f"Simulated: rolled back {service} to previous release",
        "increase_db_pool":          f"Simulated: increased database connection pool size to 100 for {service}",
        "scale_out":                 f"Simulated: scaled out {service} by 2 additional replicas",
        "clear_cache":               f"Simulated: flushed cache for {service}",
        "enable_request_coalescing": f"Simulated: enabled single-flight request coalescing on hot keys for {service}",
        "warm_cache":                f"Simulated: pre-loaded top 100 hot keys into cache for {service}",
        "sync_clock":                f"Simulated: synchronised system clocks across all {service} nodes via chrony",
    }
    return templates.get(action_id, f"Simulated: executed {action_id} on {service}")


def list_tools() -> list[dict[str, Any]]:
    """Return a description of all registered actions."""
    return [
        {"id": action_id, "description": meta["description"], "risky": meta["risky"]}
        for action_id, meta in _REGISTRY.items()
    ]
