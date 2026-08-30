#!/usr/bin/env python3
"""
finalize_ids.py — assign permanent ACI numbers at approval (merge) time.

WHY THIS EXISTS
The daily scan hands each new candidate a *provisional* parent number when it is
first drafted (see prescan_guard.py). Some candidates are then dropped in review —
duplicates, non-controversies — and a scan-time number that is never published
leaves a permanent hole in the public sequence (…356, 357, [gone], 359…).

The fix: do not burn a public number on a candidate that might not survive. A
provisional number is only a working label. The permanent ACI-NNN is assigned
HERE, once an entry has cleared review and is about to become public — to the
survivors only, contiguously, above the highest number already published in
origin/main. Dropped candidates never consume a number, so no new gaps form.

Existing historical gaps (numbers burned before this policy) are NOT touched:
those numbers are permanent identifiers behind live URLs and citations
(case.html?id=ACI-NNN) and must never move.

WHAT IT DOES
Run this on a reviewed PR branch that has already been rebuilt onto current
origin/main, just before merge:

  1. Reads origin/main and finds the highest published parent number M.
  2. Finds this branch's NEW parents (bare ACI-NNN not in main) and, in their
     current draft-number order, renumbers them ACI-(M+1), ACI-(M+2), … —
     updating `id` and `entry_id`.
  3. Renumbers any NEW sub-entries whose parent is one of those renumbered
     parents (ACI-357-A → ACI-361-A), keeping the suffix letter.
  4. Rewrites every cross-reference to a renumbered id (in title, description,
     outcome, notes, interested_parties, coverage_geography) — word-boundary
     safe, single pass, so ACI-35 is never mistaken for ACI-357.
  5. Leaves `seq` (display order), published entries, and sub-entries of
     already-published parents untouched.

It is idempotent: run twice and the second run is a no-op (the new parents are
already contiguous above M). Prints the remap so the change is auditable, and
writes data/cases.json in place.

USAGE
    python scan/finalize_ids.py            # apply
    python scan/finalize_ids.py --check    # report what WOULD change, write nothing
Exit 0 = done (or nothing to do); exit 1 = could not read origin/main; with
--check, exit 3 = changes are pending (for a pre-merge guard).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

CASES_PATH = Path(__file__).parent.parent / "data" / "cases.json"
TEXT_FIELDS = ("title", "description", "outcome", "notes",
               "interested_parties", "coverage_geography")
PARENT_RE = re.compile(r"^ACI-(\d+)$")
# A reference to any case id inside free text: ACI-357 or ACI-357-A (zero-pad tolerant).
REF_RE = re.compile(r"ACI-0*(\d+)(-[A-Z]+)?")


def _sh(*args):
    return subprocess.run(args, capture_output=True, text=True)


def _main_parent_max():
    """Highest bare-parent number published in origin/main."""
    _sh("git", "fetch", "origin", "main")
    show = _sh("git", "show", "origin/main:data/cases.json")
    if show.returncode != 0:
        return None, None
    main_cases = json.loads(show.stdout)["cases"]
    main_ids = {c["id"] for c in main_cases}
    hi = 0
    for c in main_cases:
        m = PARENT_RE.match(c["id"])
        if m:
            hi = max(hi, int(m.group(1)))
    return hi, main_ids


def build_remap(cases, main_max, main_ids):
    """{old_num:int -> new_num:int} for this branch's new parents, contiguous above main_max."""
    new_parents = []
    for c in cases:
        m = PARENT_RE.match(c["id"])
        if m and c["id"] not in main_ids:
            new_parents.append(int(m.group(1)))
    new_parents.sort()  # preserve draft order (draft numbers ascend with discovery)
    remap = {}
    nxt = main_max + 1
    for old in new_parents:
        if old != nxt:
            remap[old] = nxt
        nxt += 1
    return remap


def _reref(text, remap):
    """Rewrite any ACI-id reference whose number is remapped; leave the rest verbatim."""
    def sub(m):
        num = int(m.group(1))
        suffix = m.group(2) or ""
        if num in remap:
            return f"ACI-{remap[num]:03d}{suffix}"
        return m.group(0)
    return REF_RE.sub(sub, text)


def apply_remap(cases, remap, main_ids):
    """Mutate `cases` in place. Returns the number of entries whose id changed."""
    id_changes = 0
    for c in cases:
        is_new = c["id"] not in main_ids  # decided before we mutate the id
        # 1. renumber a new entry's own id/entry_id if its parent number is remapped.
        m = re.match(r"^ACI-(\d+)(-[A-Z]+)?$", c["id"])
        if is_new and m:
            num = int(m.group(1))
            suffix = m.group(2) or ""
            if num in remap:
                new = remap[num]
                c["id"] = f"ACI-{new:03d}{suffix}"
                c["entry_id"] = f"{new:03d}{suffix}"
                id_changes += 1
        # 2. rewrite cross-references in free text. Only new entries can reference a
        #    just-assigned number; published entries never do, so leave them untouched.
        if is_new:
            for f in TEXT_FIELDS:
                if isinstance(c.get(f), str) and "ACI-" in c[f]:
                    c[f] = _reref(c[f], remap)
    return id_changes


def main():
    check = "--check" in sys.argv
    main_max, main_ids = _main_parent_max()
    if main_max is None:
        print("FATAL: cannot read origin/main:data/cases.json")
        return 1

    data = json.loads(CASES_PATH.read_text())
    cases = data["cases"]
    remap = build_remap(cases, main_max, main_ids)

    if not remap:
        print(f"OK: nothing to finalize — new parents already contiguous above "
              f"ACI-{main_max:03d} (or none present).")
        return 0

    print(f"highest published parent in origin/main: ACI-{main_max:03d}")
    print("provisional -> final:")
    for old in sorted(remap):
        print(f"    ACI-{old:03d} -> ACI-{remap[old]:03d}")

    if check:
        print("\n--check: no files written. Pending finalization above.")
        return 3

    changed = apply_remap(cases, remap, main_ids)
    CASES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"\nApplied: {changed} entr(y/ies) renumbered; cross-references rewritten. "
          f"Wrote {CASES_PATH.relative_to(CASES_PATH.parent.parent)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
