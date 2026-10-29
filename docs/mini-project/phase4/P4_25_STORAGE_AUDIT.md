# Phase 4.25: storage audit and safe cleanup preparation

**Audit only.** Nothing was deleted, moved, compressed or rewritten. The production database, the running backend (not stopped or restarted), the application code, the models, the synchronisation and Git were not touched. Audit tools and outputs are in `data/supervised/phase4/p425/` (about 4 MB): `inventory.csv` (every file), `sqlite_survey.csv` (all 150 database copies with hash and content), `runtime_footprint.csv` / `runtime_modules.txt` (what the application opens), `cleanup_manifest.csv` (proposal) and `cleanup_manifest_files_AB.csv` (the exact file list of categories A and B, 1,960 files).

## 1. Total project size
**37.14 GB in 42,939 files** (D:\Foot IQ, symbolic links not followed). By extension: `.json` 16.2 GB and `.sqlite` 15.6 GB (150 files) dominate.

## 2. Storage by folder
| Folder | Size | What it is |
|---|---|---|
| `FootIQ_Dataset_Submission/` | 18.35 GB | the submitted dataset; **17.88 GB of it is one raw-source clone** (`_raw_sources/statsbomb_open_data`: 16.13 GB data + 1.76 GB git history) |
| `data/` | 15.96 GB | `supervised` 12.93 GB, `backups` 2.75 GB, `footiq.sqlite` 0.23 GB (production), `raw` / `processed` 0.04 GB, `snapshots` 0.01 GB |
| `FootIQ_Club_Model_Development_v2/` | 0.75 GB | v2 model study: `matched_v1_prospective_r1` 0.24, `source_adapters_r1` 0.23 (0.22 is `pilot`), `_work` 0.20, `final_refit_v2_r1` 0.07 (frozen model) |
| `FootIQ_ML_Data_Readiness/` | 0.64 GB | `_build` 0.35, training datasets 04a/04d/08 ~0.27 |
| `.venv/` | 0.38 GB | Python dependencies (13,240 files) |
| `FootIQ_ML_Training_Preparation/` | 0.36 GB | `_build` 0.22, corrected datasets 01/02/03 ~0.14 |
| `docs/` | 0.20 GB | `baseline/capture_2026-10-20` 0.16, `mini-project` 0.04 |
| `.git/` | 0.16 GB | repository history |
| `FootIQ_ML_Data_Verification/` | 0.15 GB | `player_form_v1` 0.15 |
| `frontend/` | 0.14 GB | `node_modules` 0.14 (10,709 files); source, tests and `dist` ~2 MB |
| `FootIQ_Club_Model_Baseline_v1/` | 0.02 GB | frozen model v1, metrics |
| `app/`, `tests/`, `scripts/`, `config/`, `logs/`, `outputs/`, `scratch/` | ~0.01 GB together | code, tests, configuration, old logs |
`data/supervised` in detail: `phase4` 11.06 GB (of which `p44` 7.23, `p419` 0.92, `p46` 0.54, `p421` 0.46, `p49` 0.46, `p45` 0.46, `p423` 0.23, `p412` 0.23, `p48d` 0.23, `p410` 0.23), `rehearsal` 0.69, `production_import` 0.46, three loose database copies 0.69, `rules_research` 0.025, `pytest_tmp` 0.01, `phase3` 0.006.

