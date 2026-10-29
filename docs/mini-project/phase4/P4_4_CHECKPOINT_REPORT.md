# P4.4 — Leagues and Standings checkpoint

Date: 27 October 2026. Repository: `D:\Foot IQ`. **P4.4 implemented and verified; P4.5 not started.** No staging, commits, branches, reset, cleaning or push.

## 1. Handover audit and preservation

The active project is the relocated `D:\Foot IQ`, not the old desktop path. Git HEAD remains `970f461` on `feat/club-ml-v2`. The frontend and substantial backend work were already untracked; numerous tracked files already had user changes. These were preserved. The initial sandbox Git invocation failed; explicit approved read-only access returned the actual status.

The handover's claim that P4.4 had not started was slightly stale: `lib/leagues.js`, `components/leagues/StandingsTable.jsx` and `ResultsFixtures.jsx` already existed as disconnected drafts. They were inspected, backed up, integrated and refined; they were not treated as files created in this turn. `PROJECT.md` remains the older master roadmap; it is not an accurate implementation-status inventory. The Phase 4 checkpoint documents and code are more current.

All named handover documents were located: PROJECT, UPGRADE_PLAN, PHASE4_UI_AUDIT_AND_PLAN, RECOVERY, P4.1/P4.2/P4.3 checkpoint reports, the P4.2 performance investigation, API_REFERENCE, and the Phase 3 plan, final validation protocol, rules status and dynamic-strength design. Relevant contracts and restrictions were reviewed. No simulator or model change was required.

The existing P4.0 recovery archive verified against its manifest. Before editing, a second snapshot preserved **77 current frontend files**, including the disconnected drafts, package files and frontend tests. Every archived entry was checked against its recorded SHA-256.

- Pre-edit archive: `data/supervised/phase4/p44/frontend_before.zip`.
- SHA-256: `88c21f330181112b6182706a6ea5995a38fc47194f28295b114952df8f69241a`.
- Per-file baseline: `frontend_before.json` in the same directory.
- Recovery: verify the archive against that manifest, extract to a **new empty directory**, then restore only deliberately selected files. Do not overwrite the current checkout wholesale. Existing P4.0 recovery remains intact.

## 2. Actual architecture and data contracts

Frontend entry points are `frontend/src/main.jsx` and `App.jsx`. `/analytics` renders `pages/Analytics.jsx` inside the existing responsive shell. Stack: React/JSX, React Router, Vite, Tailwind, Recharts and self-hosted Inter. Installed backend versions observed: Python 3.12.14, FastAPI 0.159.1, pandas 2.2.1, NumPy 1.26.4, scikit-learn 1.5.1, pytest 8.4.2, uvicorn 0.54.0; Node v24.13.1. Vite build reports 8.3.5. No packages were installed or upgraded.

Backend entry is `app/main.py`. `analytics.py` uses the existing cached pandas view over SQLite; `store/views.py` selects stored completed/awarded scored results for dashboard analysis. `matches.py` supplies bounded indexed fixtures/results. Forecasts and simulations retain their existing explicit-action endpoints and private-store tests.

Existing league standings award 3/1/0 points and sort by points, goal difference, goals scored, then name. Recent form uses the last five stored results. This is **not an implementation of every competition's official tie-break or administrative adjustment rules**. League-specific regulation profiles and unresolved cases belong to `app/seasonsim/` and `config/season_rules.json`; those were not repurposed or changed. Scoreline simulation remains disabled (`scoreline_method: null`).

No API endpoint, parameter, response contract, SQL statement, model feature, coefficient or prediction calculation changed. The page reuses:

- `GET /api/competitions`
- `GET /api/competitions/{key}/seasons`
- `GET /api/competitions/{key}/dashboard?season=...`
- `GET /api/competitions/{key}/coverage`
- `GET /api/sync/status`
- `GET /api/matches?comp=...&season=...&status=...&limit=8`

The existing historical dashboard/coverage implementation is cached pandas analysis, not a newly introduced indexed endpoint. Trend requests are now deferred until Stats is opened; they retain the existing bound of twelve seasons. The league fixture context uses the existing indexed Matches API rather than gameweek prediction calls.

## 3. Implemented behavior

### Leagues and standings

- Five domestic league selectors plus the existing competition dropdown, preserving UEFA/international access.
- Default newest **stored** season, historical-season selection, URL-preserved competition and season, and explicit unavailable-season states. Changing competition resets the selected season. Keyed components prevent a prior league/season table from appearing under the new selection.
- Dark-purple competition header and retained prediction-model coverage badge, labelled separately from standings validity.
- Semantic standings table with caption and scoped column headers. Desktop/tablet show position, crest initials, club, P/W/D/L/GF/GA/GD/Pts and accessible form. Mobile prioritizes position, club, P, GD and Pts, with W/D/L, goals and textual form beneath each club. Full names can wrap; no invented logo assets.
- Equal-points markers and a visible explanation of display ordering, absent administrative adjustments and clubs with no stored results. No official-final, qualification, relegation or playoff claims.
- Partial coverage, uneven matches played, freshness and missing-result notices. Current sync counts are not applied to historical selections. A full expected match count is labelled only as that, not proof of official final standings.
- Selected-season latest results and upcoming fixtures; source attribution on result rows and existing kickoff ambiguity handling. Links retain competition, season and status in the Matches hub.
- Existing outcome split, historical trends and team-performance chart preserved in Stats. Competition-wide source inventory is clearly distinguished from selected-season dates and per-result provenance.
- Loading, empty, unknown-competition, unavailable-season and API-error states, including local retry for page/coverage/freshness requests.

