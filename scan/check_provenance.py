#!/usr/bin/env python3
"""Provenance gate, two rules:

Rule 1 (reach): every outlet a new entry cites — in `outlets`, `source`,
or `additional_sources` — must have a non-blocked record in today's
retrieval ledger (success, truncated, or snippet_only all prove the
outlet was actually consulted; metadata-grade thin entries are
sanctioned by CLAUDE.md).

Rule 2 (depth): if an entry's description or outcome contains quotation
marks, at least one cited outlet must have a full status=success record
— quotes cannot come from metadata or truncated fetches.

Does NOT verify semantic fidelity: with multiple cited outlets it cannot
tell which outlet a quote came from, and it never checks that claims
match the retrieved body. That residue belongs to human review.
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).parent.parent
CASES_PATH = REPO_ROOT / "data" / "cases.json"
LEDGER_PATH = Path(__file__).parent / "retrieval_log.json"

DOMAIN_TO_OUTLET = {
    "artnews.com": "ARTnews",
    "artforum.com": "Artforum",
    "hyperallergic.com": "Hyperallergic",
    "theartnewspaper.com": "The Art Newspaper",
    "sanfernandosun.com": "San Fernando Valley Sun",
    "middleeasteye.net": "Middle East Eye",
    "nytimes.com": "New York Times",
    "washingtonpost.com": "Washington Post",
    "theguardian.com": "The Guardian",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
    "npr.org": "NPR",
    "kclu.org": "NPR",
    "wtvr.com": "WTVR",
    "wtop.com": "WTOP",
    "ansa.it": "ANSA",
    "ilfattoquotidiano.it": "Il Fatto Quotidiano",
    "lanazione.it": "La Nazione",
    "jurist.org": "JURIST",
    "euronews.com": "Euronews",
    "france24.com": "France 24",
    "cnn.com": "CNN",
    "courtlistener.com": "CourtListener",
    "storage.courtlistener.com": "CourtListener",
    "archdaily.com": "ArchDaily",
    "dezeen.com": "Dezeen",
    "artreview.com": "ArtReview",
    "parametric-architecture.com": "Parametric Architecture",
    "oc-media.org": "OC Media",
    "archpaper.com": "The Architect's Newspaper",
    "newrepublic.com": "The New Republic",
    "mediarelations.gwu.edu": "George Washington University",
    "news.stv.tv": "STV News",
    "artsprofessional.co.uk": "Arts Professional",
    "upi.com": "UPI",
    "bworldonline.com": "BusinessWorld",
    "koreaherald.com": "The Korea Herald",
    "scmp.com": "South China Morning Post",
    "english.news.cn": "Xinhua",
    "khan.co.kr": "Kyunghyang Shinmun",
    "thehill.com": "The Hill",
    "abcnews.com": "ABC News",
    "pcs.org.uk": "PCS Union",
    "manilatimes.net": "The Manila Times",
    "cbsnews.com": "CBS News",
    "nortes.me": "Nortes",
    "eltiempo.com": "El Tiempo",
    "infobae.com": "Infobae",
    "elpais.com.co": "El País (Cali)",
    "thelocal.fr": "The Local",
    "aljazeera.com": "Al Jazeera",
    "newschannel5.com": "NewsChannel5",
    "usnews.com": "U.S. News & World Report",
    "fox17.com": "Fox 17 Nashville",
    "syriacpress.com": "SyriacPress",
    "timesofisrael.com": "The Times of Israel",
    "museumsassociation.org": "Museums Association",
    "euromaidanpress.com": "Euromaidan Press",
    "variety.com": "Variety",
    "notus.org": "NOTUS",
    "prospect.org.uk": "Prospect",
    "newsweek.com": "Newsweek",
    "theglobeandmail.com": "The Globe and Mail",
    "cbc.ca": "CBC News",
    "tribune.com.pk": "The Express Tribune",
    "thehansindia.com": "The Hans India",
    "rte.ie": "RTÉ",
    "hollywoodreporter.com": "The Hollywood Reporter",
    "washingtonian.com": "Washingtonian",
    "intent.press": "Intent",
    "thecollegefix.com": "The College Fix",
    "freepressjournal.in": "The Free Press Journal",
    "news.artnet.com": "Artnet News",
    "irishnews.com": "The Irish News",
    "unesco.org": "UNESCO",
    "allafrica.com": "allAfrica",
    "cardinalnews.org": "Cardinal News",
    "blockclubchicago.org": "Block Club Chicago",
    "wvtf.org": "WVTF",
    "gofundme.com": "GoFundMe (Devins fundraiser)",
    "wgntv.com": "WGN-TV",
    "sana.sy": "SANA",
    "syriahr.com": "Syrian Observatory for Human Rights",
    "momaa.org": "MOMAA",
}

ALIASES = {
    "nyt": "new york times",
    "wapo": "washington post",
    "ap": "associated press",
    "tan": "art newspaper",
}

QUOTE_RE = re.compile(r'["""]')

