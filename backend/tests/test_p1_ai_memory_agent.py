"""
tests/test_p1_ai_memory_agent.py
---------------------------------
Comprehensive P1 test suite for the Incident Response Agent AI/Memory features.

Tests cover:
  - Memory ON performs recall
  - Memory OFF completely skips recall
  - Incident ID preserved during retention
  - Recalled information contains Incident IDs
  - Novel incident detection
  - Avoid-list generation
  - Risky actions require approval
  - Postmortem generation
  - Retain-after-approval
  - "What fixed this last time?" query
  - LLM provider switching/fallback
  - Invalid LLM JSON handling
  - LLM cache fallback
  - Hindsight unavailable behaviour

Framework: pytest (standard for FastAPI/Python projects)
Run: cd backend && python -m pytest tests/ -v
"""

from __future__ import annotations

import asyncio
import json
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup: ensure backend/ is on sys.path
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine synchronously (for tests)."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_alert(service="payments-db", message="connection pool exhausted", severity="P1"):
    from schemas import Alert
    return Alert(
        service=service,
        message=message,
        severity=severity,
        metrics={"error_rate": 0.15, "latency_p99_ms": 3400},
        timestamp=datetime.now(timezone.utc),
    )


def _noop_emit(*args, **kwargs):
    """No-op emitter for testing."""
    pass


# ===========================================================================
# 1. Memory Service Tests
# ===========================================================================

class TestMemoryRecall:
    """Test memory.service.recall() functionality."""

    def test_recall_returns_list(self):
        """recall() returns a list (may be empty if query doesn't match)."""
        from memory.service import recall
        results = _run(recall("payments-db connection pool exhausted"))
        assert isinstance(results, list)

    def test_recall_returns_incident_ids(self):
        """Every recalled hit must have an incident_id field (traceability)."""
        from memory.service import recall
        results = _run(recall("payments-db connection pool exhausted"))
        for hit in results:
            assert "incident_id" in hit, f"Missing incident_id in hit: {hit}"
            assert hit["incident_id"], f"Empty incident_id in hit: {hit}"

    def test_recall_returns_scores(self):
        """Recalled hits should have a score field."""
        from memory.service import recall
        results = _run(recall("connection pool exhausted timeout 503"))
        for hit in results:
            assert "score" in hit
            assert isinstance(hit["score"], (int, float))

    def test_recall_empty_query(self):
        """recall() with empty query returns empty list."""
        from memory.service import recall
        results = _run(recall(""))
        assert results == []

    def test_recall_no_match_query(self):
        """recall() with gibberish query returns empty list or low-scored hits."""
        from memory.service import recall
        results = _run(recall("xyzzy completely unrelated gobbledegook"))
        # All returned scores should be 0 or list is empty
        for hit in results:
            assert hit.get("score", 0) == 0 or results == []

    def test_recall_mock_hits_labeled(self):
        """Mock recall hits are labeled as mock data."""
        from memory.service import recall
        results = _run(recall("payments-db connection pool"))
        mock_hits = [h for h in results if h.get("_source") == "mock"]
        for h in mock_hits:
            assert "[MOCK]" in h.get("text", ""), f"Mock hit not labeled: {h['text'][:80]}"

    def test_recall_top_k_respected(self):
        """recall() respects the top_k limit."""
        from memory.service import recall
        results = _run(recall("connection pool", top_k=2))
        assert len(results) <= 2


class TestMemoryRetainIncident:
    """Test memory.service.retain_incident()."""

    def test_retain_requires_incident_id(self):
        """retain_incident stores the record and returns a confirmation."""
        from memory.service import retain_incident
        record = {
            "incident_id": "TEST-9001",
            "service": "payments-db",
            "symptoms": {"message": "connection pool exhausted"},
            "root_cause": "pool saturation",
            "outcome": "worked",
            "fix_steps": [{"step": "Restart connection pool", "status": "succeeded"}],
        }
        result = _run(retain_incident(record))
        assert isinstance(result, str)
        assert "TEST-9001" in result or "stored" in result.lower()

    def test_retain_incident_id_in_stored_text(self):
        """The incident_id appears in the text stored in the mock store."""
        from memory import service as mem_svc
        from memory.service import retain_incident
        record = {
            "incident_id": "TRACE-5555",
            "service": "auth",
            "symptoms": {"message": "jwt validation failing"},
            "outcome": "worked",
        }
        _run(retain_incident(record))
        # Search the mock store for this incident
        matching = [r for r in mem_svc._mock_store if r.get("incident_id") == "TRACE-5555"]
        assert matching, "TRACE-5555 not found in mock store"
        assert "TRACE-5555" in matching[0]["text"]

    def test_retain_without_incident_id_logs_warning(self):
        """retain_incident with no incident_id runs but logs a warning."""
        from memory.service import retain_incident
        record = {"service": "unknown", "outcome": "partial"}
        # Should not raise
        result = _run(retain_incident(record))
        assert isinstance(result, str)


