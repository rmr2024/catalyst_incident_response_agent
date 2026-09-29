"""
memory/service.py
-----------------
Hindsight long-term memory integration.

Provides:
  recall(query, top_k)          – search historical incidents
  retain_incident(record)       – persist an incident record
  retain_postmortem(record)     – persist an approved postmortem
  reflect(incident_id)          – generate a reflective summary for an incident

Falls back to an in-process mock store when Hindsight is unreachable or
MEMORY_ENABLED is False.  Mock data is clearly labelled as "[MOCK]" so it
is never confused with real historical evidence.
"""

from __future__ import annotations

import json
import logging
import time
from copy import deepcopy
from typing import Any

from settings import settings

log = logging.getLogger("memory.service")

# ---------------------------------------------------------------------------
# Mock / local fallback store
# ---------------------------------------------------------------------------
# A small set of seed incidents used when Hindsight is unavailable.
# Every entry has an "incident_id" field so recalled information is traceable.
# IMPORTANT: these are clearly marked as mock/seed data.

_MOCK_SEED: list[dict] = [
    {
        "id": "mock-m001",
        "incident_id": "INC-1001",
        "text": (
            "[MOCK] Incident ID: INC-1001 | Service: payments-db | "
            "Symptoms: connection pool exhausted, requests timing out, HTTP 503 spike | "
            "Root cause: database connection pool saturation under elevated load | "
            "Fix steps: restart connection pool manager, scale up pool size to 50 | "
            "Outcome: worked | Runbook: DB-POOL-RECOVERY | "
            "Lessons: monitor pool utilization; set alert at 80% capacity"
        ),
        "service": "payments-db",
        "keywords": ["connection pool", "exhausted", "timeout", "503", "payments"],
        "outcome": "worked",
        "score": 0.0,
    },
    {
        "id": "mock-m002",
        "incident_id": "INC-1002",
        "text": (
            "[MOCK] Incident ID: INC-1002 | Service: payments-db | "
            "Symptoms: connection pool exhausted after deploy v2.4.1, memory spike | "
            "Root cause: connection leak introduced in deploy v2.4.1 | "
            "Fix steps: rolled back to v2.4.0 | "
            "Failed steps: increasing pool size alone (did not resolve leak) | "
            "Outcome: worked | Runbook: ROLLBACK-SVC | "
            "Lessons: review connection handling in each new deploy"
        ),
        "service": "payments-db",
        "keywords": ["connection pool", "exhausted", "deploy", "rollback", "payments", "leak"],
        "outcome": "worked",
        "score": 0.0,
    },
    {
        "id": "mock-m003",
        "incident_id": "INC-1003",
        "text": (
            "[MOCK] Incident ID: INC-1003 | Service: payments-db | "
            "Symptoms: pool size increase attempted, no improvement | "
            "Root cause: underlying connection leak, not pool size shortage | "
            "Fix steps: increased pool size to 100 | "
            "Failed steps: increasing pool size alone did not fix the issue | "
            "Outcome: failed | "
            "Lessons: diagnose leak before increasing pool size"
        ),
        "service": "payments-db",
        "keywords": ["connection pool", "pool size", "failed", "payments"],
        "outcome": "failed",
        "score": 0.0,
    },
    {
        "id": "mock-m004",
        "incident_id": "INC-1004",
        "text": (
            "[MOCK] Incident ID: INC-1004 | Service: auth | "
            "Symptoms: authentication failures spiking, JWT validation errors | "
            "Root cause: token signing key rotation without graceful cutover | "
            "Fix steps: revert key rotation, deploy with dual-key support | "
            "Outcome: worked | Runbook: AUTH-KEY-ROTATION | "
            "Lessons: always use dual-key strategy during key rotation"
        ),
        "service": "auth",
        "keywords": ["auth", "authentication", "jwt", "token", "key", "signing"],
        "outcome": "worked",
        "score": 0.0,
    },
    {
        "id": "mock-m005",
        "incident_id": "INC-1005",
        "text": (
            "[MOCK] Incident ID: INC-1005 | Service: api-gateway | "
            "Symptoms: 5xx errors rising, upstream timeouts to payments service | "
            "Root cause: payments service overloaded, no circuit breaker | "
            "Fix steps: enable circuit breaker on api-gateway -> payments route, "
            "shed load temporarily | "
            "Outcome: worked | Runbook: CIRCUIT-BREAKER-PAYMENTS | "
            "Lessons: configure circuit breakers for all critical upstream dependencies"
        ),
        "service": "api-gateway",
        "keywords": ["5xx", "timeout", "api-gateway", "circuit breaker", "payments", "upstream"],
        "outcome": "worked",
        "score": 0.0,
    },
    {
        "id": "mock-m006",
        "incident_id": "INC-1006",
        "text": (
            "[MOCK] Incident ID: INC-1006 | Service: checkout | "
            "Symptoms: checkout flow failing, database writes timing out | "
            "Root cause: slow query after schema migration, missing index | "
            "Fix steps: added missing index on orders.created_at, query plan verified | "
            "Outcome: worked | Runbook: DB-SLOW-QUERY | "
            "Lessons: run EXPLAIN ANALYZE on all migration queries before deploying"
        ),
        "service": "checkout",
        "keywords": ["checkout", "database", "slow query", "timeout", "migration", "index"],
        "outcome": "worked",
        "score": 0.0,
    },
]

