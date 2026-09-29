"""
Direct entry point for Streamlit multipage router: Dashboard.
"""

import sys
from pathlib import Path

# Ensure frontend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from api_client import api_client
from pages.dashboard import render_dashboard

render_dashboard()

# War Room launcher (P5). Sits below the dashboard so the incident overview
# stays the primary view; the War Room itself is a separate Streamlit page.
st.markdown("---")
st.subheader("Open an incident War Room")

try:
    war_room_incidents = api_client.list_incidents(limit=50) or []
except Exception as error:  # noqa: BLE001 - surface the failure, never crash the dashboard
    st.warning(f"Could not load incidents for the War Room: {error}")
    war_room_incidents = []

if war_room_incidents:
    incident_by_id = {
        item.id: item
        for item in war_room_incidents
        if getattr(item, "id", None)
    }
    incident_ids = list(incident_by_id)
    selected_id = st.selectbox(
        "Select incident",
        options=incident_ids,
        format_func=lambda incident_id: (
            f"{incident_id} · {incident_by_id[incident_id].service} · "
            f"{str(incident_by_id[incident_id].status).replace('_', ' ')}"
        ),
        key="dashboard_war_room_incident",
    )
    if st.button("Open War Room", type="primary", key="dashboard_open_war_room"):
        st.session_state["war_room_incident_id"] = selected_id
        st.switch_page("pages/3_WarRoom.py")
else:
    st.info("No incidents are available to open.")
