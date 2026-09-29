import asyncio
import inspect
import logging

from schemas import Alert, Hypothesis, MemoryHit, Recommendation
from settings import memory_enabled

log = logging.getLogger("bridges")

try:
    from agent import investigate as _investigate
except Exception as e:
    log.warning("agent.investigate unavailable, using fallback: %s", e)
    _investigate = None

try:
    from memory.service import retain_incident as _retain_incident
except Exception as e:
    log.warning("memory.service.retain_incident unavailable, using fallback: %s", e)
    _retain_incident = None

try:
    from tools import execute_action as _execute_action
except Exception as e:
    log.warning("tools.execute_action unavailable, using fallback: %s", e)
    _execute_action = None

try:
    from tools import check_metrics as _check_metrics
except Exception as e:
    log.warning("tools.check_metrics unavailable, using fallback: %s", e)
    _check_metrics = None


async def _call(fn, *args):
    if inspect.iscoroutinefunction(fn):
        return await fn(*args)
    r = await asyncio.to_thread(fn, *args)
    if inspect.isawaitable(r):
        r = await r
    return r


async def _emit(emit, kind, step, detail):
    r = emit(kind, step, detail)
    if inspect.isawaitable(r):
        await r


async def _fake_investigate(incident_id: str, alert: Alert, emit) -> Recommendation:
    mem = memory_enabled()
    await _emit(emit, "agent", "gathering context", f"{alert.service}: {alert.message}")
    await asyncio.sleep(0.3)
    if mem:
        await _emit(emit, "memory", "recall", f"query={alert.message} -> 1 hit: INC-007 (worked, 0.82)")
        await asyncio.sleep(0.3)
    await _emit(emit, "agent", "reasoning", "ranking hypotheses (simulated)")
    await asyncio.sleep(0.3)
    steps = ["Check connection pool metrics", "Restart payments-db connection pool", "Roll back deploy abc123"]
    if "novel" in alert.message.lower():
        return Recommendation(
            hypotheses=[Hypothesis(cause="Unknown failure mode", confidence=0.25, evidence_ids=[])],
            steps=["Gather logs and metrics for the service", "Page the owning team"],
            runbook=None, avoid=[], whats_different="No similar incident found in memory",
            is_novel=True, similar=[], needs_approval=True,
        )
    if mem:
        return Recommendation(
            hypotheses=[Hypothesis(cause="DB connection pool exhaustion", confidence=0.78, evidence_ids=["INC-007"])],
            steps=steps, runbook=None, avoid=["Increasing pool size alone (failed in INC-012)"],
            whats_different="Error rate is higher than in INC-007; recent deploy abc123",
            is_novel=False,
            similar=[MemoryHit(id="m1", text="INC-007 pool exhaustion fixed by restart", incident_id="INC-007",
                               score=0.82, outcome="worked")],
            needs_approval=True,
        )
    return Recommendation(
        hypotheses=[Hypothesis(cause="DB connection pool exhaustion", confidence=0.4, evidence_ids=[])],
        steps=steps, runbook=None, avoid=[], whats_different="Memory disabled; generic analysis only",
        is_novel=False, similar=[], needs_approval=True,
    )


async def investigate(incident_id: str, alert: Alert, emit) -> Recommendation:
    if _investigate is None:
        return await _fake_investigate(incident_id, alert, emit)
    r = await _call(_investigate, incident_id, alert, emit)
    if isinstance(r, Recommendation):
        return r
    return Recommendation.model_validate(r if isinstance(r, dict) else r.model_dump())


async def retain_incident(incident: dict):
    if _retain_incident is None:
        return "skipped (no memory module)"
    return await _call(_retain_incident, incident)


async def execute_action(step: str, service: str) -> dict:
    if _execute_action is None:
        await asyncio.sleep(0.5)
        if "[fail]" in step:
            return {"ok": False, "output": "simulated failure"}
        return {"ok": True, "output": "done (simulated)"}
    r = await _call(_execute_action, step, service)
    if isinstance(r, dict):
        return {"ok": bool(r.get("ok", True)), "output": str(r.get("output", ""))}
    return {"ok": True, "output": str(r)}


async def check_metrics(service: str) -> dict:
    if _check_metrics is None:
        return {"healthy": True, "note": "within thresholds (simulated)"}
    r = await _call(_check_metrics, service)
    return r if isinstance(r, dict) else {"healthy": True, "note": str(r)}
