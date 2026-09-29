"""
Theme management utilities for Streamlit SRE Console.
Provides Dark and Light theme styling, CSS custom property definitions,
and native Streamlit component styling overrides.
"""

from typing import Literal
import streamlit as st

ThemeMode = Literal["dark", "light"]

DARK_THEME_CSS = """
:root, .stApp {
    --bg-primary: #0f172a;
    --bg-surface: #1e293b;
    --bg-card: rgba(30, 41, 59, 0.7);
    --bg-card-selected: rgba(30, 41, 59, 0.95);
    --card-border: #334155;
    --card-border-selected: #3b82f6;
    --border-color: #334155;
    --border-accent: #3b82f6;
    --text-primary: #f8fafc;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --callout-bg: rgba(30, 58, 138, 0.25);
    --callout-border: #3b82f6;
    --harness-bg: rgba(30, 41, 59, 0.35);
    --harness-border: #475569;
    --hist-bg: rgba(30, 58, 138, 0.2);
    --hist-border: #3b82f6;
    --generic-bg: rgba(51, 65, 85, 0.2);
    --generic-border: #64748b;
    --fix-bg: rgba(34, 197, 94, 0.1);
    --fix-border: rgba(34, 197, 94, 0.3);
    --fix-text: #4ade80;
    --warn-text: #facc15;
    --badge-blue: #60a5fa;
}

/* Dark Mode App & Container Overrides */
.stApp {
    background-color: #0f172a !important;
    color: #f8fafc !important;
}

[data-testid="stSidebar"] {
    background-color: #1e293b !important;
    border-right: 1px solid #334155 !important;
}

[data-testid="stHeader"] {
    background-color: rgba(15, 23, 42, 0.85) !important;
}

/* Headings and body */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: #f8fafc !important;
}

.stApp p, .stApp li {
    color: #cbd5e1 !important;
}

.stApp [data-testid="stCaptionContainer"] p {
    color: #94a3b8 !important;
}

/* Metrics in Dark Mode */
[data-testid="stMetric"] {
    background-color: rgba(30, 41, 59, 0.6) !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
}

[data-testid="stMetricValue"] {
    color: #f8fafc !important;
}

[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-weight: 600 !important;
}

/* Expanders in Dark Mode */
[data-testid="stExpander"] {
    background-color: rgba(30, 41, 59, 0.5) !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}

/* Buttons in Dark Mode */
.stButton > button:not([kind="primary"]) {
    background-color: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #475569 !important;
}

.stButton > button:not([kind="primary"]):hover {
    background-color: #334155 !important;
    border-color: #64748b !important;
    color: #ffffff !important;
}

hr {
    border-color: #334155 !important;
}
"""

LIGHT_THEME_CSS = """
:root, .stApp {
    --bg-primary: #f8fafc;
    --bg-surface: #ffffff;
    --bg-card: #ffffff;
    --bg-card-selected: #eff6ff;
    --card-border: #e2e8f0;
    --card-border-selected: #2563eb;
    --border-color: #e2e8f0;
    --border-accent: #2563eb;
    --text-primary: #0f172a;
    --text-secondary: #334155;
    --text-muted: #64748b;
    --callout-bg: rgba(219, 234, 254, 0.6);
    --callout-border: #3b82f6;
    --harness-bg: rgba(241, 245, 249, 0.85);
    --harness-border: #cbd5e1;
    --hist-bg: rgba(219, 234, 254, 0.5);
    --hist-border: #2563eb;
    --generic-bg: rgba(241, 245, 249, 0.9);
    --generic-border: #94a3b8;
    --fix-bg: rgba(220, 252, 231, 0.85);
    --fix-border: #86efac;
    --fix-text: #15803d;
    --warn-text: #b45309;
    --badge-blue: #1d4ed8;
}

/* Light Mode App & Container Overrides */
.stApp {
    background-color: #f8fafc !important;
    color: #0f172a !important;
}

[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span {
    color: #1e293b !important;
}

[data-testid="stHeader"] {
    background-color: rgba(248, 250, 252, 0.85) !important;
}

/* Headings and body */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: #0f172a !important;
}

.stApp p, .stApp li {
    color: #334155 !important;
}

.stApp [data-testid="stCaptionContainer"] p {
    color: #64748b !important;
}

/* Metrics in Light Mode */
[data-testid="stMetric"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
}

[data-testid="stMetricValue"] {
    color: #0f172a !important;
}

[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-weight: 600 !important;
}

/* Expanders in Light Mode */
[data-testid="stExpander"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
}

/* Buttons in Light Mode */
.stButton > button:not([kind="primary"]) {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}

.stButton > button:not([kind="primary"]):hover {
    background-color: #f1f5f9 !important;
    border-color: #94a3b8 !important;
    color: #0f172a !important;
}

/* Inputs in Light Mode */
[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border-color: #cbd5e1 !important;
    color: #0f172a !important;
}

[data-testid="stRadio"] label {
    color: #1e293b !important;
}

hr {
    border-color: #e2e8f0 !important;
}
"""

COMMON_CSS = """
/* Always hide default multipage auto-navigation */
[data-testid="stSidebarNav"],
section[data-testid="stSidebarNav"],
div[data-testid="stSidebarNav"] {
    display: none !important;
}

/* Clean button border radius and smooth hover */
.stButton > button {
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: all 0.15s ease-in-out !important;
}

/* Card hover elevation */
.sre-card {
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.sre-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
"""


def apply_theme():
    """Inject active theme CSS into Streamlit application."""
    mode = st.session_state.get("theme_mode", "dark")
    active_theme_css = LIGHT_THEME_CSS if mode == "light" else DARK_THEME_CSS

    st.markdown(
        f"""
        <style>
            {COMMON_CSS}
            {active_theme_css}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_theme_toggle_widget():
    """Render a clean Dark / Light mode toggle switch in the sidebar."""
    current_mode = st.session_state.get("theme_mode", "dark")
    is_light = (current_mode == "light")

    col1, col2 = st.columns([1.6, 1])
    with col1:
        icon_label = "☀️ Light Mode" if is_light else "🌙 Dark Mode"
        st.markdown(
            f'<div style="font-size: 13px; font-weight: 600; padding-top: 4px; color: var(--text-primary, #f8fafc);">'
            f'{icon_label}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col2:
        new_val = st.toggle(
            "Theme Mode",
            value=is_light,
            key="theme_switch_toggle",
            label_visibility="collapsed",
            help="Switch console between Dark and Light appearance",
        )
        target_mode = "light" if new_val else "dark"
        if target_mode != current_mode:
            st.session_state["theme_mode"] = target_mode
            st.rerun()
