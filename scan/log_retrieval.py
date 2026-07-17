#!/usr/bin/env python3
"""Append a retrieval record to today's ledger. Called immediately after
each fetch or search-result retrieval, success or not — this is what lets
check_provenance.py verify an outlet was actually read before an entry
cites it."""
import json
import argparse
from datetime import date
from pathlib import Path

LEDGER_PATH = Path(__file__).parent / "retrieval_log.json"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--outlet", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--method", required=True, choices=["fetch", "search_result"])
    p.add_argument("--status", required=True,
                   choices=["success", "truncated", "snippet_only", "blocked"])
    args = p.parse_args()

    today = date.today().isoformat()

    if LEDGER_PATH.exists():
        ledger = json.loads(LEDGER_PATH.read_text())
        if ledger.get("run_date") != today:
            ledger = {"run_date": today, "retrievals": []}
    else:
        ledger = {"run_date": today, "retrievals": []}

    ledger["retrievals"].append({
        "outlet": args.outlet,
        "url": args.url,
        "method": args.method,
        "status": args.status,
    })

    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))
    print(f"Logged: {args.outlet} ({args.status})")

if __name__ == "__main__":
    main()
