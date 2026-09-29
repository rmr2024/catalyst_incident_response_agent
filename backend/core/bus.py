import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

from pydantic import BaseModel

from db import crud
from schemas import AgentEvent

log = logging.getLogger("bus")

_subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
_global: set[asyncio.Queue] = set()
KINDS = {"agent", "memory", "human"}


def _data(data) -> str:
    if isinstance(data, BaseModel):
        return data.model_dump_json()
    if isinstance(data, str):
        return data
    return json.dumps(data, default=str)


def subscribe(incident_id: str | None = None) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    (_subs[incident_id] if incident_id else _global).add(q)
    return q


def unsubscribe(q: asyncio.Queue, incident_id: str | None = None) -> None:
    if incident_id:
        _subs.get(incident_id, set()).discard(q)
        if incident_id in _subs and not _subs[incident_id]:
            del _subs[incident_id]
    else:
        _global.discard(q)


def _put(qs, event: str, data) -> None:
    msg = {"event": event, "data": _data(data)}
    for q in list(qs):
        try:
            q.put_nowait(msg)
        except Exception:
            pass


def publish(incident_id: str, event: str, data) -> None:
    _put(_subs.get(incident_id, ()), event, data)


def publish_global(event: str, data) -> None:
    _put(_global, event, data)


def set_status(incident_id: str, status: str):
    inc = crud.update_incident(incident_id, status=status)
    publish(incident_id, "status", {"status": status})
    publish_global("status", {"incident_id": incident_id, "status": status})
    return inc


def _build_event(incident_id: str, args, kw) -> AgentEvent:
    if args and isinstance(args[0], AgentEvent):
        d = args[0].model_dump()
    elif args and isinstance(args[0], dict):
        d = dict(args[0])
    elif isinstance(kw.get("event"), (AgentEvent, dict)):
        e = kw["event"]
        d = e.model_dump() if isinstance(e, AgentEvent) else dict(e)
    else:
        d = dict(zip(("kind", "step", "detail"), args))
        d.update({k: v for k, v in kw.items() if k in ("kind", "step", "detail", "ts", "incident_id")})
    d.setdefault("incident_id", incident_id)
    d["incident_id"] = d.get("incident_id") or incident_id
    kind = str(d.get("kind") or "agent").lower()
    d["kind"] = kind if kind in KINDS else "agent"
    d["step"] = str(d.get("step") or "")
    det = d.get("detail", "")
    d["detail"] = det if isinstance(det, str) else json.dumps(det, default=str)
    if not d.get("ts"):
        d["ts"] = datetime.now(timezone.utc)
    return AgentEvent.model_validate(d)


async def _emit(incident_id: str, *args, **kw) -> None:
    try:
        ev = _build_event(incident_id, args, kw)
        crud.add_event(ev)
        publish(ev.incident_id, "agent_event", ev)
    except Exception as e:
        log.warning("emit failed: %s", e)


def make_emitter(incident_id: str):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    def emit(*args, **kw):
        coro = _emit(incident_id, *args, **kw)
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None:
            return running.create_task(coro)
        if loop is not None and loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop)
        asyncio.run(coro)
        return _done()

    return emit


def _done():
    class _Done:
        def __await__(self):
            if False:
                yield
            return None
    return _Done()
