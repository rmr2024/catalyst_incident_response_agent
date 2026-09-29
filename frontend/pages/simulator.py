"""
Incident Response Agent - Outage Simulation Sandbox (P4).
100% Pure Python + Streamlit safe demonstration environment.
Demonstrates:
1. Scenario Selector (Database Pool Exhaustion, Memory Leak, Bad Deployment, Cache Stampede, Novel Incident)
2. Scenario Cards displaying Name, Description, Service, Symptoms, Expected Severity
3. Memory Toggle (Memory ON / Memory OFF stored in st.session_state.memory_enabled)
4. Run Simulation: calls api_client.trigger_simulation(), shows spinner, displays generated incident,
   severity, service, symptoms, likely root cause, historical matches, recommendations, and memory status.
   - Memory ON: Demonstrates historical memory recall (similar incidents, historical evidence, previous successful fix, recommended runbook)
   - Memory OFF: Displays generic investigation result without historical incident context
5. Reset Simulation: resets selected scenario, simulation result, memory state, errors, and status
6. Safe isolation: All operations are simulated and never touch production environments.
"""

from typing import List, Optional
import streamlit as st

from services.api_client import api_client
from components.badges import (
    render_memory_badge,
    render_outcome_badge,
    render_severity_badge,
    render_status_badge,
)
from components.tables import render_similar_incidents_table
try:
    from models import Incident, Recommendation, SimilarIncident, SimulationResponse, SimulationScenario
except ImportError:
    from types import Incident, Recommendation, SimilarIncident, SimulationResponse, SimulationScenario
from utils.helpers import format_timestamp, get_severity_color, get_status_color, navigate_to


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


