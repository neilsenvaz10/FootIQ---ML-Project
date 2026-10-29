# Phase 4, stage P4.2: Home dashboard, technical implementation report (checkpoint 2)

Written 2026-10-27 on branch `feat/club-ml-v2` (HEAD `970f461`). Plan and decisions: [PHASE4_UI_AUDIT_AND_PLAN.md](../PHASE4_UI_AUDIT_AND_PLAN.md). Previous checkpoint: [P4_1_CHECKPOINT_REPORT.md](P4_1_CHECKPOINT_REPORT.md). Performance investigation (full detail): [P4_2_PERFORMANCE_INVESTIGATION.md](P4_2_PERFORMANCE_INVESTIGATION.md). Endpoint contract: [API_REFERENCE.md](../API_REFERENCE.md).

**Stopped here for your visual review.** P4.3 and later stages have not been started. Nothing was staged, committed or pushed (`git diff --cached` is empty, HEAD is `970f461`, `frontend/` is still untracked). No frozen model, official prospective-evaluation file, football data file, sync setting or scoreline setting was touched, and `data/footiq.sqlite` was only read and hashed (§5.5). The only backend source change is the new read-only endpoint (§3).

## 1. Status

| Stage | State |
|---|---|
| P4.0 Baseline and recovery | Done (checkpoint 1) |
| P4.1 Design system and shell | Done (checkpoint 1; approved by you with the decisions listed in your message) |
| **P4.2 Home dashboard** | **Done.** Home redesigned, `GET /api/featured-fixture` added, `/api/gameweek` slowdown investigated (optimisation proposed, not applied), tests, build, browser checks, screenshots |
| P4.3 to P4.7 | Not started (waiting for your approval of this checkpoint) |

## 2. Your P4.2 list, item by item

| # | You asked for | What is on the page | Checked by |
|---|---|---|---|
| 1 | A prominent featured upcoming match banner from a real stored fixture | `FeaturedMatch`: a gradient card with 72 px badges, club names of 18 px (24 px from 640 px wide) and the day in 24 px (30 px from 640 px wide); it is the first block after the freshness bar and the only gradient card on the page. It shows the first scheduled fixture of the five leagues whose two clubs are matched to identities, read from the store | `home.test.jsx` (focal-point test), live contract test (the featured fixture is a stored row with both clubs matched and is not repeated in `upcoming`), screenshots |
| 2 | Home and away names, TeamCrest, competition, matchday, verified kickoff | Names with HOME / AWAY labels, generated `TeamCrest` badges (no licensed crest exists), competition and matchday chips, day name ("Today", "Tomorrow", "Sat 31 Oct") with the date, and the kickoff exactly as stored: `15:00 UTC`, `18:30 (time zone not stated)` or `time not confirmed`. Never converted, never filled in | `home.test.jsx` (3 kickoff states, day labels), `fixtures.test.js` (14), live test (`kickoff.state` is one of three values and consistent with `utc` / `local`) |
| 3 | Data freshness and provisional status | Chips under the clubs: `Data fresh` / `Data not fresh` with the newest verified result date of that league, and `Provisional history` / `Fully supported history`; a disclosure lists the reasons and flags ("Notes on this fixture's data (4)") | `home.test.jsx` (stale, fresh, flags once each, disclosure opens), probe (contrast on the gradient) |
| 4 | Upcoming fixtures from the five leagues | `UpcomingFixtures`: next six after the banner, grouped by day, each row a link to that fixture's gameweek; league chip, "Provisional" once for the whole list when every row is, "Club not matched" for an unmatched club | `home.test.jsx` (grouping, links, at most six, provisional once or per row, unmatched) |
| 5 | Recent verified results | `RecentResults`: six latest stored final scores with FT / AWD, league and date, one labelled group per row | `home.test.jsx` (scores, FT / AWD, at most six, empty text) |
| 6 | Compact current-season league overview | `LeagueOverview`: one pill per league, the newest season's top six (position, club, played, goal difference, points, form), "Partial season: 60 of 380 matches in the data" when it is partial, the league's freshness, a link to the full table | `home.test.jsx` (6 tests: partial and finished season, switch league, five pills, no season and no results, retry) |
| 7 | Quick access to predictions, gameweek predictions, team comparison, simulations | Four tiles under the banner (2 x 2 on phones), plus "Open gameweek predictions", "Predict a match" and "Compare teams" in the banner | `home.test.jsx` (hrefs) |
| 8 | Desktop, tablet and phone layouts | 1440 px: banner full width, two columns below (fixtures and league overview), three result columns. 820 px: rail navigation, all blocks stacked, two result columns. 375 px: stacked, crests either side of a "vs" pill with the day and time on their own line, full-width buttons | probe at 1440, 820 and 375 px: no horizontal overflow, 0 controls under 44 px, 0 contrast failures; screenshots (§5.4) |

