# Phase 4, stage P4.3: gameweek optimisation, time-zone rules, Matches hub, Predictions (technical report, checkpoint 3)

Written 2026-10-27 on branch `feat/club-ml-v2` (HEAD `970f461`). Plans and earlier reports: [PHASE4_UI_AUDIT_AND_PLAN.md](../PHASE4_UI_AUDIT_AND_PLAN.md), [P4_2_CHECKPOINT_REPORT.md](P4_2_CHECKPOINT_REPORT.md), [P4_2_PERFORMANCE_INVESTIGATION.md](P4_2_PERFORMANCE_INVESTIGATION.md). Endpoint contracts: [API_REFERENCE.md](../API_REFERENCE.md).

**Stopped here for your approval.** P4.4 has not been started. Nothing was staged, committed or pushed. No frozen model, prospective-evaluation file, football data file, sync setting or scoreline setting was touched; `data/footiq.sqlite` was only read and hashed (§7).

## 1. Status

| Item | State |
|---|---|
| 1. Variant B in `team_form` | **Applied after verification.** Parity identical everywhere it was checked (§2); 8 regression tests |
| 2. Same-day fixtures with unconfirmed time zones | Done (§3) |
| 3. Matches hub | Done: `GET /api/matches` and the page (§4) |
| 4. Predictions redesign | Done, functionality and the explicit Predict gameweek action unchanged (§5) |
| 5. Design and accessibility | Done; the two undersized Compare texts fixed (§6) |
| Your three refinements of the Home page | Done (§8) |

## 2. Gameweek optimisation (variant B)

Applied in `app/gameweeks.py` only after every check below was identical. The change is the `INDEXED BY idx_matches_comp_season_date` hint in the one statement of `team_form` (exposed as `TEAM_FORM_SQL`); a store without that index falls back to the unhinted statement (tested). No model, feature, probability or evaluation file is involved: `team_form` only produces the "form" dots next to a fixture.

| Verification (run before the edit; scripts in `data/supervised/phase4/p43/`) | Result |
|---|---|
| `team_form`, old versus new versus an independent pure-Python oracle | **1,998 calls** (999 fixtures: stratified over 5 leagues x 9 seasons, plus every first-matchday, scheduled and awaiting-result fixture of the recent seasons): **0 differences**; results returned per call: 0 (5 calls), 1, 2, 4 and 5 (1,985): missing and partial history covered |
| Oracle versus new on **every** call a gameweek page of the two newest seasons can make | **7,008 calls, 0 differences** |
| Chronological cutoff | no returned match dated on or after the cutoff in any call (0 leaks); the regression tests also sweep every cutoff day of a synthetic season |
| Whole gameweek payloads (form, status, flags, reasons, reliability, saved forecast, evaluation), old versus new | **171 gameweeks of the five leagues** (every second matchday of the newest season, two per older season), 3.35 MB of JSON: **0 differences**. Fixtures: 948 completed, 674 scheduled, 31 awaiting result, 1 awarded; form length 0, 2, 4 and 5 present |
| **Prediction parity**: the application's own `forecast.predict_gameweek` with old and new `team_form`, same fixed clock, on a second private copy | **10 gameweeks, 80 fixtures, 240 saved rows** (three model variants each: probabilities, `feature_sha256`, `made_before_kickoff`, reliability, flags): **all identical**; paths covered: cached state and day-by-day replay; reliability full and provisional; before-kickoff yes and no |
| Postponed, cancelled, abandoned, unscored and same-day cases | The store holds no postponed or cancelled row (statuses present: completed, scheduled, awaiting_result, awarded, abandoned), so these are in the synthetic regression tests: each is excluded exactly as before (`tests/test_team_form_hint.py`, 270 old-versus-new comparisons per run) |

**Benchmarks** (EPL matchday 9, 10 fixtures, 5 fresh processes per row; cold = first call on a fresh connection, warm = the next five; `bench_gameweek.json`):

