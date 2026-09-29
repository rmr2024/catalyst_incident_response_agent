"""
API Client for Incident Response Agent frontend.
Communicates with the FastAPI backend at http://localhost:8000 with automatic fallback to mock data.
"""

import os
from typing import Any, Dict, List, Optional
import httpx

from mocks.mock_data import MOCK_INCIDENTS, MOCK_MEMORY_CALLS, MOCK_SCENARIOS, MOCK_STATS


DEFAULT_API_BASE_URL = os.environ.get("VITE_API_BASE_URL", "http://localhost:8000").rstrip("/")


class APIClient:
    def __init__(self, base_url: str = DEFAULT_API_BASE_URL, timeout: float = 8.0):
        self.base_url = base_url
        self.timeout = timeout
        self._last_error: Optional[str] = None
        self._is_live: Optional[bool] = None

    def check_health(self) -> Dict[str, Any]:
        """Check if FastAPI backend is healthy and responding."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    self._is_live = True
                    self._last_error = None
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return {"ok": False, "memory": True, "error": self._last_error}

    @property
    def is_backend_live(self) -> bool:
        if self._is_live is None:
            self.check_health()
        return bool(self._is_live)

    def list_incidents(
        self,
        status: Optional[str] = None,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch list of incident summaries from GET /incidents."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if service:
            params["service"] = service
        if severity:
            params["severity"] = severity
        if active is not None:
            params["active"] = str(active).lower()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/incidents", params=params)
                if res.status_code == 200:
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False

        # Fallback to mock data with filter support
        results = list(MOCK_INCIDENTS)
        if status:
            results = [i for i in results if i.get("status") == status]
        if service:
            results = [i for i in results if i.get("service") == service]
        if severity:
            results = [i for i in results if i.get("severity") == severity]
        if active is not None:
            active_statuses = {"investigating", "recommended", "awaiting_approval", "executing"}
            if active:
                results = [i for i in results if i.get("status") in active_statuses]
            else:
                results = [i for i in results if i.get("status") not in active_statuses]
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Fetch KPI statistics from GET /incidents/stats."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/incidents/stats")
                if res.status_code == 200:
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return MOCK_STATS

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full incident detail from GET /incidents/{incident_id}."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/incidents/{incident_id}")
                if res.status_code == 200:
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False

        for inc in MOCK_INCIDENTS:
            if inc.get("id") == incident_id:
                return {
                    **inc,
                    "alert": {"service": inc["service"], "message": inc["message"]},
                    "recommendation": {
                        "hypotheses": [
                            {"cause": inc.get("top_hypothesis", "Investigating cause"), "confidence": inc.get("top_confidence", 0.9), "evidence_ids": ["EV-101"]}
                        ],
                        "steps": ["Step 1: Check metrics", "Step 2: Apply mitigation"],
                        "runbook": "DB-POOL-RECOVERY",
                        "avoid": ["Do not restart app without clearing pool lock"],
                        "whats_different": "Matches known pattern from INC-104",
                        "is_novel": inc.get("is_novel", False),
                        "similar": [],
                        "needs_approval": True,
                    },
                    "actions": [],
                    "events": MOCK_MEMORY_CALLS,
                }
        return None

    def get_similar_incidents(self, incident_id: str) -> List[Dict[str, Any]]:
        """Fetch similar historical incidents from GET /incidents/{id}/similar."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/incidents/{incident_id}/similar")
                if res.status_code == 200:
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False

        incident = self.get_incident(incident_id) or {}
        recommendation = incident.get("recommendation") or {}
        return recommendation.get("similar") or []

    def get_incident_events(self, incident_id: str, after: int = 0) -> List[Dict[str, Any]]:
        """Fetch incident events after the given event offset."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(
                    f"{self.base_url}/incidents/{incident_id}/events",
                    params={"after": after},
                )
                if res.status_code == 200:
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False

        incident = self.get_incident(incident_id) or {}
        return (incident.get("events") or [])[after:]

    def submit_feedback(self, incident_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Submit accept/edit/reject feedback to POST /incidents/{id}/feedback."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/incidents/{incident_id}/feedback", json=payload)
                if res.status_code == 200:
                    self._is_live = True
                    self._last_error = None
                    return res.json()
                self._last_error = f"Feedback request failed ({res.status_code}): {res.text}"
                self._is_live = True
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return None

    def resolve_incident(self, incident_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve an incident via POST /incidents/{id}/resolve."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/incidents/{incident_id}/resolve", json=payload)
                if res.status_code == 200:
                    self._is_live = True
                    self._last_error = None
                    return res.json()
                self._last_error = f"Resolve request failed ({res.status_code}): {res.text}"
                self._is_live = True
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return None

    def get_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        """Fetch unified timeline from GET /incidents/{incident_id}/timeline."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/incidents/{incident_id}/timeline")
                if res.status_code == 200:
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return MOCK_MEMORY_CALLS

    def get_memory_calls(self, incident_id: str) -> List[Dict[str, Any]]:
        """Fetch memory RECALL/RETAIN logs from GET /incidents/{incident_id}/memory-calls."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/incidents/{incident_id}/memory-calls")
                if res.status_code == 200:
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return MOCK_MEMORY_CALLS

    def get_memory_status(self) -> bool:
        """Fetch memory toggle state from GET /settings/memory."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/settings/memory")
                if res.status_code == 200:
                    self._is_live = True
                    return bool(res.json().get("enabled", True))
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return True

    def toggle_memory(self, enabled: bool) -> bool:
        """Update memory toggle via POST /settings/memory."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(f"{self.base_url}/settings/memory", json={"enabled": enabled, "actor": "engineer"})
                if res.status_code == 200:
                    self._is_live = True
                    return bool(res.json().get("enabled", enabled))
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return enabled

    def trigger_demo_alert(self) -> Dict[str, Any]:
        """Trigger predefined demo alert via POST /alerts/demo."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(f"{self.base_url}/alerts/demo")
                if res.status_code in (200, 201):
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return {"incident_id": "INC-DEMO-MOCK", "status": "investigating"}

    def post_alert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest new alert via POST /alerts."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(f"{self.base_url}/alerts", json=payload)
                if res.status_code in (200, 201):
                    self._is_live = True
                    return res.json()
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return {"incident_id": "INC-NEW-MOCK", "status": "investigating"}

    def reset_demo(self) -> bool:
        """Reset demo database and memory state via POST /reset."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(f"{self.base_url}/reset")
                if res.status_code == 200:
                    self._is_live = True
                    return True
        except Exception as e:
            self._last_error = str(e)
            self._is_live = False
        return True


# Default shared client instance
api_client = APIClient()
