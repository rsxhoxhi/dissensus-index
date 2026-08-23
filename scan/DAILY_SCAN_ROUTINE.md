# Daily Scan Routine — Unattended Operating Instructions

## What this is

This file tells the scheduled Claude Code Routine how to run the Dissensus Index
daily scan **unattended, in the cloud, with no human present during the run.**

`CLAUDE.md` remains the source of truth for *what* to scan — dragnet terms and
languages, the trawl rotation, outlet lists, relevance criteria, and the
neutrality standard. This file covers only what changes when the scan runs on its
own: how to start, how to handle the absence of a human, and how to deliver the
result as a pull request for later review.

**Hard rules, never broken:** never merge, never deploy, never auto-publish, never
relax the neutrality standard. The run ends at an open PR. A human reviews and
merges.

## Step 0 — Establish the date, and start from a FRESH base

Get today's date and day of week from the environment (`date -u`), never from
memory. The day of week selects that day's regional trawl, so it must be correct.

Then fetch the latest state and cut today's branch from it, **not** from whatever
the clone happened to check out:

```
git fetch origin main
git checkout -B claude/daily-<YYYY-MM-DD> origin/main
```

Why this is mandatory: yesterday's scan PR may have merged since this container
was created. If today's scan bases on a stale `main`, its dedup misses
already-merged cases and its ID counter restarts from an old high-water mark —
so it re-logs merged stories and hands the same `ACI-2xx` ID to a different case.
That is exactly what produced the 2026-07-04/05/06 duplicate/ID-collision
pile-up. Always base the day's branch on the freshly-fetched `origin/main`.

## Step 1 — Pre-scan (against the backlog-aware union base)

**First, run the base guard — it is the gate for everything below:**

```
python scan/prescan_guard.py
```

The guard defends against **two** failure modes:

- **Stale local base** — it **exits non-zero if the working tree is behind
  `origin/main`** (missing already-merged cases). If it blocks, reset onto
  `origin/main` (Step 0) before assigning any ID.
- **Unmerged backlog** — when several daily-scan PRs sit OPEN (e.g. the maintainer
  is away for a few days), their new cases are not in `main` yet. The guard unions
  `origin/main` with every open `claude/daily-*` / `claude/scan-*` branch not yet
  merged, so the **next parent ID it prints already accounts for IDs reserved by
  pending PRs** — two runs can't hand out the same `ACI-2xx`. It lists each pending
  branch and the IDs it holds, and writes the union to **`scan/backlog_cases.json`**.

Assign new IDs starting from the number the guard prints — **not** from a hand
count of `data/cases.json`, which sees merged cases only.

With the guard green, establish from the union (`scan/backlog_cases.json`, which
`ingest.py` also reads automatically for RSS dedup):
- the next new ID (the guard prints it — it already skips IDs held by open PRs);
- every case carrying `follow_up_pending: true` (or a "[FOLLOW-UP PENDING]" marker
  in notes) — from `data/cases.json` on `origin/main`;
- a dedup index of existing `source` URLs and titles, covering **all** rows of the
  union — so a story already drafted in an unmerged PR is not logged a second time.

Do not assign any new ID until the guard passes and this read is complete.

## Step 2A — Outlet homepage scan (MANDATORY, every run)

**First, open the run's retrieval ledger** so it belongs to this scan and nothing else:

```
python scan/log_retrieval.py --new-run --outlet "<first outlet>" --url "<first url>" --method fetch --status <grade>
```

`--new-run` starts a fresh ledger and stamps it with today as the run anchor. Use it on the **first** retrieval of the scan only; every later `log_retrieval.py` call omits the flag and appends. The ledger is anchored to the date the run *started* and is never reset by the clock rolling past midnight UTC, so a scan that spans midnight keeps all its records (a genuinely separate run — more than 20h later — resets automatically). If the very first retrieval is a homepage fetch below, fold `--new-run` into that call.