Not on the page by design: no probability or forecast is computed, no `POST` is sent, `/api/gameweek` is never requested, no club or player image other than the generated badges is used.

## 3. Backend: `GET /api/featured-fixture`

Files: `app/featured.py` (new, 210 lines), `app/main.py` (the route, three imports, the cache object and one line that empties it when a synchronisation stores results), `tests/test_featured.py` (new, 27 tests). Contract, fields, rules and caching: [API_REFERENCE.md](../API_REFERENCE.md). In short:

| Requirement | How |
|---|---|
| Lightweight, read-only, efficient | Read-only connection (`mode=ro`); a fixed set of bounded statements: 5 newest-season, 5 upcoming, 5 results (each `LIMIT ?`, at most 12 rows), at most 5 season reads, 1 saved-forecast lookup and the freshness statements (about 35 small ones). Every query is anchored on `idx_matches_key`; a unary plus on `status` and `kind` keeps the planner off the store-wide `idx_matches_status_date` (the cause of the gameweek slowness). No `SELECT *`, no full-table scan, no per-fixture query |
| No `/api/gameweek` | The module does not import or call the gameweek view; eligibility uses `gameweeks.assess` (pure Python) on one season read per league shown |
| Freshness and eligibility | `freshness` follows the `/api/sync/status` rules for the five leagues; every fixture carries `eligible`, `predictable`, `reliability`, `flags`; the featured one also `reasons` and `stale_days` |
| Bounded query and caching | `upcoming` 1 to 12, `results` 0 to 12; 60 s in-process cache keyed by `(comp, upcoming, results, UTC date)`, dropped when the store file changes or a sync stores results; `Cache-Control: private, max-age=60`, `ETag`, `X-FootIQ-Cache: hit \| miss`; `304` for `If-None-Match` |
| Empty state | `featured: null` with `empty_state {code, message}` (`no_upcoming_fixture` or `no_eligible_fixture`); the page says so and never fills the gap |
| Nothing invented | Names, dates, matchdays, sources, scores and kickoff are stored values; `kickoff.state` is `utc`, `local_without_time_zone` or `unknown`; `forecast` is only an already saved one, otherwise `null` |
| No automatic forecasts | No model is imported or called; the test replaces every model entry point with a function that fails and hashes the store before and after |

The 27 backend tests build small stores of fictional clubs and cover: ordering and the featured choice, fixtures that are not upcoming (past, started, postponed), a fixture dated today, unmatched clubs, the two empty states, the league filter, newest season, exact kickoff states, stored-values-only, no model call and no write, a saved forecast passed through, freshness equal to `/api/sync/status`, eligibility parity with the gameweek page (synthetic and on the repository baseline store), stale-history flags, statement count independent of the number of fixtures (40, 380 and 1,500 per league), bounded lists, query plans (`idx_matches_key`, no scan, never `idx_matches_status_date`), a speed guard on a full-size store, the cache (hit, expiry, change, clear, fingerprint) and the HTTP layer (shape, headers, ETag and 304, validation, 503, cache emptied after a sync, never writes).

## 4. Performance

### 4.1 Why `/api/gameweek` went from about 3.7 s to 10.5 s (summary; [full report](P4_2_PERFORMANCE_INVESTIGATION.md))

