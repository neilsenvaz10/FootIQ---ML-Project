# Phase 4.29: regression test repair, five-league season simulator and final verification

No Git operation, no retraining, no new data or provider, no production import, no archived-competition change. The production database was never opened for writing (all simulation runs used private copies); its hash is unchanged.

## 1. Root cause of the four failures
`tests/test_seasonsim_service.py` runs on a copy of the production store and hard-coded the data of an earlier date: La Liga "287 remaining fixtures" (now 281 = 380 fixtures - 99 results; the verified Phase 4.22-4.24 imports added results) and "Premier League, Serie A and Ligue 1 are not eligible" (their data is now complete and recent enough, so they are Ready / Provisional). Independent audit of the current database (`p429/audit_leagues.py`, read-only):

| League 2026-27 | Fixtures | Completed | Remaining | Clubs | Duplicate pairs | Missing identity | Awaiting result |
|---|---|---|---|---|---|---|---|
| Premier League | 380 | 80 | 300 | 20 | 0 | 0 | 0 |
| La Liga | 380 | 99 | 281 | 20 | 0 | 0 | 1 (postponed) |
| Bundesliga | 306 | 63 | 243 | 18 | 0 | 0 | 0 |
| Serie A | 380 | 80 | 300 | 20 | 0 | 0 | 3 past-dated, stored as scheduled |
| Ligue 1 | 306 | 72 | 234 | 18 | 0 | 0 | 0 |

The implementation is correct: remaining = fixtures minus results with a stored score, each remaining fixture is simulated once, no completed match is re-simulated, and a postponed match stays remaining. The tests, not the application, were outdated.

## 2. Test changes made (`tests/test_seasonsim_service.py`; before-copy in `p429/before/`; patch script `p429/patch_tests.py`)
- New helper `oracle()`: expected fixtures, completed, remaining, missing results, clubs and points per club computed with plain SQL on the test's database copy, independent of the code under test. Hard-coded 243 / 287 counts were replaced by it (not by 281).
- `test_todays_eligibility_matches_the_planned_gates`: counts checked against the oracle; Bundesliga and La Liga "ready"; the final-position gates (scoreline method, initial scope, blocked rules for Serie A and Ligue 1) still asserted. The invalid "three leagues not eligible" assertion was removed.
- `test_points_only_status_follows_data_quality_and_the_approved_scope`: `can_run` must equal "state is not not_eligible" for all five leagues; the scope blocker is still tested by narrowing the scope in the test.
- `test_points_only_la_liga_run_is_sane` and the Bundesliga / La Liga count assertions use the oracle.
- New tests: five-league parametrised run (accounting, determinism, a different seed differs, no positions, missing results disclosed, ranges only for Bundesliga and La Liga), past-dated fixtures counted once and disclosed (Serie A at a later date), shipped scope = five leagues and no Champions League, API accepts the five leagues and refuses the Champions League, and two synthetic engine tests with fixed numbers (certain outcomes give exact points; seed reproducibility; 2 or 3 points per fixture).
- No valid assertion was removed. Results: that file **32 passed**.

## 3. Why the three leagues were disabled, and whether the engine supports them
`config/season_sim.json: points_only.scope` listed only Bundesliga and La Liga (the initial approval of 2026-10-25), and the eligibility gate reported "outside the approved scope". The points-only engine needs no tie-break rules and no scoreline model; it uses the frozen club v1 probabilities, which the gameweek forecasts already produce for all five leagues. The data gate (Ready / Provisional / Not eligible) was already league-neutral. The engine was validated for all five leagues before enabling (section 5).

