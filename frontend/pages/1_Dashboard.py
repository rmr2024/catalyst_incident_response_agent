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

st.markdown("---")
st.subheader("Open an incident War Room")
war_room_incidents = api_client.list_incidents(limit=50)
if war_room_incidents:
    incident_by_id = {item["id"]: item for item in war_room_incidents if item.get("id")}
    incident_ids = list(incident_by_id)
    selected_id = st.selectbox(
        "Select incident",
        options=incident_ids,
        format_func=lambda incident_id: (
            f"{incident_id} · {incident_by_id[incident_id].get('service', 'unknown service')} · "
            f"{incident_by_id[incident_id].get('status', 'unknown')}"
        ),
        key="dashboard_war_room_incident",
    )
    if st.button("Open War Room", type="primary", key="dashboard_open_war_room"):
        st.session_state["war_room_incident_id"] = selected_id
        st.switch_page("pages/3_WarRoom.py")
else:
    st.info("No incidents are available to open.")