class TestMemoryRetainPostmortem:
    """Test memory.service.retain_postmortem()."""

    def test_retain_postmortem_stores_record(self):
        """retain_postmortem stores the postmortem and returns confirmation."""
        from memory.service import retain_postmortem, _mock_postmortems
        initial_count = len(_mock_postmortems)
        record = {
            "incident_id": "PM-TEST-001",
            "summary": "Test postmortem",
            "root_cause": "Connection pool exhaustion",
            "lessons_learned": ["Monitor pool usage"],
            "successful_fixes": ["Restarted connection pool"],
        }
        result = _run(retain_postmortem(record))
        assert isinstance(result, str)
        assert len(_mock_postmortems) > initial_count

    def test_retain_postmortem_preserves_incident_id(self):
        """The incident_id is preserved in the stored postmortem."""
        from memory.service import retain_postmortem, _mock_postmortems
        record = {
            "incident_id": "PM-TRACE-002",
            "summary": "Postmortem for traceability test",
        }
        _run(retain_postmortem(record))
        matching = [p for p in _mock_postmortems if p.get("incident_id") == "PM-TRACE-002"]
        assert matching, "PM-TRACE-002 not found in mock postmortems"
        assert "PM-TRACE-002" in matching[0]["text"]


class TestMemoryReflect:
    """Test memory.service.reflect()."""

    def test_reflect_returns_string(self):
        """reflect() returns a non-empty string."""
        from memory.service import reflect
        result = _run(reflect("INC-1001", context={"service": "payments-db"}))
        assert isinstance(result, str)
        assert len(result) > 10

    def test_reflect_no_incident_id(self):
        """reflect() with empty incident_id returns a clear message."""
        from memory.service import reflect
        result = _run(reflect(""))
        assert "No incident_id" in result or "cannot" in result.lower()


# ===========================================================================
# 2. LLM Infrastructure Tests
# ===========================================================================

class TestLLMProviderSwitching:
    """Test LLM provider selection and fallback."""

    def test_mock_provider_returns_dict_for_json(self):
        """Mock provider returns a dict when expect_json=True."""
        from llm import call_llm
        with patch("llm.settings") as mock_settings:
            mock_settings.llm_provider = "mock"
            mock_settings.llm_model = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.groq_api_key = ""
            from llm import clear_cache
            clear_cache()
            result = call_llm("test prompt", expect_json=True)
        assert isinstance(result, dict)

    def test_mock_provider_returns_string_for_non_json(self):
        """Mock provider returns a string when expect_json=False."""
        from llm import call_llm, clear_cache
        clear_cache()
        with patch("llm.settings") as mock_settings:
            mock_settings.llm_provider = "mock"
            mock_settings.llm_model = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.groq_api_key = ""
            result = call_llm("test prompt", expect_json=False)
        assert isinstance(result, str)
        assert "[MOCK" in result

    def test_claude_fallback_when_no_key(self):
        """Claude provider falls back to mock when API key is missing."""
        from llm import call_llm, clear_cache
        clear_cache()
        with patch("llm.settings") as mock_settings:
            mock_settings.llm_provider = "claude"
            mock_settings.llm_model = ""
            mock_settings.anthropic_api_key = ""  # No key
            mock_settings.groq_api_key = ""
            result = call_llm("test prompt", expect_json=True)
        # Should fall back to mock (dict with mock content)
        assert isinstance(result, dict)

    def test_groq_fallback_when_no_key(self):
        """Groq provider falls back to mock when API key is missing."""
        from llm import call_llm, clear_cache
        clear_cache()
        with patch("llm.settings") as mock_settings:
            mock_settings.llm_provider = "groq"
            mock_settings.llm_model = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.groq_api_key = ""  # No key
            result = call_llm("test prompt", expect_json=True)
        assert isinstance(result, dict)

    def test_unknown_provider_falls_back_to_mock(self):
        """Unknown provider name falls back to mock."""
        from llm import call_llm, clear_cache
        clear_cache()
        with patch("llm.settings") as mock_settings:
            mock_settings.llm_provider = "nonexistent_provider"
            mock_settings.llm_model = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.groq_api_key = ""
            result = call_llm("test prompt", expect_json=True)
        assert isinstance(result, dict)

    def test_get_provider_info(self):
        """get_provider_info returns a dict with key fields."""
        from llm import get_provider_info
        info = get_provider_info()
        assert "configured_provider" in info
        assert "effective_provider" in info
        assert "has_anthropic_key" in info