# In-memory fallback store (used when Hindsight is unavailable)
_mock_store: list[dict] = [deepcopy(r) for r in _MOCK_SEED]
_mock_postmortems: list[dict] = []


# ---------------------------------------------------------------------------
# Similarity helpers (keyword-based for mock mode)
# ---------------------------------------------------------------------------

def _keyword_score(query: str, record: dict) -> float:
    """Return a rough similarity score based on keyword overlap."""
    q_words = set(query.lower().split())
    kw_hits = sum(1 for kw in record.get("keywords", []) if kw in query.lower())
    text_hits = sum(1 for w in q_words if w in record.get("text", "").lower())
    total = kw_hits * 2 + text_hits
    # Normalize loosely to 0-1
    max_possible = len(record.get("keywords", [])) * 2 + len(q_words)
    return round(min(total / max(max_possible, 1), 1.0), 3)


# ---------------------------------------------------------------------------
# Hindsight client helpers
# ---------------------------------------------------------------------------

def _get_hindsight_client():
    """Attempt to return a configured Hindsight client.  Returns None on failure."""
    try:
        import hindsight  # type: ignore
        client = hindsight.Client(
            base_url=settings.hindsight_url,
            api_key=settings.hindsight_api_key or None,
        )
        return client
    except Exception as e:
        log.debug("Hindsight client unavailable: %s", e)
        return None


def _hindsight_available() -> bool:
    """Quick reachability check for Hindsight."""
    client = _get_hindsight_client()
    if client is None:
        return False
    try:
        # Try a lightweight ping if the client supports it
        if hasattr(client, "ping"):
            client.ping()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def recall(query: str, top_k: int = 5) -> list[dict]:
    """
    Search long-term memory for incidents similar to *query*.

    Returns a list of dicts, each containing at minimum:
        id, text, incident_id, score, outcome

    Falls back to the in-process mock store when Hindsight is unreachable.
    Mock results are prefixed with [MOCK] and clearly labelled.
    """
    if not query or not query.strip():
        return []

    # --- Try Hindsight first ---
    client = _get_hindsight_client()
    if client is not None:
        try:
            results = client.recall(
                bank=settings.hindsight_bank,
                query=query,
                top_k=top_k,
            )
            hits = []
            for r in (results or []):
                meta = r.get("metadata") or {}
                hits.append({
                    "id": str(r.get("id") or r.get("memory_id") or ""),
                    "text": str(r.get("text") or r.get("content") or ""),
                    "incident_id": str(
                        meta.get("incident_id") or r.get("incident_id") or ""
                    ),
                    "score": float(r.get("score") or r.get("similarity") or 0.0),
                    "outcome": str(meta.get("outcome") or r.get("outcome") or ""),
                    "_source": "hindsight",
                })
            log.info("recall(%r) -> %d Hindsight hits", query, len(hits))
            return hits[:top_k]
        except Exception as e:
            log.warning("Hindsight recall failed, using mock fallback: %s", e)

    # --- Mock fallback ---
    scored = []
    for r in _mock_store:
        score = _keyword_score(query, r)
        hit = deepcopy(r)
        hit["score"] = score
        hit["_source"] = "mock"
        scored.append(hit)

    # Sort by score descending, return top_k with score > 0
    scored.sort(key=lambda x: x["score"], reverse=True)
    results = [h for h in scored if h["score"] > 0][:top_k]
    log.info("recall(%r) -> %d mock hits (Hindsight unavailable)", query, len(results))
    return results