| | Cold, median | Warm, median | Warm, worst |
|---|---|---|---|
| Old, idle | 2.34 s | 2.58 s | 2.85 s |
| **New, idle** | **0.157 s** | **0.155 s** | 0.159 s |
| Old, 24 busy processes on 12 threads | 12.7 s | 3.0 s | 21.2 s |
| **New, 24 busy processes** | **0.198 s** | **0.160 s** | 0.179 s |

Idle: 15 times faster; under load the old statement ranged from 3 s to 21 s while the new one stays at 0.16 to 0.2 s. Over HTTP the live gameweek test now takes 0.4 s (it needed 2.5 s idle, and 5 to 10 s under load, before).

**Regression tests** (`tests/test_team_form_hint.py`, 8): the statement equals the reference statement plus the hint; hinted and reference results equal on 270 combinations of entity, cutoff and size; strict cutoff; unplayed, postponed, cancelled, abandoned, unscored, other-competition, unmatched-club and future rows never count; the plan uses `idx_matches_comp_season_date` and not the status index; a store with 30,000 other matches makes the old statement do more than 20 times the work (SQLite VM steps, identical on any machine) while the new one stays under 20,000 steps; a wall-clock bound of 2 s for 20 calls (milliseconds in practice); a store without the index still answers identically.

## 3. Same-day fixtures with an unconfirmed time zone

Stored kickoffs are returned exactly as stored. For `local_without_time_zone` the API returns `utc: null` and `zone_verified: false`: **no UTC timestamp is made up, and none is guessed from a local time.** `GET /api/featured-fixture` and `GET /api/matches` add a `timing` object (`phase`, `ambiguous`, `note`).

| Case | Classification |
|---|---|
| Verified result stored (`completed`, `awarded`) | completed, whatever the clock says |
| Stored scheduled, date before the server's UTC date | awaiting result |
| Dated today, stored **UTC** kickoff in the future | upcoming |
| Dated today, stored **UTC** kickoff has passed, no result | awaiting result ("kickoff passed, no result yet"; ambiguous: in progress or finished cannot be known) |
| Dated today, local time **without a time zone** | stays upcoming, labelled "Today · time zone unconfirmed" (ambiguous) |
| Dated today, no time stored | stays upcoming, "Today · time not stated" (ambiguous) |

