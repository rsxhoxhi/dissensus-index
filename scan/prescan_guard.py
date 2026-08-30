#!/usr/bin/env python3
"""
prescan_guard.py — Backlog-aware pre-scan base check for the Dissensus Index scan.

The number this guard prints is PROVISIONAL — a working label while a candidate
is in review. The permanent, contiguous ACI-NNN is assigned at merge, to the
survivors only, by scan/finalize_ids.py (so a dropped candidate never burns a
public number). This guard still does the essential job below: dedup and a
collision-free provisional number across the whole open backlog.

WHY THIS EXISTS
The daily scan dedups new discoveries against data/cases.json and assigns the
next case ID from the highest existing entry number. Two ways that goes wrong:

  1. STALE LOCAL BASE — the working tree is behind origin/main because a prior
     day's PR has since merged. Dedup misses merged cases; the ID counter
     restarts from an old high-water mark.

  2. UNMERGED BACKLOG — you're away for a few days and several daily-scan PRs sit
     OPEN, unmerged. Their new cases are not in origin/main, so a scan that only
     looks at main can't see them: it re-logs the same stories and hands the same
     ACI-2xx number to a different case. The collision only surfaces at merge time.

This guard defends against both. It builds the dedup/numbering base from the UNION
of origin/main AND every open scan branch (claude/daily-* and claude/scan-* whose
tip is not already merged into main), so IDs are reserved and stories are deduped
across the whole backlog — not just what has been merged.

WHAT IT DOES
  1. Fetches origin/main.
  2. Discovers claude/daily-* / claude/scan-* branches; skips any already merged
     into main (cheap ancestor check, no fetch); fetches the rest and unions their
     cases with main's.
  3. Prints the true next parent ID computed over that union, with a per-branch
     breakdown of pending cases.
  4. Writes the union to scan/backlog_cases.json — the dedup base for ingest.py and
     for manual dedup during the run.
  5. BLOCKS (exit 1) if the working tree is behind origin/main (stale local base).

USAGE
    python scan/prescan_guard.py
Exit 0 = safe to proceed (use the printed next ID and scan/backlog_cases.json for
dedup); exit 1 = stale base, reset onto origin/main first; exit 2 = could not read
origin/main.
"""

import json
import re
import subprocess
import sys

BACKLOG_GLOBS = ["claude/daily-*", "claude/scan-*"]
UNION_OUT = "scan/backlog_cases.json"


def _sh(*args):
    return subprocess.run(args, capture_output=True, text=True)


def _max_entry_num(cases):
    n = 0
    for c in cases:
        m = re.match(r"0*(\d+)", str(c.get("entry_id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return n


def _remote_scan_branches():
    """[(sha, branch_name), …] for every claude/daily-* / claude/scan-* on origin."""
    out = _sh("git", "ls-remote", "--heads", "origin", *BACKLOG_GLOBS)
    branches = []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[1].startswith("refs/heads/"):
            branches.append((parts[0], parts[1][len("refs/heads/"):]))
    return branches


def _is_merged(sha):
    """True if `sha` is already an ancestor of origin/main (branch is merged)."""
    # rc 0 = ancestor (merged); rc 1 = not ancestor; rc 128 = object not present
    # locally (never fetched → definitely not merged). Only rc 0 means merged.
    return _sh("git", "merge-base", "--is-ancestor", sha, "origin/main").returncode == 0


def _branch_cases(branch):
    if _sh("git", "fetch", "-q", "origin", branch).returncode != 0:
        return None
    show = _sh("git", "show", "FETCH_HEAD:data/cases.json")
    if show.returncode != 0:
        return None
    try:
        return json.loads(show.stdout)["cases"]
    except Exception:
        return None


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
    main_cases = remote["cases"]
    main_ids = {c["id"] for c in main_cases}

    # Union = main ∪ (every open, not-yet-merged scan branch), keyed by id so each
    # id is reserved exactly once and merged branches (all ids already in main)
    # contribute nothing.
    union = {c["id"]: c for c in main_cases}
    pending = []  # (branch, [new_ids])
    for sha, name in _remote_scan_branches():
        if _is_merged(sha):
            continue
        cases = _branch_cases(name)
        if cases is None:
            print(f"WARN: could not read data/cases.json from origin/{name}; skipping.")
            continue
        new_ids = [c["id"] for c in cases if c["id"] not in union]
        for c in cases:
            union.setdefault(c["id"], c)
        if new_ids:
            pending.append((name, new_ids))

    union_cases = list(union.values())
    rmax = _max_entry_num(main_cases)
    umax = _max_entry_num(union_cases)

    print(f"origin/main : {len(main_cases)} cases · highest entry #{rmax}")
    if pending:
        n_new = sum(len(ids) for _, ids in pending)
        print(f"open backlog: {n_new} pending case(s) across {len(pending)} unmerged "
              f"scan branch(es) not yet in main:")
        for name, ids in pending:
            shown = ", ".join(ids[:8]) + (" …" if len(ids) > 8 else "")
            print(f"    {name}: +{len(ids)}  ({shown})")
    else:
        print("open backlog: none — no unmerged scan branches carry new cases.")

    print(f"union       : {len(union_cases)} cases · highest entry #{umax} "
          f"→ next PROVISIONAL parent ID = ACI-{umax + 1:03d}")

    with open(UNION_OUT, "w", encoding="utf-8") as fh:
        json.dump(
            {"generated_from": f"origin/main + {len(pending)} open scan branch(es)",
             "total_cases": len(union_cases),
             "cases": union_cases},
            fh, ensure_ascii=False, indent=2,
        )
        fh.write("\n")
    print(f"dedup base  : wrote {UNION_OUT} ({len(union_cases)} cases) — dedup source "
          f"URLs and titles against THIS, not just data/cases.json.")

    # Stale-local-base block (defends against problem #1).
    with open("data/cases.json", encoding="utf-8") as fh:
        local_ids = {c["id"] for c in json.load(fh)["cases"]}
    missing = main_ids - local_ids
    if missing:
        print(f"\nBLOCKED: the working tree is missing {len(missing)} case(s) already in "
              f"origin/main:")
        for cid in sorted(missing)[:20]:
            print("   ", cid)
        if len(missing) > 20:
            print(f"    … and {len(missing) - 20} more")
        print("\nThe scan base is STALE. Reset onto origin/main before drafting:")
        print("    git checkout -B claude/daily-<YYYY-MM-DD> origin/main")
        return 1

    print(f"\nOK: base current with origin/main. Draft new entries from the PROVISIONAL "
          f"number ACI-{umax + 1:03d} (a working label only); dedup against {UNION_OUT}. "
          f"Permanent contiguous ACI numbers are assigned at merge by scan/finalize_ids.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