async def retain_incident(record: dict) -> str:
    """
    Persist an incident record to long-term memory.

    The *record* must contain an 'incident_id' field so that the stored
    memory can be traced back to the original incident.

    Returns a confirmation string.
    """
    incident_id = record.get("incident_id") or record.get("id") or ""
    if not incident_id:
        log.warning("retain_incident called without incident_id – traceability will be lost")

    # Build a human-readable text blob for embedding
    service = record.get("service", "unknown")
    symptoms = record.get("symptoms") or {}
    root_cause = record.get("root_cause") or ""
    fix_steps = record.get("fix_steps") or []
    outcome = record.get("outcome") or "unknown"
    runbook = record.get("runbook") or ""
    lessons = record.get("lessons") or []
    resolution = record.get("resolution") or ""

    step_lines = "; ".join(
        f"{s['step']} ({s.get('status','?')})" if isinstance(s, dict) else str(s)
        for s in fix_steps
    )
    lesson_lines = "; ".join(str(l) for l in lessons) if lessons else ""
    msg = symptoms.get("message", "") if isinstance(symptoms, dict) else str(symptoms)
    metrics_raw = symptoms.get("metrics", {}) if isinstance(symptoms, dict) else {}
    metrics_str = ", ".join(f"{k}={v}" for k, v in metrics_raw.items()) if metrics_raw else ""

    text = (
        f"Incident ID: {incident_id} | Service: {service} | "
        f"Symptoms: {msg}"
        + (f" | Metrics: {metrics_str}" if metrics_str else "")
        + f" | Root cause: {root_cause}"
        + (f" | Resolution: {resolution}" if resolution else "")
        + (f" | Fix steps: {step_lines}" if step_lines else "")
        + f" | Outcome: {outcome}"
        + (f" | Runbook: {runbook}" if runbook else "")
        + (f" | Lessons: {lesson_lines}" if lesson_lines else "")
    )

    metadata = {
        "incident_id": incident_id,
        "service": service,
        "outcome": outcome,
        "ts": str(int(time.time())),
    }

    # --- Try Hindsight ---
    client = _get_hindsight_client()
    if client is not None:
        try:
            result = client.remember(
                bank=settings.hindsight_bank,
                text=text,
                metadata=metadata,
            )
            mem_id = getattr(result, "id", None) or (result.get("id") if isinstance(result, dict) else None) or "?"
            log.info("retain_incident(%s) stored in Hindsight, id=%s", incident_id, mem_id)
            return f"stored in Hindsight: id={mem_id}"
        except Exception as e:
            log.warning("Hindsight retain failed, using mock fallback: %s", e)

    # --- Mock fallback: deduplicate by incident_id ---
    existing_ids = {r.get("incident_id") for r in _mock_store}
    if incident_id and incident_id in existing_ids:
        # Update existing entry
        for r in _mock_store:
            if r.get("incident_id") == incident_id:
                r["text"] = text
                r["outcome"] = outcome
                r["metadata"] = metadata
                r["keywords"] = _extract_keywords(text)
        log.info("retain_incident(%s) updated in mock store", incident_id)
        return f"updated in mock store: incident_id={incident_id}"

    entry = {
        "id": f"mock-{incident_id}-{int(time.time())}",
        "incident_id": incident_id,
        "text": text,
        "service": service,
        "outcome": outcome,
        "keywords": _extract_keywords(text),
        "metadata": metadata,
        "_source": "mock",
    }
    _mock_store.append(entry)
    log.info("retain_incident(%s) stored in mock store", incident_id)
    return f"stored in mock store: incident_id={incident_id}"


