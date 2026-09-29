"""
api/assistant.py
----------------
Conversational assistant API endpoints.

POST /assistant/query
  – answer a natural-language question about incident history

GET  /assistant/what-fixed/{service}
  – "What fixed this last time?" for a specific service

GET  /assistant/seen-before
  – "Have we seen this before?" for a given service + message

GET  /assistant/avoid/{service}
  – "What should we avoid?" for a service
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from settings import memory_enabled

router = APIRouter(prefix="/assistant", tags=["assistant"])


class QueryIn(BaseModel):
    question: str
    service: str | None = None
    incident_id: str | None = None


@router.post("/query")
async def assistant_query(body: QueryIn):
    """
    Answer a natural-language question using historical incident memory.

    When memory is OFF, returns a clear message that history is unavailable.
    When memory is ON, recalls relevant incidents and answers based on evidence.
    """
    try:
        from assistant import answer_query
        return await answer_query(
            question=body.question,
            service=body.service,
            incident_id=body.incident_id,
        )
    except Exception as e:
        return {
            "answer": f"Assistant error: {str(e)[:200]}",
            "incident_id": None,
            "fix": None,
            "runbook": None,
            "confidence": 0.0,
            "evidence": [],
            "caveat": str(e)[:200],
        }


@router.get("/what-fixed/{service}")
async def what_fixed_last_time(service: str):
    """What fixed this last time for the given service?"""
    try:
        from assistant import what_fixed_last_time as _wf
        return await _wf(service)
    except Exception as e:
        return {
            "answer": f"Error: {str(e)[:200]}",
            "incident_id": None,
            "fix": None,
            "runbook": None,
            "confidence": 0.0,
            "evidence": [],
            "caveat": str(e)[:200],
        }


@router.get("/seen-before")
async def seen_before(
    service: str = Query(..., description="Service name"),
    message: str = Query(..., description="Issue description"),
):
    """Have we seen a similar incident before?"""
    try:
        from assistant import have_we_seen_this
        return await have_we_seen_this(service, message)
    except Exception as e:
        return {
            "answer": f"Error: {str(e)[:200]}",
            "incident_id": None,
            "fix": None,
            "runbook": None,
            "confidence": 0.0,
            "evidence": [],
            "caveat": str(e)[:200],
        }


@router.get("/avoid/{service}")
async def what_to_avoid(service: str):
    """What actions should we avoid for this service based on past failures?"""
    try:
        from assistant import what_to_avoid as _wta
        return await _wta(service)
    except Exception as e:
        return {
            "answer": f"Error: {str(e)[:200]}",
            "incident_id": None,
            "fix": None,
            "runbook": None,
            "confidence": 0.0,
            "evidence": [],
            "caveat": str(e)[:200],
        }


@router.get("/status")
def assistant_status():
    """Check assistant and memory status."""
    from llm import get_provider_info
    return {
        "memory_enabled": memory_enabled(),
        "llm": get_provider_info(),
    }
