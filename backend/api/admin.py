from fastapi import APIRouter
from pydantic import BaseModel

from core.bus import publish_global
from db import crud
from db.crud import as_utc
from settings import memory_enabled, set_memory_enabled

router = APIRouter(tags=["admin"])


class MemoryToggle(BaseModel):
    enabled: bool
    actor: str = "engineer"


@router.get("/settings/memory")
def get_memory():
    return {"enabled": memory_enabled()}


@router.post("/settings/memory")
def post_memory(body: MemoryToggle):
    set_memory_enabled(body.enabled)
    crud.add_audit(None, body.actor, "memory_toggle", {"enabled": body.enabled})
    publish_global("memory_toggle", {"type": "memory_toggle", "enabled": body.enabled})
    return {"enabled": memory_enabled()}


@router.post("/reset")
def reset():
    crud.reset_all()
    set_memory_enabled(True)
    publish_global("memory_toggle", {"type": "memory_toggle", "enabled": True})
    return {"ok": True}


@router.get("/audit")
def audit(incident_id: str | None = None, limit: int = 200):
    return [{"id": a.id, "incident_id": a.incident_id, "actor": a.actor, "action": a.action,
             "payload_json": a.payload_json, "ts": as_utc(a.ts)} for a in crud.list_audit(incident_id, limit)]