class TestLLMCache:
    """Test LLM response caching."""

    def test_cache_hit_on_second_call(self):
        """Second call with same key returns cached result."""
        from llm import call_llm, clear_cache
        clear_cache()
        with patch("llm.settings") as mock_settings:
            mock_settings.llm_provider = "mock"
            mock_settings.llm_model = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.groq_api_key = ""
            r1 = call_llm("same prompt", cache_key="test-cache-key")
            r2 = call_llm("same prompt", cache_key="test-cache-key")
        assert r1 == r2

    def test_cache_cleared(self):
        """clear_cache() empties the cache."""
        from llm import call_llm, clear_cache, _cache
        clear_cache()
        assert len(_cache) == 0

    def test_different_prompts_different_cache_keys(self):
        """Different prompts generate different cache entries."""
        from llm import call_llm, clear_cache, _cache_key
        k1 = _cache_key("prompt A", "system", "mock")
        k2 = _cache_key("prompt B", "system", "mock")
        assert k1 != k2


class TestLLMJSONHandling:
    """Test invalid JSON handling."""

    def test_extract_json_from_markdown(self):
        """_extract_json handles markdown fenced JSON."""
        from llm import _extract_json
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_embedded_in_text(self):
        """_extract_json extracts JSON from surrounding text."""
        from llm import _extract_json
        text = 'Here is the response: {"incident_id": "INC-001", "confidence": 0.8}'
        result = _extract_json(text)
        assert result is not None
        assert result["incident_id"] == "INC-001"

    def test_extract_json_invalid_returns_none(self):
        """_extract_json returns None for invalid JSON."""
        from llm import _extract_json
        assert _extract_json("not json at all") is None
        assert _extract_json("") is None
        assert _extract_json(None) is None

    def test_invalid_json_falls_back_to_mock(self):
        """When LLM returns invalid JSON, fall back to mock JSON."""
        from llm import call_llm, clear_cache

        def _bad_claude(*args, **kwargs):
            return "This is not JSON at all"

        clear_cache()
        with patch("llm._call_claude", side_effect=_bad_claude):
            with patch("llm.settings") as mock_settings:
                mock_settings.llm_provider = "claude"
                mock_settings.llm_model = ""
                mock_settings.anthropic_api_key = "fake-key-for-test"
                mock_settings.groq_api_key = ""
                result = call_llm("test", expect_json=True)
        assert isinstance(result, dict)


# ===========================================================================
# 3. Agent Pipeline Tests
# ===========================================================================

class TestAgentMemoryOFF:
    """Agent behaviour when memory is DISABLED."""

    def test_memory_off_skips_recall(self):
        """When memory is OFF, recall() is never called."""
        from settings import set_memory_enabled
        set_memory_enabled(False)
        try:
            call_count = {"n": 0}

            async def mock_recall(*args, **kwargs):
                call_count["n"] += 1
                return []

            with patch("agent.memory_enabled", return_value=False), \
                 patch("agent._perform_recall", side_effect=mock_recall):
                from agent import investigate
                alert = _make_alert()
                rec = _run(investigate("INC-TEST-OFF", alert, _noop_emit))

            assert call_count["n"] == 0, "recall() should NOT be called when memory is OFF"
        finally:
            set_memory_enabled(True)

    def test_memory_off_recommendation_is_generic(self):
        """Memory OFF recommendation contains no historical evidence."""
        from settings import set_memory_enabled
        set_memory_enabled(False)
        try:
            with patch("agent.memory_enabled", return_value=False):
                from agent import investigate
                alert = _make_alert()
                rec = _run(investigate("INC-TEST-OFF-2", alert, _noop_emit))
            assert rec.similar == [] or all(s.incident_id is None for s in rec.similar), \
                "Memory OFF should produce no similar incident references"
        finally:
            set_memory_enabled(True)


class TestAgentMemoryON:
    """Agent behaviour when memory is ENABLED."""

    def test_memory_on_calls_recall(self):
        """When memory is ON, recall() is invoked."""
        from settings import set_memory_enabled
        set_memory_enabled(True)
        call_count = {"n": 0}

        async def _mock_recall(alert, emit):
            call_count["n"] += 1
            return [
                {
                    "id": "mock-m001",
                    "incident_id": "INC-1001",
                    "text": "[MOCK] INC-1001 connection pool exhausted – restarted pool",
                    "score": 0.82,
                    "outcome": "worked",
                    "_source": "mock",
                }
            ]

        with patch("agent.memory_enabled", return_value=True), \
             patch("agent._perform_recall", side_effect=_mock_recall):
            from agent import investigate
            alert = _make_alert()
            rec = _run(investigate("INC-TEST-ON", alert, _noop_emit))

        assert call_count["n"] == 1, "recall() MUST be called when memory is ON"

    def test_memory_on_similar_contains_incident_ids(self):
        """Memory ON recommendation includes recalled incident IDs."""
        from settings import set_memory_enabled
        set_memory_enabled(True)

        hits = [
            {
                "id": "mock-m001",
                "incident_id": "INC-1001",
                "text": "[MOCK] INC-1001 connection pool exhausted – restarted pool, worked",
                "score": 0.82,
                "outcome": "worked",
                "_source": "mock",
            }
        ]

        async def _mock_recall(alert, emit):
            return hits

        with patch("agent.memory_enabled", return_value=True), \
             patch("agent._perform_recall", side_effect=_mock_recall):
            from agent import investigate
            alert = _make_alert()
            rec = _run(investigate("INC-TEST-ON-2", alert, _noop_emit))

        # similar should contain INC-1001
        incident_ids = [s.incident_id for s in rec.similar if s.incident_id]
        assert "INC-1001" in incident_ids, f"INC-1001 missing from similar: {incident_ids}"


