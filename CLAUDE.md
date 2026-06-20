# The Dissensus Index — Project Instructions (Merged)

> Merged draft reconciling the build-session distilled instructions with the prior scan-protocol instructions. Open judgment calls are marked `[DECISION — …]`. Resolve or strike those, then this becomes the master.

---

## 1. What this project is

This project maintains the **Dissensus Index** (dissensusindex.com), a quarterly record of art controversy. The Index tracks disputes involving artworks, artists, institutions, and cultural policy through a structured five-stage methodology. The public site is built from a dataset; the working master is the tracker spreadsheet (`art_controversy_tracker_LIVE.xlsx`), migrating to a repo-based store.

**Public identity:** An independent research project.

**Internal working context:** The tracker is a personal research instrument and a public Index documenting art and cultural-heritage controversies worldwide.

**Operational design.** The daily scan protocol is designed for low activation cost: paste the prompt, Claude runs the searches, entries get added. The design favors clear structure, minimal decision-making at the point of execution, and momentum built through daily repetition.

---

## 2. Data schema (working master)

The spreadsheet is the full-detail master. Every column is preserved; the public site renders a subset.

`[DECISION — identifier]` The build session introduced **ACI IDs** as the stable public identifier. Confirm whether the spreadsheet adopts ACI IDs directly, or whether ACI is a display layer mapped over the existing three-digit Entry IDs (001, 011-A…). Until resolved, the working master keeps three-digit Entry IDs + Parent IDs, since the sub-entry system depends on them.

Columns (working master, 20):

1. Entry ID (three-digit, e.g., 001) — maps to public ACI ID
2. Parent ID (blank for new entries; references original Entry ID for updates/sub-entries, e.g., 011-A)
3. Date Discovered
4. Date of Controversy
5. Artwork / Object
6. Artist / Subject
7. Location / Institution
8. Country
9. Governance Type (Democracy / Hybrid Regime / Authoritarian / Theocracy; annotate trajectory for democracies under authoritarian pressure)
10. Brief Description
11. Interested Parties
12. Court Case (Yes / No / Pending)
13. Broad Tags
14. Dissensus Themes [see §3]
15. Coverage Tier (Local / Regional / National / International)
16. Coverage Geography (where the story is being *covered*, not just where it happened)
17. Key Outlets
18. Primary Source Link
19. Outcome / Status
20. Notes (observations, pattern connections, class relevance — **and the `[FOLLOW-UP PENDING]` flag prefix**)
21. Stage (1–5; see §9) — added in the build session; assign at logging time

> The public-site field list (ACI ID, title, artist/subject, institution, country, governance, dates, description, outcome/status, broad tags, court case, coverage tier, key outlets, primary source link, stage) is a **display subset**. Parent ID, Interested Parties, Coverage Geography, and Notes stay in the master even if not surfaced publicly — they carry the update mechanism, the coverage-movement signal, and the active-monitoring flags.

### Required fields for every cases.json entry

Every case object written to `cases.json` MUST include all of the following.
The first block is the existing schema; the second block was historically omitted
and is now mandatory — the rich-master migration (June 2026) restored these from
the spreadsheet and they must not be dropped again.

**Existing fields:** `id`, `entry_id`, `seq`, `title`, `artist`, `institution`,
`country`, `governance_type`, `date_controversy`, `date_discovered`, `sort_date`,
`description`, `outcome`, `tags`, `court_case`, `coverage_tier`, `outlets`,
`source`, `stage`, `stage_label`

**Five fields now mandatory on every new entry:**

- `themes` — JSON array of Dissensus theme numbers, e.g. `[2, 4, 8]`. Use `[]`
  if none fit. Sub-entries copy the parent's themes unless there is a specific
  case-level reason to differ.
- `notes` — string. Cross-references to other entries by ID, Dissensus theme
  connections, pattern observations. `""` if none.
- `interested_parties` — string. Named parties and roles, e.g.
  `"Judge Cooper; Rep. Beatty; Kennedy Center board"`. `""` if unknown.
- `coverage_geography` — string. Where the story is being covered (not just where
  it happened), e.g. `"US, Europe"`. `""` if unknown at logging time.
- `follow_up_pending` — boolean. `true` when the entry anticipates a future
  development that will produce a further sub-entry or status update; `false`
  otherwise.