Directly fetch each of these four homepages and read every visible headline:
- Hyperallergic — hyperallergic.com
- The Art Newspaper — theartnewspaper.com
- ARTnews — artnews.com
- NYT — run `python scan/nyt_api.py "<query>" [from-date]` as a primary discovery step, querying the dragnet keywords defined in CLAUDE.md Part 1 across all desks (Politics, National, Business, US — not just Arts), date-anchored to the run window. Per CLAUDE.md, the API returns metadata only: log the thin entry from the abstract and store the canonical URL as the source. The Arts homepage and RSS feed see the Arts desk alone; this all-desk search is what catches the cross-desk coverage they structurally miss.
- Washington Post — washingtonpost.com — primary outlet for DC/federal cultural coverage (GSA Fine Arts, the monumental core, federal museums, New Deal/WPA art). WaPo has no API and direct fetch is frequently blocked; attempt via a targeted site-scoped web search (e.g. site:washingtonpost.com plus the day's DC/federal terms). If unretrievable, record "WaPo likely relevant — could not retrieve" in the coverage report rather than omitting it silently. A blocked fetch never means there was no coverage.

Fetch each at 8,000–10,000 tokens. List every headline with a one-word notation — relevant / already-logged / not-relevant — then state the count: "X scanned, Y relevant, Z already logged, W new."

**Log every retrieval, at retrieval time.** Immediately after each retrieval of any kind — homepage fetch, article fetch, a web-search result actually read, an NYT API call, or an RSS item an entry is drafted from — run:

`python scan/log_retrieval.py --outlet "<name>" --url "<url>" --method fetch|search_result|api --status success|truncated|snippet_only|blocked`

Grades: `success` = full body read; `truncated` = partial body; `snippet_only` = metadata/abstract/search-snippet only; `blocked` = not retrieved. Ledger records are written at retrieval time only — if the gate later fails on an unlogged outlet, the fix is to re-fetch and log properly, **never to backfill the ledger from memory**: backfilling reinstates the exact self-attestation problem the ledger exists to remove. Records only ever accumulate within a run; the ledger's `run_date` is the run's anchor and stays fixed even if the scan crosses midnight UTC.

This step is NOT satisfied by ingest.py / the RSS feed. RSS is a narrow, time-windowed slice; the homepage shows what editors are featuring across several days, including stories older than the RSS window and stories the dragnet keywords would never match. Run it as its own step, every day, regardless of what ingest.py returned.

## Step 2 — Run the scan (per CLAUDE.md, as one unattended pass)

1. **RSS baseline:** run `python scan/ingest.py`. This refreshes
   `scan/candidates.json` (the six feeds, 48-hour window, deduped against case URLs).
2. **Dragnet:** run the multilingual dragnet from CLAUDE.md Part 1 by web search —
   all listed languages, past 24–48h. The non-Latin-script passes (ZH/JA/KO/AR/FA/HI)
   are mandatory on Thursday and Saturday.
3. **Trawl:** run today's regional trawl from CLAUDE.md Part 2, including the standing
   searches for that day (Richmond/VA on Tue/Fri, etc.).
4. **Follow-up sweep:** for each `follow_up_pending` case that is plausibly ripe,
   web-search for developments.
5. **Paywalled sources:** where a direct fetch is blocked, use
   `python scan/guardian_api.py "<url>"` (full text) or
   `python scan/nyt_api.py "<query>" [from-date]` (metadata). If still blocked,
   record "could not retrieve" — never fabricate, and a blocked fetch never means
   the story doesn't exist.

## Step 3 — Triage and dedup

For every candidate from ingest + dragnet + trawl, decide tracker-relevance using
CLAUDE.md's criteria, then check each against the pre-scan dedup index:
- already logged → drop it;
- an update to an existing case → draft it as a **sub-entry** of that parent
  (e.g. ACI-043-A), not a new parent;
- genuinely new → new parent, next sequential ID.

When relevance is borderline, keep it and flag the uncertainty in the PR rather than
dropping it silently.

## Step 4 — Draft entries — NEUTRALITY IS NON-NEGOTIABLE

Draft each keeper as a full entry in the cases.json schema, applying the standard
this project is built around:

- **Describe, don't judge.** State accurate facts plainly; let cited sources carry
  any characterization. "Condemned as X by Y" belongs in the description attributed
  to Y — never in the Index's own voice.
- **Tags are descriptive, never verdicts.** Use contest/act tags (Removal, Vandalism,
  Censorship, Religious objection, Community objection, Geopolitics, and so on). Never
  use verdict tags (Islamophobia, antisemitism, racist, propaganda). Identity
  descriptors (LGBTQ+, Muslim, Indigenous) are fine when they name who or what is
  involved. An axis tag (Racial/ethnic sensitivity) is allowed only when that axis is
  the overt, explicit subject of the work and the objection — not when attributing the
  dispute to that axis is an inference about motive.
- **No over-hedging.** Don't pile on attribution disclaimers; plain accurate facts are
  enough.
- **Source provenance — every cited source must be one you actually retrieved.** Every outlet named in a `source` or `outlets` field must have been directly fetched, or returned in a search result, during *this* run. If a source was not retrieved, it may not be listed — restrict the fields to the sources actually obtained, and note the limitation. Never add an outlet because it plausibly or probably covered the story. A real event with only one retrievable source gets one source, not a likely-looking list. Dates come from the retrieved article's own dateline or text, never from inference about relative time. When an entry draws on more than one retrieved article, put the reference article — the one the entry is drafted from and verified against — in `source`, and the other retrieved-and-used URLs in `additional_sources` (see CLAUDE.md required fields). Populate it from this run’s own ledger: only URLs actually retrieved this run, and only those actually used for claims in the entry — never a thoroughness-display of everything fetched. An entry resting on a single article carries `"additional_sources": []`, which is the normal case, not a deficiency.
- **All required fields**, per CLAUDE.md's field spec: id, entry_id, seq, title, artist,
  institution, country, governance_type, date fields, description, outcome, tags,
  court_case, coverage_tier, outlets, source, themes, notes,
  interested_parties, coverage_geography, follow_up_pending, additional_sources. Sub-entries inherit parent
  themes unless a case-level reason differs. Use exact dates, never relative ones. Set
  `follow_up_pending: true` with a named note whenever the status speculates about a
  future development.

## Step 4B — Provenance gate (MANDATORY, before the PR opens)

Run `python scan/check_provenance.py`. The PR does not open until it prints OK. The gate enforces two rules against this run's ledger: (1) **reach** — every outlet cited in `outlets`, `source`, or `additional_sources` must have a non-blocked retrieval record this run (metadata-grade thin entries are legitimate); (2) **depth** — any entry containing quotation marks must have at least one cited outlet with a full `success` retrieval, because quotes cannot come from metadata or truncated fetches. The gate validates the entries authored this run, anchored to the ledger's `run_date`; if the scan crossed midnight UTC it prints a NOTE that `run_date` differs from today and validates against the anchor — this is normal, not a failure. On FAIL: re-fetch and log the missing outlet, correct the entry to match what was actually retrieved, or remove the unverifiable material — then re-run the gate. Never edit the ledger to satisfy the gate. If the failure is `unrecognized domain`, add the domain to `DOMAIN_TO_OUTLET` in `scan/check_provenance.py` as part of the run and note it in the PR.

## Step 5 — Write the result as a pull request

On the branch cut from `origin/main` in Step 0 (`claude/daily-YYYY-MM-DD`). If any
time has passed since Step 0, re-run `python scan/prescan_guard.py` before
committing — if a PR merged mid-run, rebase onto `origin/main` and re-check IDs so
you don't reintroduce a duplicate/collision:

1. Insert the drafted entries into `data/cases.json`. **Append/insert only.** Add new
   parents; insert sub-entries positionally after the last entry sharing the parent
   prefix. The only existing entries you may modify are `follow_up_pending` cases where
   the sweep found a development — update that case's outcome and drop its flag. Touch
   nothing else.
2. After any insert or removal, set `meta.total_cases` to the exact length of the
   `cases` array. This field is an integrity check against the data, not a display
   source — the site counts the array directly — so a mismatch means an insert step
   was skipped.
3. Validate: cases.json is still valid JSON, and the case count rose by exactly the
   number of new entries added.
4. Source check: for every new entry, confirm each listed source traces to an actual fetch or search result from this run. Any source that cannot be traced must be removed from the entry and flagged by name in the PR's "For your review" section ("ACI-XXX: listed outlet [name] not confirmed retrieved").
5. Open a PR titled **"Daily scan — YYYY-MM-DD (Day)"** whose description contains:
   - **Summary:** "X scanned, Y relevant, Z already logged, W new."
   - **Coverage report:** which dragnet languages ran, which trawl, non-EN sources
     returned vs. logged.
   - **Follow-up sweep:** which flags were checked and any resolved.
   - **For your review:** every judgment call the run wasn't sure about — borderline
     relevance, a tag that might near judgment, a possible duplicate, a thin entry
     needing enrichment. List these plainly so they can be settled on review.
6. **Stop at the open PR.** Do not merge. Do not deploy.

## If the run can't finish

If a session limit or a failure interrupts the scan, commit what's done to the branch,
open the PR anyway, and note in the description exactly what was completed and what was
skipped. Never leave a half-finished state uncommitted, and never leave cases.json in
an invalid state.
