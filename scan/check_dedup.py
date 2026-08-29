#!/usr/bin/env python3
"""Content-dedup check — a soft review gate run before the daily PR opens.

WHY THIS EXISTS
The RSS dedup in ingest.py only matches an item's link against already-logged
`source` URLs (exact string, source field only). So the same story logged from
a different outlet, under a different article slug, or discovered via a homepage
or web search slips through and gets a second parent ID. (The Guggenheim v.
Picasso 'Femme dans un fauteuil' suit was minted four times — ACI-318/323/332/334
— before manual review caught it.)

This compares every entry ADDED on the current branch (anything not in
origin/main) against the full union (scan/backlog_cases.json — origin/main plus
open scan branches, written by prescan_guard.py) AND against the run's other new
entries, and flags likely duplicates so the scan consciously drops them or
refiles them as sub-entries instead of minting a redundant parent.

TWO SIGNALS, deliberately conservative to avoid false alarms on related cases:
  1. URL overlap   — a shared normalized link across source/additional_sources.
  2. Title+entity  — title-token Jaccard >= TITLE_JACCARD_MIN AND a shared
                     artist or institution.

Comparisons within the same parent cluster (shared ACI-NNN prefix) are skipped:
a sub-entry is MEANT to resemble its parent.

This is a REVIEW gate, not a hard block: it exits non-zero when it flags anything
so the run stops to look, but a flag the maintainer confirms is genuinely distinct
is resolved by noting it in the PR, never by deleting a real entry.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).parent.parent
CASES_PATH = REPO_ROOT / "data" / "cases.json"
BACKLOG_PATH = Path(__file__).parent / "backlog_cases.json"

TITLE_JACCARD_MIN = 0.45  # conservative: measured true-dup titles land 0.46-0.54, genuinely different same-entity pairs ~0.05

STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "as", "at",
    "by", "from", "with", "over", "after", "amid", "its", "it", "is", "are",
    "be", "that", "this", "new", "aci", "sues", "over",
}


def parent_prefix(cid):
    m = re.match(r"(ACI-\d+)", cid or "")
    return m.group(1) if m else (cid or "")


def norm_url(u):
    if not u:
        return None
    try:
        p = urlparse(u.strip())
        host = p.netloc.replace("www.", "").lower()
        path = p.path.rstrip("/").lower()
        return (host + path) if host else None
    except Exception:
        return None


def urls_of(c):
    out = set()
    for u in [c.get("source", "")] + list(c.get("additional_sources") or []):
        n = norm_url(u)
        if n:
            out.add(n)
    return out


def title_tokens(t):
    t = re.sub(r"^ACI-\d+[-A-Za-z]*:\s*", "", t or "")  # strip "ACI-054:" prefixes
    toks = re.findall(r"[a-z0-9]+", t.lower())
    return {w for w in toks if w not in STOPWORDS and len(w) > 2}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def norm_entity(s):
    s = (s or "").strip().lower()
    if not s or s.startswith("n/a") or s in {"unknown", "various", "multiple"}:
        return None
    # collapse "pablo picasso" / "picasso (attributed)" style noise a little
    s = re.sub(r"\(.*?\)", "", s).strip()
    return s or None


def precompute(c):
    return {
        "c": c,
        "pref": parent_prefix(c["id"]),
        "urls": urls_of(c),
        "tok": title_tokens(c.get("title", "")),
        "art": norm_entity(c.get("artist", "")),
        "inst": norm_entity(c.get("institution", "")),
    }


def main():
    union_path = BACKLOG_PATH if BACKLOG_PATH.exists() else CASES_PATH
    union = json.loads(union_path.read_text())["cases"]

    base_ids = set()
    try:
        base = subprocess.run(
            ["git", "show", "origin/main:data/cases.json"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout
        base_ids = {c["id"] for c in json.loads(base)["cases"]}
    except Exception as e:
        print(f"WARN: could not read origin/main ({e}); treating all cases as candidates.")

    cases = json.loads(CASES_PATH.read_text())["cases"]
    new_entries = [c for c in cases if c["id"] not in base_ids]
    if not new_entries:
        print("OK: no new entries on this branch to dedup-check.")
        sys.exit(0)

    # comparison pool = union + this run's new entries (so intra-run dups are caught too)
    pool = {c["id"]: c for c in union}
    for c in new_entries:
        pool.setdefault(c["id"], c)
    P = [precompute(c) for c in pool.values()]

    flags = []
    for n in new_entries:
        np = precompute(n)
        for cp in P:
            c = cp["c"]
            if c["id"] == n["id"]:
                continue
            if cp["pref"] == np["pref"]:
                continue  # same cluster: sub-entries are meant to resemble the parent
            reasons = []
            shared = np["urls"] & cp["urls"]
            if shared:
                reasons.append(f"shared URL ({sorted(shared)[0]})")
            j = jaccard(np["tok"], cp["tok"])
            same_art = np["art"] and np["art"] == cp["art"]
            same_inst = np["inst"] and np["inst"] == cp["inst"]
            if j >= TITLE_JACCARD_MIN and (same_art or same_inst):
                reasons.append(f"title {j:.2f} + same {'artist' if same_art else 'institution'}")
            if reasons:
                flags.append((n["id"], c["id"], reasons, n.get("title", ""), c.get("title", "")))

    if not flags:
        print(f"OK: {len(new_entries)} new entries checked — no likely duplicates.")
        sys.exit(0)

    print("REVIEW REQUIRED — likely duplicate(s). For each: drop it, refile as a")
    print("sub-entry of the existing case, or confirm it is genuinely distinct and")
    print("note that in the PR. (This gate skips same-cluster comparisons.)\n")
    seen = set()
    for nid, cid, reasons, nt, ct in flags:
        if (nid, cid) in seen:
            continue
        seen.add((nid, cid))
        print(f"  LIKELY DUP: {nid} ~ {cid} — {'; '.join(reasons)}")
        print(f"       new:      {nt[:90]}")
        print(f"       existing: {ct[:90]}")
    sys.exit(1)


if __name__ == "__main__":
    main()