## 3. Top 20 largest files
| # | File | Size | Status |
|---|---|---|---|
| 1 | `FootIQ_Dataset_Submission/_raw_sources/statsbomb_open_data/.git/objects/pack/pack-ff32...pack` | 1,753 MB | C, optional (StatsBomb clone history) |
| 2 | `data/supervised/phase4/p412/private_copy.sqlite` | 229 MB | B, redundant copy |
| 3 | `data/supervised/phase4/p44/pytest_baseline/sim0/store.sqlite` | 229 MB | A, temporary |
| 4 | `data/supervised/phase4/p423/rehearsal/footiq_reconcile.sqlite` | 229 MB | B, rehearsal copy |
| 5 | `data/footiq.sqlite` | 229 MB | **D, production database** |
| 6 | `data/backups/p424_pre_reconcile_20261028/footiq.sqlite` | 229 MB | **D, current rollback backup** |
| 7 | `data/supervised/phase4/p421/rehearsal/footiq_ucl_fixtures.sqlite` | 229 MB | B |
| 8-9 | `data/supervised/phase4/p419/rehearsal/footiq_fixture_then_result.sqlite`, `footiq_with_fixtures.sqlite` | 229 MB each | B |
| 10 | `data/backups/p422_after_domestic_20261028/footiq.sqlite` | 229 MB | B |
| 11 | `data/supervised/phase4/p421/rehearsal/footiq_domestic.sqlite` | 229 MB | B |
| 12-13 | `data/backups/p422_pre_import_20261028/footiq.sqlite`, `p421_pre_import_20261028/footiq.sqlite` | 229 MB each | B |
| 14-15 | `data/supervised/phase4/p419/rehearsal/footiq_results_only.sqlite`, `footiq_conflicts.sqlite` | 229 MB each | B |
| 16 | `data/supervised/phase4/p46/preview.sqlite` | 229 MB | B |
| 17 | `data/backups/p420_pre_import_20261028/footiq.sqlite` | 229 MB | B |
| 18-20 | `data/supervised/live_test_copy.sqlite`, `phase4/p410/private_copy.sqlite`, `phase4/p49/private_copy.sqlite` | 229 MB each | B |
(The 21st to 40th are more 228-229 MB database copies; `data/supervised/phase4/p44/pytest_baseline` alone holds 291 files, 6.67 GB.)

## 4. Duplicate and redundant database copies
- **150 database files, 15.59 GB, but only 71 distinct contents**; 30 byte-identical groups of files over 1 MB waste 3.4 GB (for example one 228 MB state exists six times inside `pytest_baseline`, three times as an Oct 27 backup plus restore test).
- Almost all are one 223,510-row store at successive moments (differing only in the sync diary, quarantine and saved-simulation tables) or tiny synthetic test databases (about 50, under 12 MB each).
- Only **three** are worth keeping: the production database, the Phase 4.24 rollback backup and `data/supervised/footiq.before-sync.sqlite` (the earliest clean baseline, before any provider sync).
- The two real saved simulations exist in the production database and in every p420-p424 backup; earlier copies hold none or test simulations.

## 5. Other findings
- **Old staging datasets:** `data/supervised/phase4/p417/staging` (59 MB unpacked archives of the removed international competitions), `p417/private_ratings`; the staging files of `p420`, `p421`, `p423`, `p424` are small (1-19 MB) and are **inputs** of the importers: keep.
- **Temporary pytest folders:** `pytest_baseline` (6.67 GB, Phase 4.4) and `pytest_tmp` (10 MB; the folder is recreated by `tests/conftest.py`).
- **Browser profiles:** three headless profiles from the Phase 4.4-4.6 UI probes, 0.18 GB, no reference anywhere.
- **Rehearsal copies:** 7 in `p419` / `p421` / `p423` (1.60 GB), 3 in `supervised/rehearsal`, plus private copies and restore tests of Phase 4.8-4.12 (1.14 GB) and preview / test databases of Phase 4.4-4.6 (1.37 GB).
- **Old logs and generated reports:** `logs/` (11 files, under 1 MB), loose `*.log` / `*.txt` in `data/supervised` (under 1 MB), `outputs/` (163 files, 1 MB), `scratch/` (9 files): negligible; reports in `docs/mini-project/phase4` (35 MB) are project documentation: keep.
- **Archived-competition artifacts** (kept by decision; inventory of Phase 4.18 `data/supervised/phase4/p418/archived_artifacts_inventory.csv`, about 108 MB): national-team data in `data/raw` / `data/processed`, the frozen international model `data/model_artifacts/v27`, openfootball clones and Wikipedia snapshots, and the p417 staging above. **No change proposed to any of them** except the optional C9 below.
- **ML models and training data:** frozen models in `FootIQ_Club_Model_Baseline_v1/artifacts` and `FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts` (hash-verified by the application); training datasets in `FootIQ_ML_Data_Readiness` and `FootIQ_ML_Training_Preparation` (~0.4 GB of CSV) and the dataset-submission CSVs. `FootIQ_Dataset_Submission.zip` (18 MB, 250 MB uncompressed) is the submission package and **does not contain `_raw_sources`**.
- **Dependencies:** `.venv` 0.38 GB, `frontend/node_modules` 0.14 GB: required to run; regenerable (pip / `npm ci`) but not removal candidates.