## 4. Changes
- **Backend:** `config/season_sim.json`: `points_only.scope` = the five domestic leagues (before-copy kept); `app/seasonsim/eligibility.py` and `service.py`: the position-range message now says what is true ("available for the Bundesliga and La Liga only: they need verified tie-break settings"). No engine, model or database change. The Champions League is refused (HTTP 422); the full final-position simulator (`initial_scope` Bundesliga and La Liga, scoreline method null) and the position-range scope are unchanged.
- **Frontend:** no code change was needed: the league list already had five leagues; the disabled reason and unavailable-ranges reason come from the backend and are shown. Tests added (`frontend/tests/season-five-leagues.test.jsx`, 8 tests): exactly five leagues and no Champions League; for each league 2026-27 selected, finished season hidden, button enabled, POST carries league, season, 10,000 simulations and seed; Serie A provisional warning visible and the run still allowed; the backend's actual blocking reason is shown.
- **Not done:** position ranges for the Premier League, Serie A and Ligue 1. They need verified tie-break settings validated for the ranges method; the Serie A and Ligue 1 rule profiles are blocked (engine cannot apply their criteria) and the Premier League profile has no range settings. Enabling them would be an unvalidated modelling change, so the page states the reason instead. Expected points, the 10-90% range and the distribution (the "points-only methodology") work for all five.

## 5. Simulation results for all five leagues (private copy of the production database, `p429/validate_five.py`, result `validate_five_result.json`)
Each league: 1,000 simulations first, the same seed twice (identical), then 10,000. All independent checks passed (teams, remaining, per-club remaining sum = 2 x remaining, current points per club, expected total between current + 2R and current + 3R, per-club bounds, labelled experimental, no positions, distribution sums to 1).

| League | State | Completed | Remaining | Clubs | Run time (all 3 runs) | Top expected points | Ranges |
|---|---|---|---|---|---|---|---|
| Premier League | ready | 80 | 300 | 20 | 37 s | Arsenal 83.2, Manchester City 81.8 | unavailable (reason shown) |
| La Liga | ready (1 missing result disclosed) | 99 | 281 | 20 | 15 s | Barcelona 97.0, Real Madrid 86.2 | available |
| Bundesliga | ready | 63 | 243 | 18 | 13 s | Bayern 85.6, Dortmund 69.3 | available |
| Serie A | provisional (3 past-dated fixtures without a result) | 80 | 300 | 20 | 15 s | Inter 89.2, Roma 78.8 | unavailable (reason shown) |
| Ligue 1 | ready | 72 | 234 | 18 | 11 s | Paris Saint-Germain 74.6, Monaco 59.9 | unavailable (reason shown) |

Real UI check on a second stack (backend 8001 on a private database copy, front end 5174): Premier League, Serie A and Ligue 1 show 2026-27 selected and an enabled **Run points-only simulation**; a Premier League run with 10,000 simulations and seed 2026 displayed expected final points with 10-90% ranges (saved as run 3 in the private copy only). Test instances were stopped afterwards.

## 6. Missing and postponed fixtures
Past-dated fixtures without a verified result (the 3 Serie A fixtures, and the postponed La Liga match) are simulated exactly once as remaining fixtures, are never counted as completed, and are disclosed: the eligibility banner shows "n fixture(s) dated up to today have no verified result (x% of played-date fixtures); they are simulated like future fixtures" and the run records them in its saved eligibility counts. "Provisional" does not disable the run. Cancelled or abandoned fixtures (none now) would still block it. No score or goal difference is created.

## 7. Full regression
- **Backend, full `pytest tests` (23.6 min): 579 passed, 8 skipped, 0 failed** (Phase 4.28: 567 passed, 4 failed). Output `p429/full_backend.txt`.
- **Frontend `npx vitest run`: 375 passed, 13 skipped** (Phase 4.28: 367 passed); 17 files passed, 2 skipped (live-API files, by design).
- Live: `final_verify.py` 67 of 67 on the running backend (this backend still runs the code and configuration from before this phase; see section 11).

