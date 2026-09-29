"""
Header component for the Streamlit application.
Renders branding, backend status indicator, and Hindsight Memory toggle.
"""

import streamlit as st
from api_client import api_client


def render_header(title: str = "Catalyst Incident Response Agent", subtitle: str = ""):
    """Render the standard top header across all pages."""
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.markdown(f"### 🛡️ {title}")
        if subtitle:
            st.caption(subtitle)

    with col2:
        # Check backend live status
        is_live = api_client.check_health().get("ok", False)
        if is_live:
            st.markdown(
                '<div style="background-color: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; border-radius: 8px; padding: 6px 12px; text-align: center; color: #4ade80; font-size: 13px; font-weight: 500;">● Backend Live</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background-color: rgba(234, 179, 8, 0.15); border: 1px solid #eab308; border-radius: 8px; padding: 6px 12px; text-align: center; color: #facc15; font-size: 13px; font-weight: 500;">▲ Mock Mode</div>',
                unsafe_allow_html=True,
            )

    with col3:
        # Memory toggle
        if "memory_enabled" not in st.session_state:
            st.session_state["memory_enabled"] = api_client.get_memory_status()

        mem_on = st.toggle(
            "🧠 Memory",
            value=st.session_state["memory_enabled"],
            help="Toggle Hindsight operational memory recall on/off",
            key="header_memory_toggle",
        )

        if mem_on != st.session_state["memory_enabled"]:
            st.session_state["memory_enabled"] = mem_on
            api_client.toggle_memory(mem_on)
            st.toast(f"Hindsight memory {'enabled' if mem_on else 'disabled'}")

    st.markdown("---")
