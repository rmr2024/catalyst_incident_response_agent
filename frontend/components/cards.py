"""
Card layout components for incidents, recommendations, and scenarios.
"""

from typing import Optional
import streamlit as st

from components.badges import render_outcome_badge, render_severity_badge, render_status_badge
from types import Incident, Recommendation, SimulationScenario
from utils.helpers import format_timestamp


def render_incident_card(incident: Incident, is_selected: bool = False):
    """Render an incident summary card inside a container."""
    border_style = "2px solid #3b82f6" if is_selected else "1px solid #334155"
    bg_style = "rgba(30, 41, 59, 0.7)" if is_selected else "rgba(15, 23, 42, 0.6)"

    with st.container():
        st.markdown(
            f"""
            <div style="border: {border_style}; background: {bg_style}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div>
                        <span style="font-weight: 700; color: #f8fafc; font-size: 14px;">{incident.id}</span>
                        <span style="margin-left: 8px; color: #94a3b8; font-size: 13px;">[{incident.service}]</span>
                    </div>
                    <div>
                        {render_severity_badge(incident.severity)}
                        &nbsp;
                        {render_status_badge(incident.status)}
                    </div>
                </div>
                <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 6px;">
                    {incident.title}
                </div>
                <div style="display: flex; justify-content: space-between; color: #64748b; font-size: 11px;">
                    <span>Started: {format_timestamp(incident.started_at)}</span>
                    <span>Affected Users: {incident.affected_users or '—'}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_scenario_card(scenario: SimulationScenario):
    """Render details of a simulation scenario."""
    with st.container():
        st.markdown(
            f"""
            <div style="border: 1px solid #3b82f644; background: rgba(30, 41, 59, 0.5); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 700; font-size: 15px; color: #60a5fa;">{scenario.name}</span>
                    {render_severity_badge(scenario.expected_severity)}
                </div>
                <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 8px;">
                    {scenario.description}
                </div>
                <div style="display: flex; gap: 16px; font-size: 12px; color: #94a3b8;">
                    <span>Target Service: <strong style="color: #f1f5f9;">{scenario.service}</strong></span>
                    <span>Expected Match: <strong style="color: #f1f5f9;">{scenario.expected_matching_incident}</strong></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_recommendation_card(rec: Optional[Recommendation]):
    """Render structured recommendation card with hypotheses and evidence."""
    if not rec:
        st.info("No recommendation generated yet.")
        return

    with st.container():
        st.markdown(
            f"""
            <div style="border-left: 4px solid #8b5cf6; background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: 4px; margin-bottom: 12px;">
                <div style="font-size: 11px; text-transform: uppercase; color: #a78bfa; font-weight: 700; letter-spacing: 0.5px;">Top Root Cause Hypothesis</div>
                <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-top: 4px;">{rec.hypothesis}</div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Confidence Score: <strong>{rec.confidence * 100:.0f}%</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📋 Recommended Steps:**")
            for idx, step in enumerate(rec.recommended_steps, 1):
                st.markdown(f"{idx}. {step}")

        with col2:
            st.markdown(f"**📖 Recommended Runbook:** `{rec.runbook}`")
            if rec.failed_before:
                st.markdown("**⚠️ What to AVOID (Past Failed Attempts):**")
                for avoid in rec.failed_before:
                    st.markdown(f"- ❌ *{avoid}*")
