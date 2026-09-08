#!/usr/bin/env python3
"""
Dissensus Index — public dist/ builder.

Reads the full internal master (data/cases.json), strips the fields that
must stay master-only (CLAUDE.md SS2: "Parent ID, Interested Parties,
Coverage Geography, and Notes stay in the master even if not surfaced
publicly" -- plus governance_type/themes/seq/sort_date/follow_up_pending,
confirmed unused by the public frontend), and assembles dist/ as an
allowlisted copy of the public site. Nothing not named in COPY_FILES ever
reaches dist/ -- scan/, CLAUDE.md, notes/, README.md, etc. are excluded by
omission, not by exclusion rule.

dist/ is disposable: removed and rebuilt from scratch on every run.
data/cases.json (the master) is read-only here and is never modified.

Usage: python3 scan/build_public.py
"""
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_PATH = REPO_ROOT / "data" / "cases.json"
DIST = REPO_ROOT / "dist"

# Allowlist: only these paths (relative to repo root) are copied into dist/.
COPY_FILES = [
    "about.html",
    "browse.html",
    "case.html",
    "cite.html",
    "essay-hungary.html",
    "essay-pattern.html",
    "index.html",
    "methodology.html",
    "css/style.css",
]

# Fields that never leave the master.
STRIP_FIELDS = {
    "notes",
    "governance_type",
    "themes",
    "seq",
    "sort_date",
    "follow_up_pending",
    "coverage_geography",
    "interested_parties",
}

# Every other field currently in the schema. Fixed list (not "whatever's
# left") so a field added to the master later and forgotten here fails
# loudly instead of silently leaking into dist/.
KEEP_FIELDS = {
    "id",
    "entry_id",
    "title",
    "artist",
    "institution",
    "country",
    "date_controversy",
    "date_discovered",
    "description",
    "outcome",
    "tags",
    "court_case",
    "coverage_tier",
    "outlets",
    "source",
    "additional_sources",
}


def load_master():
    if not MASTER_PATH.exists():
        sys.exit(f"FATAL: master not found at {MASTER_PATH}")
    raw = MASTER_PATH.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"FATAL: {MASTER_PATH} did not parse as JSON: {e}")
    if set(data.keys()) != {"meta", "cases"}:
        sys.exit(f"FATAL: expected top-level keys {{meta, cases}}, got {sorted(data.keys())}")
    if not isinstance(data["cases"], list):
        sys.exit("FATAL: data['cases'] is not a list")
    return data


def strip_case(case):
    return {k: v for k, v in case.items() if k not in STRIP_FIELDS}


def build_public_cases(master):
    """Strip + validate. Raises AssertionError (before anything is written
    or dist/ is touched) if any guard fails."""
    cases_in = master["cases"]


    cases_out = [strip_case(c) for c in cases_in]

    for i, (c_in, c_out) in enumerate(zip(cases_in, cases_out)):
        cid = c_in.get("id", f"index {i}")

        # schema drift guard: every input field must be accounted for by
        # exactly one of STRIP_FIELDS / KEEP_FIELDS
        unknown = set(c_in.keys()) - STRIP_FIELDS - KEEP_FIELDS
        assert not unknown, (
            f"case {cid}: field(s) not in STRIP_FIELDS or KEEP_FIELDS: {unknown} "
            f"-- update build_public.py before proceeding"
        )

        # no stripped field leaked through
        leaked = STRIP_FIELDS & set(c_out.keys())
        assert not leaked, f"case {cid}: stripped field(s) leaked into output: {leaked}"

        # every kept field that existed in the master survives unchanged
        for k in KEEP_FIELDS:
            if k in c_in:
                assert k in c_out and c_out[k] == c_in[k], (
                    f"case {cid}: kept field {k!r} lost or altered in output"
                )

    assert len(cases_out) == len(cases_in), (
        f"case count mismatch: {len(cases_in)} in, {len(cases_out)} out"
    )
    assert master["meta"].get("total_cases") == len(cases_in), (
        f"meta.total_cases ({master['meta'].get('total_cases')}) != "
        f"actual case count ({len(cases_in)})"
    )

    meta_out = dict(master["meta"])

    return {"meta": meta_out, "cases": cases_out}


def print_field_inventory(master, public):
    before = set()
    for c in master["cases"]:
        before |= set(c.keys())
    after = set()
    for c in public["cases"]:
        after |= set(c.keys())
    print("\nField inventory")
    print("  before (master):", ", ".join(sorted(before)))
    print("  after  (public):", ", ".join(sorted(after)))
    print("  stripped:       ", ", ".join(sorted(before - after)))


def rebuild_dist_skeleton():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)


def copy_allowlisted_files():
    for rel in COPY_FILES:
        src = REPO_ROOT / rel
        if not src.is_file():
            sys.exit(f"FATAL: allowlisted source file missing: {rel}")
        dst = DIST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  copied  {rel}")


def main():
    print(f"Reading master: {MASTER_PATH}")
    master = load_master()
    print(f"  {len(master['cases'])} cases, meta.total_cases={master['meta'].get('total_cases')}")

    # Strip + validate BEFORE touching dist/, so a failed guard leaves
    # dist/ (and the master) exactly as they were.
    public = build_public_cases(master)
    print_field_inventory(master, public)

    print(f"\nRebuilding {DIST}/ (allowlist-only)")
    rebuild_dist_skeleton()
    copy_allowlisted_files()

    dist_data_dir = DIST / "data"
    dist_data_dir.mkdir(parents=True, exist_ok=True)
    out_path = dist_data_dir / "cases.json"
    out_path.write_text(
        json.dumps(public, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote   data/cases.json ({len(public['cases'])} cases)")

    print(f"\nOK: dist/ built. Master at {MASTER_PATH} untouched.")


if __name__ == "__main__":
    main()