def render_simulator():
    """Main render function for the Incident Simulation Sandbox."""

    # ---------------------------------------------------------
    # Header & Sandbox Safety Notice
    # ---------------------------------------------------------
    st.markdown("## 🧪 Safe Incident Simulation Sandbox")
    st.caption("Safely simulate production outages and compare autonomous root cause diagnosis with Memory ON vs Memory OFF.")

    st.info(
        "🛡️ **Safety Sandbox**: All operations, remediations, and telemetry streams are strictly simulated. "
        "No real production systems, customer databases, or infrastructure are modified."
    )

    # Fetch available simulation scenarios from API client
    scenarios: List[SimulationScenario] = api_client.get_simulation_scenarios()
    scenario_names = [s.name for s in scenarios]

    # Initialize Session State
    if "memory_enabled" not in st.session_state:
        st.session_state["memory_enabled"] = api_client.get_memory_status()

    if "selected_scenario_index" not in st.session_state:
        st.session_state["selected_scenario_index"] = 0

    if "simulation_result" not in st.session_state:
        st.session_state["simulation_result"] = None

    if "sim_feedback" not in st.session_state:
        st.session_state["sim_feedback"] = None

    st.write("")

    # ---------------------------------------------------------
    # 1. Scenario Selector & 2. Memory Toggle Row
    # ---------------------------------------------------------
    sel_col, toggle_col = st.columns([2.5, 1.5])

    with sel_col:
        st.markdown("### 1. Select Outage Scenario")
        current_idx = st.session_state.get("selected_scenario_index", 0)
        if current_idx >= len(scenarios):
            current_idx = 0

        def _format_scenario(val) -> str:
            try:
                i = int(val)
                return f"{i+1}. {scenario_names[i]} ({scenarios[i].service})"
            except Exception:
                return str(val)

        selected_idx = st.selectbox(
            "Available Pre-configured Scenarios",
            list(range(len(scenarios))),
            index=current_idx,
            format_func=_format_scenario,
            key="sim_scenario_dropdown",
        )
        selected_idx = int(selected_idx)
        st.session_state["selected_scenario_index"] = selected_idx
        selected_scenario: SimulationScenario = scenarios[selected_idx]
        st.session_state["selected_scenario"] = selected_scenario

    with toggle_col:
        st.markdown("### 2. Memory State")
        current_mem = st.session_state.get("memory_enabled", True)

        new_mem = st.toggle(
            "🧠 Memory ON / Memory OFF",
            value=current_mem,
            help="Toggle Hindsight long-term incident memory recall on or off",
            key="sim_memory_toggle",
        )

        if new_mem != current_mem:
            st.session_state["memory_enabled"] = new_mem
            api_client.set_memory_status(new_mem)
            st.toast(f"Hindsight memory {'enabled' if new_mem else 'disabled'}")
            st.rerun()

        if new_mem:
            st.markdown(
                '<div style="background-color: rgba(59, 130, 246, 0.12); border: 1px solid #3b82f6; '
                'border-radius: 6px; padding: 6px 12px; text-align: center; color: #60a5fa; '
                'font-size: 13px; font-weight: 700;">🧠 Memory ON</div>',
                unsafe_allow_html=True,
            )
            st.caption("Recalls past incident matches, historical evidence, previous fixes, and verified runbooks.")
        else:
            st.markdown(
                '<div style="background-color: rgba(148, 163, 184, 0.12); border: 1px solid #64748b; '
                'border-radius: 6px; padding: 6px 12px; text-align: center; color: #94a3b8; '
                'font-size: 13px; font-weight: 700;">⚪ Memory OFF</div>',
                unsafe_allow_html=True,
            )
            st.caption("Operates purely on raw telemetry without historical context or prior incident lessons.")

    # ---------------------------------------------------------
    # Scenario Card Display
    # For every scenario: display Scenario Name, Description, Service, Symptoms, Expected Severity
    # ---------------------------------------------------------
    sev_color = get_severity_color(selected_scenario.expected_severity)
    sev_indicator = _get_severity_indicator(selected_scenario.expected_severity)

    with st.container():
        st.markdown(
            f"""
            <div style="border: 1px solid {sev_color}66; border-left: 5px solid {sev_color}; background: rgba(15, 23, 42, 0.65); border-radius: 8px; padding: 16px; margin-top: 8px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 700; font-size: 16px; color: #f8fafc;">
                        {selected_scenario.name}
                    </span>
                    <span style="background-color: {sev_color}22; color: {sev_color}; border: 1px solid {sev_color}; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 700;">
                        {sev_indicator}
                    </span>
                </div>
                <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 10px;">
                    {selected_scenario.description}
                </div>
                <div style="display: flex; gap: 24px; color: #94a3b8; font-size: 12px; flex-wrap: wrap;">
                    <span>🎯 <strong>Target Service:</strong> <code style="color: #60a5fa;">{selected_scenario.service}</code></span>
                    <span>⚠️ <strong>Symptoms:</strong> <span style="color: #f1f5f9;">{selected_scenario.symptoms}</span></span>
                    <span>🔍 <strong>Expected Match:</strong> <code style="color: #a78bfa;">{selected_scenario.expected_matching_incident}</code></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------
    # Action Controls: Run Simulation & Reset
    # ---------------------------------------------------------
    act_col1, act_col2, act_col3, _ = st.columns([1.5, 1.3, 1.2, 1.8])

    with act_col1:
        run_clicked = st.button(
            "🚀 Run Simulation",
            type="primary",
            use_container_width=True,
            help="Inject selected simulated failure into the incident response pipeline",
        )

    with act_col2:
        reset_clicked = st.button(
            "🔄 Reset Simulation",
            type="secondary",
            use_container_width=True,
            help="Reset simulation state, scenario selection, and clear results",
        )

    with act_col3:
        if st.button("📊 Dashboard ←", use_container_width=True, help="Switch back to Incident Operations Dashboard"):
            navigate_to("Dashboard")

    # Handle Reset Simulation
    if reset_clicked:
        with st.spinner("Resetting simulation sandbox and baseline state..."):
            api_client.reset_simulation()
            st.session_state["simulation_result"] = None
            st.session_state["sim_feedback"] = None
            st.session_state["selected_scenario_index"] = 0
            st.session_state["selected_scenario"] = scenarios[0]
            st.toast("Simulation sandbox reset successfully.", icon="🔄")
            st.rerun()

    # Handle Run Simulation
    if run_clicked:
        with st.spinner(f"Simulating {selected_scenario.name} with Memory {'ON' if new_mem else 'OFF'}..."):
            try:
                # 1. Get selected scenario
                # 2. Get memory ON/OFF state
                # 3. Call api_client.trigger_simulation()
                sim_res: SimulationResponse = api_client.trigger_simulation(
                    selected_scenario,
                    memory_enabled=new_mem,
                )
                st.session_state["simulation_result"] = sim_res

                if sim_res.incident:
                    st.session_state["current_incident"] = sim_res.incident

                st.session_state["sim_feedback"] = {
                    "type": "success",
                    "message": f"Simulation completed successfully for **{selected_scenario.name}**! (Memory {'ON' if new_mem else 'OFF'})",
                }
            except Exception as e:
                st.session_state["sim_feedback"] = {
                    "type": "error",
                    "message": f"Failed to execute simulation: {e}",
                }

    # Display feedback message
    feedback = st.session_state.get("sim_feedback")
    if feedback:
        if feedback.get("type") == "success":
            st.success(feedback.get("message"))
        else:
            st.error(feedback.get("message"))

    st.markdown("---")

    # ---------------------------------------------------------
    # Simulation Results Section
    # Display when simulation_result exists in session_state
    # ---------------------------------------------------------
    sim_res: Optional[SimulationResponse] = st.session_state.get("simulation_result")

    if not sim_res:
        st.info("💡 **Ready to simulate**: Select a failure scenario above and click **'🚀 Run Simulation'** to inspect autonomous agent diagnosis.")
    else:
        inc: Optional[Incident] = sim_res.incident
        if not inc and sim_res.incident_id:
            inc = api_client.get_incident(sim_res.incident_id)

        if not inc:
            st.warning("Simulation response received, but incident details could not be parsed.")
            return

        rec: Optional[Recommendation] = inc.recommendation
        mem_is_active: bool = inc.memory_used

        st.markdown(f"### 📋 Simulation Results: {inc.id}")
        st.caption(f"Autonomous investigation summary for simulated outage on service `{inc.service}`")

        # 12. Display Memory Status Banner
        if mem_is_active:
            st.markdown(
                '<div style="background-color: rgba(59, 130, 246, 0.12); border-left: 4px solid #3b82f6; '
                'border-radius: 6px; padding: 12px; margin-bottom: 16px;">'
                '<strong style="color: #60a5fa;">🧠 Hindsight Long-Term Memory Active (Memory ON)</strong><br>'
                '<span style="color: #cbd5e1; font-size: 13px;">'
                'Agent queried Hindsight incident knowledge graph. Historical failure patterns, previous successful fixes, '
                'and proven runbooks were retrieved and used to diagnose this incident.'
                '</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background-color: rgba(234, 179, 8, 0.12); border-left: 4px solid #eab308; '
                'border-radius: 6px; padding: 12px; margin-bottom: 16px;">'
                '<strong style="color: #facc15;">⚪ Hindsight Memory Disabled (Memory OFF)</strong><br>'
                '<span style="color: #cbd5e1; font-size: 13px;">'
                'Agent executed triage <strong>WITHOUT</strong> historical incident context. Diagnosis is limited to raw telemetry heuristics, '
                'resulting in lower confidence and generic manual triage runbooks.'
                '</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        # 5. Display Generated Incident Metrics Row
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric(label="Incident ID", value=inc.id)
        with m_col2:
            # 6. Display Severity
            st.metric(label="Assigned Severity", value=inc.severity)
        with m_col3:
            # 7. Display Service
            st.metric(label="Target Service", value=inc.service)
        with m_col4:
            conf_val = f"{rec.confidence * 100:.0f}%" if rec else "N/A"
            conf_delta = "+40% via Memory" if mem_is_active else "Low (No Memory)"
            st.metric(label="Hypothesis Confidence", value=conf_val, delta=conf_delta)

        # 8. Display Symptoms
        with st.container():
            st.markdown(f"**⚠️ Incident Symptoms:** {inc.symptoms}")

        # 9. Display Likely Root Cause
        with st.container():
            root_cause_display = inc.root_cause or (rec.hypothesis if rec else "Under Investigation")
            st.markdown(f"**🎯 Likely Root Cause:** `{root_cause_display}`")

        st.markdown("---")

        # ---------------------------------------------------------
        # Memory-Specific Details vs Generic Details
        # ---------------------------------------------------------
        res_col1, res_col2 = st.columns([1.6, 1.4])

        with res_col1:
            # 11. Display Recommendation & Runbook
            st.markdown("#### 📖 Remediation Recommendation")
            if rec:
                st.markdown(f"**Top Hypothesis:** `{rec.hypothesis}`")
                st.markdown(f"**Recommended Runbook:** `{rec.runbook}`")

                st.markdown("**Action Procedure Steps:**")
                for s_idx, step in enumerate(rec.recommended_steps, 1):
                    st.markdown(f"{s_idx}. {step}")

                # Previous Successful Fix (Requirement: Display Previous successful fix when Memory ON)
                if mem_is_active and rec.previous_successful_fix:
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #22c55e66; background: rgba(34, 197, 94, 0.08); border-radius: 6px; padding: 10px; margin-top: 10px; margin-bottom: 10px;">
                            <span style="color: #4ade80; font-weight: 700; font-size: 13px;">✓ Previous Successful Fix (from Hindsight Memory):</span><br>
                            <span style="color: #f1f5f9; font-size: 12px;">{rec.previous_successful_fix}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # What to Avoid / Past Failed Fixes (when Memory ON)
                if mem_is_active and rec.failed_before:
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #ef444466; background: rgba(239, 68, 68, 0.08); border-radius: 6px; padding: 10px; margin-top: 6px;">
                            <span style="color: #f87171; font-weight: 700; font-size: 13px;">⚠️ Past Failed Attempts to AVOID:</span><br>
                            <span style="color: #f1f5f9; font-size: 12px;">{rec.failed_before[0]}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                elif not mem_is_active:
                    st.caption("⚠️ *Memory OFF: Agent cannot recall past failed attempts. Risk of repeating ineffective fixes.*")

        with res_col2:
            # Historical Evidence (Requirement: Display Historical evidence when Memory ON)
            st.markdown("#### 🔬 Investigation Evidence")
            if rec and rec.evidence:
                for ev in rec.evidence:
                    st.markdown(f"- {ev}")
            else:
                st.write("No evidence records available.")

            # 10. Display Historical Matches (Similar Incidents)
            st.markdown("#### 🔍 Historical Incident Matches")
            if mem_is_active:
                if inc.similar_incidents:
                    st.caption(f"Retrieved **{len(inc.similar_incidents)}** past incident(s) from Hindsight memory:")
                    render_similar_incidents_table(inc.similar_incidents)
                else:
                    if inc.is_novel:
                        st.info("🌟 **Novel Incident Signature**: No matching historical incidents found in Hindsight memory above confidence threshold. Human engineer review required.")
                    else:
                        st.write("No prior similar incidents found.")
            else:
                st.warning("⚪ **Historical matches unavailable**: Memory is OFF. Historical incidents cannot be queried or matched.")

        st.markdown("---")

        # Quick navigation to War Room
        nav_col1, nav_col2 = st.columns([1.5, 2])
        with nav_col1:
            if st.button("Enter War Room for Simulated Incident 🚨", type="primary", use_container_width=True):
                st.session_state["current_incident"] = inc
                navigate_to("War Room")


if __name__ == "__main__":
    render_simulator()
