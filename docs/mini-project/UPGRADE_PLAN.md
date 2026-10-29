# FootIQ upgrade plan: synchronisation, gameweek forecasts, season simulations, redesign

Status: **PLAN FOR REVIEW. Nothing in this plan has been implemented.** No source was contacted, no model touched, nothing staged or committed.
Prepared 2026-10-25 from an inspection of the repository (files read, plus counts recomputed from existing CSVs). Figures marked *measured* were recomputed today; figures marked *recorded* come from the project's earlier source-research reports and have not been re-measured.

Non-negotiables carried over from your brief: frozen models (club v1, club v2-r1, international v2.7, World Cup simulator) are never retrained, replaced or modified; the prospective-evaluation protocol is not changed and official logging is not activated; no unapproved live source is switched on; synthetic fixtures, player data, xG, events, live scores or crests are never invented; nothing is committed or pushed without your approval.

---

## 0. Where we stand (the facts that shape the plan)

| Fact | Evidence |
|---|---|
| The app's results end on **2026-09-20**, 35 days before today. | `data/miniproject/matches.csv` (measured) |
| **96 matches in the five leagues are already played but missing**: Premier League 20, La Liga 20, Serie A 20, Bundesliga 18, Ligue 1 18, all dated 2026-10-09 to 10-19. | `FootIQ_Dataset_Submission/09_Upcoming_Fixtures.csv`, status `past_date_no_result_in_source` (measured) |
| openfootball (the current source) has **no newer upstream commits** (checked 2026-10-21): it is a volunteer repository and lags. | `freshness_validation_r1/00_FRESHNESS_VALIDATION_REPORT.md` (recorded) |
| **The full 2026-27 schedule of all five leagues already exists** in the repo, snapshot 2026-10-15: 1,406 upcoming fixtures from 2026-10-21 to 2027-05-30 (Premier League 310, La Liga 291, Serie A 310, Bundesliga 252, Ligue 1 243). Gameweek prediction does not need a new fixture source today. | measured |
| Fixture detail is thin: kickoff times known for only 7-22% of upcoming fixtures (date only otherwise). | measured |
| **Matchday labels are not always chronological.** La Liga "Matchday 8-9" have unscored past dates while "Matchday 6" is still upcoming on 2026-10-21 (postponed or re-ordered fixtures). | measured |
| **No fixtures exist for UEFA competitions, the Nations League or the World Cup** in the fixtures file (the only cup rows are a Copa Libertadores stub). European gameweek prediction or simulation therefore has no fixture source yet. | measured |
| Previous phases already built and validated reusable ingestion pieces: an OpenLigaDB adapter (Bundesliga), a Wikipedia results-matrix adapter (Premier League), an identity resolver, snapshot store, rate-limited HTTP client and a 17-test suite. `live_enabled` is **false** in `adapters.json`. | `FootIQ_Club_Model_Development_v2/source_adapters_r1/` (recorded) |

---

## 1. Current architecture and reusable components

```
CSV files (research folders, frozen)  ->  app/prepare_data.py  ->  data/miniproject/matches.csv
                                                                      |
 FastAPI (app/main.py)  <-  analytics.py (pandas)                     |
        |               <-  predict.py  -> club state replay (216k matches, ~20 s once, then ms)
        |                                   uses V_universe.pkl (frozen training snapshot, 117 MB, git-ignored)
        |                                   + the research code d11_prospective_logger / v2_features / feature_contract
        |               <-  worldcup_sim.py, bracket.py, performance.py, integrity.py, names.py
React + Vite + Tailwind (frontend/)  -- 6 pages, lazy routes, Recharts
```

Reusable as they are:

