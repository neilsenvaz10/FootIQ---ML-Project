# Testing report

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

> **Phase 4.28 note:** The Phase 4.7 / 4.8 figures in this report are history. Final results (Phase 4.28) are in section 0 below and in `docs/mini-project/phase4/P4_28_FINAL_CLEANUP_AND_READINESS.md`.

Every result below was produced by running the command on 2026-10-27 on the project machine (Windows 11, Python 3.12.14, Node 24.13.1). Nothing is quoted from an earlier report without being re-run. Logs and JSON results are kept under `data/supervised/phase4/` (git-ignored).

## 0. Final results (Phase 4.29, 2026-10-28)

| Check | Result |
|---|---|
| Backend, full regression (`pytest tests`, 23.6 min) | **579 passed, 8 skipped, 0 failed** (the same 8 skips as in Phase 4.28) |
| Frontend (`npx vitest run`) | **375 passed, 13 skipped** (the live-API contract tests, by design); includes regression tests for the season list, the Predict Match prefill (with and without React StrictMode) and the five-league season simulator |
| Four tests that failed in Phase 4.28 (`tests/test_seasonsim_service.py`) | repaired: they hard-coded production data from before the verified imports; they now compute expected counts from the database copy with independent SQL, and fixed-number synthetic tests cover the engine arithmetic. 32 tests pass in that file |
| Live verification of six competitions (`final_verify.py`) | 67 of 67 checks |
| Frozen models, database, saved simulations | five frozen hashes match; integrity ok; production hash `410d9fe1...` unchanged; simulations 1 and 2 and the 30 forecast rows unchanged |

Details: `docs/mini-project/phase4/P4_29_FINAL_REGRESSION_VERIFICATION.md`. The Phase 4.28 figures that this replaces (567 passed, 4 failed) are kept in `P4_28_FINAL_CLEANUP_AND_READINESS.md`.

> **Sections 1-7 below are the Phase 4.7 record (history, 2026-10-27) for the earlier eleven-competition application. Do not quote their counts as current; the current results are section 0.**

## 1. Summary

> **Which numbers are which.** Everything in §§1–7 below is the **Phase 4.7 result as recorded on 2026-10-27, before Phase 4.8**; it is left unchanged and the tests added later did not exist then. Later regression runs of the same suites, kept in `docs/mini-project/phase4/`:
>
> | When | Backend | Frontend (no backend / live backend) | Build |
> |---|---|---|---|
> | Phase 4.7 (this report) | 260 passed | 342 passed, 13 skipped / 355 of 355 | passed |
> | Phase 4.8B | 284 passed (+24 new tests) | 342 passed, 13 skipped / 355 of 355 | passed |
> | Phase 4.8C (offline part) | 299 passed (+15 more) | 344 passed, 13 skipped / 357 of 357 | passed |
> | Phase 4.8D Stage 1 | 321 passed | 344 passed, 13 skipped / 357 of 357 | passed |
> | Phase 4.8D Stage 2 | 332 passed | 344 passed, 13 skipped / 357 of 357 | passed |
>
> Three Phase 4.7 tests were changed in 4.8B because they asserted behaviour that 4.8B deliberately replaced (see `P4_8B_CHECKPOINT_REPORT.md` §11).

| Check | Command | Result |
|---|---|---|
| Backend suite | `.venv\Scripts\python.exe -B -X utf8 -m pytest tests -q -p no:cacheprovider` | **260 passed, 0 failed, 1 warning (existing Starlette/httpx notice) in 15 min 30 s** |
| Frontend suite, no backend | `cd frontend; npx vitest run` | **342 passed, 13 skipped** (355 tests, 15 files) |
| Frontend suite, live backend on a private copy | `$env:FOOTIQ_LIVE_API="http://127.0.0.1:8000"; npx vitest run --no-file-parallelism` | **355 passed, 0 failed, 0 skipped**, default timeouts |
| Production build | `npm run build` | Succeeded: 648 modules, 19 JavaScript chunks totalling 861.82 kB (264.54 kB gzip), CSS 54.10 kB (10.46 kB gzip) |
| Cold-start API check | `node scratch\verify_api_connectivity.mjs` (backend cold-started, `/api/health` ready) | 17 of 17 endpoints HTTP 200 |
| End-to-end workflows | `node scratch\e2e_workflow_test.mjs` | **33 assertions passed, 0 failed** across 10 workflows |
| Layout probe, every page, 1440 / 820 / 375 px | `node data\supervised\phase4\tools\p47_probe.mjs` | 24 of 24 views: no horizontal overflow, one `h1`, 0 contrast failures, 0 text under 12 px, **no error or "Cannot reach the backend" banner**; 2 controls under 44 px on Simulations (see §5) |
| Integrity | `phase4_integrity.py check` | see §6 |

## 2. Backend tests (260)

Per file: `test_benchmark_preserved` 7, `test_confidence_gate_v211` 5, `test_dynamic` 8, `test_featured` 29, `test_gameweeks` 14, `test_lineup_impact_v212` 5, `test_live_tournament_v213` 7, `test_matchday_report_v29` 6, `test_matchday_validation_v210` 5, `test_matches` 41, `test_miniproject` 29, `test_pointbounds` 14, `test_pointbounds_exhaustive` 12, `test_rehearsal` 9, `test_seasonsim_engine` 16, `test_seasonsim_service` 24, `test_store` 21, `test_team_form_hint` 8.

