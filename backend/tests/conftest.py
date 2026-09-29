"""
conftest.py
-----------
Pytest configuration for P1 AI Memory Agent tests.

Sets up:
  - sys.path to include backend/
  - SQLite in-memory database for tests
  - LLM set to mock provider
  - Memory enabled by default (individual tests override as needed)
"""

import asyncio
import os
import sys

import pytest

# Ensure backend/ is always on the path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# tests/ is inside backend/, so backend = parent of tests/
BACKEND_DIR = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# Force test environment settings BEFORE any app imports
# ---------------------------------------------------------------------------

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_incidents.db")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("MEMORY_ENABLED", "true")
os.environ.setdefault("HINDSIGHT_URL", "http://localhost:9999")  # unreachable in tests
os.environ.setdefault("NOVEL_THRESHOLD", "0.25")


@pytest.fixture(scope="session")
def event_loop():
    """Provide a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True, scope="session")
def init_test_db():
    """Initialize an in-memory/test SQLite database."""
    try:
        from db.session import init_db
        init_db()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def reset_memory_state():
    """Reset memory enabled state to True before each test."""
    from settings import set_memory_enabled
    set_memory_enabled(True)
    yield
    set_memory_enabled(True)


@pytest.fixture(autouse=True)
def clear_llm_cache():
    """Clear LLM cache before each test for isolation."""
    try:
        from llm import clear_cache
        clear_cache()
    except Exception:
        pass
    yield
    try:
        from llm import clear_cache
        clear_cache()
    except Exception:
        pass