| Component | Reuse |
|---|---|
| Frozen models and their feature code (`v2_features.V2State`, `feature_contract.ClubState`, `d11` loaders) | Gameweek predictions. Parity with the original inference code is already tested. |
| `predict._club_state` (replay once, answer many fixtures) | Core of bulk fixture prediction; needs to be rebuilt from a results store instead of a frozen pickle. |
| `source_adapters_r1/footiq_sources` (`common`, `identity`, `openligadb`, `wikipedia_matrix`, `reconcile`) | Sync adapters, snapshot store, rate limiting, identity resolution. Tested; currently disabled. |
| `e3_ingest_results.py` (plan / fetch / parse / replay) | The openfootball path and the "refreshed universe" idea (replay results without touching frozen artifacts). |
| `09_Upcoming_Fixtures.csv` | Initial fixture import for 2026-27. |
| `analytics.standings`, `app/bracket.py`, `worldcup_sim.py` | League table logic, World Cup engine and bracket stay. |
| Frontend: `ui.jsx` (Card, Badge, Tabs, MatchRow, FormDots, CompareRow, Gauge), `ProbBar`, `Bracket`, `TeamPool`, `CompetitionSelect` | Base of the redesign. |

Not reusable as is: the frozen universe is a pickle, not a growing store; the dashboard dataset (`matches.csv`) is rebuilt by a script; there is no concept of fixture status, source revision, sync run or forecast history.

---

## 2. Data providers: actual coverage, freshness, permission status

All rows are from the earlier source research (recorded) unless stated.

| Source | Coverage useful to us | Freshness (measured 2026-10-21) | Permission status | Verdict |
|---|---|---|---|---|
| **openfootball** (GitHub, CC0) | All five leagues: results and schedule | Latest result 2026-09-20 everywhere; 31 days behind; fixtures snapshot 2026-10-15 | Verified, CC0 | Keep as schedule and historical reference. **Cannot be the freshness source.** |
| **OpenLigaDB** (ODbL) | Bundesliga validated live (pilot 2026-10-21); other leagues **not verified** (Premier League/La Liga "to be verified") | 3 days; UTC kickoffs; explicit 90-minute result type; per-match `lastUpdate` | ODbL terms read in full in a later phase; needs a contact string in config; ML/commercial wording of the front page was previously UNKNOWN | **Ready for approval for the Bundesliga.** Other leagues blocked until verified. |
| **Wikipedia season pages** (CC BY-SA 4.0) | Premier League validated (50/50 identical, recovered 20/20 missing); 14 other pages unverified | 0-7 days; dates only inherited from the schedule, no kickoff times | Licence read; **share-alike scope for derived data unsettled (your decision)**; needs contact string; a revision-stability rule (two revisions at least 24 h apart) | **Restricted.** Possible for the Premier League, needs your licence decision. Each other league needs its own page validation. |
| **football-data.org** (free tier, 12 competitions) | 12 "top" competitions per its pricing page; which ones is **not verified** (I expect the five leagues and the Champions League, but have not confirmed) | Not measured; vendor says free tier has delayed scores | Terms page returned 404 earlier; **needs an account and API key**; crest-URL licensing unknown | Optional. Only after you read the terms and create a free key. |
| **API-Football** | Broad | Not measured | Terms unread (403); client exists; free quota 100 calls/day; no key present | Optional, same condition. |
| football-data.co.uk, FBref, Sofascore/FotMob endpoints, official league sites, scrapers | n/a | n/a | Prohibited or unknown; not permitted by default | **Do not use.** |

Consequence: **for La Liga, Serie A and Ligue 1 no verified fresh source exists today.** The sync system can be built generically, but those three leagues will honestly show "last result 2026-09-20, stale" until a source is approved (options in section 8).

---

## 3. Missing dependencies, credentials, approvals

| Item | Status |
|---|---|
| Python packages | None required for the core (`httpx` already installed; SQLite is in the standard library). Optional: `apscheduler` is **not** needed (a small asyncio loop is enough). |
| Contact string for the Wikimedia / OpenLigaDB User-Agent | `config/contact.local` exists locally (git-ignored); the pilot used it. Confirm it is still the contact you want sent. |
| API keys | None present. football-data.org and API-Football keys would be created by you after reading their terms. |
| Approvals | (a) live use of OpenLigaDB for the Bundesliga; (b) Wikipedia share-alike decision; (c) any additional provider; (d) crest policy (section 6); (e) database choice. |
| Official league regulations | Needed to encode tie-break rules and European qualification slots correctly (section 5). |
| Crest images | None in the repo; licensing unresolved. |

---

## 4. Database and ingestion design (Phase 1)

