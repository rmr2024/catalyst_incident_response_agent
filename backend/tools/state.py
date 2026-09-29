"""
Scenario activation state for the simulation layer.

Keyed by service name so multiple services can have independent active scenarios.
All state is in-process; reset() clears everything.
"""
from __future__ import annotations

import json
import os
import pathlib
from typing import Any

# _state[service] = {"scenario": dict | None, "executed": list[str]}
_state: dict[str, dict[str, Any]] = {}

_DATA_DIR = pathlib.Path(os.environ.get("DATA_DIR", pathlib.Path(__file__).resolve().parents[2] / "data"))


def _load_scenarios() -> list[dict]:
    """Lazy-load scenarios.json; return empty list if missing."""
    path = _DATA_DIR / "scenarios.json"
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


_scenarios_cache: list[dict] | None = None


def _scenarios() -> list[dict]:
    """Return scenarios, loading from disk on first call."""
    global _scenarios_cache
    if _scenarios_cache is None:
        _scenarios_cache = _load_scenarios()
    return _scenarios_cache


def set_active_scenario(service: str, scenario_id: str) -> None:
    """Activate a scenario for *service* and clear its executed-action log."""
    scenario = next((s for s in _scenarios() if s["id"] == scenario_id), None)
    _state[service] = {"scenario": scenario, "executed": []}


def get_active_scenario(service: str) -> dict | None:
    """Return the active scenario dict for *service*, or None."""
    entry = _state.get(service)
    if entry is None:
        return None
    return entry.get("scenario")


def record_action(service: str, action_id: str) -> None:
    """Record that *action_id* was executed for *service*."""
    entry = _state.setdefault(service, {"scenario": None, "executed": []})
    if action_id not in entry["executed"]:
        entry["executed"].append(action_id)


def executed_actions(service: str) -> list[str]:
    """Return the list of action IDs already executed for *service*."""
    entry = _state.get(service)
    if entry is None:
        return []
    return list(entry.get("executed", []))


def reset() -> None:
    """Clear all scenario state (used by tests and the admin reset endpoint)."""
    global _scenarios_cache
    _state.clear()
    _scenarios_cache = None