def norm(name):
    """Normalize an outlet name for matching: lowercase, strip leading
    'the ', strip parentheticals, apply aliases."""
    n = re.sub(r"\(.*?\)", "", str(name)).strip().lower()
    n = re.sub(r"^the\s+", "", n)
    return ALIASES.get(n, n)

def outlet_from_url(url):
    domain = urlparse(url).netloc.replace("www.", "")
    return DOMAIN_TO_OUTLET.get(domain)

def main():
    today = date.today().isoformat()

    if not LEDGER_PATH.exists():
        print("FAIL: no retrieval_log.json found for this run.")
        sys.exit(1)

    ledger = json.loads(LEDGER_PATH.read_text())
    # A run is anchored to the date it STARTED (run_date); a scan may legitimately
    # span midnight UTC, so validate against that anchor, not the live wall clock.
    # A mismatch is normal (and only informational), not a failure.
    run_date = ledger.get("run_date") or today
    if run_date != today:
        print(f"NOTE: ledger run_date ({run_date}) != today ({today}); "
              f"validating this run's entries (normal for a scan that crossed midnight UTC).")

    reached = {norm(r["outlet"]) for r in ledger["retrievals"] if r["status"] != "blocked"}
    full    = {norm(r["outlet"]) for r in ledger["retrievals"] if r["status"] == "success"}

    cases = json.loads(CASES_PATH.read_text())["cases"]

    # The gate validates entries authored by THIS run. Entries already merged
    # to origin/main were gated on their own run; exclude them so a quick-add
    # from an earlier session that happens to share this run's date_discovered is
    # not re-litigated against a ledger it was never part of. If origin/main
    # can't be read, fall back to checking every entry dated in this run's window.
    base_ids = set()
    try:
        base_json = subprocess.run(
            ["git", "show", "origin/main:data/cases.json"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout
        base_ids = {c["id"] for c in json.loads(base_json)["cases"]}
    except Exception as e:
        print(f"WARN: could not read origin/main:data/cases.json ({e}); checking all entries in the run window.")

    # Scope to entries stamped with the run's anchor date OR today — a scan that
    # crosses midnight UTC may stamp entries with either, and run_date always
    # covers the pre-midnight half, so this is immune to the wall-clock rollover.
    scope_dates = {run_date, today}
    todays_entries = [
        c for c in cases
        if any(d in c.get("date_discovered", "") for d in scope_dates)
        and c.get("id") not in base_ids
    ]

    failures = []
    for entry in todays_entries:
        cited = {norm(o) for o in entry.get("outlets", []) if str(o).strip()}
        urls = [entry.get("source", "")] + list(entry.get("additional_sources", []))
        for u in urls:
            if not u:
                continue
            o = outlet_from_url(u)
            if o:
                cited.add(norm(o))
            else:
                failures.append((entry["id"], f"unrecognized domain in URL: {u} — add it to DOMAIN_TO_OUTLET"))

        # Rule 1: reach
        unreached = cited - reached
        if unreached:
            failures.append((entry["id"], f"cited but never retrieved this run: {', '.join(sorted(unreached))}"))

        # Rule 2: depth
        text = f"{entry.get('description','')} {entry.get('outcome','')}"
        if QUOTE_RE.search(text) and cited and not (cited & full):
            failures.append((entry["id"],
                "contains quotation marks but no cited outlet has a full-text (success) retrieval — quotes cannot come from metadata/truncated fetches"))

    if failures:
        print("FAIL:")
        for entry_id, msg in failures:
            print(f"  {entry_id}: {msg}")
        sys.exit(1)

    print(f"OK: {len(todays_entries)} entries checked — all cited outlets reached; all quoted entries have a full-text retrieval.")
    sys.exit(0)

if __name__ == "__main__":
    main()
