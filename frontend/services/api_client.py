"""
Service layer exporting the centralized ApiClient.
"""

from api_client import API_ENDPOINTS, ApiClient, api_client

__all__ = ["ApiClient", "api_client", "API_ENDPOINTS"]
