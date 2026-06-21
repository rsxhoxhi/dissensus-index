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
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

FEEDS = [
    ("Hyperallergic",         "https://hyperallergic.com/feed/"),
    ("ARTnews",               "https://www.artnews.com/feed/"),
    ("The Art Newspaper",     "https://www.theartnewspaper.com/rss.xml"),
    ("Artforum",              "https://www.artforum.com/feed/"),
    ("The Guardian (art)",    "https://www.theguardian.com/artanddesign/rss"),
    ("NYT Arts",              "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml"),
]

WINDOW_HOURS = 96
REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = REPO_ROOT / "data" / "cases.json"
CANDIDATES_PATH = REPO_ROOT / "scan" / "candidates.json"

ATOM_NS = "http://www.w3.org/2005/Atom"


def load_known_sources():
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return {
        c.get("source", "").strip()
        for c in data.get("cases", [])
        if c.get("source")
    }


def window_cutoff():
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=WINDOW_HOURS)


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def parse_date(date_str):
    """Parse RFC 2822 (RSS) or ISO 8601 (Atom) date strings to UTC datetime."""
    if not date_str:
        return None
    date_str = date_str.strip()
    # RFC 2822: "Tue, 21 Jun 2026 10:00:00 +0000"
    try:
        return parsedate_to_datetime(date_str).astimezone(datetime.timezone.utc)
    except Exception:
        pass
    # ISO 8601: "2026-06-21T10:00:00Z" or "2026-06-21T10:00:00+00:00"
    try:
        normalized = date_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        pass
    return None


def _parse_rss(root):
    entries = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        # Fall back to <guid> if <link> is empty
        if not link:
            guid = item.find("guid")
            if guid is not None and guid.get("isPermaLink", "true").lower() != "false":
                link = (guid.text or "").strip()
        pub_raw = (
            item.findtext("pubDate")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            or ""
        )
        summary_raw = item.findtext("description") or ""
        entries.append({
            "title": title,
            "link": link,
            "published_dt": parse_date(pub_raw),
            "summary_raw": summary_raw,
        })
    return entries


def _parse_atom(root):
    ns = {"a": ATOM_NS}
    entries = []
    for entry in root.findall("a:entry", ns):
        title_el = entry.find("a:title", ns)
        title = (title_el.text or "").strip() if title_el is not None else ""

        link = ""
        for link_el in entry.findall("a:link", ns):
            rel = link_el.get("rel", "alternate")
            if rel in ("alternate", ""):
                link = link_el.get("href", "")
                break

        pub_raw = ""
        for tag in ("a:published", "a:updated"):
            el = entry.find(tag, ns)
            if el is not None and el.text:
                pub_raw = el.text
                break

        summary_el = entry.find("a:summary", ns)
        if summary_el is None:
            summary_el = entry.find("a:content", ns)
        summary_raw = (summary_el.text or "") if summary_el is not None else ""

        entries.append({
            "title": title,
            "link": link,
            "published_dt": parse_date(pub_raw),
            "summary_raw": summary_raw,
        })
    return entries


def parse_entries(xml_bytes):
    """Detect RSS vs Atom and return a list of entry dicts."""
    root = ET.fromstring(xml_bytes)
    tag = root.tag  # may be "{namespace}feed" for Atom
    if tag == f"{{{ATOM_NS}}}feed" or tag == "feed":
        return _parse_atom(root)
    return _parse_rss(root)


def fetch_feed(name, url):
    """
    Fetch and parse one RSS/Atom feed.
    Returns (entries_list, error_string_or_None).
    """
    try:
        resp = requests.get(
            url, timeout=30,
            headers={"User-Agent": "DissensusIndex/1.0 (+https://dissensusindex.com)"},
        )
        resp.raise_for_status()
        return parse_entries(resp.content), None
    except requests.HTTPError as e:
        return [], f"HTTP {e.response.status_code}"
    except Exception as e:
        return [], str(e)


def entry_to_candidate(entry, feed_name):
    dt = entry["published_dt"]
    pub_iso = dt.isoformat() if dt else ""

    summary = strip_html(entry["summary_raw"])
    if len(summary) > 300:
        summary = summary[:300] + "…"

    return {
        "source_feed": feed_name,
        "title": entry["title"],
        "link": entry["link"],
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
            if e["published_dt"] is not None and e["published_dt"] >= cutoff
        ]

        new, already_logged = [], 0
        for entry in in_window:
            link = entry["link"]
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