### Authorized P4.3 refinements

Matches keeps league and status controls visible on mobile; season/matchday controls are behind a labelled native button with `aria-expanded` and `aria-controls`. The active-filter indication and original URL/query behavior remain.

Predictions groups only **identical complete reason arrays** repeated across provisional fixtures. The shared summary lists every reason. Affected cards retain provisional chips, an accessible description reference, and all original reasons under Details. Distinct reason sets remain separately visible. Viewing either page still makes no prediction-saving request.

## 4. Exact source/test changes

Seven existing frontend files changed (including three inherited drafts):

1. `frontend/src/pages/Analytics.jsx` — page composition, URL state, data-quality notices and deferred Stats requests.
2. `frontend/src/components/leagues/StandingsTable.jsx` — draft integration, semantic/responsive table and equal-points indicators.
3. `frontend/src/components/leagues/ResultsFixtures.jsx` — draft integration, result source and ambiguous timing notes.
4. `frontend/src/lib/leagues.js` — inherited draft helper; missing-result wording avoids assuming that a past-dated fixture was played.
5. `frontend/src/components/matches/MatchFilters.jsx` — mobile secondary-filter disclosure.
6. `frontend/src/pages/GameweekPredict.jsx` — identical-warning summaries.
7. `frontend/src/components/FixtureCard.jsx` — shared accessible description while retaining fixture-specific details.

Two test files added: `frontend/tests/leagues.test.jsx` (9 cases) and `frontend/tests/p44-warnings.test.jsx` (1 case). Existing tests were not rewritten. No backend source, backend test, package manifest, lockfile, model or production data file changed in this work.

New documentation: this report and `P4_4_EVIDENCE_MANIFEST.json`. Eleven screenshots are under `docs/mini-project/phase4/p4.4/`. Local recovery, private databases, test logs, JUnit/JSON results, verification helpers, browser profile and isolated build outputs are retained under `data/supervised/phase4/p44/`; they are not Git commits. Detailed paths/hashes and protected state are in the evidence files below.

## 5. Executed tests and failures investigated

| Check | Actual result | Evidence under `data/supervised/phase4/p44/` |
|---|---|---|
| Pre-edit frontend baseline | 325 passed, 13 skipped without live backend | `frontend_baseline.json` |
| Complete backend suite | **260 passed, 0 failures, 0 skipped**, 806.69 s; 1 existing Starlette/httpx deprecation warning | `backend_baseline.log`, `backend_baseline.xml` |
| Final complete frontend suite against private live backend | **348 passed, 0 failed, 0 skipped**, default timeouts | `frontend_verified.json` |
| Final CSS-only heading adjustment | 10 targeted P4.4 tests passed | `frontend_targeted_release.json` |
| Production build after final adjustment | Passed, 648 modules | `build_release.log`, `production-build-release/` |
| Independent standings aggregation | All totals identical for **45 league-season tables** | `standings_verify.json` |
| Final protected state | All 17 protected files and 6 frozen hashes unchanged; SQLite integrity `ok` | `integrity_final.json` |

Backend tests started as the pre-edit baseline and finished during frontend work. All database-writing tests used their private fixtures or `FOOTIQ_STORE_PATH` pointing at `p44/tests.sqlite`. No backend code changed, so a second identical 13-minute backend run was not performed. The live backend used `p44/preview.sqlite` on port 8004. No production database writes were needed.

Failures retained and investigated:

1. First full frontend/live run: 346 passed, one existing health/meta contract timed out at 5 seconds. The runner had started against a cold backend while the full backend suite was running. Later ready health-plus-meta measurements were 0.184, 0.121 and 0.111 seconds; subsequent full live suites passed without changing timeouts. Startup/cache initialization and concurrent load are the likely contributors; their individual contributions were not profiled, so this is not claimed as a proven backend performance fix.
2. A new warning test initially expected bare text, while the existing Details UI prefixes reasons with a bullet. Its exact matcher was corrected to include that existing bullet; the fixture reasons were already present. The final test verifies both shared and distinct reasons, accessible references, expansion and GET-only viewing.
3. Initial screenshot review exposed narrow mobile club/numeric columns despite zero page overflow. Fixed column allocations and nonwrapping numeric/header cells resolved this; screenshots and probes were repeated. The first keyboard script moved focus but did not activate the existing manual-activation tab. The corrected check uses ArrowRight then Enter and verifies `aria-selected=true`.
4. A recovery-archive extraction helper initially assumed LF line endings and stopped before writing. It was corrected to normalize archived CRLF. A dependent screenshot command then failed because the helper had not been created; both were rerun successfully. Failed logs remain as evidence.

