"""
Incident Response Agent - Main Console Shell.
Streamlit application root coordinating sidebar navigation, session state, and page dispatching.
Provides seamless navigation between:
1. Dashboard (Fully functional)
2. Simulator (Fully functional)
3. War Room (Coming Soon)
4. Post-Mortem (Coming Soon)
5. Analytics (Coming Soon)
Preserves memory_enabled, selected scenario, current incident, and simulation result in session_state.
"""

import sys
from pathlib import Path
from typing import Optional
import streamlit as st

# Ensure frontend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Initialize domain models & ensure types registration
import models
import types
for _attr in dir(models):
    if not _attr.startswith("_"):
        setattr(types, _attr, getattr(models, _attr))

from api_client import api_client
from components.badges import render_memory_badge, render_severity_badge, render_status_badge, render_system_status_pill
from pages.dashboard import render_dashboard
from pages.simulator import render_simulator
from models import Incident, SimulationScenario

# 1. Page Configuration
st.set_page_config(
    page_title="Incident Response Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Handle pending programmatic navigation before widget creation
if "_nav_destination" in st.session_state and st.session_state["_nav_destination"]:
    st.session_state["selected_page"] = st.session_state.pop("_nav_destination")

# 2. Initialize Session State
if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Dashboard"

if "memory_enabled" not in st.session_state:
    st.session_state["memory_enabled"] = api_client.get_memory_status()

if "selected_scenario" not in st.session_state:
    scenarios = api_client.get_simulation_scenarios()
    st.session_state["selected_scenario"] = scenarios[0] if scenarios else None

if "current_incident" not in st.session_state:
    incidents = api_client.get_incidents(active=True)
    st.session_state["current_incident"] = incidents[0] if incidents else None

if "simulation_result" not in st.session_state:
    st.session_state["simulation_result"] = None

if "loading_state" not in st.session_state:
    st.session_state["loading_state"] = False

# 3. Sidebar Navigation & Status
with st.sidebar:
    st.markdown("## 🛡️ Incident Response Agent")
    st.caption("AI-Powered SRE Console with Long-Term Memory")
    st.markdown("---")

    # Navigation Menu
    nav_options = ["Dashboard", "Simulator", "War Room", "Post-Mortem", "Analytics"]
    if st.session_state.get("selected_page") not in nav_options:
        st.session_state["selected_page"] = "Dashboard"

    st.radio(
        "Navigation",
        options=nav_options,
        key="selected_page",
    )

    st.markdown("---")

    # Sidebar Status Indicators
    st.markdown("#### System Telemetry")

    # System Status Indicator
    is_live = api_client.is_backend_live
    st.markdown(render_system_status_pill(is_live), unsafe_allow_html=True)
    st.write("")

    # Memory ON/OFF Toggle
    mem_enabled = st.session_state.get("memory_enabled", True)
    if (
        "sidebar_memory_toggle" in st.session_state
        and st.session_state["sidebar_memory_toggle"] != mem_enabled
    ):
        st.session_state["sidebar_memory_toggle"] = mem_enabled

    new_mem = st.toggle(
        "🧠 Hindsight Memory",
        value=mem_enabled,
        help="Enable/disable retrieval of historical incident knowledge from Hindsight",
        key="sidebar_memory_toggle",
    )

    if new_mem != mem_enabled:
        st.session_state["memory_enabled"] = new_mem
        if "sim_memory_toggle" in st.session_state:
            st.session_state["sim_memory_toggle"] = new_mem
        api_client.set_memory_status(new_mem)
        st.toast(f"Hindsight memory {'enabled' if new_mem else 'disabled'}")
        st.rerun()

    st.markdown(render_memory_badge(new_mem), unsafe_allow_html=True)

    # Active Incident Quick Badge in Sidebar
    active_inc: Optional[Incident] = st.session_state.get("current_incident")
    if active_inc:
        st.markdown("---")
        st.markdown("#### Active Incident Target")
        st.caption(f"**{active_inc.id}** — `{active_inc.service}`")
        st.markdown(
            f"{render_severity_badge(active_inc.severity)} &nbsp; {render_status_badge(active_inc.status)}",
            unsafe_allow_html=True,
        )

# 4. Page Dispatcher
page = st.session_state["selected_page"]

if page == "Dashboard":
    render_dashboard()

elif page == "Simulator":
    render_simulator()

elif page == "War Room":
    st.markdown("## 🚨 Incident War Room")
    st.caption("Deep-dive investigation, hypothesis ranking, and human-in-the-loop approval actions *(Owned by P5)*")
    st.info("🚧 **Coming Soon**: The Incident War Room provides real-time collaborative triage, hypothesis verification, and live runbook execution *(Under development by team member P5)*.")

    active_inc: Optional[Incident] = st.session_state.get("current_incident")
    if active_inc:
        with st.container():
            st.markdown(f"### Target Incident: {active_inc.id} ({active_inc.service})")
            st.markdown(f"**Symptoms:** {active_inc.symptoms}")
            if active_inc.root_cause:
                st.markdown(f"**Identified Root Cause:** `{active_inc.root_cause}`")
            if active_inc.recommendation:
                st.markdown(f"**Top Hypothesis:** `{active_inc.recommendation.hypothesis}`")
                st.markdown(f"**Recommended Runbook:** `{active_inc.recommendation.runbook}`")

elif page == "Post-Mortem":
    st.markdown("## 📝 Incident Post-Mortem")
    st.caption("Automated post-incident root cause analysis & Hindsight retention *(Owned by P6)*")
    st.info("🚧 **Coming Soon**: The Post-Mortem studio automatically generates incident post-mortems, root cause summaries, and Hindsight knowledge retention loops *(Under development by team member P6)*.")

elif page == "Analytics":
    st.markdown("## 📈 Incident Analytics")
    st.caption("MTTR benchmarks, memory-enabled vs disabled impact, and recurring service trends *(Owned by P6)*")
    st.info("🚧 **Coming Soon**: Advanced operational KPIs, MTTR benchmarks (Memory ON vs Memory OFF), and cross-service reliability analytics are under development by team member P6.")
