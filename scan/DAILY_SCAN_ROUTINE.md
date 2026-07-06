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

## Step 1 — Pre-scan (against origin/main's data/cases.json)

**First, run the base guard — it is the gate for everything below:**

```
python scan/prescan_guard.py
```

It fetches `origin/main`, prints the authoritative case count and the true next
parent ID (`ACI-<highest+1>`), and **exits non-zero if the working tree is behind
`origin/main`** (i.e. missing cases that are already merged). If it blocks, reset
onto `origin/main` (Step 0) before assigning any ID — do not proceed on a stale
base.

The live data is `data/cases.json` on `origin/main` (not the spreadsheet, and not
a stale local copy). With the guard green, read it and establish:
- the highest existing entry number → the next new ID is that + 1 (the guard
  prints this);
- every case carrying `follow_up_pending: true` (or a "[FOLLOW-UP PENDING]" marker
  in notes);
- a dedup index of existing `source` URLs and titles, covering **all** rows.

Do not assign any new ID until the guard passes and this read is complete.

## Step 2A — Outlet homepage scan (MANDATORY, every run)

Directly fetch each of these four homepages and read every visible headline:
- Hyperallergic — hyperallergic.com
- The Art Newspaper — theartnewspaper.com
- ARTnews — artnews.com
- NYT — run `python scan/nyt_api.py "<query>" [from-date]` as a primary discovery step, querying the dragnet keywords defined in CLAUDE.md Part 1 across all desks (Politics, National, Business, US — not just Arts), date-anchored to the run window. Per CLAUDE.md, the API returns metadata only: log the thin entry from the abstract and store the canonical URL as the source. The Arts homepage and RSS feed see the Arts desk alone; this all-desk search is what catches the cross-desk coverage they structurally miss.
- Washington Post — washingtonpost.com — primary outlet for DC/federal cultural coverage (GSA Fine Arts, the monumental core, federal museums, New Deal/WPA art). WaPo has no API and direct fetch is frequently blocked; attempt via a targeted site-scoped web search (e.g. site:washingtonpost.com plus the day's DC/federal terms). If unretrievable, record "WaPo likely relevant — could not retrieve" in the coverage report rather than omitting it silently. A blocked fetch never means there was no coverage.

Fetch each at 8,000–10,000 tokens. List every headline with a one-word notation — relevant / already-logged / not-relevant — then state the count: "X scanned, Y relevant, Z already logged, W new."

This step is NOT satisfied by ingest.py / the RSS feed. RSS is a narrow, time-windowed slice; the homepage shows what editors are featuring across several days, including stories older than the RSS window and stories the dragnet keywords would never match. Run it as its own step, every day, regardless of what ingest.py returned.

## Step 2 — Run the scan (per CLAUDE.md, as one unattended pass)

1. **RSS baseline:** run `python scan/ingest.py`. This refreshes
   `scan/candidates.json` (the six feeds, 48-hour window, deduped against case URLs).
2. **Dragnet:** run the multilingual dragnet from CLAUDE.md Part 1 by web search —
   all listed languages, past 24–48h. The non-Latin-script passes (ZH/JA/KO/AR/FA/HI)
   are mandatory on Thursday and Saturday.
3. **Trawl:** run today's regional trawl from CLAUDE.md Part 2, including the standing
   searches for that day (Richmond/VA on Tue/Fri, Hungary de-Orbánization on Wed, etc.).
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
- **Source provenance — every cited source must be one you actually retrieved.** Every outlet named in a `source` or `outlets` field must have been directly fetched, or returned in a search result, during *this* run. If a source was not retrieved, it may not be listed — restrict the fields to the sources actually obtained, and note the limitation. Never add an outlet because it plausibly or probably covered the story. A real event with only one retrievable source gets one source, not a likely-looking list. Dates come from the retrieved article's own dateline or text, never from inference about relative time.
- **All required fields**, per CLAUDE.md's field spec: id, entry_id, seq, title, artist,
  institution, country, governance_type, date fields, description, outcome, tags,
  court_case, coverage_tier, outlets, source, themes, notes,
  interested_parties, coverage_geography, follow_up_pending. Sub-entries inherit parent
  themes unless a case-level reason differs. Use exact dates, never relative ones. Set
  `follow_up_pending: true` with a named note whenever the status speculates about a
  future development.

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
2. Validate: cases.json is still valid JSON, and the case count rose by exactly the
   number of new entries added.
3. Source check: for every new entry, confirm each listed source traces to an actual fetch or search result from this run. Any source that cannot be traced must be removed from the entry and flagged by name in the PR's "For your review" section ("ACI-XXX: listed outlet [name] not confirmed retrieved").
4. Open a PR titled **"Daily scan — YYYY-MM-DD (Day)"** whose description contains:
   - **Summary:** "X scanned, Y relevant, Z already logged, W new."
   - **Coverage report:** which dragnet languages ran, which trawl, non-EN sources
     returned vs. logged.
   - **Follow-up sweep:** which flags were checked and any resolved.
   - **For your review:** every judgment call the run wasn't sure about — borderline
     relevance, a tag that might near judgment, a possible duplicate, a thin entry
     needing enrichment. List these plainly so they can be settled on review.
5. **Stop at the open PR.** Do not merge. Do not deploy.

## If the run can't finish

If a session limit or a failure interrupts the scan, commit what's done to the branch,
open the PR anyway, and note in the description exactly what was completed and what was
skipped. Never leave a half-finished state uncommitted, and never leave cases.json in
an invalid state.
