"""
Incident Response Agent - Operational Analytics (P6).

Displays:
  1. KPI banner — total, active, resolved, avg MTTR
  2. Memory ON vs OFF MTTR comparison (key demo metric)
  3. Severity distribution bar chart
  4. Incidents by service breakdown
  5. Outcome distribution (worked / partial / failed)
  6. Recent resolved incidents table
"""

from typing import Any, Dict, List
import streamlit as st

from services.api_client import api_client
from components.badges import render_memory_badge, render_severity_badge, render_outcome_badge
from utils.helpers import navigate_to


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_min(seconds: float) -> str:
    """Convert seconds to a human-readable minutes string."""
    if not seconds:
        return "N/A"
    mins = round(seconds / 60, 1)
    if mins < 60:
        return f"{mins} min"
    hrs = round(mins / 60, 1)
    return f"{hrs} hr"


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_analytics():
    """Main render function for the Operational Analytics page."""

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    st.markdown("## 📈 Operational Analytics")
    st.caption(
        "MTTR benchmarks, memory impact, severity trends, and service reliability metrics."
    )

    mem_enabled = st.session_state.get("memory_enabled", True)
    col_mem, col_refresh = st.columns([3, 1])
    with col_mem:
        st.markdown(render_memory_badge(mem_enabled), unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.pop("analytics_data", None)
            st.rerun()

    st.write("")

    # ------------------------------------------------------------------
    # Fetch data (cached in session state for the page render cycle)
    # ------------------------------------------------------------------
    if "analytics_data" not in st.session_state:
        with st.spinner("Loading analytics…"):
            st.session_state["analytics_data"] = api_client.get_analytics()

    data: Dict[str, Any] = st.session_state.get("analytics_data", {})

    total      = data.get("total", 0)
    active     = data.get("active", 0)
    resolved   = data.get("resolved", 0)
    mttr_s     = data.get("mttr_seconds") or 0
    mem_on_s   = data.get("memory_on_mttr_seconds") or 0
    mem_off_s  = data.get("memory_off_mttr_seconds") or 0
    by_sev     = data.get("by_severity") or {}
    by_svc     = data.get("by_service") or {}
    outcomes   = data.get("outcomes") or {}

    # ------------------------------------------------------------------
    # 1. KPI Banner
    # ------------------------------------------------------------------
    st.markdown("### Key Metrics")
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Total Incidents", total)
    with k2:
        st.metric("Active Now", active, delta=None)
    with k3:
        st.metric("Resolved", resolved)
    with k4:
        st.metric("Avg MTTR", _fmt_min(mttr_s))

    st.markdown("---")

    # ------------------------------------------------------------------
    # 2. Memory ON vs OFF MTTR Comparison  (key demo proof point)
    # ------------------------------------------------------------------
    st.markdown("### 🧠 Memory Impact on MTTR")
    st.caption(
        "The core proof point: Hindsight long-term memory reduces Mean Time To Resolution "
        "by surfacing proven runbooks and avoiding previously failed fixes."
    )

    if mem_on_s and mem_off_s:
        improvement_pct = round((mem_off_s - mem_on_s) / mem_off_s * 100, 1) if mem_off_s else 0
        delta_min = round((mem_off_s - mem_on_s) / 60, 1)

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(
                f'<div style="background: rgba(59,130,246,0.1); border: 1px solid #3b82f6; '
                f'border-radius: 10px; padding: 16px; text-align: center;">'
                f'<div style="color: #60a5fa; font-size: 13px; font-weight: 600; margin-bottom: 4px;">🧠 Memory ON</div>'
                f'<div style="font-size: 28px; font-weight: 800; color: #22c55e;">{_fmt_min(mem_on_s)}</div>'
                f'<div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">avg MTTR</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f'<div style="background: rgba(148,163,184,0.08); border: 1px solid #64748b; '
                f'border-radius: 10px; padding: 16px; text-align: center;">'
                f'<div style="color: #94a3b8; font-size: 13px; font-weight: 600; margin-bottom: 4px;">⚪ Memory OFF</div>'
                f'<div style="font-size: 28px; font-weight: 800; color: #ef4444;">{_fmt_min(mem_off_s)}</div>'
                f'<div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">avg MTTR</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f'<div style="background: rgba(34,197,94,0.1); border: 1px solid #22c55e; '
                f'border-radius: 10px; padding: 16px; text-align: center;">'
                f'<div style="color: #4ade80; font-size: 13px; font-weight: 600; margin-bottom: 4px;">⚡ Improvement</div>'
                f'<div style="font-size: 28px; font-weight: 800; color: #4ade80;">{improvement_pct}%</div>'
                f'<div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">faster ({delta_min} min saved)</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Visual bar comparison
        st.write("")
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Memory ON", "Memory OFF"],
                y=[round(mem_on_s / 60, 1), round(mem_off_s / 60, 1)],
                marker_color=["#22c55e", "#ef4444"],
                text=[_fmt_min(mem_on_s), _fmt_min(mem_off_s)],
                textposition="outside",
                width=0.4,
            ))
            fig.update_layout(
                title="MTTR: Memory ON vs Memory OFF",
                yaxis_title="Minutes",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                showlegend=False,
                height=320,
                margin=dict(t=40, b=20, l=20, r=20),
            )
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="rgba(148,163,184,0.15)")
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # Fallback if plotly not installed
            st.progress(
                int(mem_on_s / max(mem_off_s, 1) * 100),
                text=f"Memory ON: {_fmt_min(mem_on_s)} vs Memory OFF: {_fmt_min(mem_off_s)}",
            )
    else:
        st.info("Not enough data for Memory ON/OFF comparison yet. Run more simulations.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # 3. Severity Distribution + Outcome Distribution
    # ------------------------------------------------------------------
    st.markdown("### Severity & Outcome Breakdown")
    sev_col, out_col = st.columns(2)

    with sev_col:
        st.markdown("#### Incidents by Severity")
        p1 = by_sev.get("P1", 0)
        p2 = by_sev.get("P2", 0)
        p3 = by_sev.get("P3", 0)
        sev_total = p1 + p2 + p3 or 1

        for label, count, color in [("P1 — Critical", p1, "#ef4444"), ("P2 — Major", p2, "#f97316"), ("P3 — Minor", p3, "#eab308")]:
            pct = _pct(count, sev_total)
            st.markdown(
                f'<div style="margin-bottom: 8px;">'
                f'<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">'
                f'<span style="color: {color}; font-weight: 600;">{label}</span>'
                f'<span style="color: #94a3b8;">{count} ({pct}%)</span>'
                f'</div>'
                f'<div style="background: rgba(148,163,184,0.15); border-radius: 4px; height: 8px;">'
                f'<div style="background: {color}; width: {pct}%; height: 8px; border-radius: 4px;"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    with out_col:
        st.markdown("#### Incidents by Outcome")
        worked  = outcomes.get("worked", 0)
        partial = outcomes.get("partial", 0)
        failed  = outcomes.get("failed", 0)
        out_total = worked + partial + failed or 1

        for label, count, color in [("Worked", worked, "#22c55e"), ("Partial", partial, "#f59e0b"), ("Failed", failed, "#ef4444")]:
            pct = _pct(count, out_total)
            st.markdown(
                f'<div style="margin-bottom: 8px;">'
                f'<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">'
                f'<span style="color: {color}; font-weight: 600;">{label}</span>'
                f'<span style="color: #94a3b8;">{count} ({pct}%)</span>'
                f'</div>'
                f'<div style="background: rgba(148,163,184,0.15); border-radius: 4px; height: 8px;">'
                f'<div style="background: {color}; width: {pct}%; height: 8px; border-radius: 4px;"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ------------------------------------------------------------------
    # 4. Incidents by Service
    # ------------------------------------------------------------------
    st.markdown("### Incidents by Service")

    if by_svc:
        sorted_svcs = sorted(by_svc.items(), key=lambda x: x[1], reverse=True)
        svc_total = sum(v for _, v in sorted_svcs) or 1

        try:
            import plotly.graph_objects as go
            fig2 = go.Figure(go.Bar(
                x=[v for _, v in sorted_svcs],
                y=[s for s, _ in sorted_svcs],
                orientation="h",
                marker_color="#3b82f6",
                text=[str(v) for _, v in sorted_svcs],
                textposition="outside",
            ))
            fig2.update_layout(
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                xaxis_title="Incident Count",
                height=max(250, len(sorted_svcs) * 40),
                margin=dict(t=10, b=20, l=10, r=20),
                showlegend=False,
            )
            fig2.update_xaxes(gridcolor="rgba(148,163,184,0.15)", showgrid=True)
            fig2.update_yaxes(showgrid=False)
            st.plotly_chart(fig2, use_container_width=True)
        except ImportError:
            for svc, count in sorted_svcs:
                pct = _pct(count, svc_total)
                st.markdown(
                    f'<div style="margin-bottom: 6px;">'
                    f'<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 2px;">'
                    f'<span style="font-family: monospace; color: #60a5fa;">{svc}</span>'
                    f'<span style="color: #94a3b8;">{count}</span>'
                    f'</div>'
                    f'<div style="background: rgba(148,163,184,0.15); border-radius: 4px; height: 6px;">'
                    f'<div style="background: #3b82f6; width: {pct}%; height: 6px; border-radius: 4px;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("No service breakdown data available yet.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # 5. Recent Incidents Table
    # ------------------------------------------------------------------
    st.markdown("### Recent Incidents")

    incidents = api_client.get_incidents(limit=20)
    if incidents:
        rows = []
        for inc in incidents:
            rows.append({
                "ID": inc.id,
                "Service": inc.service,
                "Severity": inc.severity,
                "Status": inc.status,
                "Memory": "ON" if inc.memory_used else "OFF",
                "Novel": "⚠️ Yes" if inc.is_novel else "No",
            })

        import pandas as pd
        df = pd.DataFrame(rows)

        def _color_sev(val):
            colors = {"P1": "color: #ef4444", "P2": "color: #f97316", "P3": "color: #eab308"}
            return colors.get(val, "")

        def _color_mem(val):
            return "color: #60a5fa" if val == "ON" else "color: #64748b"

        styled = df.style.map(_color_sev, subset=["Severity"]).map(_color_mem, subset=["Memory"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.info("No incidents to display. Trigger a simulation to get started.")
        if st.button("Go to Simulator"):
            navigate_to("Simulator")
