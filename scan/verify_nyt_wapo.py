#!/usr/bin/env python3
"""Verify Excel-era NYT source URLs by slug-keyword search + exact URL match. Read-only.
Writes scan/nyt_wapo_verification.txt. Requires ~/.nyt_api_key. Self-calibrates before running."""
import json, re, time, os, sys
from datetime import datetime, timedelta
import requests

KEYFILE = os.path.expanduser('~/.nyt_api_key')
if not os.path.exists(KEYFILE):
    sys.exit('ERROR: ~/.nyt_api_key not found.')
KEY = open(KEYFILE).read().strip()
API = 'https://api.nytimes.com/svc/search/v2/articlesearch.json'
SLEEP = 12

def api(params):
    params['api-key'] = KEY
    for attempt in (1, 2):
        try:
            r = requests.get(API, params=params, timeout=20)
            if r.status_code == 429:
                time.sleep(30); continue
            r.raise_for_status()
            return r.json().get('response', {})
        except requests.exceptions.RequestException as e:
            if attempt == 2:
                return {'error': type(e).__name__}
            time.sleep(15)
    return {'error': 'retries exhausted'}

def check_url(url, title):
    """Returns (status, candidates). VERIFIED only on exact web_url match."""
    m = re.search(r'nytimes\.com/(\d{4})/(\d{2})/(\d{2})/(?:.+/)*([^/]+)\.html', url)
    if not m:
        return 'UNPARSEABLE', []
    y, mo, d, slug = m.groups()
    center = datetime(int(y), int(mo), int(d))
    b = (center - timedelta(days=3)).strftime('%Y%m%d')
    e = (center + timedelta(days=3)).strftime('%Y%m%d')
    norm = lambda u: (u or '').split('?')[0].rstrip('/')
    # pass 1: slug words
    docs = (api({'q': slug.replace('-', ' '), 'begin_date': b, 'end_date': e}).get('docs')) or []
    if any(norm(doc.get('web_url')) == norm(url) for doc in docs):
        return 'VERIFIED', []
    cands = docs
    # pass 2: title words, wider window
    time.sleep(SLEEP)
    q = ' '.join(re.sub(r'[^A-Za-z0-9 ]', ' ', title).split()[:7])
    b2 = (center - timedelta(days=10)).strftime('%Y%m%d')
    e2 = (center + timedelta(days=10)).strftime('%Y%m%d')
    docs2 = (api({'q': q, 'begin_date': b2, 'end_date': e2}).get('docs')) or []
    if any(norm(doc.get('web_url')) == norm(url) for doc in docs2):
        return 'VERIFIED', []
    seen, merged = set(), []
    for doc in (docs + docs2):
        u = norm(doc.get('web_url'))
        if u and u not in seen:
            seen.add(u)
            merged.append((doc.get('headline', {}).get('main', '?'), doc.get('web_url', '?'), (doc.get('pub_date') or '')[:10]))
    return 'FABRICATED', merged[:4]

# ---- calibration: a URL we know is canonical must verify, or the method is broken ----
CAL_URL = 'https://www.nytimes.com/2026/05/28/arts/design/lonnie-bunch-smithsonian-american-aspirations.html'
print('Calibration check against a known-canonical URL...')
status, _ = check_url(CAL_URL, 'Curating in the Cross Hairs Smithsonian')
if status != 'VERIFIED':
    sys.exit(f'CALIBRATION FAILED ({status}) — method unreliable, aborting before producing false verdicts.')
print('Calibration passed.\n')
time.sleep(SLEEP)

cases = json.load(open('data/cases.json'))['cases']
excel = lambda c: bool(re.match(r'^[A-Z][a-z]+ \d{1,2}, \d{4}$', str(c.get('date_discovered') or '')))
nyt  = [(c['id'], c['source'], c.get('title', '')) for c in cases if excel(c) and 'nytimes.com' in (c.get('source') or '')]
wapo = [(c['id'], c['source'], c.get('title', '')) for c in cases if excel(c) and 'washingtonpost.com' in (c.get('source') or '')]
print(f'{len(nyt)} NYT URLs to verify (~{len(nyt)*2*SLEEP//60} min worst case), {len(wapo)} WaPo URLs for browser triage.\n')

results = []
for n, (cid, url, title) in enumerate(nyt, 1):
    status, cands = check_url(url, title)
    results.append((cid, url, title, status, cands))
    print(f'  {n}/{len(nyt)}  {cid}: {status}')
    time.sleep(SLEEP)

with open('scan/nyt_wapo_verification.txt', 'w') as out:
    out.write(f'NYT/WaPo source verification (v2, exact-match method) — {time.strftime("%Y-%m-%d %H:%M")}\n')
    fab = [r for r in results if r[3] == 'FABRICATED']
    ver = [r for r in results if r[3] == 'VERIFIED']
    oth = [r for r in results if r[3] not in ('FABRICATED', 'VERIFIED')]
    out.write(f'NYT: {len(ver)} verified, {len(fab)} fabricated, {len(oth)} other | WaPo to triage: {len(wapo)}\n\n')
    out.write('=== FABRICATED NYT URLs (candidates below each) ===\n')
    for cid, url, title, status, cands in fab:
        out.write(f'\n{cid} — {title[:90]}\n  stored: {url}\n')
        for h, u, d in cands:
            out.write(f'  candidate [{d}]: {h}\n    {u}\n')
        if not cands:
            out.write('  (no candidates — needs manual keyword search)\n')
    if oth:
        out.write('\n=== OTHER (unparseable/errors) ===\n')
        for cid, url, *_ in oth:
            out.write(f'{cid}  {url}\n')
    out.write('\n=== VERIFIED (no action) ===\n')
    for cid, url, *_ in ver:
        out.write(f'{cid}  OK\n')
    out.write('\n=== WaPo URLs — click each in your browser ===\n')
    for cid, url, title in wapo:
        out.write(f'{cid} — {title[:70]}\n  {url}\n')

print('\nDone. Report: scan/nyt_wapo_verification.txt')