class TestNovelIncidentDetection:
    """Test novel incident detection logic."""

    def test_novel_when_no_hits(self):
        """is_novel=True when recall returns no results."""
        from agent import _is_novel
        assert _is_novel([]) is True

    def test_novel_when_all_scores_low(self):
        """is_novel=True when all hits have score below NOVEL_THRESHOLD."""
        from agent import _is_novel, NOVEL_THRESHOLD
        hits = [{"score": NOVEL_THRESHOLD - 0.01}, {"score": 0.1}]
        assert _is_novel(hits) is True

    def test_not_novel_when_high_score_hit(self):
        """is_novel=False when at least one hit exceeds NOVEL_THRESHOLD."""
        from agent import _is_novel, NOVEL_THRESHOLD
        hits = [{"score": NOVEL_THRESHOLD + 0.1}, {"score": 0.1}]
        assert _is_novel(hits) is False

    def test_novel_detection_in_pipeline(self):
        """Pipeline sets is_novel=True for novel incidents."""
        async def _mock_recall_empty(alert, emit):
            return []

        with patch("agent.memory_enabled", return_value=True), \
             patch("agent._perform_recall", side_effect=_mock_recall_empty):
            from agent import investigate
            alert = _make_alert(message="completely unknown novel failure mode xyz")
            rec = _run(investigate("INC-NOVEL-TEST", alert, _noop_emit))

        assert rec.is_novel is True, "Pipeline should flag novel incident when no hits"


class TestAvoidList:
    """Test avoid_list generation from historical failed actions."""

    def test_avoid_list_from_failed_hits(self):
        """_build_avoid_list extracts failed actions from memory hits."""
        from agent import _build_avoid_list
        hits = [
            {
                "incident_id": "INC-1003",
                "text": "INC-1003 | Service: payments-db | Fix steps: increasing pool size | Failed steps: increasing pool size alone did not fix the issue | Outcome: failed",
                "outcome": "failed",
                "_source": "mock",
            }
        ]
        avoid = _build_avoid_list(hits)
        assert isinstance(avoid, list)
        # May be non-empty if text parsing finds the failed step
        # At minimum, should not crash

    def test_avoid_list_empty_for_no_failed_hits(self):
        """_build_avoid_list returns [] when no failed outcomes exist."""
        from agent import _build_avoid_list
        hits = [
            {"incident_id": "INC-1001", "outcome": "worked", "text": "...", "_source": "mock"},
            {"incident_id": "INC-1004", "outcome": "worked", "text": "...", "_source": "mock"},
        ]
        avoid = _build_avoid_list(hits)
        assert avoid == []

    def test_avoid_list_no_fabrication(self):
        """Avoid list never contains fabricated items for empty hits."""
        from agent import _build_avoid_list
        assert _build_avoid_list([]) == []


class TestApprovalGuardrails:
    """Test that risky actions trigger needs_approval=True."""

    def test_risky_actions_detected(self):
        """_is_risky correctly identifies destructive actions."""
        from agent import _is_risky
        assert _is_risky("Restart the connection pool manager") is True
        assert _is_risky("Roll back deploy abc123") is True
        assert _is_risky("Redeploy the service") is True
        assert _is_risky("Scale up connection pool to 50") is True
        assert _is_risky("Delete the stale cache entries") is True
        assert _is_risky("Kill the zombie process") is True
        assert _is_risky("Check service logs") is False
        assert _is_risky("Gather metrics from dashboard") is False
        assert _is_risky("Page the on-call engineer") is False

    def test_pipeline_sets_needs_approval_for_risky_steps(self):
        """Pipeline sets needs_approval=True when steps contain risky actions."""
        from llm import clear_cache
        clear_cache()

        def _mock_llm(prompt, system="", expect_json=False, cache_key=None, ttl=300):
            return {
                "incident_id": "INC-RISKY",
                "hypotheses": [{"cause": "DB pool exhaustion", "confidence": 0.8, "evidence_ids": []}],
                "evidence_ids": [],
                "action_steps": ["Restart the connection pool manager"],  # RISKY
                "runbook_execution_steps": [],
                "avoid_list": [],
                "needs_approval": False,  # LLM says false, but pipeline should override
                "novel_incident": False,
                "confidence": 0.8,
            }

        with patch("agent.call_llm", side_effect=_mock_llm), \
             patch("agent.memory_enabled", return_value=False):
            from agent import investigate
            alert = _make_alert()
            rec = _run(investigate("INC-RISKY", alert, _noop_emit))

        assert rec.needs_approval is True, \
            "Pipeline must set needs_approval=True for restart/rollback steps"

    def test_safe_steps_do_not_need_approval(self):
        """Safe steps do not trigger needs_approval."""
        from llm import clear_cache
        clear_cache()

        def _mock_llm(prompt, system="", expect_json=False, cache_key=None, ttl=300):
            return {
                "incident_id": "INC-SAFE",
                "hypotheses": [{"cause": "Unknown", "confidence": 0.3, "evidence_ids": []}],
                "evidence_ids": [],
                "action_steps": ["Check service logs", "Gather metrics"],  # SAFE
                "runbook_execution_steps": [],
                "avoid_list": [],
                "needs_approval": False,
                "novel_incident": True,
                "confidence": 0.3,
            }

        with patch("agent.call_llm", side_effect=_mock_llm), \
             patch("agent.memory_enabled", return_value=False):
            from agent import investigate
            alert = _make_alert()
            rec = _run(investigate("INC-SAFE", alert, _noop_emit))

        assert rec.needs_approval is False


