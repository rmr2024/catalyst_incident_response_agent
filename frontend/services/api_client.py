"""
Centralized Python API Client for Incident Response Agent.
Handles communication between Streamlit UI and the FastAPI backend.
The Streamlit UI NEVER makes raw HTTP requests directly; all interactions go through this client.

Configuration:
- BACKEND_URL: Base URL of the backend (default: http://localhost:8000)
- USE_MOCKS: If true, forces fallback mock data (default: false)
"""

import os
from typing import Any, Dict, List, Optional
import httpx

from mocks.mock_data import (
    MOCK_ACTIVE_INCIDENT,
    MOCK_DEMO_ALERT,
    MOCK_INCIDENTS,
    MOCK_SIMULATION_SCENARIOS,
    MOCK_STATS,
    MOCK_TIMELINE_EVENTS,
)
from types import (
    Alert,
    Incident,
    IncidentStats,
    MemoryState,
    SimulationResponse,
    SimulationScenario,
    TimelineEvent,
)


def get_backend_url() -> str:
    """Read backend URL from BACKEND_URL with safe local default."""
    return (
        os.environ.get("BACKEND_URL")
        or os.environ.get("API_URL")
        or os.environ.get("VITE_API_URL")
        or "http://localhost:8000"
    ).rstrip("/")


def is_mock_mode_forced() -> bool:
    """Check if mock mode is forced via USE_MOCKS environment variable."""
    val = (os.environ.get("USE_MOCKS") or os.environ.get("VITE_USE_MOCKS") or "").lower()
    return val in ("true", "1", "yes")


# Centralized API Endpoints
API_ENDPOINTS = {
    "HEALTH": "/health",
    "ALERTS": "/alerts",
    "ALERT_DEMO": "/alerts/demo",
    "INCIDENTS": "/incidents",
    "INCIDENT_BY_ID": lambda id: f"/incidents/{id}",
    "INCIDENT_STATS": "/incidents/stats",
    "INCIDENT_TIMELINE": lambda id: f"/incidents/{id}/timeline",
    "INCIDENT_SIMULATE": lambda id: f"/incidents/{id}/simulate",
    "RESET_SIMULATION": "/reset",
    "SETTINGS_MEMORY": "/settings/memory",
}


