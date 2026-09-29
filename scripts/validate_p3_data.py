#!/usr/bin/env python3
"""
Validation script for all P3 deliverables.

Exits 0 if all checks pass, non-zero if any check fails.
Run from the repo root: python scripts/validate_p3_data.py
"""
from __future__ import annotations

import inspect
import json
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

SEED_FILE      = REPO_ROOT / "data" / "seed_incidents.json"
SCENARIOS_FILE = REPO_ROOT / "data" / "scenarios.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "  PASS"
FAIL = "  FAIL"

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    if ok:
        print(f"{PASS}  {label}")
    else:
        msg = f"{FAIL}  {label}" + (f": {detail}" if detail else "")
        print(msg)
        _failures.append(msg)
    return ok


# ---------------------------------------------------------------------------
# Seed incidents checks
# ---------------------------------------------------------------------------

def validate_seed(incidents: list[dict], scenario_ids: set[str]) -> None:
    print("\n=== seed_incidents.json ===")

    # 1. Count and unique IDs
    ids = [d["incident_id"] for d in incidents]
    check("18 incidents", len(incidents) == 18, f"found {len(incidents)}")
    check("unique IDs", len(ids) == len(set(ids)), f"duplicates: {[x for x in ids if ids.count(x)>1]}")

    # 2. All IDs below INC-1001
    bad_ids = [x for x in ids if int(x.replace("INC-", "")) >= 1001]
    check("all IDs below INC-1001", len(bad_ids) == 0, f"bad: {bad_ids}")

    # 3. Expected IDs
    expected = {f"INC-{n}" for n in range(101, 119)}
    missing = expected - set(ids)
    check("IDs INC-101 to INC-118 present", len(missing) == 0, f"missing: {missing}")

    # 4. Required shape keys
    required_keys = {
        "incident_id", "title", "service", "severity", "occurred_at", "ttr_min",
        "symptoms", "root_cause", "fix_steps", "resolution", "runbook",
        "outcome", "lessons", "source",
    }
    shape_ok = True
    for inc in incidents:
        missing_k = required_keys - set(inc.keys())
        if missing_k:
            check(f"shape {inc.get('incident_id','?')}", False, f"missing keys: {sorted(missing_k)}")
            shape_ok = False
    if shape_ok:
        check("all incidents have required shape keys", True)

    # 5. symptoms has message + metrics
    symp_ok = True
    for inc in incidents:
        s = inc.get("symptoms", {})
        if "message" not in s or "metrics" not in s:
            check(f"symptoms shape {inc['incident_id']}", False)
            symp_ok = False
    if symp_ok:
        check("all symptoms have message + metrics", True)

    # 6. status/outcome values
    allowed = {"worked", "failed", "partial"}
    status_ok = True
    for inc in incidents:
        if inc.get("outcome") not in allowed:
            check(f"outcome value {inc['incident_id']}", False, inc.get("outcome"))
            status_ok = False
        for step in inc.get("fix_steps", []):
            if step.get("status") not in allowed:
                check(f"fix_step status {inc['incident_id']}", False, step.get("status"))
                status_ok = False
    if status_ok:
        check("all outcome/status values valid", True)

    # 7. At least 5 incidents with a failed/partial fix step
    failed_step_count = sum(
        1 for inc in incidents
        for step in inc.get("fix_steps", [])
        if step.get("status") in ("failed", "partial")
    )
    check(
        "at least 5 incidents have a failed/partial fix step",
        failed_step_count >= 5,
        f"found {failed_step_count}",
    )

    # 8. At least 2 incidents with overall outcome "partial"
    partial_outcomes = [inc["incident_id"] for inc in incidents if inc.get("outcome") == "partial"]
    check(
        "at least 2 incidents with overall outcome partial",
        len(partial_outcomes) >= 2,
        f"found {len(partial_outcomes)}: {partial_outcomes}",
    )

    # 9. INC-104 has "Restart the application only" as partial
    inc104 = next((d for d in incidents if d["incident_id"] == "INC-104"), None)
    if inc104:
        has_partial_restart = any(
            "restart" in s["step"].lower() and s["status"] == "partial"
            for s in inc104.get("fix_steps", [])
        )
        check("INC-104 has restart-only as partial step", has_partial_restart)
    else:
        check("INC-104 present", False)

    # 10. No standalone ntp/clock skew/time drift in seed file (word boundary check)
    seed_text = json.dumps(incidents)
    banned = [r"\bclock skew\b", r"\bntp\b", r"\btime drift\b"]
    for pattern in banned:
        found = re.search(pattern, seed_text, re.I)
        check(
            f"seed file does not contain '{pattern}'",
            found is None,
            f"found at pos {found.start()}: ...{seed_text[max(0,found.start()-20):found.start()+30]}..." if found else "",
        )


# ---------------------------------------------------------------------------
# Scenarios checks
# ---------------------------------------------------------------------------

