#!/usr/bin/env python3
"""Provenance gate: every outlet named in a new entry's `source` URL or
`outlets` array must have a status=success record in today's retrieval
ledger. Fails the run (non-zero exit) if not.

Does NOT verify that the entry's claims are actually supported by the
retrieved body — that's a semantic-fidelity check this script cannot do.
It only proves the outlet was successfully retrieved at all.
"""
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).parent.parent
CASES_PATH = REPO_ROOT / "data" / "cases.json"
LEDGER_PATH = Path(__file__).parent / "retrieval_log.json"

# Domain -> outlet name, for translating `source` URLs into the same
# outlet names used in `outlets`. Add new domains here as new outlets
# start showing up in the data.
DOMAIN_TO_OUTLET = {
    "artnews.com": "ARTnews",
    "hyperallergic.com": "Hyperallergic",
    "theartnewspaper.com": "The Art Newspaper",
    "nytimes.com": "New York Times",
    "washingtonpost.com": "Washington Post",
    "theguardian.com": "The Guardian",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
}

def outlet_from_url(url):
    domain = urlparse(url).netloc.replace("www.", "")
    return DOMAIN_TO_OUTLET.get(domain)

def main():
    today = date.today().isoformat()

    if not LEDGER_PATH.exists():
        print("FAIL: no retrieval_log.json found for this run.")
        sys.exit(1)

    ledger = json.loads(LEDGER_PATH.read_text())
    if ledger.get("run_date") != today:
        print(f"FAIL: ledger run_date ({ledger.get('run_date')}) does not match today ({today}).")
        sys.exit(1)

    retrieved_ok = {
        r["outlet"] for r in ledger["retrievals"] if r["status"] == "success"
    }

    cases = json.loads(CASES_PATH.read_text())["cases"]
    todays_entries = [
        c for c in cases
        if today in c.get("date_discovered", "")
    ]

    failures = []
    for entry in todays_entries:
        named_outlets = set(entry.get("outlets", []))

        source_url = entry.get("source", "")
        source_outlet = outlet_from_url(source_url) if source_url else None
        if source_outlet:
            named_outlets.add(source_outlet)
        elif source_url:
            failures.append((entry["id"], {f"[unrecognized domain in source: {source_url}]"}))

        unretrieved = named_outlets - retrieved_ok
        if unretrieved:
            failures.append((entry["id"], unretrieved))

    if failures:
        print("FAIL: entries cite outlets with no successful retrieval this run:")
        for entry_id, outlets in failures:
            print(f"  {entry_id}: {', '.join(outlets)}")
        sys.exit(1)

    print(f"OK: {len(todays_entries)} entries checked, all cited outlets retrieved successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
