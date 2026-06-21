"""
nyt_api.py — New York Times Article Search API client for the Dissensus Index scan.

WHY THIS EXISTS
The NYT website blocks automated fetches, and unlike the Guardian, the NYT API does
NOT return full article text — only metadata. So this is a DISCOVERY tool: it finds
NYT articles by keyword and date range across EVERY desk (not just Arts), returning
headline, date, section, byline, abstract, and the article URL. Use it to surface
candidates and follow-up leads during scans and FUP sweeps; read the actual article
via the URL.

SETUP (one time)
1. Register a free developer account + app at https://developer.nytimes.com
   Create an app and switch ON the "Article Search API".
2. Store the key as an environment variable so it never lands in the repo:
       export NYT_API_KEY="your-key-here"
   Add that line to ~/.zshrc to make it permanent, then run: source ~/.zshrc

LIMITS: 500 requests/day, 5 requests/minute. This module sleeps 12s between paged
requests to stay under the per-minute cap, so large searches are deliberately slow.
"""

import os
import time
import requests

API_ROOT = "https://api.nytimes.com/svc/search/v2/articlesearch.json"


def _api_key():
    key = os.environ.get("NYT_API_KEY")
    if not key:
        raise RuntimeError(
            "No NYT API key found. Set it with: export NYT_API_KEY='your-key'"
        )
    return key


def _clean_date(d):
    # NYT wants YYYYMMDD; accept 'YYYY-MM-DD' (like guardian_api) or 'YYYYMMDD'.
    return d.replace("-", "") if d else None


def search_nyt(query, from_date=None, to_date=None, max_results=20,
               section=None, sort="newest"):
    """
    Search NYT articles across all desks. Returns a list of dicts:
        {headline, url, date, section, desk, byline, abstract}

    query       : search terms, e.g. 'museum repatriation'
    from_date   : 'YYYY-MM-DD' lower bound on publication date (optional)
    to_date     : 'YYYY-MM-DD' upper bound (optional)
    max_results : how many results to return. NYT pages are 10 each; this pages
                  as needed, sleeping 12s between pages to respect 5 req/min.
    section     : restrict to a section, e.g. 'Arts' (optional; default = all desks)
    sort        : 'newest', 'oldest', or 'relevance'
    """
    params = {
        "q": query,
        "api-key": _api_key(),
        "sort": sort,
    }
    if from_date:
        params["begin_date"] = _clean_date(from_date)
    if to_date:
        params["end_date"] = _clean_date(to_date)
    if section:
        params["fq"] = f'section_name:("{section}")'

    out = []
    page = 0
    while len(out) < max_results and page <= 100:
        params["page"] = page
        resp = requests.get(API_ROOT, params=params, timeout=30)
        resp.raise_for_status()
        docs = resp.json().get("response", {}).get("docs", [])
        if not docs:
            break
        for d in docs:
            headline = (d.get("headline") or {}).get("main", "")
            byline = (d.get("byline") or {}).get("original", "") or ""
            out.append({
                "headline": headline,
                "url": d.get("web_url", ""),
                "date": d.get("pub_date", ""),
                "section": d.get("section_name", ""),
                "desk": d.get("news_desk", ""),
                "byline": byline,
                "abstract": d.get("abstract", "") or d.get("snippet", ""),
            })
            if len(out) >= max_results:
                break
        page += 1
        if len(out) < max_results:
            time.sleep(12)  # stay under 5 requests/minute
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        q = sys.argv[1]
        fdate = sys.argv[2] if len(sys.argv) > 2 else None
        for art in search_nyt(q, from_date=fdate, max_results=10):
            print(art["date"][:10], "—", art["headline"])
            print("    ", art["section"], "/", art["desk"], "—", art["byline"])
            print("    ", art["url"])
            print("    ", (art["abstract"] or "")[:200], "\n")
    else:
        print('Usage: python scan/nyt_api.py "<search terms>" [YYYY-MM-DD from-date]')
