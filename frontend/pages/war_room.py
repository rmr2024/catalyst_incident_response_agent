"""
War Room page module: incident investigation, recommendation review, and resolution.

Follows the same page-module contract as `pages/dashboard.py` and
`pages/simulator.py` so it can be dispatched either from the console shell
(`app.py` sidebar navigation) or from the Streamlit multipage route
(`pages/3_WarRoom.py`).

Data is fetched through the central API client and validated against the War
Room contract models in `models.py` (IncidentDetail, AgentEvent, MemoryHit,
FeedbackRequest, ResolveRequest).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure frontend root is on sys.path when executed as a standalone page script
_FRONTEND_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _FRONTEND_ROOT.parent
for _path in (str(_PROJECT_ROOT), str(_FRONTEND_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import streamlit as st

from api_client import api_client
from components.header import render_header
from models import (
    AgentEvent,
    FeedbackRequest,
    IncidentDetail,
    MemoryHit,
    ResolveRequest,
)

TERMINAL_STATUSES = {"resolved", "failed", "rejected"}
REVIEWABLE_STATUSES = {"awaiting_approval", "recommended", "fix_failed"}
RESOLVABLE_STATUSES = {"mitigated", "fix_failed", "failed"}
POLL_SECONDS = 5

# Alert keys surfaced as a distinct "context" block in the UI.
_ALERT_CORE_KEYS = {"service", "message", "severity", "timestamp", "metrics"}


def timeline_key(item: Dict[str, Any]) -> tuple:
    """Stable identity for a timeline row, used to de-duplicate appended events."""
    return (
        str(item.get("ts", "")),
        str(item.get("source", item.get("kind", ""))),
        str(item.get("title", item.get("step", ""))),
        str(item.get("detail", "")),
    )


def format_timestamp(value: Optional[str]) -> str:
    """Render an ISO timestamp for display, tolerating missing values."""
    return value.replace("T", " ").replace("Z", " UTC") if value else "Time unavailable"


def render_timeline_entry(item: Dict[str, Any]) -> None:
    """Render a single unified timeline row."""
    timestamp = format_timestamp(item.get("ts"))
    event_type = item.get("source", item.get("kind", "event"))
    title = item.get("title", item.get("step", ""))
    detail = item.get("detail", "")
    with st.container(border=True):
        time_col, event_col = st.columns([1, 5])
        with time_col:
            st.caption(timestamp)
        with event_col:
            st.markdown(f"**{title or event_type}** · `{event_type}`")
            if detail:
                st.write(detail)


def _select_incident() -> Optional[str]:
    """Prompt for an incident when the War Room is opened without one."""
    st.info("Select an incident to open its War Room.")
    try:
        incidents = api_client.list_incidents(limit=50) or []
    except Exception as error:  # noqa: BLE001 - never crash the console on a fetch failure
        st.error(f"Unable to load incidents: {error}")
        return None

    if not incidents:
        st.info("No incidents are available to open.")
        return None

    by_id = {item.id: item for item in incidents if getattr(item, "id", None)}
    if not by_id:
        st.info("No incidents are available to open.")
        return None

    incident_ids = list(by_id)
    return st.selectbox(
        "Select incident",
        options=incident_ids,
        format_func=lambda iid: (
            f"{iid} · {by_id[iid].service} · {str(by_id[iid].status).replace('_', ' ')}"
        ),
        key="war_room_incident_picker",
    )


def render_war_room(
    incident_id: Optional[str] = None,
    on_back: Optional[Callable[[], None]] = None,
) -> None:
    """Render the War Room for *incident_id*.

    Args:
        incident_id: Incident to investigate. When None the user is prompted.
        on_back: Callback invoked by the back button. Defaults to returning to
            the Dashboard through the console shell's sidebar navigation.
    """
    render_header(title="War Room", subtitle="Incident Investigation & Human Review")

    def go_back() -> None:
        if on_back is not None:
            on_back()
            return
        st.session_state["selected_page"] = "Dashboard"
        st.rerun()

    if not incident_id:
        incident_id = _select_incident()
        if not incident_id:
            if st.button("← Dashboard", key="war_room_back_empty", type="primary"):
                go_back()
            st.stop()

    if st.button("← Dashboard", key="war_room_back"):
        go_back()

    try:
        with st.spinner("Loading incident and investigation context…"):
            raw_detail = api_client.get_incident_payload(incident_id)
            detail = IncidentDetail.model_validate(raw_detail) if raw_detail else None
            similar_hits = [
                MemoryHit.model_validate(item)
                for item in api_client.get_similar_incidents(incident_id)
            ]
            memory_calls = api_client.get_memory_calls(incident_id)
            timeline = api_client.get_timeline_entries(incident_id)
    except Exception as error:  # noqa: BLE001 - surface load failures inline
        st.error(f"Unable to load incident data: {error}")
        st.stop()

    if detail is None:
        st.error(f"Incident {incident_id} was not found or is unavailable.")
        st.stop()

    state_key = f"war_room:{incident_id}"
    events_key = f"{state_key}:events"
    offset_key = f"{state_key}:event_offset"
    status_key = f"{state_key}:status"

    if st.session_state.get("war_room_active_id") != incident_id:
        st.session_state["war_room_active_id"] = incident_id
        st.session_state[events_key] = [event.model_dump() for event in detail.events]
        st.session_state[offset_key] = len(detail.events)
        st.session_state[status_key] = detail.status
    else:
        known_events = st.session_state.setdefault(
            events_key, [event.model_dump() for event in detail.events]
        )
        known_keys = {timeline_key(event) for event in known_events}
        for event in detail.events:
            event_data = event.model_dump()
            if timeline_key(event_data) not in known_keys:
                known_keys.add(timeline_key(event_data))
                known_events.append(event_data)
        st.session_state.setdefault(offset_key, len(detail.events))
        st.session_state[status_key] = detail.status

    status = st.session_state[status_key]
    smart_alert = detail.smart_alert.model_dump() if detail.smart_alert else {}
    recommendation = detail.recommendation

    st.markdown("## Incident Overview")
    header_cols = st.columns([2, 2, 1, 2])
    header_cols[0].metric("Incident", detail.id)
    header_cols[1].metric("Service", detail.service)
    header_cols[2].metric("Severity", detail.severity)
    header_cols[3].metric("Status", status.replace("_", " ").title())
    if smart_alert.get("is_novel"):
        st.warning("Novel incident pattern: the smart alert marks this incident as novel.")

    if status == "awaiting_approval":
        st.warning("Human approval is required before the recommended actions can proceed.")
    elif status == "executing":
        st.info("Remediation is executing. The timeline refreshes automatically.")
    elif status == "fix_failed":
        st.error("A remediation step failed. Review the investigation and choose the next action.")
    elif status == "resolved":
        suffix = f" with outcome: {detail.outcome}" if detail.outcome else ""
        st.success(f"Incident resolved{suffix}.")
    elif status in TERMINAL_STATUSES:
        st.info(f"Incident is {status}.")

    st.markdown("### Alert & Context")
    st.markdown(f"**{detail.message}**")
    alert = detail.alert or {}
    metrics = alert.get("metrics") or {}
    extra_context = {k: v for k, v in alert.items() if k not in _ALERT_CORE_KEYS}
    context_cols = st.columns(2)
    with context_cols[0]:
        st.caption("Alert")
        st.write(f"Service: {alert.get('service', detail.service)}")
        if alert.get("severity"):
            st.write(f"Alert severity: {alert['severity']}")
        if alert.get("timestamp"):
            st.write(f"Alert timestamp: {format_timestamp(alert['timestamp'])}")
    with context_cols[1]:
        st.caption("Metrics")
        if metrics:
            st.json(metrics)
        else:
            st.caption("No metrics are included in the alert.")
    if extra_context:
        with st.expander("Additional alert context"):
            st.json(extra_context)
    if not any(key in extra_context for key in ("logs", "deployments")):
        st.caption("Logs and deployment data are not provided by the current incident response.")

    st.markdown("### AI Recommendation")
    if recommendation is None:
        st.info("No recommendation is available yet.")
    else:
        if recommendation.needs_approval or smart_alert.get("needs_approval"):
            st.warning("Human approval required")

        if recommendation.hypotheses:
            for index, hypothesis in enumerate(recommendation.hypotheses, start=1):
                with st.container(border=True):
                    st.markdown(f"**{index}. {hypothesis.cause}**")
                    st.progress(
                        max(0.0, min(1.0, hypothesis.confidence)),
                        text=f"Confidence: {hypothesis.confidence:.0%}",
                    )
                    st.caption("Evidence IDs")
                    if hypothesis.evidence_ids:
                        for evidence_id in hypothesis.evidence_ids:
                            st.markdown(f"- `{evidence_id}`")
                    else:
                        st.caption("No evidence IDs provided.")
        else:
            st.caption("No hypotheses are available.")

        st.markdown("**Recommended steps**")
        if recommendation.steps:
            for index, step in enumerate(recommendation.steps, start=1):
                st.markdown(f"{index}. {step}")
        else:
            st.caption("No recommended steps are available.")
        st.markdown(f"**Runbook:** {recommendation.runbook or 'Not provided'}")
        st.markdown("**Avoid / failed before**")
        if recommendation.avoid:
            for item in recommendation.avoid:
                st.markdown(f"- {item}")
        else:
            st.caption("No avoid guidance is available.")
        st.markdown("**What's different this time?**")
        st.write(recommendation.whats_different or "No comparison is available.")

        if status in REVIEWABLE_STATUSES:
            with st.form(f"feedback:{incident_id}"):
                edited_steps = st.text_area(
                    "Edit recommended steps (one per line)",
                    value="\n".join(recommendation.steps),
                )
                accept_col, edit_col, reject_col = st.columns(3)
                accept = accept_col.form_submit_button(
                    "Accept", type="primary", use_container_width=True
                )
                edit = edit_col.form_submit_button("Edit steps", use_container_width=True)
                reject = reject_col.form_submit_button("Reject", use_container_width=True)

            if accept or edit or reject:
                action = "accept" if accept else "edit" if edit else "reject"
                payload = FeedbackRequest(
                    action=action,
                    steps=(
                        [s.strip() for s in edited_steps.splitlines() if s.strip()]
                        if action == "edit"
                        else None
                    ),
                )
                result = api_client.submit_feedback(
                    incident_id, payload.model_dump(exclude_none=True)
                )
                if result:
                    st.session_state[status_key] = result.get("status", status)
                    st.toast(f"Feedback submitted: {action}")
                    st.rerun()
                st.error(api_client._last_error or "Feedback could not be submitted.")

    st.markdown("### Similar Incidents")
    if similar_hits:
        for hit in similar_hits:
            incident_label = hit.incident_id or hit.id
            heading = (
                f"{incident_label} · relevance {hit.score:.2f}"
                if hit.score is not None
                else incident_label
            )
            with st.expander(heading):
                st.markdown(f"**Outcome:** {hit.outcome or 'Not recorded'}")
                st.markdown("**Historical detail / root-cause context**")
                st.write(hit.text)
                st.caption(
                    "The API provides memory text, score, and outcome; it does not "
                    "provide separate root-cause or recommendation-rationale fields."
                )
    else:
        st.info("No similar incidents found.")

    st.markdown("### Live Investigation Timeline")
    timeline_slot = st.container()

    def render_live_timeline() -> None:
        current_status = st.session_state.get(status_key, status)
        if current_status in TERMINAL_STATUSES:
            timeline_slot.caption("Live updates stopped for this terminal incident status.")
            combined = list(timeline)
            known = {timeline_key(item) for item in combined}
            for event in st.session_state.get(events_key, []):
                event_item = {
                    "ts": event.get("ts"),
                    "source": "event",
                    "kind": event.get("kind", "event"),
                    "title": event.get("step", ""),
                    "detail": event.get("detail", ""),
                }
                if timeline_key(event_item) not in known:
                    known.add(timeline_key(event_item))
                    combined.append(event_item)
            for item in sorted(combined, key=lambda e: str(e.get("ts", ""))):
                render_timeline_entry(item)
            return

        previous_status = current_status
        try:
            fresh_detail_raw = api_client.get_incident_payload(incident_id)
            fresh_detail = (
                IncidentDetail.model_validate(fresh_detail_raw) if fresh_detail_raw else None
            )
            if fresh_detail:
                current_status = fresh_detail.status
                st.session_state[status_key] = current_status

            offset = st.session_state.get(offset_key, 0)
            new_events = api_client.get_incident_events(incident_id, after=offset)
            stored_events = st.session_state.setdefault(events_key, [])
            known_events = {timeline_key(item) for item in stored_events}
            for raw_event in new_events:
                event = AgentEvent.model_validate(raw_event).model_dump()
                key = timeline_key(event)
                if key not in known_events:
                    known_events.add(key)
                    stored_events.append(event)
            st.session_state[offset_key] = offset + len(new_events)

            if current_status != previous_status:
                st.rerun(scope="app")
        except Exception as error:  # noqa: BLE001 - polling must never kill the page
            timeline_slot.warning(f"Timeline refresh failed: {error}")

        combined = list(timeline)
        known = {timeline_key(item) for item in combined}
        for event in st.session_state.get(events_key, []):
            event_item = {
                "ts": event.get("ts"),
                "source": "event",
                "kind": event.get("kind", "event"),
                "title": event.get("step", ""),
                "detail": event.get("detail", ""),
            }
            if timeline_key(event_item) not in known:
                known.add(timeline_key(event_item))
                combined.append(event_item)
        for item in sorted(combined, key=lambda e: str(e.get("ts", ""))):
            render_timeline_entry(item)

    st.fragment(run_every=POLL_SECONDS if status not in TERMINAL_STATUSES else None)(
        render_live_timeline
    )()

    st.markdown("### Hindsight Memory Calls")
    if memory_calls:
        for call in memory_calls:
            with st.container(border=True):
                st.caption(format_timestamp(call.get("ts")))
                st.markdown(f"**{call.get('step', 'Memory activity')}**")
                st.write(call.get("detail", ""))
    else:
        st.info("No Hindsight memory calls recorded.")

    if status == "resolved":
        st.success("This incident has already been resolved.")
    elif status in RESOLVABLE_STATUSES:
        st.markdown("### Resolve Incident")
        with st.form(f"resolve:{incident_id}"):
            outcome = st.selectbox("Outcome", options=["worked", "failed", "partial"])
            resolution = st.text_area("Resolution details (optional)")
            resolve = st.form_submit_button("Resolve incident", type="primary")
        if resolve:
            payload = ResolveRequest(outcome=outcome, resolution=resolution or None)
            result = api_client.resolve_incident(incident_id, payload.model_dump(exclude_none=True))
            if result:
                st.session_state[status_key] = result.get("status", "resolved")
                st.toast("Incident resolved")
                st.rerun()
            st.error(api_client._last_error or "Incident could not be resolved.")
