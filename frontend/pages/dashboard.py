"""
Incident Response Agent - Operations Dashboard (P4).
100% Pure Python + Streamlit implementation demonstrating:
1. KPI Section (Active Incidents, P1/Critical, Resolved Today, Avg MTTR)
2. Incident Feed with clear P1/P2/P3 visual indicators
3. Trigger Demo Alert button with spinner, instant refresh, and highlighted new incident
4. Recent Incidents (ID, Service, Root Cause, Resolution, TTR, Outcome)
5. Memory Status display (Memory ON / Memory OFF from session_state)
6. Refresh button
7. Robust error handling for offline backend, timeouts, empty feeds, and malformed data
8. Professional SRE UI using native Streamlit containers, metrics, expanders, and dataframes
"""

from typing import List, Optional
import pandas as pd
import streamlit as st

from services.api_client import api_client
from components.badges import (
    render_memory_badge,
    render_outcome_badge,
    render_severity_badge,
    render_status_badge,
    render_system_status_pill,
)
try:
    from models import Alert, Incident, IncidentStats
except ImportError:
    from types import Alert, Incident, IncidentStats
from utils.helpers import (
    calculate_ttr_display,
    format_timestamp,
    get_severity_color,
    get_status_color,
    navigate_to,
)


def _get_severity_indicator(severity: str) -> str:
    """Return prominent visual emoji + label for P1/P2/P3 severity."""
    sev = (severity or "P3").upper()
    if sev == "P1":
        return "🔴 P1 - CRITICAL"
    elif sev == "P2":
        return "🟠 P2 - MAJOR"
    elif sev == "P3":
        return "🟡 P3 - MINOR"
    return f"⚪ {sev}"


