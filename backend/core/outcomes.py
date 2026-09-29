import asyncio
import json
import logging

from core import bridges
from core.bus import make_emitter
from core.intake import load_recommendation, spawn
from db import crud

log = logging.getLogger("outcomes")


def build_memory_record(incident_id: str, outcome: str, note: str | None = None) -> dict:
    inc = crud.get_incident(incident_id)
    rec = load_recommendation(inc)
    try:
        metrics = json.loads(inc.alert_json).get("metrics", {})
    except Exception:
        metrics = {}
    return {
        "incident_id": inc.id,
        "service": inc.service,
        "symptoms": {"message": inc.message, "metrics": metrics},
        "root_cause": inc.top_hypothesis,
        "fix_steps": [{"step": a.step, "status": a.status} for a in crud.list_actions(incident_id)],
        "resolution": inc.resolution,
        "runbook": rec.get("runbook"),
        "outcome": outcome,
        "lessons": [note] if note else [],
        "source": "live",
    }


async def _retain(incident_id: str, outcome: str, note: str | None) -> None:
    emit = make_emitter(incident_id)
    try:
        record = build_memory_record(incident_id, outcome, note)
        await emit("memory", "retain", f"{incident_id} outcome={outcome} -> sending")
        r = await asyncio.wait_for(bridges.retain_incident(record), timeout=20)
        await emit("memory", "retain", r if isinstance(r, str) and r else "stored")
    except Exception as e:
        await emit("memory", "retain", f"failed: {str(e)[:200] or type(e).__name__}")


def retain_outcome(incident_id: str, outcome: str, note: str | None = None):
    return spawn(_retain(incident_id, outcome, note))