Only the server's UTC clock and stored values are used. The frontend never reads the browser's clock (a test moves the system date to 2031 and checks that "Today" is still the server's date; a source test forbids `Date.now`, `new Date()` and locale formatting in the Matches code). There is no "live" status anywhere (tests). Wording is "time zone unconfirmed" everywhere (cells, chips, flag label, notes). Prediction eligibility and the pre-kickoff safeguard are untouched: `forecast.made_before_kickoff` still uses its stored-UTC rule or the 14-hour / 12-hour window for an unknown time, and results dated on the fixture's own day are still excluded from every forecast.

**Unavoidable ambiguity (documented, not hidden):** (a) between an unknown kickoff on the fixture's date and the arrival of a verified result, the match may be not started, in progress or finished; the page says "time zone unconfirmed" and the day-level note says so, and it does not choose. (b) "Today" and "date passed" use the server's UTC calendar day, while the stored date is the venue's calendar date; for a late evening kickoff far west of UTC the two days can differ. (c) A stored UTC kickoff that has passed only proves that the match has begun or finished, not which. (d) About half of the scheduled fixtures of the five leagues (657 of 1,443 in the newest season: all of Serie A and Ligue 1) have no UTC kickoff at all; this corrects the P4.2 report, which said "most".

## 4. Matches hub

`GET /api/matches` (`app/matches.py`, new, 221 lines; route in `app/main.py`): filters `comp`, `season` (default newest of each league), `matchday`, `status` (upcoming, awaiting_result, completed, other, all), `limit` 1 to 50, keyset `cursor`, `order`; per row the stored kickoff with `zone_verified`, `timing`, verified score and source, eligibility and reliability flags for unplayed matches, the count of saved forecast runs of its gameweek; per answer the status counts, the facets (seasons, matchdays) and the data freshness of each league. Bounded and indexed: every statement is anchored on `idx_matches_key` (tests assert the plan of every variant: no scan, never the status index), a fixed statement count independent of the number of matches (40, 380 and 1,500 per league), a page of at most 50 rows, deep pages cost the same as the first. Measured on the 223,510-row store: 25 to 50 ms per request in process; 0.4 s for the live contract test including 30 requests. Read-only, no model, no gameweek view (tests hash the store and replace every model entry point with a failing function).

The page (`pages/Matches.jsx`, `components/matches/*`, `lib/matches.js`): league pills, season and matchday selects, status pills with the server's counts, all in the address so views can be shared; rows grouped by day with clear kickoff (UTC time, or local time with "zone unconfirmed", or "Time not confirmed"), badges and full club names, verified scores with the winner marked, chips for league, matchday, status, provisional history, unmatched club, saved forecast, source; links to the gameweek (with its season), a manual prediction and the team comparison (only when both clubs are matched; no manual prediction for finished matches); data freshness (one league: chip; five: summary and a disclosure); "Show more matches" with a retry that keeps the rows already shown; loading, empty (with a hint when other statuses have rows), error and reset states; stale answers of filters the user has left are dropped. The manual predictor, the comparison and the gameweek mode read the clubs, league and season from the link and only pre-select them: nothing is computed until the user presses the button.

Scope note: the hub covers the five domestic leagues (the only competitions with scheduled fixtures, freshness and eligibility in the store). UEFA and international competitions stay on the Leagues and Models pages.

## 5. Predictions

Same tabs, requests and request bodies; the explicit "Predict gameweek" action and the warm-up gating are unchanged (existing tests pass untouched). Fixture cards (`FixtureCard.jsx`): crests and full names, kickoff as stored with "time zone unconfirmed", the probability bar labelled with the actual team names (the old "1 / 2" are gone), a visible "Why provisional" line instead of a tooltip, the validated club v1 bar and, below it, the **experimental club v2-r1** drawn thinner with a dashed edge and an "Experimental candidate" label; the predicted-versus-actual, run history and details are as before. Manual predictor: tabs read "Club v1 · validated", "Club v2-r1 · experimental" and "Elo-only baseline" for club competitions, with a warning notice on the experimental one; home and away can come from a link. Selectors are the existing labelled league, season, gameweek and previous/next controls. Saved forecast history and predicted-versus-actual remain where the API supports them (latest forecast per fixture and the run list).

## 6. Design and accessibility

| Check (1440, 820 and 375 px; Matches, Matches completed, Predictions both tabs, Compare, Home) | Result |
|---|---|
| Horizontal overflow | none on all 18 combinations |
| Contrast, WCAG 1.4.3 | 0 failures (probe with gradient and translucent layers) |
| Text under 12 px | **0** (the two undersized Compare texts, "Team A" and "Team B", and the other 11 px texts of Compare and Predictions are now 12 px; a test forbids smaller sizes in all P4.3 files) |
| Controls under 44 px | **0** of 17 to 98 per page |
| Keyboard | Matches filters are the P4.1 radio groups (arrows) and labelled selects; every link and button is a native element with a visible ring; the P4.1 tab and disclosure behaviour is unchanged |
| Names | every row is an article named "Home v Away"; the row links name the match; one `h1` per page |

Screenshots: `docs/mini-project/phase4/p4.3/` (Matches upcoming and completed, Predictions gameweek and manual, Compare, Home; desktop, tablet and mobile, first screen and whole page).

## 7. Verification

| Item | Result |
|---|---|
| Backend, complete suite | **260 passed, 1 warning in 14 min 7 s** (209 before this stage plus 51 new; the warning is the existing Starlette `httpx` notice) |
| Frontend without the backend | 325 passed, 12 skipped |
| Frontend with the live backend on a private copy (`--no-file-parallelism`, default timeouts) | **338 of 338 passed** (the gameweek test took 0.4 s, the Matches contract test 0.4 s) |
| Production build | JavaScript 847.28 kB (260.08 gzip), CSS 53.21 kB (10.35 gzip): JS + CSS gzip 270.43 kB, +4.68 kB over P4.2 |
| Frozen models, prospective-evaluation files, production store, sync | all unchanged: 6 frozen hashes, 17-file protected manifest identical to the start of Phase 4, production SHA-256 `39ab9651…61f3`, integrity ok, `simulation_runs` 0, `live_enabled` false, `scoreline_method` null; backend sources differ from the start of Phase 4 only in the seven files of §9; nothing staged, HEAD `970f461` (`p43_integrity_final.json`) |
| Home | the P4.2 tests pass (wording of the zone note changed); the live Home contract test passes |

New tests: backend `test_matches.py` 41, `test_team_form_hint.py` 8, `test_featured.py` +2; frontend `matches.test.jsx` 30, Home +1, helpers +5, design tokens +3, the `/matches` shell test replaced, one live Matches contract test.

## 8. Your three Home refinements

1. **Mobile banner** is shorter: smaller padding, 60 px badges, smaller names and day, the main action full width and the two others side by side; the banner, its chips and all three actions are now in the first phone screen (`home-mobile-fold.png`).
2. **League selectors** wrap onto lines at every width instead of scrolling out of sight (Home league overview and Matches).
3. **Featured selection**: when the earliest eligible fixture belongs to a stale league, the earliest eligible fixture of a league with fresh data at most 3 days later is featured instead (today: a Bundesliga match rather than Serie A's). The skipped fixture stays in the list, and the stale warning is computed from the featured fixture's own league, so it is never hidden (tested for fresh within the window, outside it, and nothing fresh).

## 9. Files changed

Backend: `app/gameweeks.py` (variant B), `app/featured.py` (kickoff `zone_verified`, `timing`, fresh-league preference), `app/matches.py` (new), `app/main.py` (route and cache), `tests/test_matches.py`, `tests/test_team_form_hint.py` (new), `tests/test_featured.py`. Frontend: `lib/fixtures.js`, `lib/matches.js` (new), `components/Kickoff.jsx` (new), `components/matches/{MatchCard,MatchFilters}.jsx` (new), `pages/Matches.jsx`, `pages/Predict.jsx`, `pages/GameweekPredict.jsx`, `pages/TeamComparison.jsx`, `components/FixtureCard.jsx`, `components/ui.jsx` (Pills wrap), `components/home/{FeaturedMatch,FixtureLists}.jsx`, tests `matches.test.jsx` (new), `home.test.jsx`, `fixtures.test.js`, `shell.test.jsx`, `design-tokens.test.js`, `live-api.test.js`. Docs: `API_REFERENCE.md`, `FRONTEND_INTEGRATION.md`, this report, the P4.2 report (one corrected sentence), screenshots. Git-ignored records: `data/supervised/phase4/p43/` (parity and benchmark scripts with results), `tools/p43_capture.mjs`.

## 10. Limitations and deviations

* The hub is limited to the five domestic leagues. Matches have no "live" state by design.
* Postponed and cancelled statuses do not occur in the stored data; they are covered by synthetic tests and shown as "Postponed or cancelled" only when present.
* "Saved forecast history" is the latest forecast per fixture plus the run list, because the API exposes no older forecast per fixture.
* The three live contract tests assume the backend runs on a store like the production one; the Matches walk uses Serie A's upcoming matches.
* The prediction-parity runs used a second private copy (deleted afterwards) because the routine saves its runs into the store it is given.
* Still open for later stages: Simulations radio inputs of 13 x 13 px (P4.5), the Leagues page restyle (P4.4), `frontend/README.md` (P4.7).
