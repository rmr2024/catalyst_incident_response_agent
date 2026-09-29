"""
Dashboard Page Component for Incident Response Console (P4).
Renders real-time incident feed, severity filters, KPIs, and quick inspector.
"""

from typing import List, Optional
import streamlit as st

from api_client import api_client
from components.badges import render_severity_badge, render_status_badge
from components.cards import render_incident_card, render_recommendation_card
from components.tables import render_incidents_table
from types import Incident


def render_dashboard():
    """Main render function for the Incident Dashboard."""
    st.markdown("## 📊 Incident Operations Dashboard")
    st.caption("Real-time production incidents, severity classification, and active investigation telemetry")

    # 1. KPI Metric Row
    stats = api_client.get_stats()
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.metric(
            label="Active Outages",
            value=stats.active,
            delta="Needs Attention" if stats.active > 0 else "Normal",
            delta_color="inverse" if stats.active > 0 else "normal",
        )
    with kpi_col2:
        st.metric(
            label="Total Incidents",
            value=stats.total,
        )
    with kpi_col3:
        st.metric(
            label="Critical P1 Outages",
            value=stats.p1,
            delta=f"{stats.p1} P1" if stats.p1 > 0 else None,
            delta_color="inverse",
        )
    with kpi_col4:
        st.metric(
            label="Average MTTR",
            value=f"{stats.avg_ttr_minutes:.1f}m",
            delta="-3.4m vs generic",
        )

    st.markdown("---")

    # 2. Action Controls & Filter Bar
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.5, 1, 1, 1])

    with ctrl_col1:
        if st.button("🚨 Trigger Demo Alert (P1)", use_container_width=True, type="primary"):
            with st.spinner("Ingesting alert from payments-db..."):
                alert = api_client.trigger_demo_alert()
                st.session_state["loading_state"] = False
                st.toast(f"New Alert Ingested: {alert.service} ({alert.severity})", icon="🚨")
                st.rerun()

    with ctrl_col2:
        sev_filter = st.selectbox(
            "Filter Severity",
            options=["All", "P1", "P2", "P3"],
            index=0,
            key="dash_filter_sev",
        )

    with ctrl_col3:
        status_filter = st.selectbox(
            "Filter Status",
            options=["All", "Active Only", "Resolved", "Investigating", "Awaiting Approval"],
            index=0,
            key="dash_filter_status",
        )

    with ctrl_col4:
        service_filter = st.selectbox(
            "Filter Service",
            options=["All", "payments-db", "auth-service", "order-processor", "inventory-api"],
            index=0,
            key="dash_filter_service",
        )

    # 3. Retrieve filtered incidents
    severity_param = None if sev_filter == "All" else sev_filter
    service_param = None if service_filter == "All" else service_filter

    active_param = None
    status_param = None
    if status_filter == "Active Only":
        active_param = True
    elif status_filter == "Resolved":
        status_param = "resolved"
    elif status_filter == "Investigating":
        status_param = "investigating"
    elif status_filter == "Awaiting Approval":
        status_param = "awaiting_approval"

    incidents: List[Incident] = api_client.get_incidents(
        severity=severity_param,
        service=service_param,
        status=status_param,
        active=active_param,
    )

    # 4. Main Content: Incidents Feed and Selected Detail
    feed_col, detail_col = st.columns([1.6, 1.4])

    with feed_col:
        st.subheader(f"Incidents Feed ({len(incidents)})")
        view_mode = st.radio("View Display", ["Cards View", "Table View"], horizontal=True, key="dash_view_mode")

        if not incidents:
            st.info("No incidents match the active filters.")
        elif view_mode == "Table View":
            render_incidents_table(incidents)
        else:
            current_id = (
                st.session_state.get("current_incident").id
                if st.session_state.get("current_incident")
                else None
            )

            for inc in incidents:
                is_selected = inc.id == current_id
                render_incident_card(inc, is_selected=is_selected)

                btn_col1, btn_col2 = st.columns([1, 1])
                with btn_col1:
                    if st.button("Inspect Incident →", key=f"btn_inspect_{inc.id}", use_container_width=True):
                        st.session_state["current_incident"] = inc
                        st.rerun()
                with btn_col2:
                    if st.button("Enter War Room 🚨", key=f"btn_war_{inc.id}", use_container_width=True):
                        st.session_state["current_incident"] = inc
                        st.session_state["selected_page"] = "War Room"
                        st.rerun()

    with detail_col:
        st.subheader("Incident Quick Inspector")
        active_inc: Optional[Incident] = st.session_state.get("current_incident")

        if not active_inc and incidents:
            active_inc = incidents[0]
            st.session_state["current_incident"] = active_inc

        if active_inc:
            with st.container():
                st.markdown(f"### {active_inc.id}: {active_inc.title}")
                meta_col1, meta_col2, meta_col3 = st.columns(3)
                with meta_col1:
                    st.write("**Service:**", f"`{active_inc.service}`")
                with meta_col2:
                    st.write("**Severity:**", render_severity_badge(active_inc.severity), unsafe_allow_html=True)
                with meta_col3:
                    st.write("**Status:**", render_status_badge(active_inc.status), unsafe_allow_html=True)

                st.markdown(f"**Symptoms:** {active_inc.symptoms}")

                if active_inc.root_cause:
                    st.markdown(f"**Identified Root Cause:** `{active_inc.root_cause}`")

                if active_inc.recommendation:
                    st.markdown("#### AI Memory Recommendation")
                    render_recommendation_card(active_inc.recommendation)

                st.markdown("---")
                if st.button(
                    f"Open War Room for {active_inc.id} →",
                    type="primary",
                    use_container_width=True,
                    key="btn_open_war_room_detail",
                ):
                    st.session_state["current_incident"] = active_inc
                    st.session_state["selected_page"] = "War Room"
                    st.rerun()
        else:
            st.info("Select an incident from the feed to inspect investigation details.")


if __name__ == "__main__":
    render_dashboard()
