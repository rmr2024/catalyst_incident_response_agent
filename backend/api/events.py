import asyncio

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from core import bus
from db import crud

router = APIRouter(tags=["events"])


async def _drain(request: Request, q: asyncio.Queue):
    while not await request.is_disconnected():
        try:
            yield await asyncio.wait_for(q.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue


@router.get("/incidents/{incident_id}/events")
async def incident_events(incident_id: str, request: Request):
    inc = crud.get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "incident not found")

    async def gen():
        q = bus.subscribe(incident_id)
        try:
            for ev in crud.list_events(incident_id):
                yield {"event": "agent_event", "data": ev.model_dump_json()}
            cur = crud.get_incident(incident_id)
            yield {"event": "status", "data": bus._data({"status": cur.status})}
            if cur.smart_alert_json:
                yield {"event": "smart_alert", "data": cur.smart_alert_json}
            async for msg in _drain(request, q):
                yield msg
        finally:
            bus.unsubscribe(q, incident_id)

    return EventSourceResponse(gen(), ping=15)


@router.get("/events/stream")
async def global_stream(request: Request):
    async def gen():
        q = bus.subscribe()
        try:
            async for msg in _drain(request, q):
                yield msg
        finally:
            bus.unsubscribe(q)

    return EventSourceResponse(gen(), ping=15)
