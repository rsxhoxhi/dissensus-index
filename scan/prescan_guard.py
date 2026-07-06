#!/usr/bin/env python3
"""
prescan_guard.py — Pre-scan base check for the Dissensus Index daily scan.

WHY THIS EXISTS
The daily scan dedups new discoveries against data/cases.json and assigns the
next case ID from the highest existing entry number. If the scan runs on a
branch cut from a STALE base — a local main that is behind origin/main because a
prior day's scan PR has since merged — then:
  * dedup misses cases that are already merged, so the scan re-logs them, and
  * ID assignment restarts from an outdated high-water mark, so two runs hand the
    same ACI-2xx ID to different cases (an ID collision that only surfaces at
    merge time).
This actually happened across the 2026-07-04/05/06 runs. This guard makes the
failure loud and early instead of silent and downstream.

WHAT IT DOES
  1. Fetches origin/main (best effort; warns but continues on network failure).
  2. Reads the authoritative case store from origin/main:data/cases.json.
  3. Reports the true next parent ID and case count from origin/main.
  4. BLOCKS (exit 1) if the working tree is missing any case that already exists
     in origin/main — i.e. the scan base is stale and must be reset onto
     origin/main before any ID is assigned.

USAGE
    python scan/prescan_guard.py
Run it as the first action of Step 1 (pre-scan). Exit 0 = safe to proceed;
exit 1 = stale base, reset before drafting; exit 2 = could not read origin/main.
"""

import json
import re
import subprocess
import sys


def _sh(*args):
    return subprocess.run(args, capture_output=True, text=True)


def _max_entry_num(cases):
    n = 0
    for c in cases:
        m = re.match(r"0*(\d+)", str(c.get("entry_id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return n


def main():
    fetched = _sh("git", "fetch", "origin", "main")
    if fetched.returncode != 0:
        print("WARN: `git fetch origin main` failed:", fetched.stderr.strip())
        print("      Proceeding against the local origin/main ref, which may be stale.")

    show = _sh("git", "show", "origin/main:data/cases.json")
    if show.returncode != 0:
        print("FATAL: cannot read origin/main:data/cases.json —", show.stderr.strip())
        return 2

    remote = json.loads(show.stdout)
    rcases = remote["cases"]
    with open("data/cases.json", encoding="utf-8") as fh:
        lcases = json.load(fh)["cases"]

    rmax = _max_entry_num(rcases)
    print(f"origin/main : {len(rcases)} cases · highest entry #{rmax} "
          f"→ next new parent ID = ACI-{rmax + 1:03d}")
    print(f"working tree: {len(lcases)} cases · highest entry #{_max_entry_num(lcases)}")

    missing = {c["id"] for c in rcases} - {c["id"] for c in lcases}
    if missing:
        print(f"\nBLOCKED: the working tree is missing {len(missing)} case(s) that already "
              f"exist in origin/main:")
        for cid in sorted(missing)[:20]:
            print("   ", cid)
        if len(missing) > 20:
            print(f"    … and {len(missing) - 20} more")
        print("\nThe scan base is STALE. Deduping/assigning IDs from here will re-log "
              "already-merged cases with colliding IDs.")
        print("Reset onto origin/main before drafting anything:")
        print("    git checkout -B claude/daily-<YYYY-MM-DD> origin/main")
        return 1

    print("\nOK: working tree contains every origin/main case — safe to dedup and "
          "assign IDs from here.")
    print(f"Dedup against ALL {len(rcases)} origin/main entries (source URLs + titles), "
          "not just recent rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
