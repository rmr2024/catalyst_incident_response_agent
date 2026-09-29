#!/usr/bin/env python3
"""
Seed historical incidents into Hindsight long-term memory.

Usage:
  python scripts/seed_memory.py [--no-reset] [--dry-run] [--only INC-104] [--force]

Flags:
  --no-reset   Skip the Hindsight reset step (default: reset before seeding).
  --dry-run    Validate and list incidents without writing to memory.
  --only ID    Seed only the specified incident ID (can be repeated).
  --force      Re-seed incidents already recorded in the state file.
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import pathlib
import sys

# ---------------------------------------------------------------------------
# Path setup — must happen before any backend imports
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

DATA_FILE  = REPO_ROOT / "data" / "seed_incidents.json"
STATE_FILE = REPO_ROOT / "scripts" / ".seed_state.json"

REQUIRED_KEYS = {
    "incident_id", "title", "service", "severity", "occurred_at", "ttr_min",
    "symptoms", "root_cause", "fix_steps", "resolution", "runbook", "outcome",
    "lessons", "source",
}


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------

def _load_state() -> set[str]:
    """Return the set of already-seeded incident IDs."""
    try:
        with open(STATE_FILE, encoding="utf-8") as fh:
            return set(json.load(fh).get("seeded", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _save_state(seeded: set[str]) -> None:
    """Persist the set of seeded incident IDs."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump({"seeded": sorted(seeded)}, fh, indent=2)


def _clear_state() -> None:
    """Remove the state file."""
    try:
        STATE_FILE.unlink()
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Incident loading and validation
# ---------------------------------------------------------------------------

def _load_incidents() -> list[dict]:
    with open(DATA_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def _validate(inc: dict) -> list[str]:
    """Return a list of validation error strings for *inc* (empty = valid)."""
    errors: list[str] = []
    missing = REQUIRED_KEYS - set(inc.keys())
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")
    inc_id = inc.get("incident_id", "")
    if inc_id:
        try:
            num = int(inc_id.replace("INC-", ""))
            if num >= 1001:
                errors.append(f"ID {inc_id} must be below INC-1001")
        except ValueError:
            errors.append(f"ID {inc_id} is not in INC-NNN format")
    allowed = {"worked", "failed", "partial"}
    if inc.get("outcome") not in allowed:
        errors.append(f"outcome '{inc.get('outcome')}' not in {allowed}")
    for step in inc.get("fix_steps", []):
        if step.get("status") not in allowed:
            errors.append(f"fix_step status '{step.get('status')}' not in {allowed}")
    return errors


# ---------------------------------------------------------------------------
# Memory import helpers
# ---------------------------------------------------------------------------

def _try_import_memory():
    """Return (retain_fn, reset_fn) or raise ImportError with a clear message."""
    try:
        import memory.service as mem_svc  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            f"P1's memory service is not ready yet (import failed: {exc}). "
            "Run with --dry-run to validate data without seeding."
        ) from exc
    retain = getattr(mem_svc, "retain_incident", None)
    if retain is None:
        raise ImportError(
            "memory.service does not expose 'retain_incident'. "
            "REQUEST TO P1: add async def retain_incident(record: dict) -> None to memory/service.py"
        )
    # Look for reset function
    reset_fn = None
    for name in ("reset_memory", "reset", "reset_bank", "clear_memory"):
        fn = getattr(mem_svc, name, None)
        if fn is not None:
            reset_fn = fn
            break
    return retain, reset_fn


def _to_memory_record(inc: dict) -> dict:
    """Convert a seed incident to the memory record shape."""
    return {
        "incident_id":  inc["incident_id"],
        "service":      inc["service"],
        "symptoms":     inc.get("symptoms", {}),
        "root_cause":   inc.get("root_cause", ""),
        "fix_steps":    inc.get("fix_steps", []),
        "resolution":   inc.get("resolution", ""),
        "runbook":      inc.get("runbook", ""),
        "outcome":      inc.get("outcome", "worked"),
        "lessons":      inc.get("lessons", []),
        "source":       inc.get("source", "seed"),
        # extra useful fields
        "title":        inc.get("title", ""),
        "severity":     inc.get("severity", ""),
        "occurred_at":  inc.get("occurred_at", ""),
        "error_signature": inc.get("error_signature", ""),
        "tags":         inc.get("tags", []),
    }