## 6. Dependency verification (what is really used)
1. **What the running application opens.** I imported the application with synchronisation disabled and traced every `open()` / `sqlite3.connect()` while serving 65 read-only requests for all six competitions (health, meta, dashboard, teams, team, predict, matches, gameweeks, performance, freshness, sync status, league phase, season status; no POST, no simulation, no write). Result: **23 files, 1.2 MB, plus the production database** (and no server error): the two frozen v1 / v2-r1 models, their coefficient, parameter and `FROZEN.json` files, `data/model_artifacts/v27/live_match_model.pkl`, `feature_contract_v1.1.json`, `features_v2_meta.json`, four metrics CSVs, `01_COMPETITION_SEASON_COVERAGE_MATRIX.csv`, `config/sync.json`, `season_rules.json`, `season_sim.json`. **The application opens nothing from `data/supervised`, `data/backups`, StatsBomb or the raw datasets.** Imported project code: `app/` (the modules listed in `runtime_modules.txt`, including `store` and `seasonsim`), four files of `FootIQ_Club_Model_Development_v2/_scripts`, the `footiq_sources` adapters and `FootIQ_ML_Training_Preparation/_build/feature_contract.py` (`runtime_modules.txt`).
2. **Paths the trace cannot exercise (read in the code):** the startup synchronisation loads `FootIQ_Club_Model_Development_v2/source_adapters_r1/footiq_sources` and writes `data/snapshots` and `data/run/scheduler.lock`; the season simulator reads `FootIQ_Club_Model_Baseline_v1/artifacts` and `FootIQ_ML_Training_Preparation/_build`; forecasts load the two model pickles; the baseline monitor / daily audit read `data/supervised/phase4/baselines` and list `data/backups` (listing only). The store rebuild (`app/store/baseline.py`) reads `FootIQ_ML_Training_Preparation/_build/work/V_universe.pkl`, the combined club CSV and `09_Upcoming_Fixtures.csv`: needed only to rebuild the database from scratch.
3. **Tests that depend on files under `data/supervised`:** `tests/test_benchmark_preserved.py` hash-checks five files of `data/supervised/phase3`; `tests/test_phase417_evidence.py` reads `p417/*.json` and the sizes of the downloaded zips in `p417/staging`; the importer tests read the staged files of `p420`, `p421`, `p423` and `p423/evidence.py`; `tests/conftest.py` uses `data/supervised/pytest_tmp` as the pytest temp root.
4. **Nothing proposed in A or B is read** by the application, the scripts or the tests: the names `pytest_baseline`, `chrome-profile`, `live_test_copy`, `demo.sqlite`, `before-sync`, `preview.sqlite`, `tests.sqlite` have 0 references in `app`, `scripts`, `config`, `tests`, `frontend/src`; `private_copy`, `restore_test`, `footiq.rehearsal`, `production_import` appear only in offline scripts that **write** those files; the Windows task `FootIQ-Backend` is disabled and the supervisor script is not running.
5. **Git does not protect these files:** `.gitignore` excludes `data/supervised/`, `data/footiq.sqlite*`, `data/snapshots/`, so anything deleted there is recoverable only by regenerating it.