**Two consistency rules:**

1. When `follow_up_pending` is `true`, also include a descriptive
   `[FOLLOW-UP PENDING: …]` note in `notes` or `outcome` so the pending thing
   is named, not just flagged.
2. When a follow-up resolves, set `follow_up_pending` to `false` *in addition to*
   clearing the `[FOLLOW-UP PENDING]` text from `notes`/`outcome`.

---

## 3. Dissensus themes

The ten thematic categories used to tag cases by the analytical questions they raise, so related cases can be grouped and compared across the Index.

An entry can carry zero, one, or multiple theme tags:

1. Defining Art — Who gets to decide what counts as art?
2. Public Funding — What happens when public funding meets private expression?
3. Exhibition Responsibility — What do major recurring exhibitions owe to the politics of their moment?
4. Institutional Risk — Should institutions work to avoid controversy?
5. Ethical Museum — What does an ethical encyclopedic museum look like?
6. Iconoclasm — When is iconoclasm justified? Can a consistent standard apply?
7. Unauthorized Public Art — What rights does an artist retain over unauthorized public work?
8. Artist Responsibility — Does an artist owe specific affected audiences?
9. Public Objection — When the public objects to publicly funded/sited art, whose view prevails?
10. Art and Capital — When art is treated primarily as a financial asset, what is lost, who benefits, who bears the cost?

---

## 4. Broad tags (open vocabulary, grows organically)

Censorship · Removal · Vandalism · Funding dispute · Deaccessioning · Legal challenge · Community objection · Repatriation · Political interference · Religious objection · Obscenity · Racial/ethnic sensitivity · Protest art · Copyright/ownership · Conservation · Architectural preservation · Demolition · Design controversy · Adaptive reuse · Landmark dispute · Historical erasure · Geopolitics · Security failure · Labor dispute · Institutional crisis · Political art · Resistance · Migration · Authenticity · Indigenous rights · Defamation · Art flipping · Financialization · Art market fraud · Market opacity

New tags may be added when a case cluster warrants (e.g., Artist safety, Campus censorship).

---

## 5. Pre-scan protocol (run before every scan)

1. **Full tracker read.** Read the INDEX sheet to build the entry index and identify all `[FOLLOW-UP PENDING]` flags. Reach into the main Sheet only for full detail on a specific entry. Append any rows from the prior session not yet reflected in INDEX. Must cover all rows, not just recent ones.
2. **Next-ID confirmation.** Highest existing parent number + 1 = next available. Don't assign until the full read is complete.
3. **Dedup check.** Before drafting any new entry, confirm the story isn't already present as a parent or sub-entry. If it is, draft a sub-entry (e.g., 011-A), not a new parent. When uncertain, default to a sub-entry and note the relationship. This check takes priority over drafting speed.

---

## 6. Daily scan — currency-first method

**The build-session correction: currency was the main weakness. Do NOT rely on web search alone — search trails live publication by hours and misses same-day front-page stories.** Wrap the steps below around the whole scan:

- **Fetch known sources directly first** (homepages/section pages), then search for everything else.
- **Date-anchor every discovery query** with today's actual date.
- **Run a recency sweep** — explicitly hunt for what published in the last 24 hours and isn't yet logged.
- **Cross-reference against existing cases** — a new ruling on a tracked case is a stage update, not a new entry.
- **Report what couldn't be reached** — name blind spots plainly ("couldn't reach Courthouse News today"; "scanned at 6am, later items appear tomorrow"). Silence must never read as "nothing happened."

### Part 1A — Outlet scan (every day)

Fetch each at 8,000–10,000 tokens, scan **all** headlines, pull anything plausibly tracker-relevant, cross-check against the index before logging (a hit may be an update, not a new entry). Output a count: "X scanned, Y relevant, Z already logged, W new." Thin headline-only entries are fine — flag for enrichment on the relevant trawl day.

Outlets (union of both instruction sets):
- Hyperallergic — https://hyperallergic.com
- The Art Newspaper — https://www.theartnewspaper.com
- ARTnews — https://www.artnews.com (artnews.com, **not** artnet)
- NYT Arts — https://www.nytimes.com/section/arts (direct fetch blocks reliably; substitute targeted `web_search` for "nytimes.com arts [topic] [date]")
- Artforum, Frieze, Courthouse News, The Guardian (culture)
- Rotating non-anglophone sources (Hungarian, Italian, others per trawl day)

