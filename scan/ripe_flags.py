#!/usr/bin/env python3
"""Ripe follow-up flags — the daily work list for the follow-up sweep.

WHY THIS EXISTS
Over 500 entries carry `follow_up_pending: true`, so "check the plausibly ripe
ones" (DAILY_SCAN_ROUTINE.md Step 2.4) was a judgement call made from memory,
and dated flags went stale unnoticed. On 2026-09-28 the routine itself was still
telling the scan to "watch the September NCPC final vote" on the triumphal arch
weeks after the arch thread had moved the target to November (ACI-038-R). A
trial count that day found about 35 flags whose every named date had passed.
It also found flags left on intermediate sub-entries after later ones
superseded them (e.g. the Wyland ACI-093-G..J run).

This lists flagged entries in four groups:
  A. DATED & PAST   every date named in the [FOLLOW-UP PENDING: ...] text is
                    before today. Ripe by definition: the scheduled thing
                    has happened (or didn't), so reconcile it.
  B. SUPERSEDED     a flagged sub-entry whose parent cluster has a LATER
                    sub-entry. The thread moved on; the flag is probably stale.
                    Verify against the later sibling, then clear or keep.
  C. UNNAMED        follow_up_pending is true but no named
                    "[FOLLOW-UP PENDING: ...]" text says what is pending
                    (CLAUDE.md sec 2, consistency rule 1).
  D. ORPHANED TEXT  "[FOLLOW-UP PENDING...]" text on an entry whose flag is
                    false (consistency rule 2: clear both together).

Date parsing is heuristic: "30 September 2026", "September 30, 2026",
"September 2026", ISO "2026-09-30". A month with no day counts as the END of
that month (an event "in November" is not past until November is over). A
date with no year takes the year the entry was logged. A flag whose text names
no date at all is not in group A; phrases like "in the coming weeks" are
invisible to this script, and the Sunday full sweep still covers them.

DEFAULT OUTPUT is the daily list: groups A and D in full, and B and C as counts
only (on 2026-09-28 B held 183 entries and C held 164, mostly legacy bare
"[FOLLOW-UP PENDING]" prefixes from the older notes-prefix convention; that is
real cleanup debt, but too long to work through every day). The Sunday full sweep
runs with --all.

ADVISORY ONLY: it prints a work list and always exits 0. Nothing is cleared
automatically; resolving a flag still means a sub-entry or an outcome update
per the routine.

Usage:
  python scan/ripe_flags.py                 # daily list (A + D in full; B, C counted)
  python scan/ripe_flags.py --all           # Sunday: every group in full
  python scan/ripe_flags.py --json          # machine-readable
  python scan/ripe_flags.py --today 2026-10-15   # evaluate as of another date
"""
import argparse
import calendar
import json
import re
import signal
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CASES_PATH = REPO_ROOT / "data" / "cases.json"

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS["sept"] = 9
MONTH_RE = r"(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"

FLAG_TEXT_RE = re.compile(r"\[FOLLOW-UP PENDING([^\]]*)\]", re.I)
DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+" + MONTH_RE + r"(?:,?\s+(20\d\d))?\b", re.I)
MONTH_DAY_YEAR = re.compile(r"\b" + MONTH_RE + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(20\d\d))?", re.I)
MONTH_YEAR = re.compile(r"\b" + MONTH_RE + r"\s+(20\d\d)\b", re.I)
ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")


def logged_year(c):
    m = re.search(r"(20\d\d)", str(c.get("date_discovered") or c.get("sort_date") or ""))
    return int(m.group(1)) if m else date.today().year


def safe_date(y, mo, d):
    try:
        return date(y, mo, min(d, calendar.monthrange(y, mo)[1]))
    except (ValueError, TypeError):
        return None


def named_dates(text, default_year):
    """All dates named in `text`. Month-only mentions resolve to month end."""
    found, spans = [], []

    def taken(m):
        return any(m.start() < e and s < m.end() for s, e in spans)

    for m in ISO.finditer(text):
        d = safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            found.append(d)
            spans.append(m.span())
    for rx, order in ((DAY_MONTH_YEAR, "dmy"), (MONTH_DAY_YEAR, "mdy")):
        for m in rx.finditer(text):
            if taken(m):
                continue
            if order == "dmy":
                day, mon, yr = m.group(1), m.group(2), m.group(3)
            else:
                mon, day, yr = m.group(1), m.group(2), m.group(3)
            d = safe_date(int(yr) if yr else default_year, MONTHS[mon.lower().rstrip(".")], int(day))
            if d:
                found.append(d)
                spans.append(m.span())
    for m in MONTH_YEAR.finditer(text):
        if taken(m):
            continue
        y, mo = int(m.group(2)), MONTHS[m.group(1).lower().rstrip(".")]
        found.append(safe_date(y, mo, calendar.monthrange(y, mo)[1]))
        spans.append(m.span())
    return [d for d in found if d]


