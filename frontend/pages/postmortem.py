"""
Incident Response Agent - Post-Mortem Studio (P6).

Automated post-incident root cause analysis and Hindsight knowledge retention.

Flow:
  1. Select a resolved incident.
  2. Draft a post-mortem (LLM-generated via POST /incidents/{id}/postmortem/draft).
  3. Review the draft — summary, timeline, root cause, lessons.
  4. Approve to retain to Hindsight memory (POST /incidents/{id}/postmortem/approve).
  5. Confirmation shows what was learned and stored.
"""

from typing import Optional
import streamlit as st

from services.api_client import api_client
from components.badges import render_severity_badge, render_status_badge, render_memory_badge
from utils.helpers import format_timestamp, navigate_to


def render_postmortem():
    """Main render function for the Post-Mortem Studio."""

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    st.markdown("## 📝 Post-Mortem Studio")
    st.caption(
        "Generate AI-powered post-mortems and retain lessons learned to Hindsight long-term memory."
    )

    mem_enabled = st.session_state.get("memory_enabled", True)
    st.markdown(render_memory_badge(mem_enabled), unsafe_allow_html=True)
    st.write("")

    # ------------------------------------------------------------------
    # Step 1 — Select Incident
    # ------------------------------------------------------------------
    st.markdown("### Step 1 — Select Incident")

    incidents = api_client.get_incidents(limit=50)
    resolved = [i for i in incidents if i.status in ("resolved", "mitigated")]
    all_incidents = incidents  # allow drafting for any incident

    if not all_incidents:
        st.warning("No incidents found. Trigger a simulation from the Simulator page first.")
        if st.button("Go to Simulator"):
            navigate_to("Simulator")
        return

    # Build dropdown options
    options = {
        f"{i.id} — {i.service} [{i.severity}] {i.status}": i.id for i in all_incidents
    }

    # Pre-select from session state if War Room passed an incident
    preselect = st.session_state.get("war_room_incident_id") or (
        all_incidents[0].id if all_incidents else None
    )
    preselect_label = next(
        (lbl for lbl, iid in options.items() if iid == preselect), list(options.keys())[0]
    )

    selected_label = st.selectbox(
        "Choose incident",
        options=list(options.keys()),
        index=list(options.keys()).index(preselect_label),
    )
    incident_id = options[selected_label]

    # Show incident card
    selected_inc = next((i for i in all_incidents if i.id == incident_id), None)
    if selected_inc:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                render_severity_badge(selected_inc.severity), unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                render_status_badge(selected_inc.status), unsafe_allow_html=True
            )
        with c3:
            novel_tag = "⚠️ Novel" if selected_inc.is_novel else "📚 Known Pattern"
            st.caption(novel_tag)
        st.caption(f"**Service:** `{selected_inc.service}` &nbsp;|&nbsp; **Symptoms:** {selected_inc.symptoms[:120]}")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Step 2 — Draft Post-Mortem
    # ------------------------------------------------------------------
    st.markdown("### Step 2 — Generate Draft")

    # Persist draft in session state keyed by incident_id
    draft_key = f"pm_draft_{incident_id}"
    approved_key = f"pm_approved_{incident_id}"

    already_approved = st.session_state.get(approved_key, False)

    if already_approved:
        st.success(
            f"✅ Post-mortem for **{incident_id}** has already been approved and retained to Hindsight memory."
        )
        if st.button("Draft Another Post-Mortem"):
            st.session_state.pop(approved_key, None)
            st.session_state.pop(draft_key, None)
            st.rerun()
        return

    col_draft, col_clear = st.columns([2, 1])
    with col_draft:
        draft_btn = st.button(
            "🤖 Generate AI Post-Mortem Draft",
            type="primary",
            use_container_width=True,
        )
    with col_clear:
        if st.button("🗑️ Clear Draft", use_container_width=True):
            st.session_state.pop(draft_key, None)
            st.rerun()

    if draft_btn:
        with st.spinner("Generating post-mortem draft with AI… this may take a few seconds."):
            draft = api_client.draft_postmortem(incident_id)
            st.session_state[draft_key] = draft

    draft = st.session_state.get(draft_key)

    if not draft:
        st.info(
            "Click **Generate AI Post-Mortem Draft** to create a structured post-mortem "
            "based on the incident timeline, agent investigation, and memory-backed evidence."
        )
        return

    st.markdown("---")

    # ------------------------------------------------------------------
    # Step 3 — Review Draft
    # ------------------------------------------------------------------
    st.markdown("### Step 3 — Review Draft")

    # Summary
    with st.container():
        st.markdown("#### 📋 Summary")
        st.markdown(
            f'<div style="background: rgba(59,130,246,0.08); border-left: 3px solid #3b82f6; '
            f'padding: 12px 16px; border-radius: 4px; color: inherit;">'
            f'{draft.get("summary", "—")}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # Impact + Root Cause side by side
    imp_col, rc_col = st.columns(2)
    with imp_col:
        st.markdown("#### 💥 Impact")
        st.markdown(
            f'<div style="background: rgba(239,68,68,0.08); border-left: 3px solid #ef4444; '
            f'padding: 10px 14px; border-radius: 4px; color: inherit;">'
            f'{draft.get("impact", "—")}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with rc_col:
        st.markdown("#### 🔍 Root Cause")
        st.markdown(
            f'<div style="background: rgba(234,179,8,0.08); border-left: 3px solid #eab308; '
            f'padding: 10px 14px; border-radius: 4px; color: inherit;">'
            f'{draft.get("root_cause", "—")}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # Resolution
    st.markdown("#### ✅ Resolution")
    st.markdown(
        f'<div style="background: rgba(34,197,94,0.08); border-left: 3px solid #22c55e; '
        f'padding: 10px 14px; border-radius: 4px; color: inherit;">'
        f'{draft.get("resolution", "—")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.write("")

    # Timeline
    timeline = draft.get("timeline") or []
    if timeline:
        with st.expander("🕐 Incident Timeline", expanded=False):
            for entry in timeline:
                st.markdown(f"- {entry}")

    st.write("")

    # Lessons Learned
    lessons = draft.get("lessons") or []
    st.markdown("#### 🎓 Lessons Learned")
    if lessons:
        for lesson in lessons:
            st.markdown(
                f'<div style="display: flex; align-items: flex-start; gap: 8px; '
                f'padding: 6px 0; border-bottom: 1px solid rgba(148,163,184,0.15);">'
                f'<span style="color: #22c55e; font-weight: 700; margin-top: 1px;">▸</span>'
                f'<span>{lesson}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No lessons extracted.")

    st.write("")
    st.markdown("---")

    # ------------------------------------------------------------------
    # Step 4 — Approve and Retain to Hindsight
    # ------------------------------------------------------------------
    st.markdown("### Step 4 — Approve & Retain to Memory")

    st.markdown(
        f'<div style="background: rgba(59,130,246,0.08); border: 1px solid #3b82f666; '
        f'border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">'
        f'🧠 Approving this post-mortem will retain the lessons, root cause, and resolution '
        f'to <strong>Hindsight long-term memory</strong>. Future similar incidents will '
        f'benefit from this knowledge automatically.'
        f'</div>',
        unsafe_allow_html=True,
    )

    approve_col, reject_col = st.columns([2, 1])
    with approve_col:
        if st.button(
            "✅ Approve & Retain to Hindsight",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Retaining post-mortem to Hindsight memory…"):
                result = api_client.approve_postmortem(incident_id)
            if result.get("retained") or result.get("status") == "approved":
                st.session_state[approved_key] = True
                st.session_state.pop(draft_key, None)
                st.success(
                    f"✅ Post-mortem approved and retained to Hindsight! "
                    f"Future incidents on `{selected_inc.service if selected_inc else incident_id}` "
                    f"will recall these lessons automatically."
                )
                st.balloons()
                st.rerun()
            else:
                st.error(f"Retention failed: {result}")

    with reject_col:
        if st.button("❌ Discard Draft", use_container_width=True):
            st.session_state.pop(draft_key, None)
            st.warning("Draft discarded. Generate a new one when ready.")
            st.rerun()
