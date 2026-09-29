import logging

from core import bridges
from core.bus import make_emitter, publish, set_status
from db import crud

log = logging.getLogger("execution")


async def execute_plan(incident_id: str) -> None:
    emit = make_emitter(incident_id)
    try:
        inc = set_status(incident_id, "executing")
        actions = crud.list_actions(incident_id)
        for n, a in enumerate(actions):
            publish(incident_id, "action", crud.to_action_out(crud.update_action(a.id, status="running")))
            try:
                r = await bridges.execute_action(a.step, inc.service)
            except Exception as e:
                r = {"ok": False, "output": f"error: {e}"}
            row = crud.update_action(a.id, status="succeeded" if r["ok"] else "failed", output=r["output"])
            await emit("agent", f"step {n + 1} {'ok' if r['ok'] else 'failed'}", f"{a.step}: {r['output']}")
            publish(incident_id, "action", crud.to_action_out(row))
            if not r["ok"]:
                for rest in actions[n + 1:]:
                    publish(incident_id, "action", crud.to_action_out(crud.update_action(rest.id, status="skipped")))
                set_status(incident_id, "fix_failed")
                await emit("agent", "fix failed", f"stopped at step {n + 1}; remaining steps skipped")
                return
        m = await bridges.check_metrics(inc.service)
        await emit("agent", "verification", str(m.get("note") or m))
        set_status(incident_id, "mitigated")
    except Exception as e:
        log.exception("execution failed for %s", incident_id)
        try:
            set_status(incident_id, "fix_failed")
            await emit("agent", "error", str(e)[:200] or type(e).__name__)
            crud.add_audit(incident_id, "system", "execution_failed", {"error": str(e)[:500]})
        except Exception:
            pass
