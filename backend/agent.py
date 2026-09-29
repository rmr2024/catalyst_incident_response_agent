"""
agent.py
--------
Main Incident Response Agent reasoning pipeline.

Implements:
  investigate(incident_id, alert, emit) -> Recommendation

Pipeline:
  1. Collect current incident context
  2. Recall relevant historical incidents (if memory enabled)
  3. Evaluate relevance and detect novel incidents
  4. Build LLM prompt with context + memory
  5. Call LLM for structured reasoning
  6. Parse and validate structured response
  7. Apply approval guardrails for risky actions
  8. Return Recommendation (reusing existing schemas)

The agent response schema aligns with the existing Recommendation schema
from schemas.py while also producing a fully structured AgentResult for
internal use.  Evidence from memory is always traceable to Incident IDs.

MEMORY OFF: skip all recall steps; LLM receives only current context.
MEMORY ON:  recall is performed; historical incident IDs appear in evidence.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
from datetime import datetime, timezone
from typing import Any

from llm import call_llm
from schemas import Alert, Hypothesis, MemoryHit, Recommendation
from settings import memory_enabled, settings

log = logging.getLogger("agent")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum similarity score for a memory hit to be considered "relevant"
NOVEL_THRESHOLD: float = float(getattr(settings, "novel_threshold", 0.25))

# Patterns that indicate a risky/destructive action
_RISKY_RE = re.compile(
    r"restart|rollback|roll back|redeploy|failover|scale|delete|drop|flush|kill|purge|"
    r"wipe|format|truncat|cascade|force|override|bypass|disable auth|disable ssl|"
    r"open port|expose|grant all",
    re.I,
)


def _is_risky(step: str) -> bool:
    return bool(_RISKY_RE.search(step or ""))


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------

async def _gather_context(incident_id: str, alert: Alert) -> dict:
    """Gather current-incident context from the alert and DB."""
    try:
        from db import crud
        inc = crud.get_incident(incident_id)
    except Exception:
        inc = None

    metrics = alert.metrics or {}
    actions_taken: list[dict] = []

    if inc:
        try:
            from db import crud as _crud
            actions_taken = [
                {"step": a.step, "status": a.status, "output": a.output}
                for a in _crud.list_actions(incident_id)
            ]
        except Exception:
            pass

    return {
        "incident_id": incident_id,
        "service": alert.service,
        "message": alert.message,
        "severity": alert.severity or (inc.severity if inc else "unknown"),
        "metrics": metrics,
        "actions_taken": actions_taken,
        "timestamp": alert.timestamp.isoformat() if alert.timestamp else datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Memory recall
# ---------------------------------------------------------------------------

async def _perform_recall(alert: Alert, emit) -> list[dict]:
    """Recall relevant historical incidents via memory.service."""
    try:
        from memory.service import recall
    except Exception as e:
        log.warning("memory.service unavailable: %s", e)
        return []

    query = f"{alert.service} {alert.message}"
    if alert.metrics:
        metrics_desc = " ".join(f"{k}={v}" for k, v in alert.metrics.items())
        query = f"{query} {metrics_desc}"

    try:
        hits = await recall(query, top_k=5)
        return hits or []
    except Exception as e:
        log.warning("recall() failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Novel incident detection
# ---------------------------------------------------------------------------

def _is_novel(hits: list[dict]) -> bool:
    """
    Return True if the recall results do not contain any hit above
    NOVEL_THRESHOLD similarity.  Novel = insufficient historical evidence.
    """
    if not hits:
        return True
    best_score = max(h.get("score", 0.0) for h in hits)
    return best_score < NOVEL_THRESHOLD


# ---------------------------------------------------------------------------
# Avoid-list builder
# ---------------------------------------------------------------------------

def _build_avoid_list(hits: list[dict]) -> list[str]:
    """
    Build avoid_list from historically failed actions.
    Only includes actions explicitly marked as "failed" in historical memory.
    Never fabricates failed actions.
    """
    avoid: list[str] = []
    for h in hits:
        if h.get("outcome") != "failed":
            continue
        text = h.get("text", "")
        iid = h.get("incident_id", "?")
        # Extract "Failed steps" section if present
        if "failed steps:" in text.lower():
            for line in text.split("|"):
                if "failed step" in line.lower():
                    step_text = line.split(":", 1)[-1].strip()
                    if step_text:
                        avoid.append(f"{step_text} (failed in {iid})")
        elif h.get("outcome") == "failed":
            # The whole record is a failed attempt; reference the key action
            for line in text.split("|"):
                if "fix step" in line.lower():
                    step_text = line.split(":", 1)[-1].strip()
                    if step_text:
                        avoid.append(f"{step_text} (failed in {iid})")
    return avoid


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an expert SRE (Site Reliability Engineer) incident response AI.

You analyse incidents and produce structured, evidence-based recommendations.

Rules:
- Never fabricate historical evidence, incidents, or fixes.
- Only reference incidents that are explicitly provided in the memory context.
- If memory is empty, state that no historical data is available.
- Risky actions (restart, rollback, redeploy, delete, etc.) MUST have needs_approval=true.
- If historical recall is weak or absent, set novel_incident=true.
- evidence_ids must only contain incident IDs that appear in the provided memory hits.
- Be concise and actionable.

Always respond with valid JSON only. Do not include any text outside the JSON object."""


