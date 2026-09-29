"""
assistant.py
------------
Conversational assistant for incident-related queries.

Supports natural-language questions such as:
  - "What fixed this last time?"
  - "Have we seen this before?"
  - "Which runbook worked?"
  - "What should we avoid?"

When memory is ENABLED:
  - Searches historical incidents via memory.service.recall()
  - Returns a supported fix with the source Incident ID
  - Never fabricates fixes

When memory is DISABLED:
  - Does not access historical memory
  - Clearly states that historical information is unavailable

If no reliable historical fix is found:
  - Does not invent one
  - Indicates that no supported fix was found
"""

from __future__ import annotations

import logging
from typing import Any

from llm import call_llm
from settings import memory_enabled

log = logging.getLogger("assistant")

# Module-level import for testability (mock patching requires module-level name)
try:
    from memory.service import recall
except Exception:  # pragma: no cover
    recall = None  # type: ignore


_ASSISTANT_SYSTEM = """You are an expert SRE assistant that answers questions about incident history.

Rules:
- Only answer based on the incident memory context provided.
- Never fabricate historical incidents, fixes, or evidence.
- If the memory context is empty or irrelevant, say so explicitly.
- Always include the source Incident ID when citing a fix.
- If memory is disabled, say "Historical memory is currently disabled."
- Respond with valid JSON only.

Response format:
{
  "answer": "direct answer to the question",
  "incident_id": "INC-XXXX or null if not found",
  "fix": "the specific fix/action that worked, or null",
  "runbook": "runbook name if available, or null",
  "confidence": 0.0,
  "evidence": ["evidence item 1"],
  "caveat": "any important caveats"
}"""


async def answer_query(
    question: str,
    service: str | None = None,
    incident_id: str | None = None,
) -> dict:
    """
    Answer a natural-language query about incident history.

    Args:
        question:    The user's question (e.g. "What fixed this last time?").
        service:     Optional service name to scope the search.
        incident_id: Optional incident ID for context.

    Returns:
        dict with keys: answer, incident_id, fix, runbook, confidence, evidence, caveat
    """
    if not question or not question.strip():
        return _no_history("Empty question provided.")

    mem_on = memory_enabled()

    if not mem_on:
        log.info("assistant.answer_query: memory disabled, returning no-history response")
        return {
            "answer": "Historical memory is currently disabled. Enable memory to access historical incident data.",
            "incident_id": None,
            "fix": None,
            "runbook": None,
            "confidence": 0.0,
            "evidence": [],
            "caveat": "Memory is OFF. Toggle memory ON to access historical fixes and runbooks.",
        }

    # Build search query
    search_query = question
    if service:
        search_query = f"{service} {question}"
    if incident_id:
        search_query = f"{incident_id} {search_query}"

    # Recall from memory
    hits: list[dict] = []
    try:
        if recall is None:
            raise ImportError("recall not available")
        hits = await recall(search_query, top_k=5)
    except Exception as e:
        log.warning("recall() failed in assistant: %s", e)

    if not hits:
        return _no_history(
            "No relevant historical incidents found in memory for this query.",
            question=question,
        )

    # Build LLM prompt with memory context
    mem_lines = []
    for h in hits:
        src = " [MOCK DATA]" if h.get("_source") == "mock" else ""
        mem_lines.append(
            f"  - Incident {h.get('incident_id','?')}{src} "
            f"(score={h.get('score',0):.2f}, outcome={h.get('outcome','?')}): "
            f"{h.get('text','')[:400]}"
        )
    mem_context = "\n".join(mem_lines)

    prompt = f"""Answer the following question using the incident memory context below.

QUESTION: {question}
{f'SERVICE CONTEXT: {service}' if service else ''}
{f'CURRENT INCIDENT: {incident_id}' if incident_id else ''}

HISTORICAL MEMORY:
{mem_context}

Rules:
- Only reference incidents listed in HISTORICAL MEMORY above.
- For "what fixed this last time?", identify the most recent incident with outcome=worked and extract the fix.
- Include the exact Incident ID in your response.
- If no fix is found in the memory, set fix=null and say so clearly.
- Set confidence based on how relevant the memory hits are (0.0-1.0).

Respond with valid JSON only."""

    raw = call_llm(
        prompt=prompt,
        system=_ASSISTANT_SYSTEM,
        expect_json=True,
        cache_key=f"assistant-{hash(question + str(service))}",
    )

    if not isinstance(raw, dict):
        return _no_history("LLM returned an unexpected response format.")

    # Validate – ensure incident_id is from actual memory hits
    known_ids = {h.get("incident_id") for h in hits if h.get("incident_id")}
    raw_iid = raw.get("incident_id")
    if raw_iid and raw_iid not in known_ids:
        # LLM fabricated an incident ID
        log.warning("LLM returned non-existent incident_id %r, clearing", raw_iid)
        raw["incident_id"] = None
        raw["fix"] = None
        raw["caveat"] = (
            (raw.get("caveat") or "") +
            " [WARNING: LLM cited an incident ID not found in memory; cleared for safety.]"
        )

    # Add mock-data caveat if applicable
    sources = {h.get("_source") for h in hits}
    if "mock" in sources and "hindsight" not in sources:
        existing_caveat = raw.get("caveat") or ""
        if "[MOCK" not in existing_caveat:
            raw["caveat"] = (
                (existing_caveat + " " if existing_caveat else "") +
                "[NOTE: Response based on mock/seed data – Hindsight is unavailable]"
            ).strip()

    # Ensure required fields
    raw.setdefault("answer", "No specific answer available.")
    raw.setdefault("incident_id", None)
    raw.setdefault("fix", None)
    raw.setdefault("runbook", None)
    raw.setdefault("confidence", 0.0)
    raw.setdefault("evidence", [])
    raw.setdefault("caveat", "")

    return raw


def _no_history(reason: str, question: str | None = None) -> dict:
    return {
        "answer": f"No historical information available. {reason}",
        "incident_id": None,
        "fix": None,
        "runbook": None,
        "confidence": 0.0,
        "evidence": [],
        "caveat": reason,
    }


# ---------------------------------------------------------------------------
# Convenience helpers for specific common queries
# ---------------------------------------------------------------------------

async def what_fixed_last_time(service: str) -> dict:
    """
    Dedicated handler for "What fixed this last time?" queries.
    Searches for the most relevant worked fix for the given service.
    """
    return await answer_query(
        question=f"What fixed this last time for service {service}?",
        service=service,
    )


async def have_we_seen_this(service: str, message: str) -> dict:
    """Check if a similar incident has been seen before."""
    return await answer_query(
        question=f"Have we seen this before? Service: {service}, Issue: {message}",
        service=service,
    )


async def what_to_avoid(service: str) -> dict:
    """Retrieve known failed fixes that should be avoided."""
    return await answer_query(
        question=f"What actions should we avoid for {service} based on past failures?",
        service=service,
    )