## 7. Backup review (`data/backups`, 2.75 GB)
| Backup | State | Keep? |
|---|---|---|
| **`p424_pre_reconcile_20261028`** (229 MB, sha256 `afe71c44...`, verified) | production just before the Phase 4.24 reconciliation | **Keep: current rollback point** |
| `p422_after_domestic_20261028`, `p422_pre_import_20261028`, `p421_pre_import_20261028`, `p420_pre_import_20261028` | intermediate states of the 4.20-4.23 imports, each superseded by the next and by p424 | removable (B1) |
| seven `footiq.20261027T...` files (pre-bundesliga x2, pre-laliga x2, pre-activation x2, pre-laliga-import) | Oct 27 states before the first provider syncs; three pairs are byte-identical to each other | removable (B1) |
| `p418_rollback_20261028` (0.6 MB), `p420_code_before` (0.2 MB) | **code** rollback snapshots: no Git commit holds the Phase 4.18-4.23 code | **Keep** |
| `*.json` / `SHA256.txt` notes, `sync.json.20261028T015109Z.pre-startup-mode` | descriptions and the config backup | keep (tiny) |
After removing B1, `data/backups` is ~0.23 GB. Because the Phase 4.24 production state is already in the live database, p424 alone restores the system to the point before the last change; take a fresh backup before any further production change.

## 8. `data/supervised` review (12.93 GB)
| Class | Content | Size |
|---|---|---|
| 1. Required for the running application | **none** (the application opens nothing here). Operations tooling only: `phase4/baselines` (baseline monitor, daily audit) | 0.1 MB |
| 2. Reproducibility / academic submission | `phase3` (test-protected hashes), `rules_research` (rule documents named in `config/season_rules.json`), `hashes_before.json` and `start_manifest.json` (frozen-hash record), importer inputs, evidence and reports of `p413`-`p424`, `p417` evidence and zips, the clean baseline `footiq.before-sync.sqlite` | ~342 MB |
| 3. Useful but optional | phase reports, scripts, logs and run outputs of `p41`-`p48` and this audit | ~5 MB |
| 4. Temporary and regenerable | pytest folders, browser profiles, old builds (A1-A4) | 6.86 GB |
| 5. Redundant copies | rehearsal, private, restore-test, preview, test, demo, live-test and import-backup databases (B2-B5) | 5.72 GB |
**12.58 GB of the 12.93 GB is class 4 or 5; 0.35 GB must stay.** I did not treat any folder as wholly deletable: every item below is a named file set.

## 9. Proposed cleanup manifest (`cleanup_manifest.csv`)
**Category A: safe temporary cleanup** (confirmed unused, regenerable; **6.87 GB**; risk none)
| ID | Path | Size | Purpose | Used now | Regenerable | Action |
|---|---|---|---|---|---|---|
| A1 | `data/supervised/phase4/p44/pytest_baseline/` | 6.671 GB (291 files) | pytest folders of the Phase 4.4 baseline run | no (0 references) | yes (pytest) | delete the folder |
| A2 | `data/supervised/pytest_tmp/pytest-of-DELL/` | 0.010 GB (48 files) | pytest temp root contents | no (the folder itself is recreated by conftest) | yes | delete the contents, keep `pytest_tmp` |
| A3 | `phase4/p44/chrome-profile`, `chrome-profile-p45`, `phase4/p46/chrome-profile-p46` | 0.181 GB (1,440 files) | headless browser profiles | no | yes | delete |
| A4 | `phase4/p44/production-build`, `-final`, `-release` | 0.003 GB | old frontend builds | no | yes (`npm run build`) | delete |
| A5 | `.pytest_cache/` | <0.001 GB | pytest cache | no | yes | delete |

