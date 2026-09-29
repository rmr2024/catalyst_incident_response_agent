"""
tools — simulated operational tools for the Incident Response Agent.

Public surface (contracts used by P1 and P2):
  execute_action(step, service)  -> {"ok": bool, "output": str}
  check_metrics(service)         -> dict with "note": str
  gather_context(service, ts)    -> dict
  get_logs(service, ts, limit)   -> list
  get_metrics(service, ts)       -> dict
  get_deployments(service, ts)   -> list
  get_service_info(service)      -> dict
  list_tools()                   -> list
  set_active_scenario(service, scenario_id) -> None
  reset()                        -> None
"""
from .actions import execute_action, list_tools
from .context import (
    gather_context,
    get_deployments,
    get_logs,
    get_metrics,
    get_service_info,
)
from .state import reset, set_active_scenario
from .verify import check_metrics

__all__ = [
    "execute_action",
    "check_metrics",
    "gather_context",
    "get_logs",
    "get_metrics",
    "get_deployments",
    "get_service_info",
    "list_tools",
    "set_active_scenario",
    "reset",
]