## 8. Scratch cleanup (Part D)
Preflight: the Phase 4.28 test run had exited (the new run used another folder); the folder is not the application's store (the running backend uses `data/footiq.sqlite`); contents were pytest scratch only (`.sqlite` test copies 2.74 GB, pytest snapshot `.json` 46 MB, `-shm`/`-wal`), no reports or unique data; every path resolved strictly inside `data/supervised/pytest_tmp/p428`; 70 pytest links were only unlinked, never entered. Deleted: **275 files, 2,786,965,510 bytes (2.787 GB)**, 70 links, 187 empty directories, nothing skipped (`p429/scratch_deletion_log.csv`); the folder itself remains, empty. **Project size: 7.431 GB (32,380 files) before, 4.644 GB (32,109 files) after**, measured by summing all files under `D:\Foot IQ`. Nothing else was deleted. This phase's own scratch: `data/supervised/pytest_tmp/p429` (220 MB, from one targeted run) was not in the approval and was left; the later full run wrote to a folder outside the project.

## 9. Documentation (Part E)
Rewritten: `ARCHITECTURE.md` (six competitions, no international model or World Cup engine in the architecture, start-up-only synchronisation, current store size), `ML_MODELS.md` (served models first; international v2.7 and World Cup engine moved to a clearly marked archive section; Champions League "Not validated"), `PROJECT_REPORT.md` (scope, coverage of 28 October, sources, tests, results), `VIVA_QA.md` (scope, algorithms, simulator, sources, freshness; archive question added). Also updated: `FINAL_SYSTEM_GUIDE.md`, `LIMITATIONS.md`, `DEMO_SCRIPT.md`, `SETUP_AND_RUN.md` and `TESTING_REPORT.md` (five-league simulator, test counts), root `README.md`. Checks: no claim that Champions League predictions are validated; no claim of real-time synchronisation (only two leagues, once at start); coverage matches the database; evaluation metrics unchanged from the stored reports; sources and licences as in `DATA_SOURCES.md`; start/stop instructions in `SETUP_AND_RUN.md` and the guide. Before-copies: `p429/before/docs/`.

## 10. Integrity (Part F)
- Production database hash **`410d9fe1755742c83cd03bac2a0ded8225365a59cbfba09fccfb20bd5e825a38`** unchanged (WAL 0 bytes); integrity ok.
- The Phase 4.28 backup is intact: same hash, integrity ok, 30 forecast rows, 2 saved simulations.
- Saved simulations 1 and 2 unchanged (content hash `33fbf4af...`, 10,000 each); the Premier League forecast run and its 30 rows unchanged; matches 223,636, quarantine 273.
- All five frozen model hashes match (`verify_production.py`).
- Six competitions: 67 of 67 live checks; archived competitions excluded (404 / 422); synchronisation unchanged (`sync_mode: startup`, OpenLigaDB for BUNDESLIGA and LALIGA only).

## 11. Remaining issues
1. **The running backend on port 8000 must be restarted** to use the new configuration and messages: it still reports Premier League, Serie A and Ligue 1 as out of scope. I did not restart it without your approval. Restart with the documented command in `SETUP_AND_RUN.md` section 4 (one Ctrl-C in its terminal, then start again); the saved data is not affected.
2. Position ranges remain Bundesliga and La Liga only (section 4).
3. `data/supervised/pytest_tmp/p429` (220 MB) is leftover scratch from this phase.
4. Four competitions have no update source; 3 Serie A results unapplied; 1 La Liga postponement and 60 date corrections held.
5. Occasional slow shutdown; `scipy` missing from requirements files; `/worldcup` route alias.
6. Changed files are uncommitted (no Git operation was performed).

## 12. Final verdict
**Ready for college submission, after one restart of the backend** (so that the running application shows the five-league simulator). All approved goals are met: the four failures are explained and the tests repaired without weakening them; the Season Simulator runs for all five domestic leagues, validated, deterministic, experimental and with missing results disclosed; backend 579 passed / 0 failed and frontend 375 passed; documentation describes the six-competition system; the database, backup, simulations, forecast and frozen models are intact; the project is 4.64 GB.
