"""
Incident Response Agent - Main Console Shell.
Streamlit application root coordinating sidebar navigation, session state, and page dispatching.
Provides seamless navigation between:
1. Dashboard (Fully functional)
2. Simulator (Fully functional)
3. War Room (Fully functional)
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
from pages.war_room import render_war_room
from models import Incident, SimulationScenario
from utils.theme import apply_theme, render_theme_toggle_widget

# 1. Page Configuration
st.set_page_config(
    page_title="Incident Response Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Theme Mode (defaults to dark for DevOps console)
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

# Apply active theme CSS & component styling overrides
apply_theme()

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

    # Dark / Light Theme Toggle
    render_theme_toggle_widget()
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

    # Memory Status Indicator
    mem_enabled = st.session_state.get("memory_enabled", True)
    st.markdown(render_memory_badge(mem_enabled), unsafe_allow_html=True)

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
    target_incident = st.session_state.get("war_room_incident_id")
    if not target_incident:
        active = st.session_state.get("current_incident")
        target_incident = getattr(active, "id", None)
    render_war_room(target_incident)

elif page == "Post-Mortem":
    st.markdown("## 📝 Incident Post-Mortem")
    st.caption("Automated post-incident root cause analysis & Hindsight retention *(Owned by P6)*")
    st.info("🚧 **Coming Soon**: The Post-Mortem studio automatically generates incident post-mortems, root cause summaries, and Hindsight knowledge retention loops *(Under development by team member P6)*.")

elif page == "Analytics":
    st.markdown("## 📈 Incident Analytics")
    st.caption("MTTR benchmarks, memory-enabled vs disabled impact, and recurring service trends *(Owned by P6)*")
    st.info("🚧 **Coming Soon**: Advanced operational KPIs, MTTR benchmarks (Memory ON vs Memory OFF), and cross-service reliability analytics are under development by team member P6.")
