"""
Simulated operational context: logs, metrics, deployments, service info.

All data is deterministic. If a scenario is active for the requested service
the context is derived from scenario data; otherwise a healthy baseline is returned.
Nothing here makes real network or file-system calls beyond the scenarios.json load.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from . import state as _state_mod

# ---------------------------------------------------------------------------
# Healthy baseline definitions per service
# ---------------------------------------------------------------------------

_BASELINE_METRICS: dict[str, dict] = {
    "checkout-api":       {"error_rate": 0.01, "p95_latency_ms": 210, "affected_users_pct": 1, "requests_per_min": 3200},
    "payment-service":    {"error_rate": 0.01, "p95_latency_ms": 220, "affected_users_pct": 1, "requests_per_min": 2400},
    "auth-service":       {"error_rate": 0.01, "p95_latency_ms": 85,  "affected_users_pct": 1, "requests_per_min": 5100},
    "inventory-service":  {"error_rate": 0.01, "p95_latency_ms": 130, "affected_users_pct": 1, "requests_per_min": 6400},
    "search-service":     {"error_rate": 0.01, "p95_latency_ms": 180, "affected_users_pct": 1, "requests_per_min": 8100},
    "order-service":      {"error_rate": 0.01, "p95_latency_ms": 170, "affected_users_pct": 1, "requests_per_min": 4100},
    "notification-service": {"error_rate": 0.005, "p95_latency_ms": 95, "affected_users_pct": 0, "requests_per_min": 1200},
}

_BASELINE_LOGS: dict[str, list[dict]] = {
    svc: [
        {"offset_sec": -120, "level": "INFO", "line": f"{svc} started ok"},
        {"offset_sec": -60,  "level": "INFO", "line": f"{svc} health check passed"},
        {"offset_sec": 0,    "level": "INFO", "line": f"{svc} all systems normal"},
    ]
    for svc in _BASELINE_METRICS
}

_BASELINE_DEPLOYMENTS: dict[str, list[dict]] = {
    "checkout-api":       [{"version": "v5.1.2", "minutes_before_alert": 4320, "author": "ci-bot", "summary": "Routine maintenance release"}],
    "payment-service":    [{"version": "v4.5.3", "minutes_before_alert": 4320, "author": "ci-bot", "summary": "Routine maintenance release"}],
    "auth-service":       [{"version": "v2.4.3", "minutes_before_alert": 10080, "author": "auth-team", "summary": "No recent deployments"}],
    "inventory-service":  [{"version": "v2.8.4", "minutes_before_alert": 8640, "author": "ci-bot", "summary": "Routine maintenance release"}],
    "search-service":     [{"version": "v3.2.9", "minutes_before_alert": 4500, "author": "ci-bot", "summary": "Dependency updates"}],
    "order-service":      [{"version": "v1.9.1", "minutes_before_alert": 2880, "author": "ci-bot", "summary": "Routine maintenance release"}],
    "notification-service": [{"version": "v1.4.2", "minutes_before_alert": 1440, "author": "ci-bot", "summary": "Routine maintenance release"}],
}

_SERVICE_INFO: dict[str, dict] = {
    "checkout-api":       {"owner": "checkout-team", "tier": 1, "language": "Java", "replicas": 4, "db": "postgres"},
    "payment-service":    {"owner": "payments-team", "tier": 1, "language": "Java", "replicas": 6, "db": "postgres"},
    "auth-service":       {"owner": "auth-team",     "tier": 1, "language": "Go",   "replicas": 3, "db": "postgres"},
    "inventory-service":  {"owner": "inventory-team","tier": 2, "language": "Python","replicas": 4, "db": "postgres"},
    "search-service":     {"owner": "search-team",   "tier": 2, "language": "Go",   "replicas": 6, "db": "elasticsearch"},
    "order-service":      {"owner": "orders-team",   "tier": 1, "language": "Java", "replicas": 4, "db": "postgres"},
    "notification-service": {"owner": "infra-team",  "tier": 3, "language": "Python","replicas": 2, "db": "none"},
}

_UNKNOWN_SERVICE: dict[str, Any] = {
    "owner": "unknown", "tier": 3, "language": "unknown", "replicas": 1, "db": "unknown"
}


def _default_metrics(service: str) -> dict:
    return copy.deepcopy(_BASELINE_METRICS.get(service, {"error_rate": 0.01, "p95_latency_ms": 200, "affected_users_pct": 1, "requests_per_min": 1000}))


def _ts(ts: datetime | None = None) -> str:
    """Return an ISO timestamp string."""
    return (ts or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Public context functions
# ---------------------------------------------------------------------------

def get_logs(service: str, ts: datetime | None = None, limit: int = 20) -> list[dict]:
    """
    Return simulated log lines for *service*.

    Uses the active scenario's log lines if available, otherwise returns a
    healthy baseline. Results are capped at *limit*.
    """
    scenario = _state_mod.get_active_scenario(service)
    if scenario:
        logs = scenario.get("context", {}).get("logs", [])
        return logs[:limit]
    return _BASELINE_LOGS.get(service, _BASELINE_LOGS.get("checkout-api", []))[:limit]


def get_metrics(service: str, ts: datetime | None = None) -> dict:
    """
    Return simulated current metrics for *service*.

    Uses the active scenario's peak metrics if available, otherwise returns
    the healthy baseline.
    """
    scenario = _state_mod.get_active_scenario(service)
    if scenario:
        ctx = scenario.get("context", {})
        peak = ctx.get("metrics", {}).get("peak")
        if peak:
            return copy.deepcopy(peak)
    return _default_metrics(service)


def get_deployments(service: str, ts: datetime | None = None) -> list[dict]:
    """
    Return recent simulated deployment records for *service*.

    Uses the active scenario's deployment list if available, otherwise returns
    a healthy-baseline deployment list.
    """
    scenario = _state_mod.get_active_scenario(service)
    if scenario:
        deployments = scenario.get("context", {}).get("deployments", [])
        if deployments:
            return deployments
    return _BASELINE_DEPLOYMENTS.get(service, [])


def get_service_info(service: str) -> dict:
    """Return static service metadata for *service*."""
    return copy.deepcopy(_SERVICE_INFO.get(service, _UNKNOWN_SERVICE))


def gather_context(service: str, ts: datetime | None = None) -> dict:
    """
    Return a combined context dict with logs, metrics, deployments, and service info.

    This is the primary function used by the agent to collect operational context.
    """
    return {
        "logs": get_logs(service, ts),
        "metrics": get_metrics(service, ts),
        "deployments": get_deployments(service, ts),
        "service_info": get_service_info(service),
    }
