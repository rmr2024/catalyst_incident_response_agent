from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from core.intake import ingest_alert
from schemas import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])

SEV_MAP = {"critical": "P1", "warning": "P2", "info": "P3", "p1": "P1", "p2": "P2", "p3": "P3"}
DEMO = {"service": "payments-db", "message": "connection pool exhausted, requests timing out",
        "metrics": {"error_rate": 0.12, "latency_p99_ms": 3400, "affected_users": 4200}}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sev(v) -> str | None:
    return SEV_MAP.get(str(v).strip().lower()) if v else None


def _first(d: dict, *keys):
    for k in keys:
        if d.get(k):
            return d[k]
    return None


def _to_alert(d: dict) -> Alert:
    d = dict(d)
    d.setdefault("timestamp", _now())
    if not d.get("timestamp"):
        d["timestamp"] = _now()
    try:
        return Alert.model_validate(d)
    except ValidationError as e:
        raise HTTPException(422, e.errors(include_url=False, include_context=False))


def _from_alertmanager(a: dict) -> Alert:
    labels, ann = a.get("labels") or {}, a.get("annotations") or {}
    return _to_alert({
        "service": _first(labels, "service", "job", "app") or "unknown",
        "message": _first(ann, "summary", "description") or labels.get("alertname") or "alert",
        "severity": _sev(labels.get("severity")),
        "metrics": {k: v for k, v in {**labels, **ann}.items() if isinstance(v, (int, float)) and not isinstance(v, bool)},
        "timestamp": a.get("startsAt") or _now(),
    })


def _from_generic(d: dict) -> Alert:
    skip = {"service", "app", "job", "message", "summary", "description", "title", "severity", "timestamp", "metrics"}
    metrics = d.get("metrics") if isinstance(d.get("metrics"), dict) else {
        k: v for k, v in d.items() if k not in skip and isinstance(v, (int, float)) and not isinstance(v, bool)}
    return _to_alert({
        "service": _first(d, "service", "app", "job") or "unknown",
        "message": _first(d, "message", "summary", "description", "title") or "alert",
        "severity": _sev(d.get("severity")),
        "metrics": metrics,
        "timestamp": _first(d, "timestamp", "startsAt", "time") or _now(),
    })


@router.post("")
async def post_alert(body: dict = Body(...)):
    return await ingest_alert(_to_alert(body), source="manual")


@router.post("/webhook")
async def webhook(body: Any = Body(...)):
    if isinstance(body, dict) and isinstance(body.get("alerts"), list):
        alerts = [_from_alertmanager(a) for a in body["alerts"] if isinstance(a, dict)]
    elif isinstance(body, list):
        alerts = [_from_generic(a) for a in body if isinstance(a, dict)]
    elif isinstance(body, dict):
        alerts = [_from_generic(body)]
    else:
        raise HTTPException(422, "unsupported payload")
    return [await ingest_alert(a, source="webhook") for a in alerts]


@router.post("/demo")
async def demo():
    return await ingest_alert(_to_alert(DEMO), source="demo")
