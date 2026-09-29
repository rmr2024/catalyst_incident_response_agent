"""
llm.py
------
LLM infrastructure for the Incident Response Agent.

Provides:
  call_llm(prompt, system, expect_json, cache_key)
    – routes to the configured provider (claude / groq / mock)
    – returns a validated JSON dict when expect_json=True
    – falls back to the mock provider on any error
    – caches responses to avoid redundant API calls

Provider selection:
  LLM_PROVIDER = "claude"  → Anthropic Claude
  LLM_PROVIDER = "groq"    → Groq
  LLM_PROVIDER = "mock"    → built-in mock (no API key needed)

API keys are read from environment variables only – never hardcoded.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from typing import Any

from settings import settings

log = logging.getLogger("llm")

# ---------------------------------------------------------------------------
# Simple in-memory LRU-style cache (thread-safe, TTL-aware)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[Any, float]] = {}
_cache_lock = threading.Lock()

CACHE_TTL_SECONDS = 300  # 5 minutes default


def _cache_key(prompt: str, system: str, provider: str) -> str:
    raw = f"{provider}|{system}|{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _cache_get(key: str) -> Any | None:
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        value, expires = entry
        if time.time() > expires:
            del _cache[key]
            return None
        return value


def _cache_set(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> None:
    with _cache_lock:
        _cache[key] = (value, time.time() + ttl)


def clear_cache() -> None:
    """Clear all cached LLM responses (useful for testing)."""
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict | None:
    """
    Extract the first JSON object from *text*, handling markdown code fences.
    Returns None if no valid JSON object is found.
    """
    if not text:
        return None

    # Strip markdown code fences
    clean = re.sub(r"```(?:json)?\s*", "", text).strip()
    clean = clean.replace("```", "").strip()

    # Try direct parse first
    try:
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Find first {...} block
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end > start:
        candidate = clean[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

def _mock_response(prompt: str, system: str, expect_json: bool) -> Any:
    """
    Return a deterministic mock response.  Used when no real LLM is configured
    or as a fallback when a real provider fails.
    """
    if not expect_json:
        return (
            "[MOCK LLM] This is a simulated LLM response. "
            "Configure LLM_PROVIDER and the appropriate API key for real responses."
        )

    # Try to detect what kind of JSON is expected from the prompt
    prompt_lower = prompt.lower()

    if "postmortem" in prompt_lower:
        return {
            "incident_id": _extract_field(prompt, "incident_id") or "UNKNOWN",
            "summary": "[MOCK] Simulated postmortem summary.",
            "timeline": ["[MOCK] Alert triggered", "[MOCK] Investigation started", "[MOCK] Mitigation applied"],
            "impact": "[MOCK] Impact assessment not available in mock mode.",
            "root_cause": "[MOCK] Root cause determined by mock LLM.",
            "root_cause_confidence": 0.5,
            "evidence": [],
            "actions_taken": ["[MOCK] Remediation step 1", "[MOCK] Remediation step 2"],
            "successful_fixes": ["[MOCK] Fix applied successfully"],
            "failed_fixes": [],
            "lessons_learned": ["[MOCK] Always monitor connection pool utilization."],
            "follow_up_actions": ["[MOCK] Add alerting for connection pool at 80% capacity"],
        }

    if "assistant" in prompt_lower or "what fixed" in prompt_lower or "last time" in prompt_lower:
        return {
            "answer": "[MOCK] No real historical fix available in mock mode.",
            "incident_id": None,
            "fix": None,
            "confidence": 0.0,
            "evidence": [],
        }

    # Default: investigation response
    return {
        "incident_id": _extract_field(prompt, "incident_id") or "UNKNOWN",
        "hypotheses": [
            {
                "cause": "[MOCK] Simulated hypothesis from mock LLM",
                "confidence": 0.5,
                "evidence_ids": [],
            }
        ],
        "evidence_ids": [],
        "action_steps": [
            "[MOCK] Check service logs",
            "[MOCK] Verify metrics dashboard",
            "[MOCK] Page on-call engineer if unresolved",
        ],
        "runbook_execution_steps": ["[MOCK] Follow standard runbook"],
        "avoid_list": [],
        "needs_approval": False,
        "novel_incident": True,
        "confidence": 0.3,
        "reasoning": "[MOCK] This is a simulated response. Configure a real LLM provider.",
        "whats_different": "[MOCK] No historical comparison available.",
    }


def _extract_field(text: str, field: str) -> str | None:
    """Naive field extraction from prompt text."""
    for line in text.split("\n"):
        if field.lower() in line.lower() and ":" in line:
            return line.split(":", 1)[-1].strip().strip('"').strip("'").strip(",")
    return None


# ---------------------------------------------------------------------------
# Claude (Anthropic) provider
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, system: str, model: str) -> str:
    """Call Anthropic Claude.  Raises on any error."""
    import anthropic  # type: ignore

    api_key = settings.anthropic_api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)
    resolved_model = model or "claude-3-5-haiku-20241022"

    msg = client.messages.create(
        model=resolved_model,
        max_tokens=2048,
        system=system or "You are an expert SRE incident response assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------

def _call_groq(prompt: str, system: str, model: str) -> str:
    """Call Groq.  Raises on any error."""
    from groq import Groq  # type: ignore

    api_key = settings.groq_api_key
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set")

    client = Groq(api_key=api_key)
    resolved_model = model or "llama3-70b-8192"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        max_tokens=2048,
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_llm(
    prompt: str,
    system: str = "",
    expect_json: bool = False,
    cache_key: str | None = None,
    ttl: int = CACHE_TTL_SECONDS,
) -> Any:
    """
    Call the configured LLM provider and return the response.

    Args:
        prompt:      The user/task prompt.
        system:      Optional system message / instructions.
        expect_json: When True, parse and validate the response as JSON.
                     Falls back to mock JSON if parsing fails.
        cache_key:   Optional explicit cache key.  If None, a hash of
                     provider+system+prompt is used.
        ttl:         Cache TTL in seconds (default 300).

    Returns:
        str  – if expect_json=False
        dict – if expect_json=True

    Never raises: any provider error triggers a fallback to the mock provider.
    """
    provider = (settings.llm_provider or "mock").strip().lower()
    model = settings.llm_model or ""

    ck = cache_key or _cache_key(prompt, system, provider)
    cached = _cache_get(ck)
    if cached is not None:
        log.debug("LLM cache hit: key=%s", ck)
        return cached

    raw: str | None = None
    used_provider = provider

    if provider == "mock":
        result = _mock_response(prompt, system, expect_json)
        _cache_set(ck, result, ttl)
        return result

    # Try the configured provider
    try:
        if provider == "claude":
            raw = _call_claude(prompt, system, model)
        elif provider == "groq":
            raw = _call_groq(prompt, system, model)
        else:
            log.warning("Unknown LLM provider %r, falling back to mock", provider)
            result = _mock_response(prompt, system, expect_json)
            _cache_set(ck, result, ttl)
            return result
    except Exception as e:
        log.warning("LLM provider %r failed (%s), falling back to mock", provider, e)
        result = _mock_response(prompt, system, expect_json)
        _cache_set(ck, result, ttl)
        return result

    # Process raw response
    if not expect_json:
        _cache_set(ck, raw, ttl)
        return raw

    # Parse JSON
    parsed = _extract_json(raw or "")
    if parsed is not None:
        _cache_set(ck, parsed, ttl)
        return parsed

    # JSON parse failed – log and fall back to mock
    log.warning(
        "LLM (%s) returned invalid JSON (len=%d), falling back to mock JSON",
        used_provider,
        len(raw or ""),
    )
    result = _mock_response(prompt, system, expect_json)
    _cache_set(ck, result, ttl)
    return result


def get_provider_info() -> dict:
    """Return current LLM configuration info (no secrets exposed)."""
    provider = (settings.llm_provider or "mock").strip().lower()
    has_claude_key = bool(settings.anthropic_api_key)
    has_groq_key = bool(settings.groq_api_key)
    effective = provider
    if provider == "claude" and not has_claude_key:
        effective = "mock (claude key missing)"
    elif provider == "groq" and not has_groq_key:
        effective = "mock (groq key missing)"
    return {
        "configured_provider": provider,
        "effective_provider": effective,
        "model": settings.llm_model or "(default)",
        "has_anthropic_key": has_claude_key,
        "has_groq_key": has_groq_key,
        "cache_size": len(_cache),
    }
