"""
Formatting and presentation helpers for Streamlit SRE console.
"""

from datetime import datetime
from typing import Optional


def format_timestamp(ts: Optional[str]) -> str:
    """Format ISO timestamp to human-readable SRE format."""
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %H:%M:%S UTC")
    except Exception:
        return str(ts)[:19]


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds is None:
        return "Active"
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = int(minutes // 60)
    rem_min = int(minutes % 60)
    return f"{hours}h {rem_min}m"


def calculate_ttr_display(started_at: Optional[str], resolved_at: Optional[str]) -> str:
    """Calculate and format time-to-resolution duration between start and resolution."""
    if not started_at or not resolved_at:
        return "—"
    try:
        t0 = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        diff = max(0.0, (t1 - t0).total_seconds())
        return format_duration(diff)
    except Exception:
        return "—"


def format_error_rate(rate: Optional[float]) -> str:
    """Format fractional error rate as percentage string."""
    if rate is None:
        return "—"
    return f"{rate * 100:.1f}%" if rate <= 1.0 else f"{rate:.1f}%"


def get_severity_color(severity: str) -> str:
    """Return hex color matching SRE severity level."""
    s = (severity or "").upper()
    if s == "P1":
        return "#ef4444"  # Red
    elif s == "P2":
        return "#f97316"  # Orange
    elif s == "P3":
        return "#eab308"  # Yellow
    return "#94a3b8"      # Slate


def get_status_color(status: str) -> str:
    """Return hex color matching incident workflow status."""
    st = (status or "").lower()
    if st in ("resolved", "mitigated"):
        return "#22c55e"  # Green
    elif st in ("investigating", "executing"):
        return "#3b82f6"  # Blue
    elif st == "awaiting_approval":
        return "#f59e0b"  # Amber
    elif st == "recommended":
        return "#8b5cf6"  # Purple
    elif st == "fix_failed":
        return "#ef4444"  # Red
    return "#94a3b8"


def navigate_to(page: str) -> None:
    """Safely navigate to another page without violating Streamlit widget state lifecycle."""
    import streamlit as st
    st.session_state["_nav_destination"] = page
    st.rerun()