def _build_prompt(context: dict, hits: list[dict], novel: bool) -> str:
    """Build the LLM investigation prompt."""
    mem_section = ""
    if hits:
        mem_lines = []
        for h in hits:
            src_label = " [MOCK DATA]" if h.get("_source") == "mock" else ""
            mem_lines.append(
                f"  - Incident {h.get('incident_id','?')}{src_label} "
                f"(score={h.get('score',0):.2f}, outcome={h.get('outcome','?')}): "
                f"{h.get('text','')[:300]}"
            )
        mem_section = "HISTORICAL MEMORY (from Hindsight recall):\n" + "\n".join(mem_lines)
    else:
        mem_section = "HISTORICAL MEMORY: None (memory disabled or no relevant history found)"

    avoid_from_memory = _build_avoid_list(hits)
    avoid_hint = ""
    if avoid_from_memory:
        avoid_hint = "\nKNOWN FAILED ACTIONS (from historical memory, do not repeat):\n" + "\n".join(
            f"  - {a}" for a in avoid_from_memory
        )

    metrics_str = ""
    if context.get("metrics"):
        metrics_str = "\nCurrent metrics:\n" + "\n".join(
            f"  {k}: {v}" for k, v in context["metrics"].items()
        )

    novel_note = "\nNOTE: No strong historical match found. This may be a novel incident." if novel else ""

    prompt = f"""Analyse the following incident and provide a structured JSON response.

CURRENT INCIDENT:
  Incident ID: {context['incident_id']}
  Service: {context['service']}
  Message: {context['message']}
  Severity: {context['severity']}
  Timestamp: {context['timestamp']}{metrics_str}

{mem_section}{avoid_hint}{novel_note}

REQUIRED JSON RESPONSE FORMAT:
{{
  "incident_id": "{context['incident_id']}",
  "hypotheses": [
    {{
      "cause": "description of root cause",
      "confidence": 0.0,
      "evidence_ids": ["INC-XXXX"]
    }}
  ],
  "evidence_ids": ["INC-XXXX"],
  "action_steps": ["step 1", "step 2"],
  "runbook_execution_steps": ["runbook step 1"],
  "avoid_list": ["action to avoid (source)"],
  "needs_approval": false,
  "novel_incident": {str(novel).lower()},
  "confidence": 0.0,
  "reasoning": "brief reasoning",
  "whats_different": "what differs from historical incidents"
}}

Evidence IDs must only reference incident IDs listed in HISTORICAL MEMORY above.
Set needs_approval=true if ANY action_step involves: restart, rollback, redeploy, delete, scale, failover, flush, purge, kill.
Respond with valid JSON ONLY."""

    return prompt