| | |
|---|---|
| Bottleneck | `gameweeks.team_form`, called twice per fixture (20 times for a gameweek of 10): 5.906 s of the 5.949 s request in the profiled run (99%); timed on their own the 20 calls took 8.81 s against a mean request of 9.66 s |
| Cause in the query | SQLite plans it on `idx_matches_status_date (status, match_date)` and so visits **220,006 completed matches** (every competition in the store) per call to return 5 rows; 13,226 of them belong to the competition (16.6 times as many). No planner statistics exist and there is no index on (competition, team, date). The page's other statements are milliseconds |
| Why it varies | The request is CPU-bound. Idle it takes **2.8 s**; with the CPU oversubscribed twofold (24 busy processes on 12 threads) the same request took **5.8 s**, and 2.8 s again afterwards. One call took 118 ms at best and 633 ms at worst today, so 20 calls take 2.4 s to 12.7 s, which contains both 3.7 s and 10.5 s. The code and the store were unchanged. I did not record what else was running on the 26th and in the afternoon of the 27th |
| Proposed optimisation (**not applied**) | **B:** one planner hint (`INDEXED BY idx_matches_comp_season_date`) in the single statement of `team_form`: 10.1 s to 0.26 s per gameweek, no schema change, output byte-identical (7,008 calls and 10 whole gameweeks compared). **D:** two composite indexes and a `UNION ALL`: 0.02 s, but +29 MB and a schema change to the store. **C:** `ANALYZE`: same plan as B for every statement, but it writes into the store. Recommendation and test plan: report section 5 |
| Test timeout | Not used as a remedy. The live gameweek test is unchanged; with the machine idle the whole live suite passes with default timeouts (that test took 2.5 s); under load the request exceeds 5 s again until the optimisation is decided |

### 4.2 The new endpoint, measured over HTTP (backend on a private copy, machine idle, new connection per request)

| Request | Result |
|---|---|
| First request (cache miss) | 46 ms, 13,010 bytes |
| Uncached builds (15 different `upcoming` / `results` pairs) | median 54 ms, min 37, max 81 |
| Repeated request (30, all `X-FootIQ-Cache: hit`) | median 27 ms, max 32 |
| Conditional request (30, all `304`, 0 body bytes) | median 15 ms |
| Reference: trivial `seasons` list (91 bytes) | 31 ms (so about 27 to 30 ms of each figure is the connection and the client) |
| Reference: `GET /api/gameweek` EPL matchday 9 | 2,878 ms (what the banner would have cost on the same machine, idle) |
| Body size | 8,250 bytes (`upcoming=1`), 13,010 (default 8), 15,747 (12) |

Requests the Home page sends per load (checked in the browser's network log): `sync/status` (4,961 bytes, from the freshness bar), `meta` (2,723, footer), `featured-fixture` (13,010), `competitions/EPL/seasons` (91), `coverage` (1,131) and `dashboard?season=2026-27` (7,363): six requests, 29.3 kB, all `GET`, none to `/api/gameweek`, `/api/predict` or the competition catalogue. (In the development server React's StrictMode runs each effect twice and aborts the first request; a production build does not.)

### 4.3 Bundle (production build, `npm run build`, 462 ms)

| | P4.1 | P4.2 | Change |
|---|---|---|---|
| JavaScript, all chunks (18 now) | 820.04 kB (252.80 gzip) | 834.73 kB (255.63 gzip) | +14.69 kB (+2.83 gzip) |
| CSS | 47.77 kB (9.46 gzip) | 51.80 kB (10.12 gzip) | +4.03 kB (+0.66 gzip) |
| JavaScript + CSS, gzip | 262.26 kB | 265.75 kB | **+3.49 kB (+1.3%)** |
| JavaScript the Home route loads first | the entry, `ui`, `Overview` and the Recharts chunks (`BarChart` 352 kB, `PieChart` 17 kB) | 4 files, 316.3 kB, **101.2 kB gzip**, **no Recharts** | Home no longer loads the charts; Models and Leagues do |

`dist/` contains no `DesignSystem`, no `contrast.js` and no external host (searched). Fonts unchanged (7 Inter subsets, 218 kB on disk).

## 5. Verification

### 5.1 Backend tests

`.venv/Scripts/python.exe -X utf8 -m pytest tests -q`: **209 passed, 1 warning in 12 min 36 s** (182 before this stage plus the 27 new ones; the warning is the Starlette notice about `httpx` in `fastapi.testclient` that was already present). Log: `data/supervised/phase4/p42_backend_pytest.log`.

### 5.2 Frontend tests

