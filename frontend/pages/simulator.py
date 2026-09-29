"""
Simulator Page Component for Outage Simulation & Memory Comparison (P4).
Injects failure scenarios, compares Memory ON vs Memory OFF, and triggers simulated actions.
"""

from typing import List, Optional
import time
import streamlit as st

from api_client import api_client
from components.badges import render_severity_badge
from components.cards import render_scenario_card
from types import Incident, SimulationScenario


def render_simulator():
    """Main render function for the Outage Simulator."""
    st.markdown("## 🧪 Outage Simulator & Memory Lab")
    st.caption("Inject production failure scenarios and compare AI incident diagnosis with Memory ON vs OFF")

    scenarios: List[SimulationScenario] = api_client.get_simulation_scenarios()
    scenario_titles = [f"{s.name} ({s.service} — {s.expected_severity})" for s in scenarios]

    col1, col2 = st.columns([1.6, 1.4])

    with col1:
        st.subheader("1. Select Outage Scenario")
        scenario_idx = st.selectbox(
            "Available Pre-configured Scenarios",
            range(len(scenarios)),
            format_func=lambda i: scenario_titles[i],
            key="sim_scenario_select",
        )
        selected_scenario = scenarios[scenario_idx]
        st.session_state["selected_scenario"] = selected_scenario

        render_scenario_card(selected_scenario)

        st.subheader("2. Operational Memory Configuration")
        mem_enabled = st.session_state.get("memory_enabled", True)

        mem_col1, mem_col2 = st.columns([1, 1])
        with mem_col1:
            new_mem = st.toggle(
                "🧠 Enable Hindsight Operational Memory",
                value=mem_enabled,
                key="sim_mem_toggle",
            )
            if new_mem != mem_enabled:
                st.session_state["memory_enabled"] = new_mem
                api_client.set_memory_state(new_mem)
                st.rerun()

        with mem_col2:
            if new_mem:
                st.success("● **Memory ON**: Agent retrieves historical incidents, proven runbooks, and past failed fixes.")
            else:
                st.warning("○ **Memory OFF**: Agent sees only current metrics and relies on generic LLM guesswork.")

        st.markdown("---")

        action_col1, action_col2 = st.columns([2, 1])

        with action_col1:
            if st.button("🚀 Trigger Outage Simulation", type="primary", use_container_width=True):
                st.session_state["loading_state"] = True

                with st.status(f"Simulating Outage: {selected_scenario.name}...", expanded=True) as status_box:
                    st.write("📡 Ingesting alert telemetry...")
                    time.sleep(0.4)
                    st.write(f"⚖️ Normalizing impact: classified as **{selected_scenario.expected_severity}**")
                    time.sleep(0.4)

                    if new_mem:
                        st.write("🧠 Querying Hindsight operational memory...")
                        time.sleep(0.5)
                        st.write(f"🎯 Historical match found: **{selected_scenario.expected_matching_incident}**")
                    else:
                        st.write("⚪ Memory disabled: skipping Hindsight recall...")
                        time.sleep(0.3)

                    st.write("🔍 Running agent investigation & hypothesis generation...")
                    time.sleep(0.5)

                    res = api_client.trigger_simulation(selected_scenario.id)
                    status_box.update(label="Simulation Pipeline Completed!", state="complete", expanded=False)

                st.session_state["simulation_result"] = {
                    "scenario": selected_scenario,
                    "memory_used": new_mem,
                    "response": res,
                    "timestamp": time.strftime("%H:%M:%S UTC"),
                }

                # Update current incident in session state
                incidents = api_client.get_incidents(service=selected_scenario.service)
                if incidents:
                    st.session_state["current_incident"] = incidents[0]

                st.toast(f"Outage triggered for {selected_scenario.service}!", icon="🚀")
                st.rerun()

        with action_col2:
            if st.button("🔄 Reset Demo State", use_container_width=True):
                with st.spinner("Resetting demo state..."):
                    api_client.reset_simulation()
                    st.session_state["simulation_result"] = None
                    st.session_state["current_incident"] = None
                    st.toast("Demo state and database reset to baseline.", icon="🔄")
                    st.rerun()

    with col2:
        st.subheader("Simulation Results & Telemetry")
        sim_res = st.session_state.get("simulation_result")

        if sim_res:
            sc: SimulationScenario = sim_res["scenario"]
            mem_used: bool = sim_res["memory_used"]

            st.markdown(
                f"""
                <div style="border: 1px solid #22c55e; background: rgba(34, 197, 94, 0.08); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <div style="font-weight: 700; color: #4ade80; font-size: 15px; margin-bottom: 4px;">
                        ✓ Outage Active: {sc.name}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Executed at {sim_res['timestamp']} | Service: <strong>{sc.service}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("#### Diagnosis Comparison")
            if mem_used:
                st.markdown(
                    f"""
                    > **🧠 Memory-Grounded Output:**
                    >
                    > - **Root Cause:** Identifies specific failure pattern matching `{sc.expected_matching_incident}`.
                    > - **Recommended Runbook:** Pinpoints verified mitigation runbook.
                    > - **Safety Warnings:** Flags previously attempted fixes that failed in past incidents to avoid duplicate outages.
                    """
                )
            else:
                st.markdown(
                    """
                    > **⚪ Generic LLM Output (No Memory):**
                    >
                    > - **Root Cause:** Generic hypotheses with lower confidence score.
                    > - **Runbook:** Generic restart or inspect logs without historical verification.
                    > - **Blind Spots:** No memory of past failed attempts, risking repeated mistakes.
                    """
                )

            st.markdown("---")
            if st.button("Inspect in War Room →", type="primary", use_container_width=True, key="btn_sim_to_war"):
                st.session_state["selected_page"] = "War Room"
                st.rerun()
        else:
            st.info("Select a scenario and click **'Trigger Outage Simulation'** to generate a live incident diagnosis.")


if __name__ == "__main__":
    render_simulator()