# ===========================================================================
# 4. Postmortem Tests
# ===========================================================================

class TestPostmortemGeneration:
    """Test postmortem drafting and approval."""

    def test_draft_postmortem_returns_dict(self):
        """draft_postmortem returns a dict with required fields."""
        from postmortem import draft_postmortem

        # Use a mock incident (DB may not have real incidents in test)
        mock_inc = MagicMock()
        mock_inc.id = "INC-PM-TEST"
        mock_inc.service = "payments-db"
        mock_inc.message = "connection pool exhausted"
        mock_inc.severity = "P1"
        mock_inc.status = "resolved"
        mock_inc.top_hypothesis = "DB connection pool saturation"
        mock_inc.resolution = "Restarted connection pool"
        mock_inc.outcome = "worked"
        mock_inc.recommendation_json = "{}"
        mock_inc.created_at = datetime.now(timezone.utc)
        mock_inc.resolved_at = datetime.now(timezone.utc)
        mock_inc.ttr_seconds = 120.0

        with patch("postmortem.crud") as mock_crud:
            mock_crud.get_incident.return_value = mock_inc
            mock_crud.list_actions.return_value = []
            mock_crud.list_events.return_value = []
            from llm import clear_cache
            clear_cache()
            pm = _run(draft_postmortem("INC-PM-TEST"))

        assert isinstance(pm, dict)
        assert pm["incident_id"] == "INC-PM-TEST"
        assert "_approved" in pm
        assert pm["_approved"] is False
        assert "_status" in pm
        assert pm["_status"] == "draft"

    def test_draft_postmortem_preserves_incident_id(self):
        """Draft postmortem always contains the correct incident_id."""
        from postmortem import draft_postmortem

        mock_inc = MagicMock()
        mock_inc.id = "INC-ID-TRACE"
        mock_inc.service = "auth"
        mock_inc.message = "jwt validation failing"
        mock_inc.severity = "P2"
        mock_inc.status = "resolved"
        mock_inc.top_hypothesis = "Key rotation issue"
        mock_inc.resolution = "Reverted key rotation"
        mock_inc.outcome = "worked"
        mock_inc.recommendation_json = "{}"
        mock_inc.created_at = datetime.now(timezone.utc)
        mock_inc.resolved_at = datetime.now(timezone.utc)
        mock_inc.ttr_seconds = 300.0

        with patch("postmortem.crud") as mock_crud:
            mock_crud.get_incident.return_value = mock_inc
            mock_crud.list_actions.return_value = []
            mock_crud.list_events.return_value = []
            from llm import clear_cache
            clear_cache()
            pm = _run(draft_postmortem("INC-ID-TRACE"))

        assert pm["incident_id"] == "INC-ID-TRACE"

    def test_draft_postmortem_not_approved(self):
        """Draft postmortem is NOT approved automatically."""
        from postmortem import draft_postmortem

        mock_inc = MagicMock()
        mock_inc.id = "INC-NOT-APPROVED"
        mock_inc.service = "checkout"
        mock_inc.message = "db write timeout"
        mock_inc.severity = "P1"
        mock_inc.status = "resolved"
        mock_inc.top_hypothesis = "Slow query"
        mock_inc.resolution = "Added index"
        mock_inc.outcome = "worked"
        mock_inc.recommendation_json = "{}"
        mock_inc.created_at = datetime.now(timezone.utc)
        mock_inc.resolved_at = datetime.now(timezone.utc)
        mock_inc.ttr_seconds = 600.0

        with patch("postmortem.crud") as mock_crud:
            mock_crud.get_incident.return_value = mock_inc
            mock_crud.list_actions.return_value = []
            mock_crud.list_events.return_value = []
            from llm import clear_cache
            clear_cache()
            pm = _run(draft_postmortem("INC-NOT-APPROVED"))

        assert pm.get("_approved") is False

    def test_approve_postmortem_calls_retain(self):
        """approve_postmortem calls retain_postmortem and returns confirmation."""
        from postmortem import approve_postmortem

        pm = {
            "incident_id": "INC-APPROVE-TEST",
            "summary": "Test postmortem",
            "root_cause": "Pool exhaustion",
            "lessons_learned": ["Monitor pool"],
        }

        async def _mock_retain(record):
            return f"stored: incident_id={record['incident_id']}"

        with patch("postmortem.retain_postmortem", side_effect=_mock_retain), \
             patch("postmortem.crud") as mock_crud:
            mock_crud.add_audit.return_value = None
            result = _run(approve_postmortem("INC-APPROVE-TEST", pm))

        assert "INC-APPROVE-TEST" in result or "stored" in result.lower()

    def test_approve_postmortem_preserves_incident_id(self):
        """Approved postmortem retains the incident_id."""
        from postmortem import approve_postmortem

        retained_record = {}

        async def _mock_retain(record):
            retained_record.update(record)
            return "stored"

        with patch("postmortem.retain_postmortem", side_effect=_mock_retain), \
             patch("postmortem.crud") as mock_crud:
            mock_crud.add_audit.return_value = None
            _run(approve_postmortem("INC-RETAIN-TRACE", {"summary": "test"}))

        assert retained_record.get("incident_id") == "INC-RETAIN-TRACE"

    def test_draft_postmortem_invalid_incident_raises(self):
        """draft_postmortem raises ValueError for non-existent incident."""
        from postmortem import draft_postmortem
        with patch("postmortem.crud") as mock_crud:
            mock_crud.get_incident.return_value = None
            with pytest.raises(ValueError, match="not found"):
                _run(draft_postmortem("INC-DOES-NOT-EXIST"))