async def retain_postmortem(record: dict) -> str:
    """
    Persist an approved postmortem to long-term memory.

    Only call after human approval – the postmortem becomes permanent knowledge.
    The incident_id is preserved so the memory is traceable.
    """
    incident_id = record.get("incident_id") or ""
    if not incident_id:
        log.warning("retain_postmortem called without incident_id")

    # Build rich text for embedding
    summary = record.get("summary", "")
    root_cause = record.get("root_cause", "") or record.get("hypotheses", "")
    actions_taken = record.get("actions_taken") or record.get("resolution", "")
    lessons = record.get("lessons_learned") or record.get("lessons") or []
    successful_fixes = record.get("successful_fixes") or []
    failed_fixes = record.get("failed_fixes") or []
    follow_up = record.get("follow_up_actions") or []

    if isinstance(lessons, list):
        lessons_str = "; ".join(lessons)
    else:
        lessons_str = str(lessons)

    if isinstance(successful_fixes, list):
        ok_str = "; ".join(str(f) for f in successful_fixes)
    else:
        ok_str = str(successful_fixes)

    if isinstance(failed_fixes, list):
        fail_str = "; ".join(str(f) for f in failed_fixes)
    else:
        fail_str = str(failed_fixes)

    if isinstance(follow_up, list):
        follow_str = "; ".join(str(f) for f in follow_up)
    else:
        follow_str = str(follow_up)

    text = (
        f"POSTMORTEM | Incident ID: {incident_id} | Summary: {summary} | "
        f"Root cause: {root_cause} | "
        + (f"Actions taken: {actions_taken} | " if actions_taken else "")
        + (f"Successful fixes: {ok_str} | " if ok_str else "")
        + (f"Failed fixes: {fail_str} | " if fail_str else "")
        + (f"Lessons learned: {lessons_str} | " if lessons_str else "")
        + (f"Follow-up: {follow_str}" if follow_str else "")
    )

    metadata = {
        "incident_id": incident_id,
        "type": "postmortem",
        "ts": str(int(time.time())),
    }

    # --- Try Hindsight ---
    client = _get_hindsight_client()
    if client is not None:
        try:
            result = client.remember(
                bank=settings.hindsight_bank,
                text=text,
                metadata=metadata,
            )
            mem_id = getattr(result, "id", None) or (result.get("id") if isinstance(result, dict) else None) or "?"
            log.info("retain_postmortem(%s) stored in Hindsight, id=%s", incident_id, mem_id)
            return f"postmortem stored in Hindsight: id={mem_id}"
        except Exception as e:
            log.warning("Hindsight retain_postmortem failed, using mock fallback: %s", e)

    # --- Mock fallback ---
    entry = {
        "id": f"mock-pm-{incident_id}-{int(time.time())}",
        "incident_id": incident_id,
        "text": text,
        "type": "postmortem",
        "keywords": _extract_keywords(text),
        "metadata": metadata,
        "_source": "mock",
    }
    _mock_postmortems.append(entry)
    log.info("retain_postmortem(%s) stored in mock store", incident_id)
    return f"postmortem stored in mock store: incident_id={incident_id}"


async def reflect(incident_id: str, context: dict | None = None) -> str:
    """
    Generate a reflective summary for a given incident by searching
    for related historical incidents.

    Returns a plain-text reflection string.
    This does NOT use the LLM – it aggregates memory evidence only.
    """
    if not incident_id:
        return "No incident_id provided; cannot reflect."

    service = (context or {}).get("service", "")
    query = f"{incident_id} {service}"
    hits = await recall(query, top_k=5)

    if not hits:
        return (
            f"No historical memory found for incident {incident_id}. "
            "This may be a novel incident."
        )

    lines = [f"Reflection for {incident_id} (based on {len(hits)} memory hits):"]
    for h in hits:
        src = h.get("_source", "")
        label = " [MOCK]" if src == "mock" else ""
        lines.append(
            f"  - [{h.get('incident_id','?')}]{label} score={h.get('score',0):.2f} "
            f"outcome={h.get('outcome','?')}: {h.get('text','')[:120]}..."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a memory text blob."""
    important = [
        "connection pool", "exhausted", "timeout", "503", "5xx", "deploy",
        "rollback", "restart", "authentication", "jwt", "token", "checkout",
        "payments", "auth", "api-gateway", "database", "slow query", "index",
        "circuit breaker", "memory", "cpu", "leak", "saturation",
        "pool size", "failed", "worked", "partial",
    ]
    return [kw for kw in important if kw in text.lower()]