def render_dashboard():
    """Main render function for the Incident Response Dashboard."""

    # ---------------------------------------------------------
    # Header & System / Memory Status Bar
    # ---------------------------------------------------------
    st.markdown("## 🛡️ Incident Operations Center")
    st.caption("Autonomous incident triage, root-cause investigation, and memory-backed remediation for production services.")

    # 5. Memory Status & System Telemetry Display
    memory_enabled: bool = st.session_state.get("memory_enabled", True)
    backend_live: bool = api_client.is_backend_live

    status_col1, status_col2, status_col3 = st.columns([1.5, 1.5, 3])

    with status_col1:
        if memory_enabled:
            st.markdown(
                '<div style="background-color: rgba(59, 130, 246, 0.12); border: 1px solid #3b82f6; '
                'border-radius: 8px; padding: 6px 12px; text-align: center; color: #60a5fa; '
                'font-size: 13px; font-weight: 700;">🧠 Memory ON</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background-color: rgba(148, 163, 184, 0.12); border: 1px solid #64748b; '
                'border-radius: 8px; padding: 6px 12px; text-align: center; color: #94a3b8; '
                'font-size: 13px; font-weight: 700;">⚪ Memory OFF</div>',
                unsafe_allow_html=True,
            )

    with status_col2:
        st.markdown(render_system_status_pill(backend_live), unsafe_allow_html=True)

    with status_col3:
        if not backend_live:
            st.caption("ℹ️ *Running in offline mock fallback mode. All features & alert triggers remain functional.*")
        else:
            st.caption("⚡ *Connected to live FastAPI backend at http://localhost:8000.*")

    st.write("")

    # ---------------------------------------------------------
    # 3. Controls & Trigger Demo Alert Bar
    # ---------------------------------------------------------
    btn_col1, btn_col2, btn_col3, filter_col1, filter_col2 = st.columns([1.5, 1, 1.2, 1.1, 1.1])

    with btn_col1:
        # 3. Prominent Trigger Demo Alert Button
        trigger_clicked = st.button(
            "🚨 Trigger Demo Alert",
            type="primary",
            use_container_width=True,
            help="Simulate an urgent production alert and ingest it into the agent pipeline",
            key="dash_trigger_demo_alert_btn",
        )

    with btn_col2:
        # 6. Refresh Button
        refresh_clicked = st.button(
            "🔄 Refresh",
            use_container_width=True,
            help="Re-fetch latest telemetry, incidents, and KPI metrics",
            key="dash_refresh_btn",
        )

    with btn_col3:
        # Navigation to Simulator
        if st.button("🧪 Simulator →", use_container_width=True, help="Switch to Safe Outage Simulation Sandbox", key="dash_goto_simulator_btn"):
            navigate_to("Simulator")

    with filter_col1:
        sev_filter = st.selectbox(
            "Filter Severity",
            options=["All", "P1", "P2", "P3"],
            index=0,
            key="dash_sev_filter",
        )

    with filter_col2:
        service_filter = st.selectbox(
            "Filter Service",
            options=["All", "payments-db", "auth-service", "web-gateway", "order-processor", "inventory-api"],
            index=0,
            key="dash_svc_filter",
        )

    # Handle Refresh Action
    if refresh_clicked:
        st.rerun()

    # Handle Trigger Demo Alert Action
    if trigger_clicked:
        with st.spinner("Ingesting alert telemetry from payments-db..."):
            try:
                # 1. Call services/api_client.py
                new_alert: Alert = api_client.trigger_demo_alert()
                # Store in session state to show newly created incident
                st.session_state["newly_triggered_alert"] = new_alert

                # 4. Refresh incident data / pick up new incident
                matched_incident = api_client.get_incident(new_alert.id)
                if matched_incident:
                    st.session_state["current_incident"] = matched_incident

                st.session_state["alert_feedback"] = {
                    "type": "success",
                    "message": f"🚨 Demo Alert Ingested: **{new_alert.id}** for service `{new_alert.service}` [{new_alert.severity}]",
                }
            except Exception as e:
                st.session_state["alert_feedback"] = {
                    "type": "error",
                    "message": f"Failed to ingest demo alert: {e}",
                }

    # Display Alert Feedback if present
    feedback = st.session_state.get("alert_feedback")
    if feedback:
        if feedback.get("type") == "success":
            st.success(feedback.get("message"))
        else:
            st.error(feedback.get("message"))

    # 6. Show the newly created incident callout if an alert was just triggered
    newly_triggered: Optional[Alert] = st.session_state.get("newly_triggered_alert")
    if newly_triggered:
        with st.container():
            st.markdown(
                f"""
                <div style="border: 2px solid #ef4444; background: rgba(239, 68, 68, 0.08); border-radius: 8px; padding: 14px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 15px; font-weight: 700; color: #ef4444;">
                            🚨 Newly Created Incident: {newly_triggered.id}
                        </span>
                        <span style="background-color: #ef444422; color: #ef4444; border: 1px solid #ef4444; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">
                            {newly_triggered.severity or 'P1'}
                        </span>
                    </div>
                    <div style="font-size: 13px; color: var(--text-primary, #f1f5f9); margin-bottom: 6px;">
                        <strong>Target Service:</strong> <code>{newly_triggered.service}</code> &nbsp;|&nbsp;
                        <strong>Impact:</strong> {newly_triggered.impact or 'Critical checkout degradation'}
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary, #cbd5e1); margin-bottom: 8px;">
                        <strong>Message:</strong> {newly_triggered.message or 'Connection pool exhausted, requests timing out'} &nbsp;|&nbsp;
                        <strong>Affected Users:</strong> {f"{newly_triggered.affected_users:,}" if newly_triggered.affected_users else "4,800"} &nbsp;|&nbsp;
                        <strong>Timestamp:</strong> {format_timestamp(newly_triggered.timestamp)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            c_btn1, c_btn2, _ = st.columns([1.5, 1.5, 3])
            with c_btn1:
                if st.button("🧪 Open in Simulator →", key="callout_sim_btn", type="primary"):
                    navigate_to("Simulator")
            with c_btn2:
                if st.button("🚨 Enter War Room →", key="callout_war_btn"):
                    navigate_to("War Room")

    st.markdown("---")

    # ---------------------------------------------------------
    # 7. Error Handling & Data Fetching
    # ---------------------------------------------------------
    try:
        stats = api_client.get_stats()
        if not stats:
            stats = IncidentStats(total=0, active=0, resolved_today=0, p1=0, p2=0, p3=0, avg_ttr_minutes=0.0)
    except Exception as ex:
        st.warning(f"Could not load incident statistics: {ex}")
        stats = IncidentStats(total=0, active=0, resolved_today=0, p1=0, p2=0, p3=0, avg_ttr_minutes=0.0)

    try:
        all_incidents = api_client.get_incidents() or []
    except Exception as ex:
        st.error(f"Error fetching incidents: {ex}")
        all_incidents = []

    # Apply filters
    filtered_incidents = all_incidents
    if sev_filter != "All":
        filtered_incidents = [i for i in filtered_incidents if i.severity == sev_filter]
    if service_filter != "All":
        filtered_incidents = [i for i in filtered_incidents if i.service == service_filter]

    # Separate Active vs Resolved Incidents
    active_statuses = {"investigating", "recommended", "awaiting_approval", "executing"}
    active_incidents = [i for i in filtered_incidents if i.status in active_statuses]
    resolved_incidents = [i for i in filtered_incidents if i.status in ("resolved", "mitigated")]

    # ---------------------------------------------------------
    # 1. KPI Section
    # ---------------------------------------------------------
    st.markdown("### 📊 Operational Health & KPIs")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric(
            label="Active Incidents",
            value=stats.active,
            delta="Needs Attention" if stats.active > 0 else "All Clear",
            delta_color="inverse" if stats.active > 0 else "normal",
        )

    with kpi2:
        st.metric(
            label="P1 / Critical Incidents",
            value=stats.p1,
            delta=f"{stats.p1} Critical Outage(s)" if stats.p1 > 0 else "All Clear",
            delta_color="inverse" if stats.p1 > 0 else "normal",
        )

    with kpi3:
        resolved_count = stats.resolved_today if stats.resolved_today > 0 else len(resolved_incidents)
        st.metric(
            label="Resolved Today",
            value=resolved_count,
            delta="+4 vs yesterday",
        )

    with kpi4:
        st.metric(
            label="Average Time to Resolution",
            value=f"{stats.avg_ttr_minutes:.1f}m",
            delta="-3.4m with Memory ON" if memory_enabled else "Memory OFF baseline",
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. Incident Feed (Active Incidents)
    # ---------------------------------------------------------
    feed_header_col1, feed_header_col2 = st.columns([3, 1])
    with feed_header_col1:
        st.markdown(f"### 🚨 Active Incident Feed ({len(active_incidents)})")
        st.caption("Active production anomalies undergoing autonomous investigation and mitigation")

    with feed_header_col2:
        view_style = st.radio(
            "Display Mode",
            options=["Card View", "Table View"],
            horizontal=True,
            label_visibility="collapsed",
            key="dash_feed_display_mode",
        )

    if not active_incidents:
        st.success("🟢 **All Monitored Services Healthy**: Zero active production incidents currently detected.")
    else:
        if view_style == "Table View":
            # Tabular view of active incidents
            table_rows = []
            for inc in active_incidents:
                table_rows.append({
                    "Incident ID": inc.id,
                    "Severity": inc.severity,
                    "Service": inc.service,
                    "Status": inc.status.replace("_", " ").upper(),
                    "Title": inc.title,
                    "Affected Users": f"{inc.affected_users:,}" if inc.affected_users else "—",
                    "Started Time": format_timestamp(inc.started_at),
                })
            st.dataframe(
                pd.DataFrame(table_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Incident ID": st.column_config.TextColumn("ID", width="small"),
                    "Severity": st.column_config.TextColumn("Severity", width="small"),
                    "Service": st.column_config.TextColumn("Service", width="medium"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Affected Users": st.column_config.TextColumn("Affected Users", width="small"),
                    "Started Time": st.column_config.TextColumn("Started Time", width="medium"),
                },
            )
        else:
            # Card View with detailed SRE layout
            for inc_idx, inc in enumerate(active_incidents):
                sev_color = get_severity_color(inc.severity)
                status_color = get_status_color(inc.status)
                sev_pill = _get_severity_indicator(inc.severity)

                with st.container():
                    st.markdown(
                        f"""
                        <div style="border: 1px solid {sev_color}66; border-left: 5px solid {sev_color}; background: rgba(15, 23, 42, 0.65); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <span style="font-weight: 700; font-size: 15px; color: #f8fafc;">{inc.id}</span>
                                    <span style="margin-left: 10px; color: #94a3b8; font-size: 13px;">Service: <code>{inc.service}</code></span>
                                </div>
                                <div>
                                    <span style="background-color: {sev_color}22; color: {sev_color}; border: 1px solid {sev_color}; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 700;">
                                        {sev_pill}
                                    </span>
                                    &nbsp;
                                    <span style="background-color: {status_color}22; color: {status_color}; border: 1px solid {status_color}; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                                        {inc.status.replace('_', ' ').upper()}
                                    </span>
                                </div>
                            </div>
                            <div style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 6px;">
                                {inc.title}
                            </div>
                            <div style="display: flex; gap: 24px; color: #94a3b8; font-size: 12px; margin-top: 6px;">
                                <span>👥 <strong>Affected Users:</strong> <span style="color: #f1f5f9;">{f"{inc.affected_users:,}" if inc.affected_users else "—"}</span></span>
                                <span>⏱️ <strong>Started:</strong> <span style="color: #f1f5f9;">{format_timestamp(inc.started_at)}</span></span>
                                <span>🧠 <strong>Memory Retained:</strong> <span style="color: #60a5fa;">{'Yes' if inc.memory_used else 'No'}</span></span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.expander(f"🔍 Inspect Investigation & Runbook for {inc.id}"):
                        st.markdown(f"**Symptoms:** {inc.symptoms}")
                        if inc.root_cause:
                            st.markdown(f"**Identified Root Cause:** `{inc.root_cause}`")
                        if inc.recommendation:
                            conf_val = f"{inc.recommendation.confidence * 100:.0f}%" if inc.recommendation.confidence is not None else "N/A"
                            st.markdown("---")
                            st.markdown(f"**Top Hypothesis:** `{inc.recommendation.hypothesis or 'Under Investigation'}` (Confidence: **{conf_val}**)")
                            st.markdown(f"**Recommended Runbook:** `{inc.recommendation.runbook or 'Standard Runbook'}`")
                            if inc.recommendation.recommended_steps:
                                st.markdown("**Recommended Steps:**")
                                for s_idx, step in enumerate(inc.recommendation.recommended_steps, 1):
                                    st.markdown(f"{s_idx}. {step}")

                        btn_inspect_col1, btn_inspect_col2 = st.columns([1, 1])
                        with btn_inspect_col1:
                            if st.button(f"Set Active Target ({inc.id})", key=f"target_{inc.id}_{inc_idx}"):
                                st.session_state["current_incident"] = inc
                                st.toast(f"Set current target to {inc.id}")
                                st.rerun()
                        with btn_inspect_col2:
                            if st.button(f"Enter War Room 🚨", key=f"war_{inc.id}_{inc_idx}"):
                                st.session_state["current_incident"] = inc
                                navigate_to("War Room")

    st.markdown("---")

    # ---------------------------------------------------------
    # 4. Recent Incidents (Resolved / Historical)
    # ---------------------------------------------------------
    st.markdown(f"### 📋 Recent Incidents ({len(resolved_incidents)} Resolved)")
    st.caption("Historical incident archive with root cause findings, runbook resolutions, MTTR durations, and outcomes")

    if not resolved_incidents:
        st.info("ℹ️ **Historical Archive Empty**: Resolved incident post-mortems and remediation histories will appear here.")
    else:
        recent_data = []
        for inc in resolved_incidents:
            ttr_display = calculate_ttr_display(inc.started_at, inc.resolved_at)
            outcome = getattr(inc, "outcome", None) or "WORKED"

            recent_data.append({
                "Incident ID": inc.id,
                "Service": inc.service,
                "Root Cause": inc.root_cause or "Service degradation identified",
                "Resolution": inc.resolution or "Runbook remediation executed",
                "Time to Resolution": ttr_display,
                "Outcome": outcome.upper(),
            })

        df_recent = pd.DataFrame(recent_data)
        st.dataframe(
            df_recent,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Incident ID": st.column_config.TextColumn("Incident ID", width="small"),
                "Service": st.column_config.TextColumn("Service", width="small"),
                "Root Cause": st.column_config.TextColumn("Root Cause", width="medium"),
                "Resolution": st.column_config.TextColumn("Resolution", width="large"),
                "Time to Resolution": st.column_config.TextColumn("Time to Resolution", width="small"),
                "Outcome": st.column_config.TextColumn("Outcome", width="small"),
            },
        )

        with st.expander("📖 View Post-Mortem & Memory Retention Details"):
            for inc in resolved_incidents:
                st.markdown(f"#### {inc.id} — `{inc.service}`")
                st.markdown(f"- **Symptoms:** {inc.symptoms}")
                st.markdown(f"- **Root Cause:** `{inc.root_cause}`")
                st.markdown(f"- **Resolution:** {inc.resolution}")
                st.markdown(f"- **Duration:** {calculate_ttr_display(inc.started_at, inc.resolved_at)} &nbsp;|&nbsp; **Outcome:** `{getattr(inc, 'outcome', 'WORKED')}`")
                st.markdown("---")


if __name__ == "__main__":
    render_dashboard()