| Run | Result |
|---|---|
| Without the backend (twice in a row, and again after the last source change) | **285 passed, 12 skipped** (the 12 live tests), about 8 s |
| With the live backend on a private copy of the store (`FOOTIQ_LIVE_API=http://127.0.0.1:8000 npx vitest run --no-file-parallelism`, default timeouts) | **297 passed, 0 failed, 0 skipped**; the gameweek test took 2.5 s, the new Home endpoint test 266 ms |

Per file: `home.test.jsx` 38 (new), `fixtures.test.js` 14 (new), `design-tokens.test.js` 94 (27 new), `shell.test.jsx` 40, `crest.test.jsx` 43, `app.test.jsx` 17, `season.test.jsx` 17, `redesign.test.jsx` 14, `gameweek.test.jsx` 8, `live-api.test.js` 10 (1 new), `crest-live.test.js` 2. Results are saved in `data/supervised/phase4/p42_vitest_mock.json` and `p42_vitest_live_default.json`.

New tests, by what they protect:

* **Page behaviour (38):** banner content and the focal order; Today and Tomorrow; local-time and unknown-time kickoffs never shown as UTC; stale and provisional chips; flags listed once and the disclosure; the three links; no forecast shown or made (every request is a `GET`, exactly four distinct paths are requested); a saved forecast with club names and the three `made_before_kickoff` wordings, never "1" or "2"; loading state; both empty states; banner error with retry while the rest of the page works; league-table error with retry that fetches only what failed; fixtures grouped by day, linked, limited to six, provisional once or per row, unmatched club; results with FT and AWD; league overview in six situations; quick links; one `h1`; section order; the old charts and catalogue request are gone; every control has a name.
* **Helpers (14):** the three kickoff states, UTC-pinned dates (including 1 January and 31 December), Today and Tomorrow across a month and a year end, grouping, flag labels (every flag the backend can raise has one), freshness wording, gameweek link.
* **Design tokens (27):** the hero gradient is made of tokens; `ink` and `ink-2` reach 4.5:1 on each of its three stops; text on darkened glass (20, 25, 30, 45% black) reaches 4.5:1 on each stop; the `ok` and `warn` chips reach 4.5:1 on it; the light button reaches 7:1; **the edge of a glass button reaches 3:1 on each stop** (the first border I used, white at 30%, computes to 1.90:1 on the lightest stop and would fail; at 50% it is 3.43:1, and 3.25:1 on the hovered fill); the focus ring reaches 3:1; no text under 12 px, no hard-coded colour, 44 px targets and no write calls in the Home sources.
* **Live contract (1):** shape and stored-value rules of the real response, cache headers, `304`, validation (`comp=UCL`, `upcoming=0`, `upcoming=13`, `results=99` give 422), latency guard (first request under 2 s, cached under 0.5 s) and that the saved-forecast count of every league is the same before and after.

### 5.3 Existing tests that were changed

* `app.test.jsx` and `redesign.test.jsx`: **three tests that exercised the old Home (coverage chart, validation donut, grouped competition cards and "View sources") now render `AboutTheData`**, because that content moved to Models (your decision). Their assertions are otherwise unchanged, with one removed (a "Model performance" link that belonged to the old Home) and one added (the "About the data" heading).
* `shell.test.jsx`: the `routes` tests import every lazy page once in a `beforeAll`. The first route test had failed on vitest's 5 s limit (5.8 s) because the first import of the Recharts pages takes seconds while the test workers are busy; this moves test start-up out of the assertions and says nothing about how fast a page loads for a user. Two consecutive full runs pass.

### 5.4 Browser checks (headless Chrome driven over CDP, dev server on 5173, backend on 8000 with a private copy)