# ---------------------------------------------------------------------------
# Response parsing & validation
# ---------------------------------------------------------------------------

def _parse_agent_response(
    raw: dict | str,
    context: dict,
    hits: list[dict],
    novel: bool,
    avoid_from_memory: list[str],
) -> Recommendation:
    """
    Convert LLM response dict into the Recommendation schema.
    Falls back gracefully if fields are missing or malformed.
    """
    if isinstance(raw, str):
        # Should not happen if expect_json=True, but handle defensively
        from llm import _extract_json
        raw = _extract_json(raw) or {}

    if not isinstance(raw, dict):
        raw = {}

    # --- Hypotheses ---
    hyp_raw = raw.get("hypotheses") or []
    hypotheses: list[Hypothesis] = []
    known_incident_ids = {h.get("incident_id") for h in hits if h.get("incident_id")}

    for h in hyp_raw:
        if not isinstance(h, dict):
            continue
        # Validate evidence_ids – only allow IDs that exist in memory hits
        ev_ids = [
            eid for eid in (h.get("evidence_ids") or [])
            if eid in known_incident_ids
        ]
        try:
            conf = float(h.get("confidence", 0.0))
            conf = max(0.0, min(1.0, conf))
        except (TypeError, ValueError):
            conf = 0.0
        hypotheses.append(
            Hypothesis(
                cause=str(h.get("cause", "Unknown")),
                confidence=conf,
                evidence_ids=ev_ids,
            )
        )

    if not hypotheses:
        hypotheses = [
            Hypothesis(
                cause="Unknown – insufficient evidence",
                confidence=0.1,
                evidence_ids=[],
            )
        ]

    # --- Action steps ---
    action_steps: list[str] = []
    for s in (raw.get("action_steps") or raw.get("steps") or []):
        if isinstance(s, str) and s.strip():
            action_steps.append(s.strip())

    if not action_steps:
        action_steps = [
            "Gather logs from the affected service",
            "Check metrics dashboard for anomalies",
            "Page on-call engineer if unresolved within 15 minutes",
        ]

    # --- Needs approval (risky action guard) ---
    needs_approval = bool(raw.get("needs_approval", False))
    # Always enforce: if any step is risky, require approval
    if any(_is_risky(s) for s in action_steps):
        needs_approval = True

    # --- Avoid list ---
    avoid: list[str] = []
    for a in (raw.get("avoid_list") or []):
        if isinstance(a, str) and a.strip():
            avoid.append(a.strip())
    # Merge with memory-derived avoid list
    for a in avoid_from_memory:
        if a not in avoid:
            avoid.append(a)

    # --- Confidence ---
    try:
        confidence = float(raw.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    # --- Similar hits (MemoryHit objects) ---
    similar: list[MemoryHit] = []
    for h in hits:
        try:
            similar.append(
                MemoryHit(
                    id=str(h.get("id", "")),
                    text=str(h.get("text", ""))[:300],
                    incident_id=str(h.get("incident_id", "")) or None,
                    score=float(h.get("score", 0.0)),
                    outcome=h.get("outcome") or None,
                )
            )
        except Exception as e:
            log.debug("Could not create MemoryHit from %r: %s", h, e)

    # --- Runbook ---
    runbook_steps = raw.get("runbook_execution_steps") or []
    runbook: str | None = None
    if runbook_steps:
        runbook = "; ".join(str(s) for s in runbook_steps if s)

    # --- Whats different ---
    whats_different = str(raw.get("whats_different") or raw.get("reasoning") or "")
    if not whats_different:
        if novel:
            whats_different = "No similar historical incident found; this appears novel."
        else:
            whats_different = "Based on available historical context."

    return Recommendation(
        hypotheses=hypotheses,
        steps=action_steps,
        runbook=runbook,
        avoid=avoid,
        whats_different=whats_different,
        is_novel=novel,
        similar=similar,
        needs_approval=needs_approval,
    )


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

async def investigate(incident_id: str, alert: Alert, emit) -> Recommendation:
    """
    Main investigation pipeline.

    Args:
        incident_id: The incident ID being investigated.
        alert:       The incoming Alert object.
        emit:        Async-capable event emitter for the bus.

    Returns:
        Recommendation (existing schema from schemas.py)
    """

    async def _emit(kind: str, step: str, detail: str) -> None:
        try:
            r = emit(kind, step, detail)
            if inspect.isawaitable(r):
                await r
        except Exception as e:
            log.debug("emit failed: %s", e)

    await _emit("agent", "investigation started", f"Analysing {alert.service}: {alert.message[:100]}")

    # Step 1: Gather context
    await _emit("agent", "gathering context", f"service={alert.service}, severity={alert.severity}")
    context = await _gather_context(incident_id, alert)

    # Step 2: Recall (only when memory is enabled)
    hits: list[dict] = []
    mem_on = memory_enabled()

    if mem_on:
        await _emit("memory", "recall started", f"query: {alert.service} {alert.message[:60]}")
        hits = await _perform_recall(alert, emit)
        if hits:
            best = max(h.get("score", 0.0) for h in hits)
            iids = ", ".join(h.get("incident_id", "?") for h in hits[:3])
            await _emit(
                "memory",
                "recall complete",
                f"{len(hits)} hit(s) found: [{iids}] (best score={best:.2f})",
            )
        else:
            await _emit("memory", "recall complete", "no relevant historical incidents found")
    else:
        await _emit(
            "memory",
            "recall skipped",
            "memory is DISABLED – using current incident context only",
        )

    # Step 3: Novel detection
    novel = _is_novel(hits)
    if novel:
        await _emit(
            "agent",
            "novel incident check",
            f"novel=True (best score < {NOVEL_THRESHOLD}; no strong historical match)",
        )
    else:
        best = max(h.get("score", 0.0) for h in hits)
        await _emit(
            "agent",
            "novel incident check",
            f"novel=False (best score={best:.2f} >= {NOVEL_THRESHOLD})",
        )

    # Step 4: Build avoid list from memory
    avoid_from_memory = _build_avoid_list(hits)
    if avoid_from_memory:
        await _emit(
            "agent",
            "avoid list",
            f"Failed actions from memory: {'; '.join(avoid_from_memory[:3])}",
        )

    # Step 5: Build LLM prompt
    await _emit("agent", "reasoning", "calling LLM for hypothesis generation")
    prompt = _build_prompt(context, hits, novel)

    # Step 6: Call LLM
    raw_response = call_llm(
        prompt=prompt,
        system=_SYSTEM_PROMPT,
        expect_json=True,
        cache_key=None,  # Always fresh per incident
    )

    await _emit("agent", "llm response", "structured response received from LLM")

    # Step 7: Parse and validate
    recommendation = _parse_agent_response(
        raw=raw_response,
        context=context,
        hits=hits,
        novel=novel,
        avoid_from_memory=avoid_from_memory,
    )

    # Step 8: Emit final summary
    top_h = recommendation.hypotheses[0] if recommendation.hypotheses else None
    summary_parts = []
    if top_h:
        summary_parts.append(f"top cause: {top_h.cause} ({round(top_h.confidence * 100)}%)")
    summary_parts.append(f"{len(recommendation.steps)} action steps")
    summary_parts.append(f"novel={recommendation.is_novel}")
    summary_parts.append(f"needs_approval={recommendation.needs_approval}")
    if recommendation.similar:
        iids = ", ".join(s.incident_id for s in recommendation.similar[:3] if s.incident_id)
        if iids:
            summary_parts.append(f"similar incidents: [{iids}]")

    await _emit("agent", "recommendation ready", "; ".join(summary_parts))

    return recommendation