They cover: the original research pipeline (confidence gate, lineup impact, matchday validation, live tournament); the mini-project API and prediction parity with the original inference code; the SQLite store, import and rehearsal; Home, Matches and gameweek endpoints (plans, bounds, statement counts, read-only behaviour); the season simulator engine, eligibility, rules and position bounds; and the equivalence and performance guard for the gameweek speed-up. **Tests that write data use synthetic stores in temporary folders** or a private store path; they never target `data/footiq.sqlite` for writing.

## 3. Frontend tests (355)

Per file: `app` 17, `crest` 43, `design-tokens` 97, `fixtures` 20, `gameweek` 8, `home` 39, `leagues` 11, `matches` 30, `p44-warnings` 1, `redesign` 14, `season` 17, `shell` 40, `simulations` 5 (all run without a backend: **342**), plus `live-api` 11 and `crest-live` 2 (**13, need a backend**).

## 4. The 13 skipped tests

| Tests | File | Why skipped | Release-blocking? |
|---|---|---|---|
| 11: health/meta/CORS, competitions, dashboard/coverage/team shapes, predictions, season filter and model performance, bracket and standings form, gameweek endpoints, featured fixture, matches hub, invalid-input errors, simulator seeded and reproducible | `tests/live-api.test.js` | The file is a **contract test against a running backend** and uses `describe.skip` unless `FOOTIQ_LIVE_API` is set. It checks that every field the frontend reads exists in the real API responses. | **No.** Intentional. Run with the backend up, all 11 pass (this run) |
| 2: every team in every competition gets a letters-only badge code; the teams of one league's newest season get different three-letter codes | `tests/crest-live.test.js` | Same switch: it reads real team names from the live API. The same logic is covered offline by `crest.test.jsx` (43 tests) | **No.** Intentional; passes live (this run) |

No test was enabled, deleted or edited to change the counts. The skipping is conditional on an environment variable by design, so that the default suite runs without a backend; a release check should run the live variant, as done here.

## 5. Browser and responsive checks

Headless Chrome (CDP), live backend, dev server on 5173, 24 views (8 routes × 3 widths; `data/supervised/phase4/p47_ui_probe.json`). Pages: Home, Matches, Leagues, Compare, Predictions (gameweek and manual), Simulations, Models. The probe loads each page against the live backend from the 5173 origin, so a CORS failure or an unreachable backend would show as the connectivity banner; none appeared. Known remainder: on Simulations two radio inputs measure 20 × 20 px (their labels are larger), and the season-simulator results tables use 9–11 px text in places (not reachable without running a simulation, so the probe does not see them). Screenshots from Phase 4.6 (17 full pages at the three widths) are in `docs/mini-project/phase4/p4.6/`; this phase did not retake them.

Core workflows exercised by `e2e_workflow_test.mjs`: Home and freshness; Matches filtering and paging; league standings and coverage; team comparison; match prediction; gameweek list and prediction; World Cup pre-tournament simulation (same seed gives the same result); archived World Cup state and bracket; the season simulator (**final-position simulation blocked**, points-only eligible, position ranges computed); model performance and caveats.

## 6. Integrity and safety checks

| Check | Result |
|---|---|
| Frozen artifact hashes (5 model files + `config/sync.json`, `hashes_before.json`) | unchanged |
| Protected manifest (17 files incl. the prospective-evaluation files) | unchanged except `data/footiq.sqlite` (below) |
| `PRAGMA integrity_check` on `data/footiq.sqlite` | `ok` |
| `simulation_runs` in the production store | 0 |
| `config/sync.json` `live_enabled` | `false`; no network call is made by the app |
| `config/season_sim.json` `scoreline_method` | `null` (final-position simulation disabled; `failed_predeclared_criteria`) |
| Git | nothing staged or committed; HEAD `970f461` |
| **Production store hash** | **Not equal to the recorded post-import value.** `data/footiq.sqlite` now hashes to `3641e4da…3922`; the recorded value is `39ab9651…61f3`. Cause found: on 2026-10-27 10:37 UTC a backend was started on the production file; its start-up check wrote one `sync_runs` row (id 8, `skipped_live_disabled`, no network) and (correction in Phase 4.8B: the file was already in WAL mode since the 2026-10-25 import, so only the row and the checkpoint changed the bytes). Evidence that no football data changed: `matches` still has 223,510 rows, the newest `last_changed_utc` is the import time (2026-10-25T09:07:13Z), all other table counts equal the earlier inspection, `sync_runs` is exactly one row larger, `forecasts` and `simulation_runs` are empty. The earlier Phase 4.6 statement that the hash was unchanged was true when written and is stale now. Nothing was repaired in this phase; a decision is requested in the checkpoint report |

## 7. Reproducing

See `SETUP_AND_RUN.md` §5. For the live variants use a private copy of the store (`$env:FOOTIQ_STORE_PATH`) and wait for `club_prediction_ready` first. The full backend suite takes about 14 minutes.