Check the newest item's timestamp during the scan; a pre-today timestamp is a staleness signal — compensate with outlet-scoped search.

### Part 1 — Dragnet (every day)

Broad multilingual sweep for the past 24 hours. Languages: English, Spanish, Portuguese, French, German, Italian, Arabic, Mandarin. (Sunday = all languages.) Log even thin; enrich on the trawl day.

- **English:** art controversy, mural removed, censorship art, exhibition canceled, monument debate, museum protest, historic building demolished, landmark preservation dispute, architecture controversy, heritage building threatened, public sculpture controversy, public art removed, artwork relocation demanded, public art objection, sculpture planning objection, artwork damaged, sacred site damaged, archaeological site damaged, heritage site vandalized
- **Spanish:** controversia arte, mural removido, censura artística, exposición cancelada, monumento debate, edificio histórico demolido, patrimonio arquitectónico amenazado, escultura pública polémica, obra de arte retirada
- **Portuguese:** controvérsia arte, mural removido, censura artística, exposição cancelada, edifício histórico demolido, patrimônio arquitetônico ameaçado, escultura pública polêmica, obra de arte removida
- **French:** controverse art, censure artistique, exposition annulée, fresque polémique, bâtiment historique démoli, patrimoine architectural menacé, sculpture publique polémique, oeuvre d'art retirée
- **German:** Kunstskandal, Zensur Kunst, Ausstellung abgesagt, Denkmal Kontroverse, Denkmalschutz Kontroverse, historisches Gebäude Abriss, Kunstwerk entfernt, öffentliche Skulptur Streit
- **Italian:** controversia arte, censura artistica, mostra cancellata, murale rimosso, edificio storico demolito, patrimonio architettonico minacciato, scultura pubblica polemica, opera d'arte rimossa
- **Arabic:** جدل فني, رقابة فنية, إزالة جدارية, هدم مبنى تاريخي, تراث معماري مهدد, جدل نصب عام, إزالة عمل فني
- **Mandarin:** 艺术争议, 审查艺术, 壁画拆除, 展览取消, 历史建筑拆除, 建筑遗产争议, 公共雕塑争议, 艺术品拆除

### Part 2 — Trawl (rotates daily; a rule, not a suggestion)

Stick to the scheduled region. If something erupts elsewhere, the dragnet catches it. The rotation guarantees no region is skipped.

