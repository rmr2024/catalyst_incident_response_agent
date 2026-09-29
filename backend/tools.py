"""
tools.py
--------
Simulated operational tools for the Incident Response Agent.

These tools simulate interactions with infrastructure.
In a real deployment, they would call actual services.
For the hackathon, they simulate actions and verify results.

Exports:
  execute_action(step, service) -> dict
  check_metrics(service)        -> dict

All actions are simulated and do NOT affect real infrastructure.
Destructive actions (restart, rollback, etc.) require prior approval
through the incident approval workflow.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re

log = logging.getLogger("tools")

# Patterns for different action types
_RESTART_RE = re.compile(r"restart|reboot|cycle", re.I)
_ROLLBACK_RE = re.compile(r"rollback|roll back|revert", re.I)
_SCALE_RE = re.compile(r"scale|increase|pool size", re.I)
_FAILOVER_RE = re.compile(r"failover|fail over|switch over", re.I)
_CHECK_RE = re.compile(r"check|inspect|verify|monitor|gather|watch|look", re.I)
_FLUSH_RE = re.compile(r"flush|clear|purge|drain", re.I)
_PAGE_RE = re.compile(r"page|alert|notify|escalate", re.I)

# Services with simulated metric profiles
_METRIC_PROFILES: dict[str, dict] = {
    "payments-db": {
        "healthy": {"error_rate": 0.001, "latency_p99_ms": 120, "connection_pool_usage": 0.3},
        "degraded": {"error_rate": 0.15, "latency_p99_ms": 3400, "connection_pool_usage": 0.98},
    },
    "auth": {
        "healthy": {"error_rate": 0.0, "auth_failure_rate": 0.01, "token_validation_ms": 45},
        "degraded": {"error_rate": 0.3, "auth_failure_rate": 0.8, "token_validation_ms": 2000},
    },
    "checkout": {
        "healthy": {"error_rate": 0.002, "db_write_ms": 50, "cart_success_rate": 0.99},
        "degraded": {"error_rate": 0.2, "db_write_ms": 5000, "cart_success_rate": 0.1},
    },
    "api-gateway": {
        "healthy": {"error_rate": 0.001, "upstream_timeout_rate": 0.0, "rps": 1200},
        "degraded": {"error_rate": 0.25, "upstream_timeout_rate": 0.4, "rps": 300},
    },
}

_DEFAULT_HEALTHY = {"error_rate": 0.005, "latency_p99_ms": 200, "availability": 0.999}
_DEFAULT_DEGRADED = {"error_rate": 0.1, "latency_p99_ms": 2000, "availability": 0.85}

# Simulate slow recovery after fix
_service_state: dict[str, str] = {}  # service -> "healthy" | "degraded"


async def execute_action(step: str, service: str) -> dict:
    """
    Simulate executing an action step.

    Returns:
        {"ok": bool, "output": str}

    "[fail]" in step forces a simulated failure (for testing).
    All actions are simulated – no real infrastructure is affected.
    """
    step_lower = (step or "").lower()
    svc = (service or "unknown").lower()

    # Force failure flag (for testing)
    if "[fail]" in step_lower:
        await asyncio.sleep(0.3)
        return {"ok": False, "output": f"[SIMULATED FAILURE] {step}"}

    # Simulate action latency
    await asyncio.sleep(random.uniform(0.2, 0.8))

    if _RESTART_RE.search(step):
        _service_state[svc] = "healthy"
        return {
            "ok": True,
            "output": f"[SIMULATED] Restarted {service}. Connection pool reset. "
                      f"New pool size: 20 connections.",
        }

    if _ROLLBACK_RE.search(step):
        _service_state[svc] = "healthy"
        return {
            "ok": True,
            "output": f"[SIMULATED] Rolled back {service} to previous stable version. "
                      f"Traffic shifting to previous build.",
        }

    if _SCALE_RE.search(step):
        return {
            "ok": True,
            "output": f"[SIMULATED] Scaled {service}. "
                      f"Connection pool increased. Current utilization: 45%.",
        }

    if _FAILOVER_RE.search(step):
        _service_state[svc] = "healthy"
        return {
            "ok": True,
            "output": f"[SIMULATED] Failover initiated for {service}. "
                      f"Traffic redirected to secondary region.",
        }

    if _FLUSH_RE.search(step):
        return {
            "ok": True,
            "output": f"[SIMULATED] Cache/queue flushed for {service}. "
                      f"Backlog cleared.",
        }

    if _PAGE_RE.search(step):
        return {
            "ok": True,
            "output": f"[SIMULATED] On-call engineer paged for {service}. "
                      f"PagerDuty incident created.",
        }

    if _CHECK_RE.search(step):
        metrics = await check_metrics(service)
        return {
            "ok": True,
            "output": f"[SIMULATED] Metrics gathered for {service}: {metrics.get('note', str(metrics))}",
        }

    # Generic action
    return {
        "ok": True,
        "output": f"[SIMULATED] Executed: {step} (service={service}). No errors.",
    }


async def check_metrics(service: str) -> dict:
    """
    Simulate checking service health metrics.

    Returns a dict with health status and representative metrics.
    In a real deployment, this would query Prometheus/Datadog/etc.
    """
    await asyncio.sleep(0.1)
    svc = (service or "unknown").lower()
    state = _service_state.get(svc, "degraded")

    profile = _METRIC_PROFILES.get(svc, {})
    if profile:
        metrics = profile.get(state, profile.get("healthy", _DEFAULT_HEALTHY))
    else:
        metrics = _DEFAULT_HEALTHY if state == "healthy" else _DEFAULT_DEGRADED

    healthy = metrics.get("error_rate", 0) < 0.05
    note = (
        f"[SIMULATED] {service} appears {'healthy' if healthy else 'degraded'}. "
        f"Metrics: {', '.join(f'{k}={v}' for k, v in metrics.items())}"
    )
    return {"healthy": healthy, "metrics": metrics, "note": note}