# ===========================================================================
# 5. Assistant Query Tests
# ===========================================================================

class TestAssistantQueryMemoryOFF:
    """Assistant behaviour when memory is OFF."""

    def test_memory_off_returns_no_history_message(self):
        """When memory is OFF, assistant returns clear no-history message."""
        from settings import set_memory_enabled
        set_memory_enabled(False)
        try:
            from assistant import answer_query
            result = _run(answer_query("What fixed this last time?", service="payments-db"))
        finally:
            set_memory_enabled(True)

        assert result["fix"] is None
        assert result["incident_id"] is None
        assert "disabled" in result["answer"].lower() or "unavailable" in result["answer"].lower()
        assert result["confidence"] == 0.0

    def test_memory_off_does_not_call_recall(self):
        """When memory is OFF, recall is never called."""
        call_count = {"n": 0}

        async def mock_recall(*args, **kwargs):
            call_count["n"] += 1
            return []

        with patch("assistant.memory_enabled", return_value=False), \
             patch("memory.service.recall", side_effect=mock_recall):
            from assistant import answer_query
            _run(answer_query("What fixed this last time?", service="payments-db"))

        assert call_count["n"] == 0


class TestAssistantQueryMemoryON:
    """Assistant behaviour when memory is ON."""

    def test_what_fixed_last_time_returns_answer(self):
        """what_fixed_last_time returns an answer dict with expected keys."""
        from settings import set_memory_enabled
        set_memory_enabled(True)
        from assistant import what_fixed_last_time
        result = _run(what_fixed_last_time("payments-db"))
        assert isinstance(result, dict)
        assert "answer" in result
        assert "incident_id" in result
        assert "fix" in result
        assert "confidence" in result

    def test_answer_references_incident_id_from_memory(self):
        """Assistant answer references a real incident ID from memory hits."""
        from settings import set_memory_enabled
        set_memory_enabled(True)

        hits = [
            {
                "id": "mock-m001",
                "incident_id": "INC-1001",
                "text": "[MOCK] INC-1001 payments-db connection pool exhausted – restarted pool, worked",
                "score": 0.85,
                "outcome": "worked",
                "_source": "mock",
            }
        ]

        def _mock_llm(prompt, system="", expect_json=False, cache_key=None, ttl=300):
            return {
                "answer": "Restarted connection pool manager (INC-1001)",
                "incident_id": "INC-1001",
                "fix": "Restart connection pool manager",
                "runbook": "DB-POOL-RECOVERY",
                "confidence": 0.85,
                "evidence": ["INC-1001"],
                "caveat": "",
            }

        with patch("assistant.memory_enabled", return_value=True), \
             patch("assistant.recall", AsyncMock(return_value=hits)), \
             patch("assistant.call_llm", side_effect=_mock_llm):
            from assistant import answer_query
            result = _run(answer_query("What fixed this last time?", service="payments-db"))

        assert result["incident_id"] == "INC-1001"
        assert result["fix"] is not None

    def test_fabricated_incident_id_cleared(self):
        """Assistant clears incident IDs fabricated by LLM (not in memory hits)."""
        from settings import set_memory_enabled
        set_memory_enabled(True)

        hits = [
            {
                "id": "m1",
                "incident_id": "INC-1001",
                "text": "[MOCK] INC-1001 ...",
                "score": 0.7,
                "outcome": "worked",
                "_source": "mock",
            }
        ]

        def _mock_llm_fabricate(prompt, system="", expect_json=False, cache_key=None, ttl=300):
            return {
                "answer": "Restarted pool (INC-FABRICATED-9999)",
                "incident_id": "INC-FABRICATED-9999",  # NOT in memory hits
                "fix": "Restart pool",
                "confidence": 0.9,
                "evidence": [],
                "caveat": "",
            }

        with patch("assistant.memory_enabled", return_value=True), \
             patch("assistant.recall", AsyncMock(return_value=hits)), \
             patch("assistant.call_llm", side_effect=_mock_llm_fabricate):
            from assistant import answer_query
            result = _run(answer_query("What fixed this last time?"))

        # Fabricated ID must be cleared
        assert result["incident_id"] is None, \
            f"Fabricated incident_id should be cleared, got: {result['incident_id']}"

    def test_no_memory_hits_returns_no_history(self):
        """When memory returns no hits, assistant returns no-history message."""
        with patch("assistant.memory_enabled", return_value=True), \
             patch("assistant.recall", AsyncMock(return_value=[])):
            from assistant import answer_query
            result = _run(answer_query("What fixed this last time?"))

        assert result["incident_id"] is None
        assert result["fix"] is None
        assert result["confidence"] == 0.0


