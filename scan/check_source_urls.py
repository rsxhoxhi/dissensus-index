#!/usr/bin/env python3
"""Read-only source-URL audit for the Dissensus Index. Writes scan/source_report.txt. No data changes."""
import json, time
from collections import defaultdict
import requests

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'}

data = json.load(open('data/cases.json'))
cases = data['cases']

items = [(c['id'], (c.get('source') or '').strip()) for c in cases]
blank = [i for i, u in items if not u.startswith('http')]
todo  = [(i, u) for i, u in items if u.startswith('http')]

by_url = defaultdict(list)
for i, u in todo:
    by_url[u].append(i)
urls = list(by_url)

print(f'{len(cases)} entries | {len(todo)} with URLs | {len(urls)} unique URLs | {len(blank)} blank/invalid')
print('Checking (about 1.8s per URL — this will take a while)...')

results = {}
start = time.time()
for n, u in enumerate(urls, 1):
    try:
        r = requests.get(u, headers=UA, timeout=15, allow_redirects=True, stream=True)
        code = r.status_code
        r.close()
    except requests.exceptions.Timeout:
        code = 'TIMEOUT'
    except requests.exceptions.RequestException as e:
        code = f'ERR:{type(e).__name__}'
    results[u] = code
    if n % 25 == 0 or n == len(urls):
        print(f'  {n}/{len(urls)} checked ({int(time.time()-start)}s elapsed)')
    time.sleep(0.8)

def bucket(code):
    if code in (404, 410): return 'DEAD'
    if code in (401, 403, 429): return 'BLOCKED'
    if isinstance(code, int) and 200 <= code < 300: return 'OK'
    if isinstance(code, int) and 500 <= code < 600: return 'SERVER'
    return 'ERROR'

counts = defaultdict(int)
rows = []
for u, code in results.items():
    b = bucket(code)
    counts[b] += 1
    rows.append((b, code, u, by_url[u]))

order = {'DEAD': 0, 'ERROR': 1, 'SERVER': 2, 'BLOCKED': 3, 'OK': 4}
rows.sort(key=lambda r: (order[r[0]], str(r[1])))

with open('scan/source_report.txt', 'w') as out:
    out.write(f'Source URL audit — {time.strftime("%Y-%m-%d %H:%M")}\n')
    out.write(f'Entries: {len(cases)} | unique URLs checked: {len(urls)} | blank/invalid: {len(blank)}\n')
    out.write('Counts: ' + ', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) + '\n\n')
    if blank:
        out.write('BLANK/INVALID source field:\n')
        for i in blank:
            out.write(f'  {i}\n')
        out.write('\n')
    for b, code, u, ids in rows:
        if b == 'OK':
            continue
        out.write(f'[{b} {code}] {", ".join(ids)}\n  {u}\n')
    out.write('\n(OK URLs omitted from listing — see counts.)\n')

print('\nSummary:', dict(counts))
print('Report: scan/source_report.txt — DEAD is the review bucket.')
