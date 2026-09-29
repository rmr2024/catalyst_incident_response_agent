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
    MOCK_SIMILAR_INCIDENTS,
    MOCK_SIMULATION_SCENARIOS,
    MOCK_STATS,
    MOCK_TIMELINE_EVENTS,
    generate_simulated_incident,
)
try:
    from models import (
        Alert,
        Incident,
        IncidentStats,
        MemoryState,
        SimulationResponse,
        SimulationScenario,
        TimelineEvent,
    )
except ImportError:
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
    # War Room (P5)
    "INCIDENT_EVENTS": lambda id: f"/incidents/{id}/events",
    "INCIDENT_MEMORY_CALLS": lambda id: f"/incidents/{id}/memory-calls",
    "INCIDENT_FEEDBACK": lambda id: f"/incidents/{id}/feedback",
    "INCIDENT_RESOLVE": lambda id: f"/incidents/{id}/resolve",
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
        self._mock_memory_enabled: bool = True

    def check_health(self) -> Dict[str, Any]:
        """Check if FastAPI backend is healthy and responding."""
        if self.force_mocks:
            self._is_live = False
            return {"ok": False, "memory": True, "mode": "forced_mock"}

        try:
            with httpx.Client(timeout=httpx.Timeout(1.0, connect=0.5)) as client:
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

    def refresh_connection(self) -> bool:
        """Force re-check of backend health."""
        self._is_live = None
        return self.is_backend_live

    # 1. trigger_demo_alert()
    def trigger_demo_alert(self) -> Alert:
        """Trigger predefined demo alert (POST /alerts/demo) or return mock Alert."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(f"{self.base_url}{API_ENDPOINTS['ALERT_DEMO']}")
                    if res.status_code in (200, 201):
                        self._is_live = True
                        data = res.json()
                        inc_id = data.get("incident_id") or data.get("id") or "ALT-LIVE"
                        return Alert(
                            id=inc_id,
                            service=data.get("service", "payments-db"),
                            error_rate=0.14,
                            affected_users=4800,
                            impact="Critical payment authorization degradation",
                            timestamp="2026-09-29T11:30:00Z",
                            message=data.get("message") or "connection pool exhausted, requests timing out",
                            severity=data.get("severity") or "P1",
                            metrics={"error_rate": 0.14, "affected_users": 4800, "latency_p99_ms": 3400},
                        )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        from datetime import datetime, timezone
        from mocks.mock_data import MOCK_RECOMMENDATION_DB_POOL, MOCK_SIMILAR_INCIDENTS, MOCK_TIMELINE_EVENTS

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        demo_count = len([i for i in MOCK_INCIDENTS if "DEMO" in str(i.get("id", ""))]) + 1
        demo_id = f"INC-2026-0929-DEMO{demo_count:02d}"

        new_inc = {
            "id": demo_id,
            "title": "PostgreSQL Connection Pool Saturation on Payments DB",
            "service": "payments-db",
            "severity": "P1",
            "status": "investigating",
            "symptoms": "connection pool exhausted, client requests timing out after 30s",
            "rootCause": "Database connection pool saturation under sudden checkout surge",
            "root_cause": "Database connection pool saturation under sudden checkout surge",
            "resolution": None,
            "startedAt": now_str,
            "started_at": now_str,
            "resolvedAt": None,
            "resolved_at": None,
            "affectedUsers": 4800,
            "affected_users": 4800,
            "recommendation": MOCK_RECOMMENDATION_DB_POOL,
            "similarIncidents": MOCK_SIMILAR_INCIDENTS,
            "similar_incidents": MOCK_SIMILAR_INCIDENTS,
            "timeline": MOCK_TIMELINE_EVENTS,
            "isNovel": False,
            "is_novel": False,
            "memoryUsed": True,
            "memory_used": True,
            "outcome": None,
        }

        # Prepend to mock incidents list so it appears right at the top
        MOCK_INCIDENTS.insert(0, new_inc)
        MOCK_STATS["active"] = MOCK_STATS.get("active", 0) + 1
        MOCK_STATS["total"] = MOCK_STATS.get("total", 0) + 1
        MOCK_STATS["p1"] = MOCK_STATS.get("p1", 0) + 1

        return Alert(
            id=demo_id,
            service="payments-db",
            error_rate=0.14,
            affected_users=4800,
            impact="Critical checkout degradation for active shoppers",
            timestamp=now_str,
            message="connection pool exhausted, requests timing out after 30s",
            severity="P1",
            metrics={"error_rate": 0.14, "latency_p99_ms": 3400, "affected_users": 4800},
        )

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
        if not self.force_mocks and self.is_backend_live:
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
                        if isinstance(raw_items, dict) and "items" in raw_items:
                            raw_items = raw_items["items"]
                        elif not isinstance(raw_items, list):
                            raw_items = []
                        incidents: List[Incident] = []
                        for raw in raw_items:
                            if not isinstance(raw, dict):
                                continue
                            incidents.append(
                                Incident(
                                    id=raw.get("id") or raw.get("incident_id") or "INC-UNKNOWN",
                                    title=raw.get("headline") or raw.get("title") or raw.get("message") or f"Incident {raw.get('id', '')}",
                                    service=raw.get("service") or "unknown-service",
                                    severity=raw.get("severity") or "P3",
                                    status=raw.get("status") or "investigating",
                                    symptoms=raw.get("message") or raw.get("symptoms") or "",
                                    root_cause=raw.get("top_hypothesis") or raw.get("root_cause") or raw.get("rootCause"),
                                    resolution=raw.get("resolution"),
                                    started_at=raw.get("created_at") or raw.get("started_at") or raw.get("startedAt") or "2026-09-29T11:30:00Z",
                                    resolved_at=raw.get("resolved_at") or raw.get("resolvedAt"),
                                    affected_users=raw.get("affected_users") or raw.get("affectedUsers"),
                                    is_novel=raw.get("is_novel") or raw.get("isNovel") or False,
                                    memory_used=raw.get("memory_used") if raw.get("memory_used") is not None else raw.get("memoryUsed", True),
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
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_BY_ID'](incident_id)}")
                    if res.status_code == 200:
                        self._is_live = True
                        raw = res.json()
                        if not isinstance(raw, dict):
                            raw = {}
                        return Incident(
                            id=raw.get("id") or raw.get("incident_id") or incident_id,
                            title=raw.get("headline") or raw.get("title") or raw.get("message") or f"Incident {incident_id}",
                            service=raw.get("service") or "unknown-service",
                            severity=raw.get("severity") or "P3",
                            status=raw.get("status") or "investigating",
                            symptoms=raw.get("message") or raw.get("symptoms") or "",
                            root_cause=raw.get("top_hypothesis") or raw.get("root_cause") or raw.get("rootCause"),
                            resolution=raw.get("resolution"),
                            started_at=raw.get("created_at") or raw.get("started_at") or raw.get("startedAt") or "2026-09-29T11:30:00Z",
                            resolved_at=raw.get("resolved_at") or raw.get("resolvedAt"),
                            affected_users=raw.get("affected_users") or raw.get("affectedUsers"),
                            is_novel=raw.get("is_novel") or raw.get("isNovel") or False,
                            memory_used=raw.get("memory_used") if raw.get("memory_used") is not None else raw.get("memoryUsed", True),
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

        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}{API_ENDPOINTS['INCIDENT_SIMULATE'](scenario_id)}"
                    )
                    if res.status_code in (200, 201):
                        self._is_live = True
                        data = res.json()
                        sim_inc = None
                        if data.get("incident"):
                            sim_inc = Incident.model_validate(data["incident"])
                        elif data.get("incident_id"):
                            sim_inc = self.get_incident(data["incident_id"])
                        return SimulationResponse(
                            success=True,
                            incident_id=data.get("incident_id") or scenario_id,
                            status=data.get("status", "investigating"),
                            message="Simulation execution initiated on backend",
                            incident=sim_inc,
                            memory_enabled=memory_enabled,
                        )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        # Fallback / mock mode: generate simulated incident matching scenario and memory toggle
        raw_inc = generate_simulated_incident(scenario_id, memory_enabled=memory_enabled)
        # Prepend to MOCK_INCIDENTS so it is accessible across the console
        MOCK_INCIDENTS.insert(0, raw_inc)
        sim_incident = Incident.model_validate(raw_inc)

        return SimulationResponse(
            success=True,
            incident_id=sim_incident.id,
            status=sim_incident.status,
            message=f"Simulation running (Memory {'ON' if memory_enabled else 'OFF'})",
            incident=sim_incident,
            memory_enabled=memory_enabled,
        )

    # 5. reset_simulation()
    def reset_simulation(self) -> Dict[str, bool]:
        """Reset simulation and demo database state (POST /reset)."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(f"{self.base_url}{API_ENDPOINTS['RESET_SIMULATION']}")
                    if res.status_code == 200:
                        self._is_live = True
                        return {"success": True}
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        # Filter out temporary simulation incidents from mock incidents
        MOCK_INCIDENTS[:] = [i for i in MOCK_INCIDENTS if not str(i.get("id", "")).startswith("SIM-")]
        return {"success": True}

    # 6. get_memory_status()
    def get_memory_status(self) -> bool:
        """Fetch Hindsight memory toggle status (GET /settings/memory)."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=3.0) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['SETTINGS_MEMORY']}")
                    if res.status_code == 200:
                        self._is_live = True
                        val = bool(res.json().get("enabled", True))
                        self._mock_memory_enabled = val
                        return val
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return getattr(self, "_mock_memory_enabled", True)

    def set_memory_status(self, enabled: bool) -> bool:
        """Update Hindsight memory toggle status (POST /settings/memory)."""
        self._mock_memory_enabled = enabled
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(
                        f"{self.base_url}{API_ENDPOINTS['SETTINGS_MEMORY']}",
                        json={"enabled": enabled, "actor": "engineer"},
                    )
                    if res.status_code == 200:
                        self._is_live = True
                        val = bool(res.json().get("enabled", enabled))
                        self._mock_memory_enabled = val
                        return val
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return self._mock_memory_enabled

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
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_STATS']}")
                    if res.status_code == 200:
                        self._is_live = True
                        data = res.json()
                        if not isinstance(data, dict):
                            data = {}
                        by_sev = data.get("by_severity") or {}
                        mttr_s = data.get("mttr_seconds")
                        avg_ttr = round(mttr_s / 60.0, 1) if mttr_s else 0.0
                        return IncidentStats(
                            total=data.get("total", 0),
                            active=data.get("active", 0),
                            resolved_today=data.get("resolved") or data.get("resolved_today", 0),
                            p1=by_sev.get("P1", 0),
                            p2=by_sev.get("P2", 0),
                            p3=by_sev.get("P3", 0),
                            avg_ttr_minutes=avg_ttr or data.get("avg_ttr_minutes", 0.0),
                        )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return IncidentStats.model_validate(MOCK_STATS)

    def get_simulation_scenarios(self) -> List[SimulationScenario]:
        """Fetch predefined outage scenarios."""
        return [SimulationScenario.model_validate(sc) for sc in MOCK_SIMULATION_SCENARIOS]

    def get_timeline(self, incident_id: str) -> List[TimelineEvent]:
        """Fetch incident timeline events (GET /incidents/{incident_id}/timeline)."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_TIMELINE'](incident_id)}")
                    if res.status_code == 200:
                        self._is_live = True
                        items = res.json()
                        if not isinstance(items, list):
                            items = []
                        return [
                            TimelineEvent(
                                id=f"EVT-{idx+1}",
                                timestamp=ev.get("ts") or ev.get("timestamp") or "2026-09-29T11:30:00Z",
                                type=ev.get("kind") or ev.get("type") or "agent",
                                message=ev.get("title") or ev.get("step") or ev.get("message") or "Timeline step",
                                status=ev.get("status"),
                                detail=ev.get("detail"),
                            )
                            for idx, ev in enumerate(items)
                            if isinstance(ev, dict)
                        ]
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return [TimelineEvent.model_validate(ev) for ev in MOCK_TIMELINE_EVENTS]

    # ------------------------------------------------------------------
    # War Room support (P5)
    #
    # These return raw JSON payloads rather than dashboard-contract models,
    # because the War Room validates the backend investigation contract
    # (backend/db/models.py IncidentDetail) which is a different shape.
    # ------------------------------------------------------------------

    def get_incident_payload(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Raw GET /incidents/{id} payload, shaped for IncidentDetail validation."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_BY_ID'](incident_id)}")
                    if res.status_code == 200:
                        self._is_live = True
                        raw = res.json()
                        if isinstance(raw, dict):
                            return raw
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return self._mock_incident_payload(incident_id)

    def _mock_incident_payload(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Build a War Room-shaped payload from dashboard-contract mock data.

        The mocks use the dashboard contract (title/symptoms/recommendation.recommended_steps)
        whereas the War Room validates the backend investigation contract
        (message/top_hypothesis/recommendation.hypotheses).
        """
        for inc in MOCK_INCIDENTS:
            if inc.get("id") != incident_id:
                continue

            message = inc.get("message") or inc.get("title") or inc.get("symptoms") or ""
            started_at = (
                inc.get("created_at")
                or inc.get("started_at")
                or inc.get("startedAt")
                or "2026-09-29T11:30:00Z"
            )

            recommendation = inc.get("recommendation")
            if not isinstance(recommendation, dict) or "hypotheses" not in recommendation:
                hypothesis = inc.get("top_hypothesis") or inc.get("root_cause") or message
                recommendation = {
                    "hypotheses": [
                        {
                            "cause": hypothesis or "Investigating cause",
                            "confidence": inc.get("top_confidence", 0.9),
                            "evidence_ids": list(recommendation.get("evidence", []) or []),
                        }
                    ],
                    "steps": [str(s) for s in (recommendation.get("recommended_steps") or [])] or [
                        "Check connection pool metrics",
                        "Apply the runbook mitigation",
                    ],
                    "runbook": recommendation.get("runbook") or "DB-POOL-RECOVERY",
                    "avoid": [str(a) for a in (recommendation.get("failed_before") or [])],
                    "whats_different": recommendation.get("whats_different", ""),
                    "is_novel": recommendation.get("is_novel", inc.get("is_novel", False)),
                    "similar": [
                        self._as_memory_hit(item)
                        for item in (
                            recommendation.get("similar")
                            or inc.get("similar_incidents")
                            or MOCK_SIMILAR_INCIDENTS
                        )
                    ],
                    "needs_approval": recommendation.get("needs_approval", True),
                }

            return {
                "id": inc.get("id", incident_id),
                "service": inc.get("service", "unknown-service"),
                "message": message,
                "severity": inc.get("severity", "P3"),
                "severity_reason": inc.get("severity_reason", ""),
                "source": inc.get("source", "manual"),
                "status": inc.get("status", "investigating"),
                "headline": inc.get("title") or message,
                "is_novel": inc.get("is_novel", inc.get("isNovel", False)),
                "memory_used": inc.get("memory_used", inc.get("memoryUsed", True)),
                "top_hypothesis": inc.get("root_cause") or inc.get("rootCause"),
                "top_confidence": inc.get("top_confidence"),
                "suggestion_verdict": inc.get("suggestion_verdict"),
                "outcome": inc.get("outcome"),
                "resolution": inc.get("resolution"),
                "created_at": started_at,
                "resolved_at": inc.get("resolved_at") or inc.get("resolvedAt"),
                "ttr_seconds": inc.get("ttr_seconds"),
                "alert": {
                    "service": inc.get("service", "unknown-service"),
                    "message": message,
                    "severity": inc.get("severity"),
                    "timestamp": started_at,
                    "metrics": inc.get("metrics", {}),
                },
                "recommendation": recommendation,
                "smart_alert": inc.get("smart_alert"),
                "actions": inc.get("actions", []),
                "events": self._as_agent_events(inc.get("timeline") or [], inc.get("id", incident_id)),
            }
        return None

    @staticmethod
    def _as_agent_events(timeline: List[Dict[str, Any]], incident_id: str) -> List[Dict[str, Any]]:
        """Translate dashboard timeline rows into the backend AgentEvent shape."""
        kind_map = {"agent": "agent", "memory": "memory", "human": "human"}
        events: List[Dict[str, Any]] = []
        for row in timeline:
            if not isinstance(row, dict):
                continue
            kind = str(row.get("type") or row.get("kind") or "agent").lower()
            events.append(
                {
                    "incident_id": row.get("incident_id") or incident_id,
                    "kind": kind_map.get(kind, "agent"),
                    "step": row.get("message") or row.get("step") or "Timeline step",
                    "detail": row.get("detail", ""),
                    "ts": row.get("timestamp") or row.get("ts"),
                }
            )
        return events

    def get_similar_incidents(self, incident_id: str) -> List[Dict[str, Any]]:
        """Similar historical incidents, derived from the incident recommendation."""
        payload = self.get_incident_payload(incident_id) or {}
        recommendation = payload.get("recommendation") or {}
        similar = recommendation.get("similar")
        if isinstance(similar, list) and similar:
            return [self._as_memory_hit(item) for item in similar if isinstance(item, dict)]
        return [self._as_memory_hit(item) for item in MOCK_SIMILAR_INCIDENTS]

    @staticmethod
    def _as_memory_hit(item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a similar-incident record into the MemoryHit shape.

        The dashboard contract uses incidentId/similarity/rootCause/resolution,
        while MemoryHit expects id/text/score/incident_id/outcome.
        """
        if "text" in item:
            return item
        incident_ref = item.get("incident_id") or item.get("incidentId") or item.get("id") or ""
        cause = item.get("root_cause") or item.get("rootCause") or ""
        resolution = item.get("resolution") or ""
        text = cause if not resolution else f"{cause} Resolution: {resolution}"
        return {
            "id": incident_ref,
            "incident_id": incident_ref,
            "text": text or incident_ref,
            "score": item.get("similarity") if item.get("similarity") is not None else item.get("score"),
            "outcome": item.get("outcome"),
        }

    def get_incident_events(self, incident_id: str, after: int = 0) -> List[Dict[str, Any]]:
        """Agent/memory/human events recorded after the given offset."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(
                        f"{self.base_url}{API_ENDPOINTS['INCIDENT_EVENTS'](incident_id)}",
                        params={"after": after},
                    )
                    if res.status_code == 200:
                        self._is_live = True
                        items = res.json()
                        if isinstance(items, list):
                            return [item for item in items if isinstance(item, dict)]
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        payload = self.get_incident_payload(incident_id) or {}
        events = payload.get("events") or []
        return [e for e in events[after:] if isinstance(e, dict)]

    def get_memory_calls(self, incident_id: str) -> List[Dict[str, Any]]:
        """Hindsight memory RECALL/RETAIN log for an incident."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_MEMORY_CALLS'](incident_id)}")
                    if res.status_code == 200:
                        self._is_live = True
                        items = res.json()
                        if isinstance(items, list):
                            return [item for item in items if isinstance(item, dict)]
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return [
            {
                "incident_id": incident_id,
                "kind": "memory",
                "step": "RECALL",
                "detail": "Searched long-term memory for prior incidents on this service.",
                "ts": "2026-09-29T11:30:12Z",
            },
            {
                "incident_id": incident_id,
                "kind": "memory",
                "step": "RETAIN",
                "detail": "Recorded investigation findings for future recall.",
                "ts": "2026-09-29T11:41:03Z",
            },
        ]

    def get_timeline_entries(self, incident_id: str) -> List[Dict[str, Any]]:
        """Raw timeline rows (dicts) for the War Room renderer."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}{API_ENDPOINTS['INCIDENT_TIMELINE'](incident_id)}")
                    if res.status_code == 200:
                        self._is_live = True
                        items = res.json()
                        if isinstance(items, list):
                            return [item for item in items if isinstance(item, dict)]
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return [
            {
                "ts": ev.get("timestamp") or ev.get("ts"),
                "source": "event",
                "kind": ev.get("type") or ev.get("kind", "event"),
                "title": ev.get("message") or ev.get("step", ""),
                "detail": ev.get("detail", ""),
            }
            for ev in MOCK_TIMELINE_EVENTS
        ]

    def submit_feedback(self, incident_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """POST accept/edit/reject verdict to /incidents/{id}/feedback."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}{API_ENDPOINTS['INCIDENT_FEEDBACK'](incident_id)}",
                        json=payload,
                    )
                    if res.status_code in (200, 201):
                        self._is_live = True
                        self._last_error = None
                        data = res.json()
                        return data if isinstance(data, dict) else {"incident_id": incident_id}
                    self._last_error = f"Feedback request failed ({res.status_code}): {res.text}"
                    return None
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False
                return None

        action = payload.get("action", "accept")
        status = "executing" if action in ("accept", "edit") else "rejected"
        self._apply_mock_feedback(incident_id, action, payload.get("steps"))
        return {"incident_id": incident_id, "status": status}

    def _apply_mock_feedback(
        self,
        incident_id: str,
        action: str,
        steps: Optional[List[str]] = None,
    ) -> None:
        """Mutate mock incident state so the War Room reflects the verdict."""
        for inc in MOCK_INCIDENTS:
            if inc.get("id") != incident_id:
                continue
            if action == "rejected":
                inc["status"] = "investigating"
            else:
                inc["status"] = "executing"
                inc["suggestion_verdict"] = "accepted" if action == "accept" else "edited"
                if steps:
                    inc["recommended_steps"] = list(steps)
            return

    def resolve_incident(self, incident_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """POST an operator resolution outcome to /incidents/{id}/resolve."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(
                        f"{self.base_url}{API_ENDPOINTS['INCIDENT_RESOLVE'](incident_id)}",
                        json=payload,
                    )
                    if res.status_code in (200, 201):
                        self._is_live = True
                        self._last_error = None
                        data = res.json()
                        return data if isinstance(data, dict) else {"incident_id": incident_id}
                    self._last_error = f"Resolve request failed ({res.status_code}): {res.text}"
                    return None
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False
                return None

        self._apply_mock_resolution(incident_id, payload)
        return {"incident_id": incident_id, "status": "resolved"}

    def _apply_mock_resolution(self, incident_id: str, payload: Dict[str, Any]) -> None:
        """Mark the mock incident resolved and reflect it in mock stats."""
        for inc in MOCK_INCIDENTS:
            if inc.get("id") != incident_id:
                continue
            inc["status"] = "resolved"
            inc["outcome"] = payload.get("outcome", "worked")
            if payload.get("resolution"):
                inc["resolution"] = payload["resolution"]
            break
        MOCK_STATS["active"] = max(0, MOCK_STATS.get("active", 0) - 1)
        MOCK_STATS["resolved_today"] = MOCK_STATS.get("resolved_today", 0) + 1

    def post_alert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest a new alert via POST /alerts."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.post(f"{self.base_url}{API_ENDPOINTS['ALERTS']}", json=payload)
                    if res.status_code in (200, 201):
                        self._is_live = True
                        data = res.json()
                        return data if isinstance(data, dict) else {}
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return {"incident_id": "INC-NEW-MOCK", "status": "investigating"}

    def get_analytics(self) -> Dict[str, Any]:
        """Fetch operational analytics (GET /analytics)."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    res = client.get(f"{self.base_url}/analytics")
                    if res.status_code == 200:
                        self._is_live = True
                        data = res.json()
                        if isinstance(data, dict):
                            return data
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        # Mock analytics data
        return {
            "total": 18,
            "active": 2,
            "resolved": 14,
            "mttr_seconds": 2220,
            "by_severity": {"P1": 8, "P2": 7, "P3": 3},
            "by_service": {
                "checkout-api": 4,
                "payment-service": 4,
                "search-service": 3,
                "inventory-service": 3,
                "auth-service": 2,
                "order-service": 1,
                "notification-service": 1,
            },
            "memory_on_mttr_seconds": 1680,
            "memory_off_mttr_seconds": 3540,
            "outcomes": {"worked": 14, "partial": 2, "failed": 2},
        }

    def draft_postmortem(self, incident_id: str) -> Dict[str, Any]:
        """Draft a post-mortem via LLM (POST /incidents/{id}/postmortem/draft)."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=30.0) as client:
                    res = client.post(f"{self.base_url}/incidents/{incident_id}/postmortem/draft")
                    if res.status_code == 200:
                        self._is_live = True
                        data = res.json()
                        if isinstance(data, dict):
                            return data
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        # Mock postmortem draft
        return {
            "incident_id": incident_id,
            "summary": f"[MOCK] {incident_id}: Database connection pool exhausted under elevated checkout load.",
            "timeline": [
                f"09:13 — Alert triggered: checkout-api connection pool exhausted",
                f"09:14 — AI investigation started; similar incidents INC-104 and INC-117 recalled from memory",
                f"09:22 — Root cause confirmed: pool size of 20 insufficient for peak load",
                f"09:28 — Action approved: increase pool size to 100 + restart pods",
                f"09:35 — Simulation executed; pool utilisation dropped to 8%",
                f"09:42 — Incident resolved",
            ],
            "impact": "40% of checkout users received 503 errors for 28 minutes.",
            "root_cause": "Database connection pool saturation under checkout surge; pool size of 20 was insufficient.",
            "resolution": "Increased pool size to 100 and restarted pods to clear stale connections.",
            "lessons": [
                "Pre-scale connection pools before planned high-traffic events.",
                "Add pool-utilisation alert at 70% to allow proactive action.",
                "Separate analytical queries from the transactional pool.",
            ],
            "status": "draft",
        }

    def approve_postmortem(self, incident_id: str) -> Dict[str, Any]:
        """Approve post-mortem and retain to memory (POST /incidents/{id}/postmortem/approve)."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=15.0) as client:
                    res = client.post(f"{self.base_url}/incidents/{incident_id}/postmortem/approve")
                    if res.status_code == 200:
                        self._is_live = True
                        data = res.json()
                        if isinstance(data, dict):
                            return data
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return {"incident_id": incident_id, "retained": True, "status": "approved"}

    def get_postmortem_status(self, incident_id: str) -> Dict[str, Any]:
        """Check post-mortem status (GET /incidents/{id}/postmortem/status)."""
        if not self.force_mocks and self.is_backend_live:
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.get(f"{self.base_url}/incidents/{incident_id}/postmortem/status")
                    if res.status_code == 200:
                        self._is_live = True
                        data = res.json()
                        if isinstance(data, dict):
                            return data
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, Exception) as e:
                self._last_error = str(e)
                self._is_live = False

        return {"incident_id": incident_id, "status": "none"}


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
