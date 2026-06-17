#!/usr/bin/env python3
"""
Dissensus Index — RSS ingestion script.

Fetches art-world RSS feeds, pulls items from the last 48 hours,
dedupes against already-logged cases, and writes new candidates to
scan/candidates.json.
"""

import datetime
import json
import re
import time
from pathlib import Path

import feedparser

FEEDS = [
    ("Hyperallergic",         "https://hyperallergic.com/feed/"),
    ("ARTnews",               "https://www.artnews.com/feed/"),
    ("The Art Newspaper",     "https://www.theartnewspaper.com/rss"),
    ("Artforum",              "https://www.artforum.com/feed/"),
    ("The Guardian (art)",    "https://www.theguardian.com/artanddesign/rss"),
    ("NYT Arts",              "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml"),
]

WINDOW_HOURS = 48
REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = REPO_ROOT / "data" / "cases.json"
CANDIDATES_PATH = REPO_ROOT / "scan" / "candidates.json"


def load_known_sources():
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return {
        c.get("source", "").strip()
        for c in data.get("cases", [])
        if c.get("source")
    }


def window_cutoff():
    """Return a UTC struct_time for 48 hours ago."""
    return time.gmtime(time.time() - WINDOW_HOURS * 3600)


def fetch_feed(name, url):
    """
    Parse one RSS feed. Returns (entries_list, error_string_or_None).
    feedparser never raises — failures surface via .bozo and .status.
    """
    d = feedparser.parse(url)
    if d.get("bozo") and not d.get("entries"):
        return [], str(d.get("bozo_exception", "unknown parse error"))
    status = d.get("status", 200)
    if status >= 400:
        return [], f"HTTP {status}"
    return d.entries, None


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def entry_to_candidate(entry, feed_name):
    pub = entry.get("published_parsed") or entry.get("updated_parsed")
    pub_iso = ""
    if pub:
        pub_iso = datetime.datetime(*pub[:6], tzinfo=datetime.timezone.utc).isoformat()

    summary = strip_html(entry.get("summary", ""))
    if len(summary) > 300:
        summary = summary[:300] + "…"

    return {
        "source_feed": feed_name,
        "title": entry.get("title", "").strip(),
        "link": entry.get("link", "").strip(),
        "published": pub_iso,
        "summary": summary,
    }


def main():
    cutoff = window_cutoff()
    known_sources = load_known_sources()

    candidates = []
    feed_summaries = []
    unreachable = []

    print()
    print("Dissensus Index — RSS Ingestion")
    print(f"Window : last {WINDOW_HOURS} hours")
    print(f"Logged : {len(known_sources)} source URLs already in cases.json")
    print("─" * 60)

    for name, url in FEEDS:
        entries, error = fetch_feed(name, url)

        if error:
            print(f"  ✗  {name}")
            print(f"       UNREACHABLE — {error}")
            unreachable.append({"feed": name, "url": url, "error": error})
            feed_summaries.append({"feed": name, "status": "unreachable", "error": error})
            continue

        in_window = [
            e for e in entries
            if (e.get("published_parsed") or e.get("updated_parsed") or None) is not None
            and (e.get("published_parsed") or e.get("updated_parsed")) >= cutoff
        ]

        new, already_logged = [], 0
        for entry in in_window:
            link = entry.get("link", "").strip()
            if link in known_sources:
                already_logged += 1
            else:
                new.append(entry_to_candidate(entry, name))

        candidates.extend(new)
        print(
            f"  ✓  {name}\n"
            f"       {len(entries)} in feed · "
            f"{len(in_window)} in window · "
            f"{len(new)} new · "
            f"{already_logged} already logged"
        )
        feed_summaries.append({
            "feed": name,
            "status": "ok",
            "total_in_feed": len(entries),
            "in_window": len(in_window),
            "new_candidates": len(new),
            "already_logged": already_logged,
        })

    print("─" * 60)
    print(f"New candidates total : {len(candidates)}")

    if unreachable:
        print(f"Unreachable feeds    : {len(unreachable)}")
        for u in unreachable:
            print(f"  • {u['feed']} ({u['url']})")

    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "window_hours": WINDOW_HOURS,
        "feed_summary": feed_summaries,
        "candidates": candidates,
    }
    CANDIDATES_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nWritten → scan/candidates.json ({len(candidates)} items)")


if __name__ == "__main__":
    main()