**Category B: redundant database copies** (**8.23 GB**; risk low; after you confirm the retained rollback point)
| ID | Path | Size | Purpose | Used now | Regenerable | Action |
|---|---|---|---|---|---|---|
| B1 | `data/backups/` sqlite files except p424 (4 import backups + 7 Oct 27 files, and their -wal / -shm) | 2.516 GB (31 files) | superseded backups | no | no (past states) but superseded | delete the .sqlite files, keep notes |
| B2 | `phase4/p419`, `p421`, `p423` `rehearsal/*.sqlite` | 1.602 GB (17 files) | rehearsal copies of production | no | yes (`rehearse_*.py`, under 2 min) | delete, keep reports |
| B3 | `phase4/p410`, `p412`, `p49` private copies, `p49/restore_test`, `p48d/restore_test_activation` | 1.144 GB (13 files) | trial and restore-test copies | no | yes | delete |
| B4 | `phase4/p44`, `p45`, `p46` `preview.sqlite` and `tests.sqlite` | 1.372 GB (16 files) | UI preview and test databases | no | yes | delete |
| B5 | `supervised/live_test_copy`, `demo`, `rehearsal/*`, `production_import/*.backup` (.sqlite) | 1.599 GB (15 files) | Oct 25 demo, rehearsal and import backups | no | no, superseded | delete, keep reports and logs |
**Kept databases:** `data/footiq.sqlite`, `data/backups/p424_pre_reconcile_20261028/footiq.sqlite`, `data/supervised/footiq.before-sync.sqlite`.

**Category C: optional historical / archived: needs your separate decision** (19.5 GB; none proposed for automatic removal)
| ID | Path | Size | Notes | Action |
|---|---|---|---|---|
| C1 | `FootIQ_Dataset_Submission/_raw_sources/statsbomb_open_data/` | **17.883 GB** | shallow clone of statsbomb/open-data, commit `4b73468f...` (2026-09-07, recorded in `RAW_SOURCES_MANIFEST.csv`); used only to build the player-statistics CSVs, which stay; not used by the application, models or tests; not part of the submission zip | keep for reproducibility **or** delete and re-clone from the recorded commit if ever needed |
| C1a | the same clone's `.git` only | 1.755 GB | git history of that clone | smaller option: delete only `.git` |
| C2 | `FootIQ_Club_Model_Development_v2/source_adapters_r1/pilot/` | 0.232 GB | adapter pilot snapshots (the adapter code is kept) | optional |
| C3 | `FootIQ_Club_Model_Development_v2/matched_v1_prospective_r1/` | 0.244 GB | prospective-study data | optional (academic evidence) |
| C4 | `FootIQ_Club_Model_Development_v2/_work/` except `features_v2_meta.json` | 0.203 GB | intermediate tables of the v2 study | optional; **`features_v2_meta.json` is loaded by the application** |
| C5 | `FootIQ_ML_Data_Readiness/_build/` | 0.351 GB | build work files | keep unless you accept losing a from-scratch rebuild |
| C6 | `FootIQ_ML_Training_Preparation/_build/` except `feature_contract.py` | 0.222 GB | includes `V_universe.pkl` (from-scratch store build) | same; **`feature_contract.py` is imported by the application** |
| C7 | `docs/baseline/capture_2026-10-20/` | 0.162 GB | baseline evidence capture with five repeated copies of the same data files | optional: keep the manifest, dedupe |
| C8 | `FootIQ_ML_Data_Verification/player_form_v1/` | 0.149 GB | player-form tables | optional |
| C9 | `phase4/p417/staging/*/unpacked/`, `p417/private_ratings/` | 0.058 GB | archived international staging (the zips and evidence stay for the test) | optional |