def flag_texts(c):
    blob = f"{c.get('notes') or ''} {c.get('outcome') or ''}"
    return [m.group(0) for m in FLAG_TEXT_RE.finditer(blob)]


def named_flag_texts(c):
    """Flag texts that actually name the pending thing ('[FOLLOW-UP PENDING: ...]')."""
    return [t for t in flag_texts(c) if re.match(r"\[FOLLOW-UP PENDING\s*[:\-—–]\s*\S", t, re.I)]


def split_id(cid):
    """'ACI-093-G' -> ('ACI-093', 'G'); 'ACI-093' -> ('ACI-093', '')."""
    m = re.match(r"^(ACI-\d+)(?:-([A-Z]+))?$", cid)
    return (m.group(1), m.group(2) or "") if m else (cid, "")


def suffix_key(s):
    return (len(s), s)  # A < B < ... < Z < AA < AB


def classify(cases, today):
    latest_suffix = {}
    for c in cases:
        parent, suf = split_id(c["id"])
        if suf and suffix_key(suf) > suffix_key(latest_suffix.get(parent, "")):
            latest_suffix[parent] = suf

    groups = {"A": [], "B": [], "C": [], "D": []}
    for c in cases:
        flagged = bool(c.get("follow_up_pending"))
        texts = flag_texts(c)
        if not flagged:
            if texts:
                groups["D"].append({"id": c["id"], "title": c.get("title", ""), "text": texts[0][:160]})
            continue
        named = named_flag_texts(c)
        if not named:
            groups["C"].append({"id": c["id"], "title": c.get("title", "")})
        dates = [d for t in named for d in named_dates(t, logged_year(c))]
        if dates and max(dates) < today:
            groups["A"].append({"id": c["id"], "title": c.get("title", ""), "latest_named_date": max(dates).isoformat(),
                                "text": named[-1][:200]})
        parent, suf = split_id(c["id"])
        if suf and suffix_key(latest_suffix[parent]) > suffix_key(suf):
            groups["B"].append({"id": c["id"], "title": c.get("title", ""), "later": f"{parent}-{latest_suffix[parent]}"})
    groups["A"].sort(key=lambda r: r["latest_named_date"])
    return groups


LABELS = {
    "A": "DATED & PAST: every named date has passed; reconcile",
    "B": "SUPERSEDED: a later sub-entry exists; verify, then clear or keep",
    "C": "UNNAMED: flagged, but no '[FOLLOW-UP PENDING: ...]' names the pending thing",
    "D": "ORPHANED TEXT: pending text on an entry whose flag is false",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--today", help="evaluate as of YYYY-MM-DD (default: today)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--all", action="store_true", help="list groups B and C in full too (Sunday sweep)")
    ap.add_argument("--file", default=str(CASES_PATH), help="cases.json to read")
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()

    cases = json.loads(Path(args.file).read_text())["cases"]
    groups = classify(cases, today)
    flagged = sum(1 for c in cases if c.get("follow_up_pending"))

    if args.json:
        print(json.dumps({"today": today.isoformat(), "flagged": flagged, "groups": groups}, indent=1))
        return

    shown = "ABCD" if args.all else "AD"
    print(f"Ripe follow-up flags as of {today.isoformat()}: {flagged} entries flagged. "
          f"A={len(groups['A'])} B={len(groups['B'])} C={len(groups['C'])} D={len(groups['D'])}"
          + ("" if args.all else "  (B and C counted only; --all lists them)"))
    for g in "ABCD":
        rows = groups[g]
        print(f"\n{g}. {LABELS[g]} ({len(rows)})")
        if g not in shown:
            print("  (counted only; run with --all)")
            continue
        for r in rows:
            if g == "A":
                print(f"  {r['id']:<12} {r['latest_named_date']}  {r['title'][:70]}")
                print(f"  {'':<12} {r['text'][:150]}")
            elif g == "B":
                print(f"  {r['id']:<12} later: {r['later']:<12} {r['title'][:60]}")
            else:
                print(f"  {r['id']:<12} {r['title'][:80]}")
    print("\nAdvisory only. Resolve per DAILY_SCAN_ROUTINE.md Step 2.4 "
          "(sub-entry or outcome update, then clear flag + text together).")


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet exit when piped to head
    sys.exit(main())