## 6. Responsive and accessibility evidence

Table, Matches and Stats were probed at **1440, 820 and 375 CSS pixels**. The two P4.3 refinements were additionally probed at 375 px. In all eleven final states: no horizontal page overflow, no measured text-contrast failures, no nondecorative text below 12 px, and no measured controls below 44 px. The table container is checked separately for hidden horizontal overflow. Every page has one h1; the existing route title, navigation and font remain.

Keyboard check: native league controls and labelled selects; the existing tabs support arrow-key focus followed by Enter activation, verified in Chrome at all three widths. Filter disclosure behavior and table semantics are covered by component tests. This is a targeted accessibility check, **not a complete WCAG certification**: the existing probe is not a full screen-reader audit and decorative crest letters/SVG chart labels are not equivalent to all measured HTML text. No P4.6-wide accessibility claim is made.

| View | 1440 px | 820 px | 375 px |
|---|---|---|---|
| Standings | [Desktop](p4.4/leagues-1440.png) | [Tablet](p4.4/leagues-820.png) | [Mobile](p4.4/leagues-375.png) |
| Results / fixtures | [Desktop](p4.4/fixtures-1440.png) | [Tablet](p4.4/fixtures-820.png) | [Mobile](p4.4/fixtures-375.png) |
| Stats | [Desktop](p4.4/stats-1440.png) | [Tablet](p4.4/stats-820.png) | [Mobile](p4.4/stats-375.png) |

Additional screenshots: [Matches mobile filters](p4.4/matches-filters-375.png), [Prediction warnings](p4.4/prediction-warnings-375.png). Machine-readable measurements: `visual_probe_final.json`.

## 7. Integrity, constraints and reproducibility

Production `data/footiq.sqlite` SHA-256 remains:

`39ab965115b160c7debb37e930f87652195a6cf496d1a529a50ad2d7d53b61f3`

It matches the recorded post-import hash and the Phase 3/Phase 4 protected manifest. SQLite integrity is `ok`, production `simulation_runs` remains zero, and all six prospective-evaluation files in the manifest are unchanged. Six frozen artifact hashes match. The 76 backend-source inventory differs from the start of Phase 4 only in the seven documented P4.2/P4.3 files, exactly as before this task.

`config/sync.json` still has `live_enabled=false`. Scoreline simulation remains disabled and its failed validation status remains. No external football provider request, data import, model training, package installation or Git mutation was performed. The frontend backup and SHA-256 before/after inventory preserve the inherited untracked work.

Reproduction uses existing dependencies. Run the backend with `FOOTIQ_STORE_PATH` set to a **new private copy**, then wait for `/api/health` readiness before running `node node_modules/vitest/vitest.mjs run --no-file-parallelism` with `FOOTIQ_LIVE_API` set to that server. Use `python -B -X utf8 -m pytest tests -q -p no:cacheprovider` with a new private test database and fresh `--basetemp`. Build from `frontend/` using `node node_modules/vite/bin/vite.js build --outDir <new-output-directory>`; no `--emptyOutDir` is needed. Exact helpers and output locations are retained under `p44/`.

## 8. Remaining limitations and P4.5 recommendation

- Historical source conflicts, quarantined scores and fixture-date disagreements were not resolved. Freshness can remain stale because synchronization is intentionally off.
- Standings reflect stored scored results and the preserved generic ordering, not every official league rule. Administrative points adjustments and teams without a stored result are not reconstructed. Current-season means newest season in the stored inventory, not a claim based on the browser clock.
- Fixture context remains limited to the five domestic leagues. Other competitions retain their historical results and Stats; no cup fixture data is invented.
- The source list is competition-wide. Selected-season per-match attribution is available through Matches; no new provenance API was added.
- The existing outcome-trend helper still uses a bounded multi-request historical chart and its original generic empty/error fallback. Backend analytical caching and query architecture were not redesigned.
- Ready-state live tests pass, but cold startup can exceed the first contract's timeout; readiness must be explicit in future harnesses. No timeout was increased.
- Browser checks focus on P4.4 at the three requested widths and the two authorized refinements. The broader P4.6 matrix and full assistive-technology audit remain future work.
- Local recovery and evidence reside on the same drive as the project. There is no new Git checkpoint or off-device backup.

**P4.4 checkpoint satisfied with these documented limits.** For P4.5, preserve the simulation eligibility gates, points-only bounds, disabled scoreline mode, fixed-seed behavior and experimental labels while reorganizing the UI. Establish a fresh source snapshot and private-store parity evidence before editing those screens. **P4.5 requires the user's explicit approval and has not begun.**