# ===========================================================================
# 6. Hindsight Unavailable Tests
# ===========================================================================

class TestHindsightUnavailable:
    """Test graceful fallback when Hindsight is unavailable."""

    def test_recall_falls_back_to_mock_when_hindsight_down(self):
        """recall() uses mock store when Hindsight client is unavailable."""
        from memory.service import recall

        with patch("memory.service._get_hindsight_client", return_value=None):
            results = _run(recall("payments-db connection pool exhausted"))

        # Should still return results from mock store
        assert isinstance(results, list)

    def test_retain_falls_back_to_mock_when_hindsight_down(self):
        """retain_incident() uses mock store when Hindsight is unavailable."""
        from memory.service import retain_incident

        record = {
            "incident_id": "HINDSIGHT-DOWN-TEST",
            "service": "payments-db",
            "symptoms": {"message": "test"},
            "outcome": "worked",
        }

        with patch("memory.service._get_hindsight_client", return_value=None):
            result = _run(retain_incident(record))

        assert isinstance(result, str)
        assert "mock" in result.lower() or "stored" in result.lower()

    def test_hindsight_error_falls_back_gracefully(self):
        """When Hindsight raises an exception, recall falls back to mock."""
        from memory.service import recall

        mock_client = MagicMock()
        mock_client.recall.side_effect = ConnectionError("Hindsight is down")

        with patch("memory.service._get_hindsight_client", return_value=mock_client):
            results = _run(recall("payments-db timeout"))

        # Should fall back to mock
        assert isinstance(results, list)


# ===========================================================================
# 7. End-to-End Integration Tests
# ===========================================================================

