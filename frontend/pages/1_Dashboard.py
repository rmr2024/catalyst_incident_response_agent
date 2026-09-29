"""
Incident Dashboard - Foundation Stub (P4).
Full implementation will follow in subsequent task.
"""

import streamlit as st
import sys
from pathlib import Path

# Ensure frontend root is on sys.path for direct page runs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_client import api_client
from components.header import render_header

st.set_page_config(
    page_title="Incident Dashboard",
    page_icon="📊",
    layout="wide",
)

render_header(title="Incident Dashboard", subtitle="Real-time Incident Feed & System Telemetry")

st.info("🚧 **Dashboard Foundation Ready**: The foundation and API client bindings are established. Full incident feed, KPI cards, and trigger controls will be implemented in the next step.")

# Display quick connection and mock data preview
with st.expander("🔌 Connection & Data Contract Status", expanded=True):
    stats = api_client.get_stats()
    incidents = api_client.list_incidents(limit=5)
    st.write("**Backend Live Status:**", "Connected" if api_client.is_backend_live else "Mock Fallback Active")
    st.write(f"**Aggregated Stats:** Total: {stats.get('total', 0)}, Active: {stats.get('active', 0)}")
    st.write(f"**Incidents Loaded:** {len(incidents)} items ready")
