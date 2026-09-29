"""
Outage Simulator - Foundation Stub (P4).
Full implementation will follow in subsequent task.
"""

import streamlit as st
import sys
from pathlib import Path

# Ensure frontend root is on sys.path for direct page runs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_client import api_client
from components.header import render_header
from mocks.mock_data import MOCK_SCENARIOS

st.set_page_config(
    page_title="Outage Simulator",
    page_icon="🧪",
    layout="wide",
)

render_header(title="Outage Simulator", subtitle="Pre-configured Outage Scenarios & Memory ON/OFF Testing")

st.info("🚧 **Simulator Foundation Ready**: The foundation and API client bindings are established. Full scenario injectors and Memory ON/OFF comparison triggers will be implemented in the next step.")

with st.expander("🧪 Pre-configured Scenarios Available", expanded=True):
    st.write(f"Loaded **{len(MOCK_SCENARIOS)}** test outage scenarios:")
    for sc in MOCK_SCENARIOS:
        st.markdown(f"- **{sc['title']}** (`{sc['service']}`) — *{sc['severity']}*")
