# Submission checklist

> **Final state (rewritten in Phase 4.32, 2026-10-28):** FootIQ supports exactly **six competitions** (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League league phase) and an experimental points-only Monte Carlo season simulator for the five domestic leagues. The earlier Phase 4.7 checklist (eleven competitions) is kept in `data/supervised/phase4/p432/before/`. Authoritative description: `FINAL_SYSTEM_GUIDE.md`; package contents and size: `docs/mini-project/phase4/P4_32_FINAL_SUBMISSION_PACKAGING.md`.

M = mandatory, O = optional. **Done** = exists and was checked; **Pending** = needs an action or a decision.

## A. Deliverables

| # | Item | M/O | Status | Location / note |
|---|---|---|---|---|
| 1 | Project report | M | Done | `docs/mini-project/final/PROJECT_REPORT.md` |
| 2 | Source code (backend, frontend, tests) | M | Done, **uncommitted** | `app/`, `frontend/`, `tests/`, `scripts/`. The work is in the working tree only; decide between a Git commit and a zip |
| 3 | Frozen models and verification hashes | M | Done | `FootIQ_Club_Model_Baseline_v1/artifacts/`, `FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts/`; hashes in `ML_MODELS.md` section 6 |
| 4 | Database | M | Done | `data/footiq.sqlite` (229 MB; schema in `app/store/db.py`); verified backups are not part of the submission |
| 5 | Data engineering pipeline | M | Done | `app/store/` importers (`uefa_import`, `league_results_import`, `reconcile_import`), source adapters (`FootIQ_Club_Model_Development_v2/source_adapters_r1`), phase reports 4.9-4.24 |
| 6 | Architecture, ML, data sources, limitations documents | M | Done | `ARCHITECTURE.md`, `ML_MODELS.md`, `DATA_SOURCES.md`, `LIMITATIONS.md`, `FINAL_SYSTEM_GUIDE.md` |
| 7 | Installation and run instructions | M | Done | `SETUP_AND_RUN.md` (clean install tested in Phase 4.32) |
| 8 | Demo script and demo plan | M | Done | `DEMO_SCRIPT.md`, `docs/mini-project/phase4/P4_31_FINAL_DEMO_PREPARATION.md`; **pending: one timed rehearsal by you** |
| 9 | Viva Q&A | M | Done (29 questions) | `VIVA_QA.md`; **pending: read aloud once** |
| 10 | Test reports | M | Done | `TESTING_REPORT.md` section 0 (backend 579 passed / 8 skipped / 0 failed; frontend 375 passed / 13 skipped) |
| 11 | Dataset attribution and licences | M | Done | `DATA_SOURCES.md`, the in-app footer, `/api/meta` |
| 12 | Dataset submission (player and match CSVs) | O | Done | `FootIQ_Dataset_Submission.zip` (StatsBomb credit required; raw clone removed, reconstruction note in `FootIQ_Dataset_Submission/_raw_sources/`) |
| 13 | Screenshots of the final application | M | **Pending** | none taken yet for the final six-competition interface; list in `P4_31_FINAL_DEMO_PREPARATION.md` section 6 and `P4_32_FINAL_SUBMISSION_PACKAGING.md`. The images in `docs/mini-project/phase4/p4.*` show earlier versions |
| 14 | Literature survey | M if your course requires it | **Pending** | only an outline exists (`PROJECT.md` section 12); no written survey. Needs your decision |

## B. Verification (Phase 4.29 to 4.32)

| Item | Result |
|---|---|
| Backend tests | **579 passed, 8 skipped, 0 failed** (full suite, Phase 4.29) |
| Frontend tests | **375 passed, 13 skipped** (the live-API tests, by design); also 375 passed in a clean copy of the package |
| Production build | passes |
| Live verification | 67 of 67 checks on the running backend and on a clean-install package instance |
| Frozen model hashes, database integrity, saved simulations, forecast | verified (Phase 4.30 and 4.32) |

## C. Open items

| # | Issue | M/O | Proposed action |
|---|---|---|---|
| 1 | Nothing is committed to Git | M if the submission is a repository | Your call: commit to the branch or submit a zip of the package |
| 2 | Final screenshots not yet taken | M | Capture from the running application (list in the P4_32 report) |
| 3 | Literature survey not written | M if required | Decide whether it is required; a draft would need verified references |
| 4 | `scipy` is imported directly (`d11_prospective_logger.py`, season simulator) but is not named in the requirements files; it arrives as a dependency of scikit-learn | O | Use the packaged `requirements-final.txt` (adds `scipy==1.17.1`) |
| 5 | `py -3.12` may not resolve on a machine whose Python 3.12 is installed by another launcher | O | Documented alternative in `SETUP_AND_RUN.md` |
| 6 | Position ranges only for Bundesliga and La Liga; Champions League predictions not validated | known | Stated in the application and documents |

## D. Day-of checklist

1. Backend and front end started with the commands in `SETUP_AND_RUN.md`; `/api/health` shows `club_prediction_ready: true`; Home shows no red banner.
2. Remember: **pressing Run in the Season simulator (or Predict gameweek) saves a record to the database in use.** Use 1,000 simulations, or start on a private copy (`FOOTIQ_STORE_PATH`).
3. `config\sync.json` shows `sync_mode: startup` (OpenLigaDB, Bundesliga and La Liga only); offline, start with `FOOTIQ_DISABLE_SYNC=1` (tested: all pages, predictions and simulations still work).
4. Demo script and fallback open; screenshots ready.
5. The honest answers: data is historical (two leagues refreshed once at start); v2-r1 and Champions League predictions are unvalidated; final-position simulation is disabled on purpose.