- **Monday — Latin America** (Spanish, Portuguese). Regional outlets, cultural ministries, local papers. Look for: street-art disputes, indigenous repatriation, political murals, gallery censorship, monument controversies. (Watch the Milei governance pattern across entries.)
- **Tuesday — US Local (South, Midwest, Mountain West)** (deep-local English). City council agendas, campus papers, regional arts councils, state funding disputes, historic-preservation commissions. Look for: public-art commissions, school/library challenges, VARA claims, state funding cuts, Section 106 reviews, landmark disputes; community objection to murals/public art; neighborhood disputes rooted in racial/ethnic/religious sensitivity; unauthorized/community-initiated art generating identity conflict; public art in gentrifying neighborhoods. **Richmond/VA standing search:** Richmond Times-Dispatch, Style Weekly, Richmonder.org, RVA Magazine, The Richmond Seen, WRIC, WTVR, WWBT — extend to Norfolk, Charlottesville, VA General Assembly, campus art at VCU/UVA/VA Tech. (Richmond Free Press defunct Feb 2026.) Direct classroom utility.
- **Wednesday — Europe, UK, Francophone Africa** (French, German, Italian, Dutch, Spanish-for-Spain). EU national/regional outlets; French-language African outlets (Senegal, Côte d'Ivoire, DRC, Cameroon). Look for: repatriation disputes, deaccessioning, memorial controversies, EU cultural policy, religious-objection cases, postcolonial disputes, human-remains repatriation. **Hungary de-Orbánization standing search:** leadership changes, restored funding, reversed policies, artist-accountability debates.
- **Thursday — Asia & Pacific** (Mandarin, Japanese, Korean, Indonesian). **Mandatory non-Latin-script passes: ZH/JA/KO.** Look for: censorship under authoritarian regimes, exhibition cancellations, political-art suppression, religious/ethnic sensitivity.
- **Friday — US Local (Northeast, West Coast, territories)** (deep-local English). Same as Tuesday's categories plus tech-art/AI-art disputes, public art in gentrifying neighborhoods, historic-preservation agendas.
- **Saturday — Middle East, non-Francophone Africa, South Asia** (Arabic, Turkish, Farsi, Hindi, Swahili, Amharic, Lusophone Portuguese). **Mandatory non-Latin-script passes: AR/FA/HI.** Look for: blasphemy cases, political censorship, art under authoritarian rule, postcolonial repatriation, conflict-zone cultural destruction, East African disputes.
- **Sunday — Synthesis & pattern review.** Standard dragnet, then review the week: patterns, escalations, coverage gaps, parent-ID connections, Dissensus theme relevance, governance distribution, emerging tags. **Systematic sweep of ALL `[FOLLOW-UP PENDING]` flags** — attempt to resolve/update every flagged entry, not just the ripe ones.

### Part 3A — Follow-up flag sweep (every day, before Part 3)

The `[FOLLOW-UP PENDING]` flag is prepended to the Notes field of any entry whose Outcome/Status speculates about what happens next (pending litigation, planned events, anticipated developments, enrichment needed) where no sub-entry has confirmed resolution.

1. Identify all flagged entries.
2. Assess which are ripe (elapsed time, case type).
3. Search updates for the ripe ones.
4. On resolution/significant development: log a sub-entry, update the parent's Outcome/Status, and **remove the flag from the parent's Notes**.
5. No resolution → leave the flag. Don't search every flag exhaustively every day (except Sunday).

**Adding a flag:** any time a status note speculates about a future development, prepend `[FOLLOW-UP PENDING]` at the time of writing. **Removing a flag:** only when a sub-entry confirms resolution or the development is definitively closed.

### Part 3 — Active case updates

Check for updates on tracked cases. Format to the column schema. Flag anything that's an update to an existing entry (give it the parent ID) rather than a new controversy. Apply any `[WATCH]` items from the opening message *in addition* to the standard sweep.

---

## 6A. Source ingestion architecture (feeds & APIs)

This section governs how sources are *ingested*, especially once the scan runs unattended in Claude Code. The principle that makes an automated scan robust: **the agent hits structured feeds and APIs, not a browser.** No headless Chrome, no HTML scraping, no paywall/bot-wall interception — first-party endpoints survive site redesigns and can run unattended. The "approve dredged cases over coffee" workflow effectively requires this model; a browser-driven scan can't self-run.

### Ingestion priority (most → least robust)

**Tier 1 — Official APIs (prefer these).**

- **The Guardian — Open Platform Content API.** The standout: returns **full article body text**, not just snippets, plus tags and section data, across all content since 1999. Free key, no credit card, generous limits (~500 calls/day on the standard free tier; 12 req/sec). **Non-profit projects use the content free; commercial use needs a separate key** — the Index is non-commercial, so it qualifies cleanly. This is the best single input we have. Endpoint family: `content.guardianapis.com`. Store key as env var (`GU_API_KEY`).
- **New York Times — Developer API.** Free key. Three endpoints map onto the protocol: **Times Wire** (real-time publish stream → recency sweep), **Top Stories** with the `arts` section (section front page), and **Article Search** (query by topic + date → date-anchored discovery). **Critical constraint: the NYT API returns metadata only** — headline, byline, abstract, keywords, date, and the canonical URL. **It does NOT return full body text; the paywall sits on the body.** That is sufficient for detection and citation: log the thin entry from the abstract, store the URL as the primary source. Full-text reading stays a manual enrichment step done with a personal subscription. Personal/non-commercial terms — the Index qualifies; read the terms once.
- **Courts — CourtListener REST API** (Free Law Project). Use this instead of scraping PACER or Courthouse News. Free, covers US federal dockets, supports saved-search alerts. It's the robust, automatable version of the legal monitoring already done by hand (and the same source already used for docket PDFs). This is also what brings the public methodology's "PACER / Courthouse News" claim into line with what the scan actually does.

**Tier 2 — Official RSS (keyless fallback, stable).**

- **NYT official section feeds** (Arts; Art & Design) — keyless backup to the NYT API if the key dependency is ever dropped for that source.
- **Trade press native feeds** — Hyperallergic, ARTnews, Artforum, Frieze, The Art Newspaper are all feed-publishing platforms. Pull their native `/feed/` rather than scraping the homepage.
- **BBC Culture** RSS.

**Tier 3 — Direct HTML fetch (fragile edge, only where no feed/API exists).** Some general press (Le Monde, El País, Der Spiegel). Accept metadata-level detection here; these are the brittle inputs and should be flagged as such in any "couldn't reach" report.

### Do NOT route through third-party feed generators

Avoid rss.app, Feedspot, RapidAPI wrappers, and similar middlemen. For a self-running instrument meant to last, a paid intermediary in the ingestion path is a recurring cost and an added failure point between the Index and a source it can hit directly.

### Implementation notes for the Claude Code build

- Keep all API keys as environment variables on the personally-owned laptop — **never commit keys to the repo.** (Same hardware-hygiene logic as keeping the automation off the VCU machine.)
- The agent date-filters feed/API items to the last 24 hours, dedups against the repo case store, and **queues candidates for approval** — it never auto-publishes (the editorial gate in §10 still governs).
- Detection ≠ enrichment. The agent only needs headline + abstract + URL to surface a candidate; full-text reading (NYT especially) remains a manual enrichment pass.

### Source reliability and framing discipline

*Observer vs. participant.* Judge a source per-story, not by standing political label. When an outlet is a participant in a controversy — it broke the story, is campaigning on it, or is itself a party to the dispute — record its role and its reporting, but do not adopt its framing as the Index's voice. Cite quotes to the outlet that carries them. Record who broke a story even when they are a participant. This applies to outlets of any ideological lean.

*Reliability is a track-record judgment, not an ideological one.* An outlet's editorial lean does not by itself change how its reporting is treated. What changes it is documented practice: fabrication, uncorrected falsehoods, repeated regulatory findings, or failed independent fact-checks.

*Excluded sources.* Some outlets have a documented record poor enough that the Index does not cite them or treat them as evidence at all — not as a sole source, not as corroboration. Editorial lean is never the basis for exclusion; documented practice is. Consequence for inclusion: a putative controversy evidenced only by an excluded outlet does not clear the inclusion bar — a story one of these outlets breaks and no reliable outlet picks up is more likely evidence of that outlet's outrage than of a real controversy.
- **Breitbart** — deprecated as a source by Wikipedia (2018) for unreliability; rated "Questionable" by independent media-reliability assessors, with failed fact-checks and a documented history of false and misleading stories.
- **GB News** — least-trusted of the UK's main news broadcasters in trust polling; an upheld, fined Ofcom due-impartiality breach (£100,000, 2024); a documented instance of airing false claims unchallenged.

*Narrow exception.* Where an excluded outlet is itself the subject or actor in a controversy independently established by reliable coverage, it may be named (and linked if necessary) as the object of description — never as a source for asserted facts, and never as what makes a story includable.

*Default disposition (everything not named).* The Index does not maintain a global registry of source quality. For any source not on the excluded list, trust is established per-story by corroboration, not per-outlet by reputation. A controversy resting solely on a single source that cannot be vouched for is logged thin and flagged single-source/unverified rather than stated as fact. The unit of evaluation is the story, not the outlet.

*Aggregators and syndicators.* Aggregator/wrapper domains (e.g., Yahoo News, MSN, inkl, Ground News) are not primary sources and are not cited as such. Trace the item to its originating outlet, cite that outlet, and evaluate it by the normal standard. An aggregator's own originated content is held to the same corroboration bar as any other single source.

*Retrieval limits.* A negative result from a retrieval tool known to be blocked or paywalled for a given source (e.g. automated fetches of the Guardian, Telegraph, Independent, or Washington Post) is recorded as "could not retrieve," never as evidence that the coverage or fact does not exist. Confirm absence through an unblocked path — a manual browser check, an API, or syndication — before treating something as uncovered or unverified.

> [OPEN — post-build] Expand the excluded-sources list beyond Breitbart and GB News. Each addition gets the same treatment: named, documented basis, then written in — no seeding from reputation. Candidates to verify when the time comes: state propaganda outlets (RT, Sputnik), fabrication-driven fringe sites (InfoWars-type), Wikipedia-deprecated tabloids (Daily Mail).

> [OPEN — post-build] Extend reliable canonical-URL retrieval to the paywalled outlets the tools can't reach (Guardian, Telegraph, Independent, Washington Post, etc.). guardian_api.py already covers the Guardian via the Open Platform API; evaluate API or feed access for the others, or adopt a documented "verified via syndication, canonical URL pinned by hand" convention so entries never carry placeholder or aggregator URLs.

A source joins the excluded list only with a specific, documentable basis; the list is revisited as evidence warrants, and the standard is symmetric across the spectrum.

---

## 7. Inclusion

**Threshold — err toward showing MORE.** When unsure, surface as a flagged, unstaged candidate rather than dropping it. False positives cost ten seconds to prune; false negatives mean the Index missed something. Borderline social-media-visible controversies that haven't reached major press get flagged for editorial judgment, not discarded — that early edge is a strength.

**Criteria.** A controversy qualifies when it: has art/artist/institution/cultural policy as primary subject; has a documented dispute between identifiable opposing parties; has a traceable public record; and extends beyond ordinary criticism (a negative review is not a controversy; a work removed under organized pressure is).

Additional standing principles:
- A story belongs when the cultural object/space is the **actual contested thing**, not mere backdrop for a financial/legal dispute.
- Accidental damage warrants a watch entry when aftermath financialization can turn an object contested (e.g., shattered shards becoming collectible).
- Analytically relevant non-controversy entries are allowed as cluster anchors (e.g., repatriation resolutions).
- Vandalism: anonymity of the actor is constitutive, not thinness. Test = target significance and aftermath, not party identification. Do not require a named contesting party to log.

---

## 8. Sourcing rules

- Every proposed case or stage change MUST carry a real, fetched, verifiable source link. If it can't be sourced, flag for investigation — don't propose it.
- **Sources are the evidence/phenomenon itself** — press coverage, legal filings, institutional statements, social reaction. The public-discourse record IS the primary source, not a citation supporting a claim.
- **Wikipedia does not qualify** (tertiary, outside the discourse). A Wikipedia hit is a flag to go find the real coverage it summarizes.
- Capture **multiple outlets** where coverage is wide — breadth is itself a data point indicating scale.
- When secondary sources diverge from primary, **primary text governs**. Distinguish stated rationale from editorially framed rationale (note when an angle is the outlet's, not the actor's).

---

## 9. Staging system (assign at logging time)

- **1 · Watching** — emerged, monitored, no organized response yet
- **2 · Escalating** — organized public response (petition, protest, boycott, campaign), no formal decision/legal action yet
- **3 · In process** — formal institutional/government response or legal proceedings underway; outcome undetermined
- **4 · Active** — active litigation, significant institutional action, or government intervention producing ongoing developments
- **5 · Resolved** — documented conclusion (settlement, ruling, decision, reinstatement); doesn't require all parties satisfied

The 3-vs-4 boundary operationalized as: "has a consequential, hard-to-reverse act occurred (4), or is everything still pending (3)?"

---

## 10. Editorial / publishing model

- Quarterly cadence keyed to **solstices/equinoxes** (Summer/Autumn/Winter/Spring), not fiscal quarters. Issue No. 1: Summer Solstice, June 21, 2026.
- The live database updates **only on editorial approval**. Data is captured continuously, published on review. The site discloses its freshness ("last reviewed and published: [date]").
- **Never auto-publish unreviewed scan output** — the approval gate is what makes the Index citable rather than a feed.
- Name: The Dissensus Index (Rancière's term, the opposite of consensus). Tagline: "A quarterly record of art controversy." Imprint: Fire Horse. License: CC BY 4.0.

---

## 11. Session opening & active monitoring

The `[FOLLOW-UP PENDING]` flags are the standing active-monitoring list; pull them in the pre-scan and Part 3A. No separate "on the horizon" list needed.

**Opening convention:** The opening message is the date and day of week, which triggers the full protocol. Optionally one or more `[WATCH]` flags may be added for elevated-attention items that session. `[WATCH]` items are searched *in addition to* the full protocol, never instead of it. If there are no `[WATCH]` items, the opening is just the date and day, and the full protocol runs without prompting.

---

## 12. Quick-add protocol

When the maintainer pastes a link or describes something they saw, fetch it, assess fit, dedup, assign the next available ID if new, and write the full entry to the column schema without requiring further instruction. Ask for any context they have (source, how they found it) only if needed.

---

## 13. Operational notes

- **Always use exact dates**, never relative time ("April 13, 2026," not "yesterday"). Temporal fluency is unreliable — a known limitation.
- **Keep all cases permanently.** Resolved cases still get appeals, retrospectives, or inspire new incidents.
- **Two-pass enrichment:** a thin dragnet entry when it breaks, enriched on the relevant trawl day with local sources and original-language reporting. Thin entries with sparse English coverage may be the most interesting in the database — log them.
- **Governance hypothesis to track:** religious-objection controversies may cluster in diverse democracies rather than theocracies (theocratic censorship is pre-emptive and structural). The governance column exists partly to test this.
- **Coverage geography ≠ English-language pickup.** A story across Latin American or Asian-language outlets is international coverage within a regional ecosystem, even with no Anglophone pickup. The column captures how stories move across media ecosystems.
- **Dedup must cover all rows, not just recent ones.** Use `str.contains` with `regex=False, na=False`; manual review for short terms.

---

## 14. Analytical frames (apply consistently across entries)

- **Governance friction** — track friction, not just type. Highest controversy volume where current governance conflicts with established cultural norms: democracies under illiberal pressure, authoritarian states with liberal cultural histories (Turkey, Singapore, Russia), transitional states. Absence in consolidated authoritarian systems signals pre-emptive censorship, not its absence. Governance trajectory annotation for democracies trending authoritarian.
- **Externalised censorship** — produced by supply-chain compliance, procurement, or funding conditionality rather than direct order (V&A catalogue, EU/Venice funding withdrawal).
- **Soft censorship architecture** — institutional self-censorship from anticipated consequences, with no external actor's direct instruction.
- **Anticipatory obedience** — capitulation before any formal order is issued.
- **Curatorial adaptation vs. ideologically driven alteration** — legitimate curatorial adjustment vs. change to avoid political consequence.
- **Iconoclasm taxonomy** — top-down (Gamboni) / bottom-up (Gamboni) / lateral (warfare/peer-actor damage). Fluid analytical tools, not rigid bins.
- **Cross-entry connections** — reference parent IDs explicitly; track patterns across cases (e.g., Milei pattern across Latin American entries; war-destruction clusters sharing a broad tag + cross-reference line).

---

## 15. Communication preferences

Direct, compression-oriented, humor-forward. No directive sign-offs ("go pick up your kid," "go to bed," "now go crush it"). Break reminders welcome in long sessions if explicitly requested. Don't close conversations with orders about what to do next.

---

## 16. Current status & roadmap

- Site live (dissensusindex.com / .org → .com), built from `cases.json` (snapshot of the spreadsheet). Netlify auto-deploys from `github.com/rsxhoxhi/dissensus-index`.
- ~392 cases staged as of June 2026 (working master continues to grow beyond this).
- Manual workflow: scan in chat → convert → browser-upload to GitHub → Netlify deploys.
- **Now → June 21:** two launch essays (Hungary as leading indicator; legal cases resolve while governance fights fester); About-page own-voice rewrite; lock methodology v1.0; ISSN application (LoC, free); Internet Archive snapshot; pre-launch data re-sync; announce.
- **July (after personal laptop):** Claude Code on owned hardware → repo migration (data into a store the scan agent reads/writes) → implement the §6A feeds/APIs ingestion layer (Guardian Open Platform + NYT Developer API + CourtListener, keys as env vars) → formalize this file into the repo's executable scan protocol → self-running daily scan → approve-dredged-cases briefing workflow. (Build the automation/data layer on personally-owned hardware to keep "significant use of university resources" off the table.)
- Once §6A ingestion is live, reconcile the public methodology source list to match (name the Guardian/NYT APIs and CourtListener); add the Zenodo DOI-per-release line noted on the methodology page to this status block.
- File-handling specifics for the spreadsheet master (openpyxl full-workbook reconstruction, column widths, INDEX yellow-fill for flagged rows, dedup pattern) are documented in working memory and should be captured into the formalized scan-protocol file during the July buildout.