class ApiClient:
    """
    Robust HTTP client for FastAPI backend with automatic graceful fallback
    to clean typed mock objects on connection errors, timeouts, or invalid responses.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        force_mocks: Optional[bool] = None,
        timeout: float = 8.0,
    ):
        self.base_url = (base_url or get_backend_url()).rstrip("/")
        self.force_mocks = force_mocks if force_mocks is not None else is_mock_mode_forced()
        self.timeout = timeout
        self._last_error: Optional[str] = None
        self._is_live: Optional[bool] = None

    def check_health(self) -> Dict[str, Any]:
        """Check if FastAPI backend is healthy and responding."""
        if self.force_mocks:
            return {"ok": False, "memory": True, "mode": "forced_mock"}

        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}{API_ENDPOINTS['HEALTH']}")
                if res.status_code == 200:
                    self._is_live = True
                    self._last_error = None
                    return res.json()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
            self._last_error = str(e)
            self._is_live = False

        return {"ok": False, "memory": True, "error": self._last_error}

    @property
    def is_backend_live(self) -> bool:
        """Property indicating if the backend was reachable on last check."""
        if self._is_live is None:
            self.check_health()
        return bool(self._is_live)

    # 1. trigger_demo_alert()
    def trigger_demo_alert(self) -> Alert:
        """Trigger predefined demo alert (POST /alerts/demo) or return mock Alert."""
        if not self.force_mocks:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(f"{self.base_url}{API_ENDPOINTS['ALERT_DEMO']}")
                    if res.status_code in (200, 201):
                        self._is_live = True
                        data = res.json()
                        metrics = data.get("metrics") or {}
                        return Alert(
                            id=data.get("incident_id") or data.get("id") or "ALT-LIVE",
                            service=data.get("service", "payments-db"),
                            error_rate=metrics.get("error_rate", 0.14),
                            affected_users=metrics.get("affected_users", 4800),
                            impact="Critical payment authorization degradation",
                            timestamp=data.get("timestamp", "2026-09-29T11:30:00Z"),
                            message=data.get("message", "connection pool exhausted"),
                            severity=data.get("severity", "P1"),
                            metrics=metrics,
                        )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return Alert.model_validate(MOCK_DEMO_ALERT)

    # 2. get_incidents()
    def get_incidents(
        self,
        status: Optional[str] = None,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Incident]:
        """Fetch list of incidents from backend (GET /incidents) with filtering, or fallback to mock data."""
        if not self.force_mocks:
            try:
                params: Dict[str, Any] = {"limit": limit}
                if status:
                    params["status"] = status
                if service:
                    params["service"] = service
                if severity:
                    params["severity"] = severity
                if active is not None:
                    params["active"] = str(active).lower()

                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENTS']}", params=params)
                    if res.status_code == 200:
                        self._is_live = True
                        raw_items = res.json()
                        incidents: List[Incident] = []
                        for raw in raw_items:
                            incidents.append(
                                Incident(
                                    id=raw["id"],
                                    title=raw.get("headline") or raw.get("message") or f"Incident {raw['id']}",
                                    service=raw["service"],
                                    severity=raw["severity"],
                                    status=raw["status"],
                                    symptoms=raw.get("message", ""),
                                    root_cause=raw.get("top_hypothesis"),
                                    resolution=raw.get("resolution"),
                                    started_at=raw.get("created_at", "2026-09-29T11:30:00Z"),
                                    resolved_at=raw.get("resolved_at"),
                                    affected_users=raw.get("affected_users"),
                                    is_novel=raw.get("is_novel", False),
                                    memory_used=raw.get("memory_used", True),
                                )
                            )
                        return incidents
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        # Fallback to rich mock data
        results = [Incident.model_validate(inc) for inc in MOCK_INCIDENTS]
        if status:
            results = [i for i in results if i.status == status]
        if service:
            results = [i for i in results if i.service == service]
        if severity:
            results = [i for i in results if i.severity == severity]
        if active is not None:
            active_statuses = {"investigating", "recommended", "awaiting_approval", "executing"}
            results = [i for i in results if (i.status in active_statuses) == active]

        return results[:limit]

    # Alias for get_incidents
    def list_incidents(self, **kwargs) -> List[Incident]:
        return self.get_incidents(**kwargs)

    # 3. get_incident(incident_id)
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Fetch detailed information for a single incident (GET /incidents/{incident_id})."""
        if not self.force_mocks:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_BY_ID'](incident_id)}")
                    if res.status_code == 200:
                        self._is_live = True
                        raw = res.json()
                        return Incident(
                            id=raw["id"],
                            title=raw.get("headline") or raw.get("message") or f"Incident {raw['id']}",
                            service=raw["service"],
                            severity=raw["severity"],
                            status=raw["status"],
                            symptoms=raw.get("message", ""),
                            root_cause=raw.get("top_hypothesis"),
                            resolution=raw.get("resolution"),
                            started_at=raw.get("created_at", "2026-09-29T11:30:00Z"),
                            resolved_at=raw.get("resolved_at"),
                            affected_users=raw.get("affected_users"),
                            is_novel=raw.get("is_novel", False),
                            memory_used=raw.get("memory_used", True),
                        )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        for inc in MOCK_INCIDENTS:
            if inc.get("id") == incident_id:
                return Incident.model_validate(inc)
        return None

    # 4. trigger_simulation(scenario, memory_enabled)
    def trigger_simulation(
        self,
        scenario: Any,
        memory_enabled: bool = True,
    ) -> SimulationResponse:
        """
        Trigger simulated remediation action for an incident or scenario.
        Takes either a scenario object, dictionary, or scenario ID string.
        """
        scenario_id = (
            scenario.id
            if hasattr(scenario, "id")
            else scenario.get("id")
            if isinstance(scenario, dict)
            else str(scenario)
        )

        # Update memory toggle on backend if needed
        self.set_memory_status(memory_enabled)

        if not self.force_mocks:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}{API_ENDPOINTS['INCIDENT_SIMULATE'](scenario_id)}"
                    )
                    if res.status_code in (200, 201):
                        self._is_live = True
                        data = res.json()
                        return SimulationResponse(
                            success=True,
                            incident_id=data.get("incident_id") or scenario_id,
                            status=data.get("status", "executing"),
                            message="Simulation execution initiated on backend",
                        )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return SimulationResponse(
            success=True,
            incident_id=scenario_id,
            status="executing",
            message=f"Simulation running (Memory {'ON' if memory_enabled else 'OFF'})",
        )

    # 5. reset_simulation()
    def reset_simulation(self) -> Dict[str, bool]:
        """Reset simulation and demo database state (POST /reset)."""
        if not self.force_mocks:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(f"{self.base_url}{API_ENDPOINTS['RESET_SIMULATION']}")
                    if res.status_code == 200:
                        self._is_live = True
                        return {"success": True}
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return {"success": True}

    # 6. get_memory_status()
    def get_memory_status(self) -> bool:
        """Fetch Hindsight memory toggle status (GET /settings/memory)."""
        if not self.force_mocks:
            try:
                with httpx.Client(timeout=3.0) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['SETTINGS_MEMORY']}")
                    if res.status_code == 200:
                        self._is_live = True
                        return bool(res.json().get("enabled", True))
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return True

    def set_memory_status(self, enabled: bool) -> bool:
        """Update Hindsight memory toggle status (POST /settings/memory)."""
        if not self.force_mocks:
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(
                        f"{self.base_url}{API_ENDPOINTS['SETTINGS_MEMORY']}",
                        json={"enabled": enabled, "actor": "engineer"},
                    )
                    if res.status_code == 200:
                        self._is_live = True
                        return bool(res.json().get("enabled", enabled))
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return enabled

    def get_memory_state(self) -> MemoryState:
        """Return typed MemoryState model."""
        return MemoryState(enabled=self.get_memory_status())

    def set_memory_state(self, enabled: bool) -> MemoryState:
        """Return typed MemoryState model after updating."""
        return MemoryState(enabled=self.set_memory_status(enabled))

    def toggle_memory(self, enabled: bool) -> bool:
        """Alias for set_memory_status."""
        return self.set_memory_status(enabled)

    # Supporting domain helpers
    def get_stats(self) -> IncidentStats:
        """Fetch KPI statistics (GET /incidents/stats)."""
        if not self.force_mocks:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_STATS']}")
                    if res.status_code == 200:
                        self._is_live = True
                        return IncidentStats.model_validate(res.json())
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return IncidentStats.model_validate(MOCK_STATS)

    def get_simulation_scenarios(self) -> List[SimulationScenario]:
        """Fetch predefined outage scenarios."""
        return [SimulationScenario.model_validate(sc) for sc in MOCK_SIMULATION_SCENARIOS]

    def get_timeline(self, incident_id: str) -> List[TimelineEvent]:
        """Fetch incident timeline events (GET /incidents/{incident_id}/timeline)."""
        if not self.force_mocks:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_TIMELINE'](incident_id)}")
                    if res.status_code == 200:
                        self._is_live = True
                        items = res.json()
                        return [
                            TimelineEvent(
                                id=f"EVT-{idx+1}",
                                timestamp=ev.get("ts", "2026-09-29T11:30:00Z"),
                                type=ev.get("kind", "agent"),
                                message=ev.get("title") or ev.get("step") or "Timeline step",
                                status=ev.get("status"),
                                detail=ev.get("detail"),
                            )
                            for idx, ev in enumerate(items)
                        ]
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return [TimelineEvent.model_validate(ev) for ev in MOCK_TIMELINE_EVENTS]


# Shared singleton client instance
api_client = ApiClient()

# Module-level convenience functions matching user specification
def trigger_demo_alert() -> Alert:
    return api_client.trigger_demo_alert()


def get_incidents(
    status: Optional[str] = None,
    service: Optional[str] = None,
    severity: Optional[str] = None,
    active: Optional[bool] = None,
    limit: int = 50,
) -> List[Incident]:
    return api_client.get_incidents(
        status=status, service=service, severity=severity, active=active, limit=limit
    )


def get_incident(incident_id: str) -> Optional[Incident]:
    return api_client.get_incident(incident_id)


def trigger_simulation(scenario: Any, memory_enabled: bool = True) -> SimulationResponse:
    return api_client.trigger_simulation(scenario, memory_enabled=memory_enabled)


def reset_simulation() -> Dict[str, bool]:
    return api_client.reset_simulation()


def get_memory_status() -> bool:
    return api_client.get_memory_status()
