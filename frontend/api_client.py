"""
Re-export centralized ApiClient and functions from services.api_client.
Ensures full compatibility for both `from api_client import ...` and `from services.api_client import ...`.
"""

from services.api_client import (
    API_ENDPOINTS,
    ApiClient,
    api_client,
    get_backend_url,
    get_incident,
    get_incidents,
    get_memory_status,
    is_mock_mode_forced,
    reset_simulation,
    trigger_demo_alert,
    trigger_simulation,
)

__all__ = [
    "API_ENDPOINTS",
    "ApiClient",
    "api_client",
    "get_backend_url",
    "is_mock_mode_forced",
    "trigger_demo_alert",
    "get_incidents",
    "get_incident",
    "trigger_simulation",
    "reset_simulation",
    "get_memory_status",
]