# ---------------------------------------------------------------------------
# Async retain helper (handles both sync and async retain_incident)
# ---------------------------------------------------------------------------

async def _retain_async(retain_fn, record: dict) -> None:
    result = retain_fn(record)
    if inspect.isawaitable(result):
        await result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-reset", action="store_true", help="Skip Hindsight reset before seeding")
    parser.add_argument("--dry-run",  action="store_true", help="Validate without writing to memory")
    parser.add_argument("--only",     action="append",     metavar="ID", help="Seed only these IDs")
    parser.add_argument("--force",    action="store_true", help="Re-seed even if already in state file")
    args = parser.parse_args()

    # Load and validate incidents
    try:
        incidents = _load_incidents()
    except FileNotFoundError:
        print(f"ERROR: {DATA_FILE} not found. Run T1 first.", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: {DATA_FILE} is invalid JSON: {exc}", file=sys.stderr)
        return 1

    # Apply --only filter
    if args.only:
        only_set = set(args.only)
        incidents = [i for i in incidents if i.get("incident_id") in only_set]
        not_found = only_set - {i["incident_id"] for i in incidents}
        if not_found:
            print(f"WARNING: IDs not found in seed file: {sorted(not_found)}")

    # Validate all
    all_valid = True
    for inc in incidents:
        errs = _validate(inc)
        if errs:
            print(f"INVALID {inc.get('incident_id', '?')}: {errs}")
            all_valid = False
    if not all_valid:
        print("ERROR: fix validation errors above before seeding.", file=sys.stderr)
        return 1

    total = len(incidents)
    print(f"Loaded {total} incidents from {DATA_FILE}")

    if args.dry_run:
        print("DRY-RUN: validation passed. The following incidents would be seeded:")
        for i, inc in enumerate(incidents, 1):
            print(f"  would seed {inc['incident_id']} ({i}/{total})")
        print("DRY-RUN complete. No data written.")
        return 0

    # Import memory service
    try:
        retain_fn, reset_fn = _try_import_memory()
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Determine whether to reset
    did_reset = False
    if not args.no_reset:
        if reset_fn is not None:
            print("Resetting Hindsight memory bank...")
            result = reset_fn()
            if inspect.isawaitable(result):
                asyncio.run(result)
            _clear_state()
            did_reset = True
            print("Hindsight reset complete.")
        else:
            print(
                "REQUEST TO P1: expose async def reset_memory() -> None in memory/service.py"
            )
            print("Continuing WITHOUT a reset; relying on state file to skip already-seeded IDs.")

    # Load seeded state
    already_seeded = _load_state()
    seeded_ids: set[str] = set(already_seeded) if not did_reset else set()

    # Seed incidents
    failed_ids: list[str] = []

    async def seed_all() -> None:
        for i, inc in enumerate(incidents, 1):
            inc_id = inc["incident_id"]
            if inc_id in seeded_ids and not args.force and not did_reset:
                print(f"skipping {inc_id} (already seeded; use --force to re-seed)")
                continue
            record = _to_memory_record(inc)
            try:
                await _retain_async(retain_fn, record)
                seeded_ids.add(inc_id)
                print(f"retained {inc_id} ({i}/{total})")
            except Exception as exc:
                print(f"FAILED  {inc_id}: {exc}", file=sys.stderr)
                failed_ids.append(inc_id)

    asyncio.run(seed_all())
    _save_state(seeded_ids)

    if failed_ids:
        print(f"ERROR: {len(failed_ids)} incidents failed to seed: {failed_ids}", file=sys.stderr)
        return 1

    print(f"Done. {len(seeded_ids)} incidents in memory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