### 4.1 Store
Replace "regenerate a CSV" with a single **SQLite** file (`data/footiq.sqlite`, git-ignored, rebuilt from the CSVs if lost). It needs no new dependency, supports idempotent upserts and transactions, and keeps the research CSVs untouched as the immutable baseline.

Tables (core):

| Table | Purpose |
|---|---|
| `competitions`, `seasons` | The 11 competitions; season labels; format metadata (rounds, teams, tie-break profile). |
| `teams`, `team_aliases` | Canonical entity id (the project's existing `CLUB:ENG:arsenal-fc` ids) plus every source spelling; a versioned alias table, never fuzzy-matched silently. |
| `matches` | One row per fixture, **unique on (competition, season, home_entity, away_entity, round, leg)**. Columns: `status` (`scheduled`, `live_unknown`, `completed`, `postponed`, `cancelled`, `awarded`), `kickoff_utc` nullable with `time_precision`, `matchday_label` (source) and `matchday_seq` (chronological order we derive), scores, `result_type` (90 minutes / extra time / penalties), `first_seen`, `last_changed`. |
| `match_sources` | Per match, one row per source reference (openfootball file:line, OpenLigaDB matchID, Wikipedia revid and cell): provenance, licence, retrieval time. |
| `source_snapshots` | Raw payload hash, URL, HTTP status, retrieval time, revision, licence tag (immutable, as in the existing snapshot store). |
| `sync_runs`, `sync_errors` | Start/end, source, requests made, rows inserted/updated/unchanged/quarantined, outcome. This is the "Last updated" truth. |
| `quarantine` | Conflicts and unresolved identities (never silently merged). |
| `forecast_runs`, `forecasts` | Saved gameweek forecasts (section 5.4). |
| `simulation_runs` | Parameters, seed, data cutoff, model versions, result tables. |

### 4.2 Sync flow (your "Proposed data flow", made concrete)

```
backend start
  -> read sync_runs: last successful update per source/competition
  -> freshness check (cheap, read-only): git ls-remote / OpenLigaDB getlastchangedate / Wikipedia revision id
  -> only if something changed: fetch incrementally (changed matchdays only), rate-limited, with User-Agent + contact
  -> raw snapshot saved -> parse -> staging records
  -> validate (dates, scores, status, season, matchday) -> resolve team identities -> reconcile sources
  -> upsert (idempotent) in one transaction; conflicts to quarantine
  -> refresh derived state: standings, form, prediction state (not model weights), forecasts marked stale
  -> write sync_run; UI shows Last updated / Latest match result / Source
```

Rules:
* **Backend only**, in the FastAPI lifespan; React never calls providers.
* Startup sync runs **in the background** so the app opens instantly; the UI shows the sync state. While the backend runs, a low-frequency loop (default every 60 minutes, only when a match could have finished) repeats the cheap freshness check. Per-source limits: at least 3 s between requests (as in the pilot), at most the quotas in `adapters.json`, exponential back-off on 429/5xx, hard timeouts, circuit breaker after repeated failures.
* **Idempotent**: re-running an import changes nothing (verified by tests that import the same payload twice).
* **Fallback**: provider down or rate-limited -> serve cached data, mark the source `stale` with the age, never label it live. The words "live" are used only if a source actually reports an in-play status (none of the approved sources is used for live scores in this plan).
* **Statuses kept apart**: completed results, scheduled fixtures, postponed/cancelled/awarded matches never share one "result" field.
* **Visible timestamps** on every data page: *Last updated* (last successful sync), *Latest match result* (max completed date), *Source* (per competition, with licence).
* **Updating results never retrains or alters a model.** New results only extend the historical state (Elo, form, rest days) from which frozen weights produce probabilities. The frozen artifacts' hash check in `/api/meta` stays and is run after every sync.

### 4.3 What a sync can and cannot deliver today
| League | Source for fresh results | Expected state after Phase 1 |
|---|---|---|
| Bundesliga | OpenLigaDB (validated) | Current (about 3 days lag) once approved |
| Premier League | Wikipedia matrix (validated, restricted) or OpenLigaDB if verified | Current if you approve the licence route, else stale |
| La Liga, Serie A, Ligue 1 | none verified | **Stale, shown as stale**, until a source is approved |
| Schedule for all five | openfootball snapshot (fixtures to 2027-05) | Present; kickoff times mostly unknown |

Even with a source, a result that is "yesterday's" is only as current as that provider; the UI always shows the actual newest completed date per competition.

### 4.4 Verification criteria (Phase 1)
1. Importing the existing CSVs into SQLite reproduces the current `matches.csv` exactly (row counts per competition, team names, scores); predictions rebuilt from the store equal today's predictions to 1e-9 (parity test as before).
2. Replaying the pilot payloads yields the recorded results: Bundesliga 54 completed, 18 newly recovered, 0 conflicts, 0 unresolved identities.
3. Same payload twice -> zero changes; a corrected score updates one row and logs the change; a conflicting source goes to quarantine.
4. Provider outage test: sync fails, API serves cached data with a stale flag and age.
5. No request is made when `live_enabled` is false; request ledger shows host, count and spacing for every real run.
6. Frozen-artifact hashes unchanged before and after sync.

---

## 5. Prediction and simulation architecture

### 5.1 Time-safe gameweek predictions (Phase 2)
* **Gameweek definition.** Use the source's `matchday_label`, but expose the **date range** and flag fixtures whose date is out of order for their label (La Liga case). Selector: competition, season, gameweek, showing "8 Nov - 10 Nov".
* **State.** Rebuild the club state from the store through the data cutoff (latest completed result), as the current app does from the pickle. Every fixture is featurised **only from completed results dated strictly before that fixture's date** (the existing `features_for` rule). A fixture is never given information from a match that finishes later; a test shuffles future scores and asserts identical probabilities.
* **Bulk action.** One call returns all fixtures of a gameweek: about 10 fixtures at about 40 ms each. Both v1 (primary, validated for the five leagues) and v2-r1 (experimental, development-only) are returned, as now.
* **Uncertainty flags per fixture** (so the UI can be honest):
  * `unresolved_prior_matches`: fixtures of either team dated before this fixture that are completed in reality but missing from the store (the 96 missing matches today). Probabilities are then built from an older state.
  * `days_after_cutoff`: how far the fixture is beyond the latest data (reuse the existing 180-day note; add a staleness tier "standard / extended / low confidence" mirroring the earlier protocol's 14-day rule; this is an app label, not evaluation logging).
  * Missing identity, fewer than 5 earlier matches, unconnected Elo graph, unknown kickoff (date-only).
  * Fixtures that cannot be predicted (unresolved team, status postponed/cancelled) are listed, not hidden.
* **Static versus rolling forecasts.** Gameweeks beyond the next one use the state at the cutoff (results of the intervening gameweeks are unknown). This is stated on the page; a fully rolling "what-if" forecast belongs to the simulator, not the fixtures page.
* **Comparing with actual results.** When a result arrives the card shows predicted versus actual. To compare fairly, a forecast must be **saved at the time it was made** (`forecast_runs`: model version, data cutoff, feature hash, creation time). Forecasts created after kickoff are marked "after the fact". This is a plain app history; it is *not* the pre-registered prospective evaluation and is labelled as such. **Decision for you:** save forecasts automatically per gameweek, or only when the user presses "Predict gameweek" (recommended: only on user action, to stay clearly separate from official logging).
* **Manual team-versus-team prediction stays**, unchanged, on the same page as a second mode.

### 5.2 Domestic league simulation (Phase 3)
* Inputs: the store's completed matches (current table), remaining scheduled fixtures, per-fixture H/D/A probabilities from the frozen model at the cutoff.
* Method: for N simulations (default 10,000, seeded, configurable), sample each remaining result from its probabilities, accumulate points, apply the league's tie-break rules, record the final position.
* **Goal difference problem.** The models give only 1X2. Tie-breaks and goal-based rankings need scores. Proposed assumption: sample the outcome first, then a scoreline from independent Poisson goals using the v2 feature generator's expected goals (`lambda_home/away`), conditioned on the outcome. This is an **explicit modelling assumption, shown on the page**, and it affects only tie-breaks and goal-difference ordering.
* **Static probabilities.** Per-fixture probabilities are fixed at the cutoff and are not re-rated as simulated results accumulate. This slightly understates how results feed back into strength and is stated as a limitation; an optional dynamic-Elo mode can be added later and compared.
* **Rules per league are configuration, sourced from official regulations before implementation** (I will not rely on memory): points, then league-specific tie-breaks (goal difference, goals scored, head-to-head criteria differ by league and have changed over time), and play-off rules. Each league's rule profile is unit-tested on constructed tables including multi-team ties.
* **Qualification and relegation** are configurable position bands per league and season (title, top four, European places, relegation positions). Because European slots depend on UEFA allocations that vary by year, outputs are described as "finishing in positions 1-4" rather than "qualifying" unless the rule is sourced.
* Output: predicted final table (expected points with a 10-90% interval), position-probability matrix, title / top-four / relegation probabilities, plus simulation count, seed, assumptions, model version, data cutoff, and a warning when results are missing (today the three stale leagues).
* Verification: (1) with zero remaining fixtures the result equals the real table with probability 1; (2) probabilities sum to 1; title probabilities sum to 1; (3) same seed -> identical output; (4) tie-break unit tests; (5) a backtest on a finished past season: simulate from a mid-season cutoff and check calibration of title/relegation probabilities against what happened (reported as historical evidence with the usual caveat); (6) convergence: the change in probabilities between 10k and 50k simulations is within sampling error.

### 5.3 European competitions (Phase 5, experimental)
* **No fixture source exists today** (measured). First task is a source decision, then a format engine.
* Format logic needed: league phase table (36 teams, 8 matches each, top 8 direct, 9-24 play-off), seeded two-legged ties, aggregate scores with extra time and penalties, draw rules, and the different formats of Europa and Conference League. These are built as data-driven configs reviewed against UEFA regulations.
* The club models were **never validated on UEFA competitions** and Elo across leagues forms disconnected islands. All outputs carry the existing "Not validated (indicative only)" badge plus an "Experimental" tag, and cross-league Elo caveats.
* The International Nations League and Copa America would reuse the international v2.7 model only if a fixture source is approved; the World Cup engine and the real bracket stay as they are.

### 5.4 Forecast history
`forecasts` rows link to a `forecast_run`, never overwrite, and store the model id and artifact hash. This table supplies "predicted vs actual" and a small running scoreboard (accuracy, log loss with sample sizes) clearly labelled "since this app started saving forecasts".

---

## 6. UI redesign plan

**Reference note.** Your message mentions three attached images and says the third is primary; only two images came with this message (a proposed data-flow diagram and a "fixture predictions" layout with sample teams). I am treating the dark-purple dashboard from your earlier reference set (sidebar, spacious cards, club-crest hero, two-column home) as the primary style and these two as flow and layout guidance. **Please confirm which image is "the third" if I have this wrong.** The design is inspired by, not copied from, any reference: FootIQ branding, our own copy and colours.

### 6.1 Navigation
Sidebar: **FootIQ** brand, Home, Matches, Leagues, Compare, Predictions, Simulations, Models. Mobile: bottom tab bar (as now) with the same seven sections or "More". The existing pages map as: Overview -> Home; Leagues -> Leagues; Compare -> Compare; Predict -> Predictions (gains Gameweek and Manual tabs); World Cup -> Simulations (gains League simulator); Models stays.

### 6.2 Page plans (only real data)

| Page | Content | Appears only when data supports it |
|---|---|---|
| **Home** | Featured upcoming fixture (next scheduled in a chosen league, with the model's H/D/A), latest completed results, upcoming fixtures, standings snapshot, title-race mini chart from the latest simulation, sync status bar | Fixtures/forecast cards need the store; "Top scorers" **omitted**: the repo has no reliable scorer data for these leagues |
| **Matches** (new) | Date strip, results and fixtures by competition, status chips (completed, scheduled, postponed), source/updated footer | Kickoff time only when known; otherwise date |
| **Leagues** | Standings with form column, matchweek selector, results, fixtures, season stats | Club crests only if licensed (below) |
| **Compare** | As now, plus model-input bars | |
| **Predictions** | Gameweek mode: league, season, gameweek, "Predict gameweek", cards with H/D/A bar, flags and, after play, actual result; Manual mode (existing); detail page with gauges, Elo, form, v1 vs v2-r1 | Unpredictable fixtures listed with the reason |
| **Simulations** | League season simulator, World Cup simulator and bracket, European (experimental, later) | |
| **Models** | As now plus forecast scoreboard (once saved forecasts exist) | |

New shared components: `SyncStatusBar`, `FixtureCard`, `GameweekSelector`, `FlagChip` (missing/uncertain data), `StandingsTable` (crest slot, form, position bands), `PositionProbabilityMatrix`, `TitleRaceChart`, `AssumptionsPanel` (simulation count, seed, cutoff, model versions). Existing `ProbBar`, `Gauge`, `CompareRow`, `MatchRow`, `Bracket` are reused.

### 6.3 What is deliberately not drawn
Player statistics, scorers, xG, possession, match events, live indicators, momentum charts, transfers: **absent** because the data does not exist. If a provider is later approved and delivers them, each widget is added behind a "data available" check with attribution.

### 6.4 Club crests
Club badges are trademarked and no licensed crest set is in the repo. Options, in order of recommendation: (1) keep generated initials badges (current); (2) a crest pack you supply with rights to use, placed in `frontend/public/crests/<entity-id>.png` and picked up automatically; (3) provider-supplied crest URLs only if that provider's terms allow it. I will not scrape or hotlink crests.

---

## 7. Phased roadmap, risks, verification

Order follows your advice (data before design), with one change: the visual shell can proceed in parallel with Phase 2 because it only restyles existing pages.

| Phase | Work | Effort (rough) | Main risks | Done when |
|---|---|---|---|---|
| **0 Decisions** | Answer section 8 | 0.5 d (you) | Wikipedia share-alike; provider terms | Decisions recorded |
| **1 Store and sync** | SQLite schema, CSV import with parity, adapters wired into the backend (OpenLigaDB for BL, Wikipedia for PL if approved), sync runs, stale fallback, status endpoint and UI bar, tests | 5-7 d | Source gaps for 3 leagues; identity mismatches; provider format change | Section 4.4 criteria pass; Bundesliga current after one sync |
| **2 Gameweek predictions** | Fixture import, gameweek API, bulk prediction, flags, forecast history, predicted-vs-actual, Predictions page | 4-5 d | Non-chronological matchday labels; missing prior results; kickoff times unknown | Time-safety test passes; every fixture either predicted or listed with a reason; parity with single predictions |
| **3 League simulator** | Rule profiles per league, scoreline model, Monte Carlo engine, API, Simulations page | 5-6 d | Wrong tie-break rules; goal sampling assumption; static probabilities | Section 5.2 criteria pass, incl. past-season backtest |
| **4 UI redesign** | New shell and pages from 6.2 | 5-6 d | Scope creep into data we lack | All pages show only real data; mobile and desktop verified |
| **5 European** | Fixture source decision, format engines, experimental simulator/predictions | 6-8 d | No fixture source; unvalidated models | Format unit tests; clearly flagged output |
| **6 Later** | Licensed crests, richer stats, live features | open | Licences, costs | Per-feature approval |

Cross-cutting verification: existing 57 backend + 37 frontend tests keep passing; new tests for idempotency, time-safety, tie-breaks, stale fallback and API contracts; browser checks on mobile and desktop; frozen-artifact hashes checked after every phase.

---

## 8. Decisions I need from you before Phase 1

1. **Sources.** Approve OpenLigaDB for the Bundesliga (needs your contact string confirmed). Approve or decline Wikipedia as a results source for the Premier League and your position on its share-alike terms (or "confirmation only, never the sole source"). Do you want me to prepare a verification pass for OpenLigaDB's Premier League / La Liga coverage first?
2. **La Liga, Serie A, Ligue 1.** Accept "stale until a source is approved", or create a free football-data.org key after reading its terms (I can summarise its terms for you to approve, but cannot create the account).
3. **Forecast history.** Save forecasts only when the user presses Predict (recommended) or automatically each gameweek?
4. **Database.** Approve SQLite as the store (CSV stays as the baseline).
5. **Crests.** Initials for now, or will you supply a licensed crest pack?
6. **Which image is the third reference?** (section 6)
7. **Order.** Data first as above, or restyle first?

Nothing starts until you reply. Phase 1 would begin with a read-only design review of the schema and a parity import, with no network access.
