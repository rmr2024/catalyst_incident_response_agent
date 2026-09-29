"""
Badge and status pill components for Streamlit SRE console.
Rendered using clean, inline CSS styles.
"""

from utils.helpers import get_severity_color, get_status_color


def render_severity_badge(severity: str) -> str:
    """Return HTML string for severity badge."""
    sev = (severity or "P3").upper()
    color = get_severity_color(sev)
    return (
        f'<span style="background-color: {color}22; color: {color}; '
        f'border: 1px solid {color}88; padding: 2px 8px; border-radius: 6px; '
        f'font-size: 11px; font-weight: 700; letter-spacing: 0.5px;">{sev}</span>'
    )


def render_status_badge(status: str) -> str:
    """Return HTML string for status badge."""
    st = (status or "investigating").lower()
    color = get_status_color(st)
    label = st.replace("_", " ").upper()
    return (
        f'<span style="background-color: {color}22; color: {color}; '
        f'border: 1px solid {color}88; padding: 2px 8px; border-radius: 6px; '
        f'font-size: 11px; font-weight: 600;">{label}</span>'
    )


def render_outcome_badge(outcome: str) -> str:
    """Return HTML string for remediation outcome badge."""
    oc = (outcome or "pending").lower()
    if oc == "worked":
        color = "#22c55e"
        label = "WORKED"
    elif oc == "failed":
        color = "#ef4444"
        label = "FAILED"
    else:
        color = "#f59e0b"
        label = "PARTIAL"

    return (
        f'<span style="background-color: {color}22; color: {color}; '
        f'border: 1px solid {color}88; padding: 2px 8px; border-radius: 6px; '
        f'font-size: 10px; font-weight: 700;">{label}</span>'
    )


def render_system_status_pill(is_live: bool) -> str:
    """Return HTML string for backend connection status."""
    if is_live:
        return (
            '<div style="background-color: var(--fix-bg, rgba(34, 197, 94, 0.12)); border: 1px solid #22c55e; '
            'border-radius: 6px; padding: 4px 10px; text-align: center; color: var(--fix-text, #4ade80); '
            'font-size: 12px; font-weight: 600;">● Live Backend</div>'
        )
    return (
        '<div style="background-color: rgba(234, 179, 8, 0.15); border: 1px solid #eab308; '
        'border-radius: 6px; padding: 4px 10px; text-align: center; color: var(--warn-text, #facc15); '
        'font-size: 12px; font-weight: 600;">▲ Mock Mode</div>'
    )


def render_memory_badge(memory_enabled: bool) -> str:
    """Return HTML string for Hindsight memory state badge."""
    if memory_enabled:
        return (
            '<span style="background-color: var(--callout-bg, rgba(59, 130, 246, 0.15)); color: var(--badge-blue, #60a5fa); '
            'border: 1px solid #3b82f6; padding: 3px 8px; border-radius: 6px; '
            'font-size: 11px; font-weight: 600;">🧠 Memory ON</span>'
        )
    return (
        '<span style="background-color: var(--generic-bg, rgba(148, 163, 184, 0.15)); color: var(--text-muted, #94a3b8); '
        'border: 1px solid var(--border-color, #64748b); padding: 3px 8px; border-radius: 6px; '
        'font-size: 11px; font-weight: 600;">⚪ Memory OFF</span>'
    )
