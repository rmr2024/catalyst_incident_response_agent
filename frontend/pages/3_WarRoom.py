"""
Direct entry point for Streamlit multipage router: War Room.
"""

import sys
from pathlib import Path

# Ensure frontend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from pages.war_room import render_war_room

st.set_page_config(page_title="War Room", page_icon="🚨", layout="wide")


def _back_to_dashboard() -> None:
    st.switch_page("pages/1_Dashboard.py")


render_war_room(st.session_state.get("war_room_incident_id"), on_back=_back_to_dashboard)
