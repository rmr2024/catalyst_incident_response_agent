"""
Incident Response Agent - Frontend Entry Point.
Streamlit multipage application root.
"""

import streamlit as st
from api_client import api_client
from components.header import render_header

st.set_page_config(
    page_title="Incident Response Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_header(
    title="Incident Response Agent",
    subtitle="AI-Powered Operational Incident Response with Long-Term Memory",
)

# Landing overview
st.markdown("""
### Welcome to the Incident Response Console

An AI-powered incident response system that leverages **Hindsight long-term operational memory**
to investigate production outages, retrieve relevant historical incidents, recommend proven runbooks,
and learn from resolved incidents.

> **Central Principle:** An incident response agent should never investigate every outage from scratch.
> It remembers what happened before, what worked, what failed, and what engineers learned.
""")

col1, col2, col3 = st.columns(3)

stats = api_client.get_stats()
with col1:
    st.metric(label="Active Incidents", value=stats.get("active", 0))
with col2:
    st.metric(label="Total Recorded", value=stats.get("total", 0))
with col3:
    st.metric(label="Avg MTTR", value=f"{stats.get('avg_ttr_minutes', 0.0):.1f} min")

st.markdown("---")
st.subheader("Console Navigation")

nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    st.markdown("""
    #### 📊 Dashboard
    Real-time incident feed, severity classification badges, active outage telemetry, and alert triggers.
    """)
    if st.button("Open Dashboard →", use_container_width=True, key="btn_nav_dashboard"):
        st.switch_page("pages/1_Dashboard.py")

with nav_col2:
    st.markdown("""
    #### 🧪 Simulator
    Inject pre-configured production failure scenarios and compare AI diagnosis with **Memory ON vs OFF**.
    """)
    if st.button("Open Simulator →", use_container_width=True, key="btn_nav_simulator"):
        st.switch_page("pages/2_Simulator.py")

with nav_col3:
    st.markdown("""
    #### 🚨 War Room
    Deep-dive investigation view with root-cause prediction, evidence ranking, and human-in-the-loop approval.
    *(Owned by P5)*
    """)
    st.info("Select an active incident from the Dashboard to enter its War Room.")
