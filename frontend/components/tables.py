"""
Table components for rendering incidents, timeline events, and similar incidents.
"""

from typing import List
import pandas as pd
import streamlit as st

try:
    from models import Incident, SimilarIncident, TimelineEvent
except ImportError:
    from types import Incident, SimilarIncident, TimelineEvent
from utils.helpers import format_timestamp


def render_incidents_table(incidents: List[Incident]):
    """Render a clean structured dataframe table for incident list."""
    if not incidents:
        st.info("No incidents found matching the selected filters.")
        return

    data = []
    for inc in incidents:
        data.append({
            "ID": inc.id,
            "Severity": inc.severity,
            "Service": inc.service,
            "Status": inc.status.replace("_", " ").upper(),
            "Title / Symptoms": inc.title,
            "Started": format_timestamp(inc.started_at),
            "Affected Users": inc.affected_users or "—",
        })

    df = pd.DataFrame(data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Severity": st.column_config.TextColumn("Sev", width="small"),
            "Service": st.column_config.TextColumn("Service", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Title / Symptoms": st.column_config.TextColumn("Title / Symptoms", width="large"),
            "Started": st.column_config.TextColumn("Started", width="medium"),
            "Affected Users": st.column_config.TextColumn("Users", width="small"),
        },
    )


def render_timeline_table(events: List[TimelineEvent]):
    """Render a clean timeline events log."""
    if not events:
        st.info("No timeline events recorded.")
        return

    data = []
    for ev in events:
        data.append({
            "Time": format_timestamp(ev.timestamp),
            "Kind": ev.type.upper(),
            "Event": ev.message,
            "Detail": ev.detail or "—",
        })

    df = pd.DataFrame(data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Time": st.column_config.TextColumn("Time", width="medium"),
            "Kind": st.column_config.TextColumn("Type", width="small"),
            "Event": st.column_config.TextColumn("Event", width="large"),
            "Detail": st.column_config.TextColumn("Detail", width="large"),
        },
    )


def render_similar_incidents_table(similar: List[SimilarIncident]):
    """Render recalled similar incidents table."""
    if not similar:
        st.info("No historical matches found in Hindsight memory.")
        return

    data = []
    for sim in similar:
        data.append({
            "Historical ID": sim.incident_id,
            "Similarity": f"{sim.similarity * 100:.0f}%",
            "Past Outcome": sim.outcome.upper(),
            "Historical Root Cause": sim.root_cause,
            "Resolution": sim.resolution,
        })

    df = pd.DataFrame(data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )
