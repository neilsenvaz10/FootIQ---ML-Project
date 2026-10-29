# Phase 4.28: final cleanup and submission readiness

No Git operation, no retraining, no provider request, no synchronisation or archived-competition change, no production import. Production database touched only by the normal application reads (hash unchanged).

## 1. Fresh database backup (Part A)
- Production `data/footiq.sqlite`: integrity ok, 0 foreign-key problems; matches 223,636; quarantine 273; **forecast_runs 1 / forecasts 30** (the Premier League Matchday 9 run, preserved); simulation_runs 2 (Bundesliga seed 1398654699, La Liga seed 1499656622, unchanged); six competitions answer (67 of 67 checks).
- **Database hash (current, and after every later check): `410d9fe1755742c83cd03bac2a0ded8225365a59cbfba09fccfb20bd5e825a38`**.
- Fresh backup: `data/backups/p428_fresh_20261028/footiq.sqlite` (229,015,552 bytes), hash in `SHA256.txt` equals the line above; integrity ok; the same row counts and forecast rows hash. The older Phase 4.24 backup was not restored and remains as a second rollback point.

## 2. StatsBomb cleanup (Part B)
- Preflight (`data/supervised/phase4/p428/statsbomb_cleanup.py preflight`): preserved files present; the recorded commit and clone command are in `RAW_SOURCES_MANIFEST.csv`; the four exported player/match CSVs and the submission ZIP exist; only four dataset-build scripts name the clone (none in `app/`, `tests/`, `config/`, `scripts/`, the frontend or the model folders); the application runtime footprint does not name it.
- Deleted: **9,006 files, 17.881 GB** (`data/` 8,977 files 16.127 GB and `.git/` 29 files 1.755 GB), nothing skipped, plus 45 emptied directories. Log: `p428/statsbomb_deletion_log.csv` (timestamp, path, bytes, status per file); list: `statsbomb_delete_list.csv`.
- **Preserved:** `LICENSE.pdf`, `README.md`, `doc/`, `img/`, `.github/`, `.DS_Store`; `FootIQ_Dataset_Submission` exports, ZIP, `RAW_SOURCES_MANIFEST.csv` and provenance. Added `FootIQ_Dataset_Submission/_raw_sources/STATSBOMB_RECONSTRUCTION.md` (pinned commit `4b73468f...` and the commands to recreate the clone). Consequence: `_build/build_players_statsbomb.py` cannot be re-run until the clone is recreated.
- **Storage:** recovered 17.881 GB. Project size: before 22.05 GB (Phase 4.26 inventory), now about **4.6 GB** (4.5-4.6 GB depending on method) without test scratch; see section 8 for 2.6 GB of test scratch from this phase's own test run.

## 3. Season simulator fix (Part C)
`frontend/src/pages/SeasonSimulator.jsx`: for the chosen league the page asks `/api/season/status` for every stored season and offers only those with unplayed fixtures to simulate (`counts.remaining_to_simulate > 0`), newest first and selected by default; finished historical seasons are hidden; if none qualifies the Season box is disabled and the page says "No season to simulate", with no request that could run a simulation. No prediction or simulation logic changed. Result in the real app: Bundesliga, La Liga, Premier League, Serie A and Ligue 1 each offer only **2026-27**, selected, with the eligibility banner (Serie A "Provisional"). Tests (`frontend/tests/p428-fixes.test.jsx`): only the current season shown; several eligible seasons kept in order; no eligible season handled.

## 4. Predict Match prefill fix (Part D)
Cause: `Predict.jsx` cleared the clubs in an effect guarded by a one-shot "preselected" flag; React StrictMode (development) runs effects twice, consumed the flag and cleared the clubs. Fix: remember the competition the selection belongs to and reset only when it really changes. Competition and club identifiers are kept. Verified: in the dev server (StrictMode) a Champions League card opened Predict with LASK Linz v ŠK Slovan Bratislava filled and `comp=UCL`; in a **production build** (served on port 5174) Chelsea FC v Manchester United FC and `comp=EPL` stayed filled. Regression tests run each case with and without StrictMode (Premier League, Champions League, and a real competition change still clears the clubs); the StrictMode tests were confirmed to **fail on the old code**.

## 5. Documentation (Part E)
New: `docs/mini-project/final/FINAL_SYSTEM_GUIDE.md` (six competitions and coverage, results/fixtures/standings/predictions, Champions League league-phase support and its not-validated status, frozen models, saved simulations, data-engineering pipeline, sources/licences/attribution, start and stop, known gaps, how to demonstrate). Rewritten: `SETUP_AND_RUN.md` (sections 4-7), `DEMO_SCRIPT.md`, `LIMITATIONS.md`, `DATA_SOURCES.md`. Phase 4.28 notes (superseded statements named) added to `ARCHITECTURE.md`, `ML_MODELS.md`, `PROJECT_REPORT.md`, `VIVA_QA.md`, `SUBMISSION_CHECKLIST.md` (and one stale check line fixed), `TESTING_REPORT.md` (new section 0). Also `README.md`, `app/README.md`, `MINI_PROJECT_PLAN.md` (status paragraph). Before-copies: `data/supervised/phase4/p428/before/`. Historical phase reports unchanged. **Not done:** the bodies of `ARCHITECTURE.md`, `ML_MODELS.md`, `PROJECT_REPORT.md` and `VIVA_QA.md` still contain the older text (World Cup, international model) under the supersession note, not rewritten line by line.

## 6. Tests (Part F)
| | Result |
|---|---|
| Frontend `npx vitest run` | **367 passed, 13 skipped** (16 files passed, 2 skipped) |
| Backend full `pytest tests` (23 min) | **567 passed, 8 skipped, 4 failed** |
| The 4 failures | all in `tests/test_seasonsim_service.py`: `test_todays_eligibility_matches_the_planned_gates`, `test_la_liga_run_uses_its_verified_rule_profile_and_is_consistent`, `test_points_only_status_follows_data_quality_and_the_approved_scope`, `test_points_only_la_liga_run_is_sane`. They hard-code the data as it was before the Phase 4.22-4.24 imports (287 remaining La Liga fixtures, now 281; a league expected "not_eligible" is now "ready"). Backend code is unchanged in this phase; they were not in the earlier targeted 295 and were last run in a full suite before those imports. Not edited. Full output: `p428/full_backend.txt` |
| Production build | `npm run build` ok |

## 7. Live verification
- `final_verify.py` on the running backend (8000): **67 of 67**; on a fresh second instance (8001, sync disabled, started with the documented command): **67 of 67**, ready in about 18 s, stopped with one Ctrl-C and shut down cleanly ("Application shutdown complete"). Evidence: `p428/final_verify_8000.json`, `final_verify_8001.json`.
- Six competitions: dashboards, results, standings (or the league-phase table), fixtures, team pages and predictions work (80 / 99 / 63 / 80 / 72 / 54 completed; 300 / 280 / 243 / 297 / 234 / 90 upcoming); five leagues "Validated", Champions League "Not validated (indicative only)"; archived competitions 404 / 422; sync startup-only (OpenLigaDB).
- Frozen hashes: all five match; simulations 1 and 2 retrievable with their seeds; forecast run 1 with 30 rows; database integrity ok; hash `410d9fe1...` unchanged.

## 8. Remaining issues
1. **4 outdated backend tests** (section 6): need their expected data values updated to the current database, or approval to do so.
2. **2.6 GB of test scratch** written by this phase's full backend run in `data/supervised/pytest_tmp/p428` (the 7.2 GB total project size includes it). It is not part of the approved deletions, so it was left; removing it brings the project to about 4.6 GB.
3. Premier League, Serie A, Ligue 1 and Champions League have no update source; 3 Serie A results unapplied, 1 La Liga postponement and 60 date corrections held.
4. Known occasional shutdown lingering (use the documented stop procedure); `scipy` missing from requirements files; `/worldcup` route alias in `App.jsx`.
5. `frontend/dist` was rebuilt by the production-build check; `SeasonSimulator.jsx`, `Predict.jsx` and `p428-fixes.test.jsx` are uncommitted changes (no Git operation performed).
