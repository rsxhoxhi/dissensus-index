"""
guardian_api.py — Guardian Open Platform Content API client for the Dissensus Index scan.

WHY THIS EXISTS
The Guardian's website blocks automated page fetches, but its Open Platform API
returns FULL article body text as JSON — free for non-commercial use. This module
hits the API directly, so the scan can read real article text (and verify quotes)
instead of scraping blocked pages or trusting RSS summaries.

SETUP (one time)
1. Register for a free developer key: https://open-platform.theguardian.com/access
   (Short form; the key arrives by email.)
2. Store it as an environment variable so it never lands in the repo:
       export GU_API_KEY="your-key-here"
   Add that line to ~/.zshrc to make it permanent, then run: source ~/.zshrc

FREE-TIER LIMITS: 12 calls/sec, 5,000 calls/day — far more than the scan needs.
"""

import os
import requests

API_ROOT = "https://content.guardianapis.com"
DEFAULT_FIELDS = "headline,byline,firstPublicationDate,lastModified,shortUrl,bodyText"


def _api_key():
    key = os.environ.get("GU_API_KEY")
    if not key:
        raise RuntimeError(
            "No Guardian API key found. Set it with: export GU_API_KEY='your-key'"
        )
    return key


def search_guardian(query, from_date=None, to_date=None, page_size=20,
                    section=None, fields=DEFAULT_FIELDS):
    """
    Search Guardian content. Returns a list of dicts:
        {headline, url, api_url, date, body}   (body = plain-text article body)

    query     : search terms, e.g. 'Helen Cammock National Portrait Gallery'
    from_date : 'YYYY-MM-DD' lower bound on publication date (optional)
    to_date   : 'YYYY-MM-DD' upper bound (optional)
    section   : restrict to a section id, e.g. 'artanddesign' (optional)
    """
    params = {
        "q": query,
        "api-key": _api_key(),
        "show-fields": fields,
        "page-size": page_size,
        "order-by": "newest",
    }
    if from_date:
        params["from-date"] = from_date
    if to_date:
        params["to-date"] = to_date
    if section:
        params["section"] = section

    resp = requests.get(f"{API_ROOT}/search", params=params, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("response", {}).get("results", [])

    out = []
    for r in results:
        f = r.get("fields", {})
        out.append({
            "headline": f.get("headline", r.get("webTitle", "")),
            "url": r.get("webUrl", ""),
            "api_url": r.get("apiUrl", ""),
            "date": f.get("firstPublicationDate", r.get("webPublicationDate", "")),
            "body": f.get("bodyText", ""),
        })
    return out


def fetch_guardian_article(url_or_id, fields=DEFAULT_FIELDS):
    """
    Fetch ONE Guardian article's full text by web URL or content id.
    Returns {headline, url, date, body} or None if not found.

    Accepts either:
      - a full web URL: https://www.theguardian.com/artanddesign/2026/jun/16/slug
      - a content id (the path):        artanddesign/2026/jun/16/slug
    """
    content_id = url_or_id
    if content_id.startswith("http"):
        content_id = content_id.split("theguardian.com/", 1)[-1].lstrip("/")

    params = {"api-key": _api_key(), "show-fields": fields}
    resp = requests.get(f"{API_ROOT}/{content_id}", params=params, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    content = resp.json().get("response", {}).get("content")
    if not content:
        return None
    f = content.get("fields", {})
    return {
        "headline": f.get("headline", content.get("webTitle", "")),
        "url": content.get("webUrl", ""),
        "date": f.get("firstPublicationDate", content.get("webPublicationDate", "")),
        "body": f.get("bodyText", ""),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        art = fetch_guardian_article(sys.argv[1])
        if art:
            print(art["headline"])
            print(art["date"])
            print()
            print(art["body"])
        else:
            print("could not retrieve:", sys.argv[1])
    else:
        print('Usage: python scan/guardian_api.py "<guardian article URL>"')