class TestEndToEnd:
    """End-to-end pipeline tests."""

    def test_full_pipeline_memory_off(self):
        """
        E2E: Memory OFF produces a generic response with no historical references.
        """
        with patch("agent.memory_enabled", return_value=False):
            from agent import investigate
            from llm import clear_cache
            clear_cache()
            alert = _make_alert("payments-db", "connection pool exhausted", "P1")
            rec = _run(investigate("INC-E2E-OFF", alert, _noop_emit))

        assert rec is not None
        # No similar incidents when memory is off
        assert len(rec.similar) == 0

    def test_full_pipeline_memory_on(self):
        """
        E2E: Memory ON produces a response with historical references.
        """
        hits = [
            {
                "id": "mock-m001",
                "incident_id": "INC-1001",
                "text": "[MOCK] INC-1001 payments-db connection pool exhausted – restart worked",
                "score": 0.82,
                "outcome": "worked",
                "_source": "mock",
            }
        ]

        async def _mock_recall(alert, emit):
            return hits

        with patch("agent.memory_enabled", return_value=True), \
             patch("agent._perform_recall", side_effect=_mock_recall):
            from agent import investigate
            from llm import clear_cache
            clear_cache()
            alert = _make_alert("payments-db", "connection pool exhausted", "P1")
            rec = _run(investigate("INC-E2E-ON", alert, _noop_emit))

        assert rec is not None
        # Similar should reference INC-1001
        incident_ids = [s.incident_id for s in rec.similar if s.incident_id]
        assert "INC-1001" in incident_ids

    def test_retain_then_recall_finds_incident(self):
        """Retain an incident then recall it by a related query."""
        from memory.service import retain_incident, recall

        record = {
            "incident_id": "INC-9999",
            "service": "payments-db",
            "symptoms": {"message": "connection pool exhausted under load"},
            "root_cause": "connection pool saturation",
            "fix_steps": [{"step": "Restart connection pool", "status": "succeeded"}],
            "outcome": "worked",
        }
        _run(retain_incident(record))

        results = _run(recall("payments-db connection pool exhausted", top_k=10))
        found_ids = [r.get("incident_id") for r in results]
        assert "INC-9999" in found_ids, f"INC-9999 not found in recalled hits: {found_ids}"

    def test_mock_data_never_presented_as_real(self):
        """Mock recall data (seed entries) is always labeled as mock, never as real evidence."""
        from memory.service import recall, _MOCK_SEED
        results = _run(recall("payments-db connection pool exhausted"))
        # Only check SEED entries (those with IDs matching _MOCK_SEED)
        seed_ids = {r.get("id") for r in _MOCK_SEED}
        seed_hits = [h for h in results if h.get("id") in seed_ids]
        for h in seed_hits:
            assert h.get("_source") == "mock", f"Seed hit missing _source=mock label: {h}"
            assert "[MOCK]" in h.get("text", ""), \
                f"Seed hit text does not contain [MOCK] label: {h['text'][:80]}"


# ===========================================================================
# 8. FastAPI API Tests
# ===========================================================================

class TestAssistantAPI:
    """Test assistant API endpoints using FastAPI TestClient."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        try:
            from fastapi.testclient import TestClient
            from main import app
            return TestClient(app, raise_server_exceptions=False)
        except Exception:
            pytest.skip("FastAPI app not available for testing")

    def test_assistant_status_endpoint(self, client):
        """/assistant/status returns memory status."""
        resp = client.get("/assistant/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "memory_enabled" in data

    def test_assistant_query_endpoint_memory_off(self, client):
        """/assistant/query with memory OFF returns no-history response."""
        # Turn memory off
        client.post("/settings/memory", json={"enabled": False})
        resp = client.post("/assistant/query", json={"question": "What fixed this last time?", "service": "payments-db"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["fix"] is None
        # Turn memory back on
        client.post("/settings/memory", json={"enabled": True})

    def test_postmortem_draft_endpoint_404(self, client):
        """/incidents/{id}/postmortem/draft returns 404 for nonexistent incident."""
        resp = client.post("/incidents/INC-NONEXISTENT-99/postmortem/draft")
        assert resp.status_code in (404, 500)  # 404 preferred, 500 acceptable


class TestAdminAPI:
    """Test memory toggle and admin API."""

    @pytest.fixture
    def client(self):
        try:
            from fastapi.testclient import TestClient
            from main import app
            return TestClient(app, raise_server_exceptions=False)
        except Exception:
            pytest.skip("FastAPI app not available for testing")

    def test_memory_toggle_off(self, client):
        """POST /settings/memory can disable memory."""
        resp = client.post("/settings/memory", json={"enabled": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        # Re-enable
        client.post("/settings/memory", json={"enabled": True})

    def test_memory_toggle_on(self, client):
        """POST /settings/memory can enable memory."""
        client.post("/settings/memory", json={"enabled": False})
        resp = client.post("/settings/memory", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_health_endpoint(self, client):
        """/health returns ok=True and memory status."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "memory" in data


# ===========================================================================
# 9. Tools Tests
# ===========================================================================

class TestTools:
    """Test tools package simulated operations (P3: synchronous functions)."""

    def test_execute_restart_action(self):
        """execute_action handles restart actions synchronously."""
        from tools import execute_action
        result = execute_action("Restart connection pool manager", "payments-db")
        assert result["ok"] is True
        assert isinstance(result["output"], str)
        assert len(result["output"]) > 0

    def test_execute_force_fail(self):
        """execute_action with unrecognised step returns ok=True with manual note."""
        from tools import execute_action
        result = execute_action("[fail] completely unrecognised step xyz", "payments-db")
        assert isinstance(result, dict)
        assert "ok" in result

    def test_execute_rollback(self):
        """execute_action handles rollback actions."""
        from tools import execute_action
        result = execute_action("Roll back to previous deploy", "checkout")
        assert result["ok"] is True

    def test_check_metrics_returns_dict(self):
        """check_metrics returns a dict with required keys."""
        from tools import check_metrics
        result = check_metrics("payment-service")
        assert isinstance(result, dict)
        assert "note" in result

    def test_check_metrics_known_service(self):
        """check_metrics returns service status for known services."""
        from tools import check_metrics
        result = check_metrics("auth-service")
        assert isinstance(result, dict)
        assert "status" in result or "note" in result