| Check | Result |
|---|---|
| Horizontal overflow at 1440, 820 and 375 px, all 7 routes | none (`scrollWidth - innerWidth` is 0) |
| Contrast (WCAG 1.4.3) | **0 failures on all 21 route and width combinations.** The probe now composites translucent fills over a gradient and tests every colour stop; Home has 32 text nodes on the gradient, all checked. Negative control: a `text-mute` line on the hero is reported at 4.38:1 and a quiet chip at 3.84:1, while `ink-2` passes |
| Target size | Home: **0 of 30 controls under 44 px** at 1440 and 820 px, 0 of 29 at 375 px. Models: 0 (the two disclosure summaries fixed in this stage use the new shared `Summary`, 44 px with a turning chevron). Remaining: Simulations has 2 radio inputs of 13 x 13 px (stage P4.5) |
| Headings and font | one `h1` per route; Inter loaded on every route |
| Keyboard on Home (real key events) | 18 Tab stops in order (freshness toggle, banner buttons, notes, the four tiles, "Gameweek predictions", six fixture rows, the selected league pill, "Full table"), **every one with a 2 px solid focus ring**; Enter opens the notes disclosure and Space closes it; Arrow Right on the league pills selects La Liga, moves focus and updates the table (the caption names La Liga); Enter on a fixture row opens `/predict?mode=gameweek&comp=SERIEA&gw=9` |
| Console | no errors or warnings on Home |
| Accessible names (Chrome's accessibility tree) | regions "Data freshness", "Next match" and "Quick access"; each fixture row is a link named "20:45 local AS Roma versus Cagliari Calcio Serie A" (the badges are hidden from assistive technology); each result row is a group named "Borussia Dortmund 1, Eintracht Frankfurt 0"; the league table is named "Premier League 2026-27: the top 6 clubs by points, from the matches in the data"; the league pills are a radio group named "League" |

Screenshots (`docs/mini-project/phase4/p4.2/`, real stored data of 2026-10-27, the featured fixture is a Serie A match dated that day with a local time and no time zone):

| File | View |
|---|---|
| `home-desktop-fold.png`, `home-desktop-full.png` | 1440 x 900 and the whole page at 1440 |
| `home-tablet-fold.png`, `home-tablet-full.png` | 820 x 1180 and the whole page |
| `home-mobile-fold.png`, `home-mobile-full.png` | 375 x 812 (2x) and the whole page |
| `probe-p42.json` | the measurements of every route and width |

### 5.5 Protected state (`phase4_integrity.py check`, saved as `data/supervised/phase4/p42_integrity_final.json`)

| Item | Result |
|---|---|
| Frozen files recorded in `hashes_before.json` (6) | unchanged |
| Protected manifest (17 files: production store, original CSV, sync settings, frozen models, prospective-evaluation files) | identical to the start of Phase 4 and to the end of Phase 3 |
| Production store | SHA-256 `39ab9651…61f3` matches the post-import record; `integrity_check` ok; `simulation_runs` 0 |
| Settings | `live_enabled` false; `scoreline_method` null (`failed_predeclared_criteria`); position bounds as before |
| Backend sources (73 files) | differ from the start of Phase 4 in exactly `app/featured.py`, `app/main.py` and `tests/test_featured.py` (the expected set) |
| Git | nothing staged, HEAD `970f461`, no file under `frontend/` tracked |

## 6. Files changed in this stage

Method: files modified after the P4.1 report was finished (10:16 on 2026-10-27), plus the new ones.

**Frontend (`frontend/`, untracked)**

| File | Change |
|---|---|
| `src/pages/Overview.jsx` | rewritten: the Home dashboard (35 lines) |
| `src/components/home/FeaturedMatch.jsx` (new, 206 lines) | banner, forecast strip (only if saved), loading, error and empty states |
| `src/components/home/FixtureLists.jsx` (new, 101) | next fixtures and latest results |
| `src/components/home/LeagueOverview.jsx` (new, 106) | league pills and compact table; retry fetches only what failed |
| `src/components/home/QuickActions.jsx` (new, 31) | four quick-access tiles |
| `src/lib/fixtures.js` (new, 80) | formatting helpers; `FLAG_LABELS` moved here |
| `src/components/AboutTheData.jsx` (new, 124) | the old Home's coverage chart, validation donut and grouped competition cards, now at the end of Models |
| `src/pages/Models.jsx` | renders `AboutTheData`; its summary uses `Summary` |
| `src/components/ui.jsx` | `Chip` tone `hero`; `Button` variants `light` and `glass`; `Pills` option `wrap`; `MatchRow` rows get `role="group"` and a spoken label; new `Summary` (44 px disclosure line) |
| `src/components/SourceDetails.jsx` | "View sources" uses `Summary` |
| `src/components/FixtureCard.jsx` | imports `FLAG_LABELS` from `lib/fixtures.js` |
| `src/lib/hooks.js` | `useApi(path, params, { retry })`: a counter that refetches and is never sent to the backend |
| `src/index.css` | tokens `hero-from` and `hero-via`; `.hero` is built from tokens |
| `tests/home.test.jsx` (new, 458 lines), `tests/fixtures.test.js` (new, 111) | see §5.2 |
| `tests/design-tokens.test.js` | 27 tests added |
| `tests/live-api.test.js` | 1 live test added |
| `tests/app.test.jsx`, `tests/redesign.test.jsx`, `tests/shell.test.jsx` | see §5.3 |

**Backend:** `app/featured.py` (new), `app/main.py` (route, imports, cache emptied after a sync), `tests/test_featured.py` (new). No other `app/`, `config/` or `data/` file.

**Documentation:** `API_REFERENCE.md` (new endpoint), `FRONTEND_INTEGRATION.md` (Home rules and screens table), `phase4/P4_2_PERFORMANCE_INVESTIGATION.md` and this report (new), `phase4/p4.2/` (6 screenshots and the probe results), the status note in `PHASE4_UI_AUDIT_AND_PLAN.md`.

**Git-ignored tooling and records (`data/supervised/phase4/`):** `p42/` (profiling, experiment, timing and contention scripts with their JSON results), `tools/p42_capture.mjs` (`shots`, `probe`, `keys`), `tools/probe.js` (gradient and translucent-layer contrast), `tools/probe_negative_control.mjs`, `phase4_integrity.py` (the expected P4.2 backend differences), `p42_backend_pytest.log`, `p42_build.log`, `p42_vitest_*.json`, `p42_integrity_final.json`.

## 7. Deviations from the plan and what remains

| Item | Detail |
|---|---|
| Component names | The plan named a `FeaturedFixture` and a `MatchCard`; the banner is `FeaturedMatch`, fixture rows are in `FixtureLists`, and results reuse `MatchRow`. The `MatchCard` family belongs to P4.3 |
| Three existing tests retargeted | because the content moved to Models by your decision (§5.3) |
| Beyond the Home | a shared `Summary` (it also fixed the two Models disclosure targets that P4.1 had left), hero tokens, a stronger edge on the glass button (found by the new 3:1 test), the `shell.test.jsx` warm-up, and a correction to my own contrast probe (it measured translucent chips against the page colour instead of the gradient under them; nothing it had reported as passing turned out to fail) |
| **Gameweek optimisation not applied** | proposed only (§4.1); it changes `app/gameweeks.py` (variant B) or the store (variant D) and needs your decision |
| Same-day fixtures without a time zone | about half of the scheduled fixtures of the five leagues have no UTC kickoff (all of Serie A's and Ligue 1's, and a few of the others; 657 of 1,443 in the newest season; corrected in P4.3, this report first said "most"), so such a fixture stays "upcoming" until the day ends and the banner says "Today, 18:30 (time zone not stated)" even after that local time has passed. Only a fixture with a stored UTC kickoff that has passed is dropped from the list. Say if you want a different rule |
| Real data state | the featured Serie A fixture shows "Data not fresh" and "Provisional history" because the stored Serie A results end on 2026-09-20 (37 days earlier); four of the five leagues are stale in the sync bar. This is the data, not a defect of the page |
| Phones | the league pills scroll sideways inside their own strip (P4.1 behaviour); the page itself does not overflow |
| Still open for later stages | Simulations radio inputs of 13 x 13 px (P4.5); two small texts on Compare (P4.3); `/matches` is still the placeholder (P4.3); `frontend/README.md` is out of date (P4.7); Leagues, Predictions and Simulations are not restyled yet |

## 8. Reproduce

```bash
.venv/Scripts/python.exe -X utf8 -m pytest tests -q                                        # backend, about 13 minutes
cd frontend && npx vitest run                                                              # frontend, no backend
FOOTIQ_LIVE_API=http://127.0.0.1:8000 npx vitest run --no-file-parallelism                 # with the backend on a private copy
npm run build
node data/supervised/phase4/tools/p42_capture.mjs shots | probe | keys                     # needs the dev server on 5173 and the backend on 8000
.venv/Scripts/python.exe -X utf8 data/supervised/phase4/p42/http_timing.py                 # endpoint timings
.venv/Scripts/python.exe -X utf8 data/supervised/phase4/phase4_integrity.py check
```

Run the backend for these checks on a private copy: `FOOTIQ_STORE_PATH=data/supervised/rehearsal/<copy>.sqlite .venv/Scripts/python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000`.
