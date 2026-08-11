#!/usr/bin/env python3
"""Append a retrieval record to the current run's ledger. Called immediately
after each fetch or search-result retrieval, success or not — this is what lets
check_provenance.py verify an outlet was actually read before an entry cites it.

A "run" is one scan session and may legitimately span midnight UTC. The ledger
is therefore anchored to the date the run STARTED (``run_date``), not the live
wall clock, and records are only ever appended within a run. The ledger is reset
to start a NEW run only when:

  (a) --new-run is passed (explicit) — the deterministic mechanism; the daily
      routine calls this once at the start of the scan, and a fresh cloud
      container starts with no ledger at all, so both normal paths get a clean
      slate without relying on any heuristic;
  (b) no ledger exists yet; or
  (c) as a safety net for ad-hoc reuse of a container, the existing ledger is
      stale — its last activity was more than NEW_RUN_GAP_HOURS ago.

A rolled-over calendar date is NOT by itself a reason to reset. That was the old
behaviour, and it silently wiped the earlier half of any scan that crossed
midnight UTC — the exact records the provenance gate then needed.
"""
import json
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

LEDGER_PATH = Path(__file__).parent / "retrieval_log.json"

# Safety net only — the routine's explicit --new-run at scan start is the real
# run boundary. Chosen larger than any single continuous scan (a thorough run
# plus same-session quick-adds can span many hours) so a run never resets
# itself, while still catching a ledger left behind by a clearly earlier run in
# a reused container.
NEW_RUN_GAP_HOURS = 20


def _load_current_run(now):
    """Return the existing ledger if it belongs to the current run, else None
    (meaning: start a fresh ledger)."""
    if not LEDGER_PATH.exists():
        return None
    try:
        ledger = json.loads(LEDGER_PATH.read_text())
    except (ValueError, OSError):
        return None

    last = ledger.get("last_updated")
    if last:
        try:
            if (now - datetime.fromisoformat(last)) > timedelta(hours=NEW_RUN_GAP_HOURS):
                return None  # stale → previous run, start fresh
        except ValueError:
            pass  # unparseable timestamp → treat as same run, append
    return ledger


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--outlet", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--method", required=True, choices=["fetch", "search_result", "api"])
    p.add_argument("--status", required=True,
                   choices=["success", "truncated", "snippet_only", "blocked"])
    p.add_argument("--new-run", action="store_true",
                   help="Force a fresh ledger, ending any prior run.")
    args = p.parse_args()

    now = datetime.now()
    today = date.today().isoformat()

    ledger = None if args.new_run else _load_current_run(now)
    if ledger is None:
        ledger = {"run_date": today, "started_at": now.isoformat(), "retrievals": []}

    # Anchor stays put across midnight; only last_updated advances.
    ledger.setdefault("run_date", today)
    ledger.setdefault("started_at", now.isoformat())
    ledger["last_updated"] = now.isoformat()
    ledger.setdefault("retrievals", []).append({
        "outlet": args.outlet,
        "url": args.url,
        "method": args.method,
        "status": args.status,
    })

    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))
    print(f"Logged: {args.outlet} ({args.status})")


if __name__ == "__main__":
    main()