**Category D: must preserve**
`data/footiq.sqlite` (+ -shm / -wal); the p424 backup and its hash note; `data/supervised/footiq.before-sync.sqlite`; the code rollback snapshots `data/backups/p418_rollback_20261028` and `p420_code_before`; **frozen models and their verification hashes**: `FootIQ_Club_Model_Baseline_v1/artifacts`, `FootIQ_Club_Model_Development_v2/final_refit_v2_r1`, `data/model_artifacts/v27`, `data/supervised/hashes_before.json`; **both saved simulations** (inside the production database and every p420-p424 backup); `data/snapshots` (provider snapshots, `request_ledger.jsonl`: provenance); `data/miniproject` (CSV fallback and audit tables); `config/`; `app/`, `tests/`, `scripts/`, `frontend/src`, `frontend/tests`, package files; `docs/` (including `mini-project/phase4`); `.git`; `.venv`; `frontend/node_modules` (regenerable but required to run); the dataset-submission CSVs, `QA_Reports`, `_build`, `FootIQ_Dataset_Submission.zip`; the training and readiness CSVs and the verification and metrics reports; attribution and provenance in `RAW_SOURCES_MANIFEST.csv`, `DATASET_PROVENANCE_DETAILS.json`, `data/supervised/rules_research`, `phase3`, and the staging, evidence and reports of `p413`-`p424`; `data/raw` / `data/processed` archived-competition data (no change to archived competitions).

## 10. Estimated recoverable storage
| | Size | Project after |
|---|---|---|
| Current | 37.14 GB | |
| **A: safe temporary cleanup** | **6.87 GB** | 30.27 GB |
| **B: redundant copies and old backups** | **8.23 GB** | 22.04 GB |
| **A + B (safe estimate, 1,960 files)** | **15.10 GB (40.7%)** | **22.04 GB** |
| C1 StatsBomb clone (your decision) | up to 17.88 GB | 4.16 GB |
| Other C items (C2-C9) | ~1.6 GB | |
Preserved after A + B + C1: about 4.2 GB, of which the three databases are 0.69 GB, dependencies 0.52 GB, `.git` 0.16 GB.

## 11. Risks and dependencies
1. **Unrecoverable by Git:** `data/supervised`, the database files and `data/snapshots` are git-ignored; deleted copies exist only by regeneration. B1 backups are past states of the database that cannot be recreated, but p424 plus the live database cover every restore need.
2. **Rollback after cleanup:** only p424 remains; make a new verified backup before the next production change.
3. **Do not delete anything under the preserved lists above;** in particular the five hash-checked `phase3` files and the `p417` zips would make two existing tests fail or skip, and `p420` / `p421` / `p423` staged files are the importers' inputs.
4. **C1 is the only large saving that costs something:** the raw StatsBomb data of the dataset you built; it is not part of the submission zip and not needed to run anything, but rebuilding the player statistics would need the network and the recorded commit.
5. Deleting files while the backend runs is safe for everything in A and B (the backend holds only `data/footiq.sqlite` open); do not touch that file or `data/snapshots`.
6. Windows may keep a browser profile (A3) locked if a probe browser is still open; close it first.

## 12. Recommended cleanup order (after your approval)
1. Confirm the p424 backup hash (`afe71c445bfeddcb...`) and that `/api/health` is ok; note the production database hash.
2. **A2, A4, A5, A3** (small, no risk), then **A1** (6.67 GB).
3. **B2, B3, B4, B5** (rehearsal, private, preview, test, demo and import-backup copies, 5.72 GB).
4. Re-check: production database hash unchanged, `/api/health`, a six-competition GET check, the targeted tests.
5. **B1** last (older backups, 2.52 GB), keeping p424, the code snapshots and the notes.
6. Decide C1 / C1a and the optional C items separately; if C1 is removed, keep a note of the commit `4b73468f...` and the clone command.
7. Write a deletion log (path, size, hash where relevant) and re-run the inventory to confirm the new total.

## 13. Application health after the audit
No change was made to the project's operating files. The backend answered `/api/health` ok (15,855 rows) throughout; the production database hash is `376afad6...`, identical before and after the audit (the trace opened it read-only with synchronisation disabled); the request ledger is unchanged.