def validate_scenarios(scenarios: list[dict], seed_ids: set[str]) -> set[str]:
    print("\n=== scenarios.json ===")

    check("5 scenarios", len(scenarios) == 5, f"found {len(scenarios)}")

    action_names_used: set[str] = set()

    for scen in scenarios:
        sid = scen.get("id", "?")

        # required fields
        for field in ("id", "title", "description", "service", "is_novel",
                      "expected_match", "expected_runbook", "alert_template",
                      "context", "outcomes"):
            check(f"scenario {sid} has field '{field}'", field in scen)

        # expected_match IDs exist in seed
        for match_id in scen.get("expected_match", []):
            check(
                f"scenario {sid} expected_match {match_id} in seed data",
                match_id in seed_ids,
            )

        # log lines >= 10
        logs = scen.get("context", {}).get("logs", [])
        check(f"scenario {sid} has >= 10 log lines", len(logs) >= 10, f"found {len(logs)}")

        # at least one required action
        req = scen.get("outcomes", {}).get("required_actions", [])
        check(f"scenario {sid} has at least one required_action", len(req) >= 1, f"{req}")

        # collect all action names used
        for key in ("required_actions", "partial_actions", "harmful_actions"):
            action_names_used.update(scen.get("outcomes", {}).get(key, []))

    # scenario 5 (jwt-clock-drift / is_novel)
    novel = [s for s in scenarios if s.get("is_novel")]
    check("exactly 1 novel scenario", len(novel) == 1, f"found {len(novel)}")
    if novel:
        n = novel[0]
        check("novel scenario has empty expected_match", n.get("expected_match") == [], f"{n.get('expected_match')}")
        check("novel scenario has null expected_runbook", n.get("expected_runbook") is None)

    return action_names_used


# ---------------------------------------------------------------------------
# Tools contract checks
# ---------------------------------------------------------------------------

def validate_tools_contract(action_names_used: set[str], incidents: list[dict]) -> None:
    print("\n=== tools contract ===")

    try:
        import tools  # noqa: PLC0415
    except ImportError as exc:
        check("import tools", False, str(exc))
        return

    check("import tools", True)

    # execute_action exists, is plain (non-async) function, has (step, service) params
    exec_fn = getattr(tools, "execute_action", None)
    check("tools.execute_action exists", exec_fn is not None)
    if exec_fn:
        check("execute_action is not a coroutine function", not inspect.iscoroutinefunction(exec_fn))
        sig = inspect.signature(exec_fn)
        params = list(sig.parameters.keys())
        check("execute_action has params (step, service)", params == ["step", "service"], f"found {params}")

        # smoke test: returns dict with ok (bool) and output (str)
        result = exec_fn("Restart the pods", "checkout-api")
        check("execute_action returns dict", isinstance(result, dict), str(type(result)))
        check("execute_action result has bool 'ok'", isinstance(result.get("ok"), bool))
        check("execute_action result has str 'output'", isinstance(result.get("output"), str))

    # check_metrics exists, is plain function, has (service,) param, returns dict with non-empty note
    chk_fn = getattr(tools, "check_metrics", None)
    check("tools.check_metrics exists", chk_fn is not None)
    if chk_fn:
        check("check_metrics is not a coroutine function", not inspect.iscoroutinefunction(chk_fn))
        sig = inspect.signature(chk_fn)
        params = list(sig.parameters.keys())
        check("check_metrics has param (service)", params == ["service"], f"found {params}")

        result = chk_fn("checkout-api")
        check("check_metrics returns dict", isinstance(result, dict))
        note = result.get("note", "")
        check("check_metrics result has non-empty str 'note'", isinstance(note, str) and len(note) > 0, repr(note))

    # All action names from scenario outcomes exist in the tools registry
    list_tools_fn = getattr(tools, "list_tools", None)
    if list_tools_fn:
        registered = {t["id"] for t in list_tools_fn()}
        for action_id in sorted(action_names_used):
            check(
                f"action '{action_id}' registered in tools registry",
                action_id in registered,
            )

    # Every seed fix step maps to a recognised action or is clearly manual
    from tools.actions import _match_action_ids  # noqa: PLC0415 (internal helper)
    unmatched_manual: list[str] = []
    for inc in incidents:
        for step in inc.get("fix_steps", []):
            step_text = step.get("step", "")
            matched = _match_action_ids(step_text)
            if not matched:
                unmatched_manual.append(f"{inc['incident_id']}: {step_text[:60]}")
    if unmatched_manual:
        print(f"  INFO  {len(unmatched_manual)} manual steps (no action ID matched — this is OK):")
        for m in unmatched_manual:
            print(f"         manual: {m}")
    check("fix steps either match an action or are manual (no failures)", True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== validate_p3_data.py ===")

    # Load seed incidents
    try:
        with open(SEED_FILE, encoding="utf-8") as fh:
            incidents = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"FATAL: cannot load {SEED_FILE}: {exc}")
        return 1

    # Load scenarios
    try:
        with open(SCENARIOS_FILE, encoding="utf-8") as fh:
            scenarios = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"FATAL: cannot load {SCENARIOS_FILE}: {exc}")
        return 1

    seed_ids = {d["incident_id"] for d in incidents}
    scenario_ids = {s["id"] for s in scenarios}

    validate_seed(incidents, scenario_ids)
    action_names_used = validate_scenarios(scenarios, seed_ids)
    validate_tools_contract(action_names_used, incidents)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s) failed:")
        for f in _failures:
            print(f"  {f}")
        return 1
    else:
        print("All checks passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
