# Phase 4.34: GitHub push readiness audit (including datasets)

**Audit and proposal only. Nothing was staged, committed, pushed or changed in Git (no history, remote, `.gitignore` or `.gitattributes` change); no project data file was modified; the production database hash is unchanged (`9d40c8ef...`).** Everything is waiting for your approval. Evidence and tools: `data/supervised/phase4/p434/` (`proposed_manifest.py` and `.csv`, `exclusions_summary.csv`, `duplicates_in_proposed_set.csv`, `scan_secrets.py` and `secrets_scan.csv`, `db_personal_scan.py`, `simulate_clone.py`, `proposed.gitignore`, `proposed.gitattributes`).

## 1. Current branch and GitHub remote
- Branch `feat/club-ml-v2` at `970f461` ("Mini Project Scope Update"), tracking `origin/feat/club-ml-v2`. Remote `origin`: `https://github.com/neilsenvaz10/FootIQ---Football-Data-Engineering-Analytics-Machine-Learning-Platform.git` (fetch and push).
- `origin/main` is at `685910e` ("Merge pull request #2 from neilsenvaz10/feat/club-ml-v2"): `HEAD` is an ancestor of it and **the trees are identical** (`git diff HEAD origin/main` is empty), so a new branch from `HEAD` merges cleanly. Local `main` is 3 commits behind `origin/main`.
- Working tree: 14 modified and about 86 untracked top-level entries (the whole Phase 1-4 application: `app/*`, `app/store`, `app/seasonsim`, `frontend/`, 24 new tests, `docs/mini-project/*`, `config/*.json`, `scripts/ops`, `scratch`). 943 files are tracked (88 MB; `.git` is 155 MB). `.gitignore` currently hides `FootIQ_Dataset_Submission/`, `FootIQ_ML_Data_Readiness/`, `FootIQ_ML_Data_Verification/`, the three large training CSVs, the large pickles, `data/footiq.sqlite*`, `data/snapshots/` and `data/supervised/`: that is why the datasets are not on GitHub today. `.gitattributes` has no LFS entry. Source files are CRLF in the working tree (Git warns on 7 files).
- Git LFS 3.7.1 is installed. The GitHub CLI (`gh`) is not installed (not needed). Commit identity: `neilsenvaz10` (the remote history already carries it).

## 2. Datasets proposed for inclusion
Role, source and licence per dataset (licences from the project's own audits `FootIQ_ML_Data_Verification/08_SOURCE_AND_LICENSE_AUDIT.md`, `RAW_SOURCES_MANIFEST.csv`, per-row `licence` columns, and the StatsBomb user agreement read in full):

| Dataset (path) | Role | Source / licence | Size | Decision |
|---|---|---|---|---|
| `FootIQ_ML_Data_Readiness/04a..04e` league, cup, continental and combined club matches; `05` identity mapping; `08` training-ready extended and strict; schema, coverage, leakage reports | historical club matches, ML training/validation/test inputs, store baseline | openfootball CC0-1.0; 1.2% of extended rows Wikipedia (CC BY-SA 4.0, attribution in the `provenance` column) | 285 MB (4 files LFS: 04d 69.4, 08 extended 62.3, 04a 62.0, 08 strict 60.4 MiB) | **include** with notice |
| `FootIQ_ML_Training_Preparation/01, 02, 03` corrected datasets, feature contract, reports | ML training inputs and correction log | same sources | 259 MB (01: 52.1 MiB and 03: 56.8 MiB LFS) | **include** |
| `FootIQ_ML_Training_Preparation/_build/work/V_universe.pkl` | frozen model universe; **read by `app/store/baseline.py` to build the store** | derived from the above | 111.6 MiB (over GitHub's 100 MiB block) | **include via LFS (required)** |
| `FootIQ_Dataset_Submission/01` international, `02` club (99.1 MiB, LFS), `03` recent results, `09` fixtures, `10-13` dictionary, summary and coverage, `RAW_SOURCES_MANIFEST.csv`, `QA_Reports` | historical international and club matches, recent results, current-season fixtures, provenance | martj42 CC0-1.0, openfootball CC0 | 134 MB | **include** |
| `FootIQ_Dataset_Submission/04, 05, 06, 07, 08, 14` (players, player match statistics, teams, competitions, memberships, StatsBomb index) and `FootIQ_ML_Data_Verification/player_form_v1/*STATSBOMB*`, `data/raw/statsbomb` | player statistics | **mixed with StatsBomb Open Data** (see section 6) | 116 + 120 + 3 MB | **do not push** (replace by generated CC0-only extracts, see below) |
| `FootIQ_ML_Data_Verification/player_form_v1/PLAYER_RECENT_FORM_OPENFOOTBALL_APPEARANCES` | player appearances | openfootball CC0 | 29 MB | include |
| `data/miniproject/matches.csv`, `data_audit.csv`, `season_coverage.csv` | dashboard dataset the tests use | derived CC0 | 5 MB | include |
| `data/raw` (international_results CC0, openfootball CC0, worldbank CC BY 4.0, Wikipedia squads CC BY-SA) and `data/processed` | archived international / World Cup pipeline inputs and outputs | see section 6 | 19 + 22 MB | include (with the flagged exceptions) |
| `data/snapshots/openligadb`, `p48c`, `p48d_trial`, `investigation`, `request_ledger.jsonl` | provenance of the synchronisation (stored responses) | OpenLigaDB ODbL-1.0 | 7 MB | include with ODbL notice |
| `data/supervised/phase4` (importer inputs: `p417/uefa_2026_27_staging.csv`, `p419`, `p420/staging`, `p421`, `p423/staging`; verification tools; evidence) and `phase3` | data-engineering pipeline inputs, outputs and evidence | Wikipedia CC BY-SA derived staging; evidence | 38 + 6 MB | include (without `footballdatauk_*` / `fixturedownload*` raw copies, 1 MB) |
| `FootIQ_ML_Data_Readiness/raw_external/wikipedia` (wikitext cache) | provenance of the Wikipedia rows | CC BY-SA 4.0 (notice required; the audit says not to ship it without one) | 7 MB | include with notice |
| Models: `FootIQ_Club_Model_Baseline_v1` (artifacts, metrics, predictions CSVs), `FootIQ_Club_Model_Development_v2/final_refit_v2_r1` artifacts, `data/model_artifacts/v27` | frozen models, evaluation | project's own | 22 + 1 + small | include (all < 50 MiB) |
| `data/footiq.sqlite` (229 MB) | production store | CC0 + CC BY-SA + ODbL + 130 unlicensed rows | 229 MB | **not pushed automatically; see section 5** |

**Total proposed dataset-like content: 833 MB across the files above** (of it 574 MiB through LFS); whole proposed repository tree 887 MB in 2,024 files (Git 286 MB raw, LFS 601 MB). **Generated CC0-only player extracts** (not yet created, proposal): `04/05/06/07/08` filtered to rows whose `source_dataset` is openfootball (about 15,382 of 25,288 players, 66,549 of 180,172 player-match rows, 15,972 of 34,277 memberships; about 47 MB raw, about 8 MB compressed), made by a script that filters by the licence column, not by size, and not a truncation. Your decision (section 10).

## 3. Large files and Git LFS
GitHub: warns at **50 MiB**, blocks at **100 MiB**, recommends repositories under 1 GB (strongly under 5 GB), browser uploads 25 MiB (docs.github.com, read today). Eight files qualify for LFS (explicit paths, not wildcards; `proposed.gitattributes`):

| File | MiB |
|---|---|
| `FootIQ_ML_Training_Preparation/_build/work/V_universe.pkl` | 111.6 (over the hard limit: LFS or exclusion; required for the store build) |
| `FootIQ_Dataset_Submission/02_Historical_Club_Matches.csv` | 99.1 (0.9 MiB under the block) |
| `FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv` | 69.4 |
| `FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv` | 62.3 |
| `FootIQ_ML_Data_Readiness/04a_LEAGUE_RESULTS_v1.0.csv` | 62.0 |
| `FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv` | 60.4 |
| `FootIQ_ML_Training_Preparation/03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv` | 56.8 |
| `FootIQ_ML_Training_Preparation/01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv` | 52.1 |
| **Total** | **573.6 MiB** |
No dataset is split or truncated. Files over 100 MiB that are **not** proposed (172 MiB `data_all.pkl`, the 110-117 MiB prospective-study and pilot pickles, `club_matches_all.csv`, `E_final.pkl`, `PLAYER_RECENT_FORM_STATSBOMB`) are regenerable intermediates or StatsBomb-derived, never required to run (section 9).

## 4. Git LFS quota and hosting feasibility
GitHub documentation (read today): **GitHub Free includes 10 GiB LFS storage and 10 GiB bandwidth per month**; every LFS download counts against the repository owner's bandwidth (clones, pulls, Actions, source archives that include LFS objects; forks count against the parent). The page does not state the per-file LFS maximum for your plan (assumed 2 GB for Free; not verified here, all our files are under 112 MiB). Over quota without a payment method: storage full = you can still clone but get pointer files and cannot push; bandwidth exhausted = LFS disabled until next month.
Feasibility: 574 MiB (0.56 GiB) of storage uses about 6% of the quota; **each full clone downloads about 0.56 GiB, so roughly 17 full clones per month** exhaust the bandwidth (fewer if the database snapshot is also in LFS: 218 MiB more, about 12 clones). That is adequate for a college project and a few reviewers; it is not for public traffic or CI that clones on every push. Mitigation: LFS only for the 8 files; the clone instructions use `GIT_LFS_SKIP_SMUDGE=1` plus `git lfs pull --include` for people who need only the code.
Simulated check (a copy of the proposed GIT and LFS files into a scratch folder, `simulate_clone.py`): 2,041 files, 888 MB; `python app/store/build.py` rebuilt the store in 23 s with the **same four input SHA-256 hashes** the production store recorded (baseline universe, 04d, dashboard matches, fixtures); the backend started in 24 s (six competitions, predictions working); 117 targeted tests passed (5 skipped). An actual `git clone` could not be tested before a push exists.

## 5. The production SQLite database
- **Is a snapshot necessary for the demo?** Yes for the current six-competition state. A clone without a snapshot builds only the **baseline** store (data through 2026-09-20): Premier League 50 results instead of 80, Champions League 18 results and 0 fixtures instead of 54 + 90, and the season simulator reports "not eligible" (30 fixtures past their date without a result). Reproducing the current state needs the importers to be replayed on top of the baseline (inputs are in the repository, the apply sequence of Phases 4.19-4.24 is documented, **but a full replay was not verified**) plus the OpenLigaDB refresh for 61 rows.
- **Can it be distributed legally and safely?** Safety: no personal data (no e-mail, name or local path found in any text column). Licence: 99.9% of the rows are CC0; **989 Wikipedia rows (CC BY-SA 4.0 share-alike), 61 OpenLigaDB rows (ODbL-1.0 share-alike on the database) and 130 World Cup rows (9 from API-Football) whose licence is recorded as "not asserted"**. A single merged SQLite file combines share-alike sources and unlicensed rows, which is the weakest legal position (I am not a lawyer; this is a risk assessment).
- **Options:** (A, recommended) do not commit the database; publish the build recipe (baseline build + documented importer replay) and, for the demo, a sanitized snapshot as a **GitHub Release asset** (deflate about 32 MB, no repository or LFS cost) if you accept the licence statement below. (B1) the same snapshot through LFS (+218 MiB). (C) no database at all, with the baseline-state demo.
- **Sanitization if you choose A or B1:** delete the 130 unlicensed rows (all archived World Cup, not part of the six competitions), keep the rows with their per-row `licence` column and add `DATA_LICENSES.md`: attribution for Wikipedia (CC BY-SA), OpenLigaDB (ODbL, attribution and the database stays under ODbL), openfootball and martj42 (CC0). Keep saved simulations and forecasts (application outputs, no personal data) or reset them: your choice. Never publish the WAL files; publish a checkpointed copy and its SHA-256.

## 6. Dataset licence and attribution findings
1. **StatsBomb Open Data: blocker for the player datasets.** The User Agreement (read from `LICENSE.pdf`, kept in the project) says the user may not "edit, distort, distribute, reproduce, sell or in any way provide the data to any external or third party" (1.2.1) nor commercially exploit the data or analysis (1.2.2), and must credit any published analysis with the StatsBomb logo (1.4). Files derived from StatsBomb rows: `04`, `05`, `06`, `07`, `08`, `14`, `player_form_v1/*STATSBOMB*`, `data/raw/statsbomb` (3 MB, 131 files). Pushing them to GitHub is distribution. **Do not push; acquisition alternative:** `RAW_SOURCES_MANIFEST.csv` and `FootIQ_Dataset_Submission/_raw_sources/STATSBOMB_RECONSTRUCTION.md` give the repository and the pinned commit `4b73468f...`; the build scripts (`_build/build_players_statsbomb.py`) regenerate the tables locally.
2. **Wikipedia (CC BY-SA 4.0):** the existing audit left the share-alike scope open ("legal review needed before redistribution"). Affected: 1.21% of the training rows, `raw_external/wikipedia`, the UEFA staging and verified-result CSVs, 989 database rows. Proposal: ship with a notice and per-file licence statement; accept that those files are CC BY-SA.
3. **OpenLigaDB (ODbL-1.0):** snapshots and 61 rows: ship with attribution; share-alike applies to derivative databases.
4. **openfootball and martj42 (CC0):** no restriction; keep the attribution anyway.
5. **football-data.co.uk and FixtureDownload: do not push.** The audit says private use only and no automated use. They were "never stored in the database" but the importer evidence CSVs (`p420` staging, `p423/proposed_changes.csv`) have columns `footballdatauk_score`, `fixturedownload_score`, `footballdatauk_date` and the raw copies `footballdatauk_*.csv`. The raw copies (17 files) are excluded; the evidence columns need a decision (strip them from a published copy, which may affect replaying the reconcile importer, untested).
6. **football-data.org:** the PL/SA/FL1 API responses in `data/snapshots/footballdata` (1 MB) are excluded; `provider_date` columns in the same evidence CSVs fall under item 5.
7. **API-Football (provider-restricted) material is already on GitHub:** 19 tracked files in `data/processed` (`v25_*`, `friendlies_v24_*`, `*_lineups*`, odds, weather, provider fixture matches). History cannot be rewritten in this task; I recommend you review them and decide whether to remove them in the new commit (they would stay in history). Not touched.
8. **League regulation PDFs and text** (`data/supervised/rules_research`, 25 MB: Premier League Handbook, LFP, FIGC, RFEF, DFL): public but copyrighted documents; excluded. `config/season_rules.json` already stores each URL and SHA-256, so the acquisition alternative is a table of those URLs (to be added to the docs).
9. **FIFA ranking page copy** (`data/raw/fifa`, 0.2 MB) excluded; **RSSSF pages** (in `_raw_sources`) excluded.
10. **No `LICENSE` file exists for the project's own code** and no `DATA_LICENSES.md`/`NOTICE`: both are proposed additions (you choose the code licence; MIT or Apache-2.0 are common for coursework).

## 7. Security scan
Scanned every text file proposed (about 7,100 files, excluding `.venv`, `node_modules`, `.git`, caches, backups, captures). **Secrets: none** (no API key, token, Bearer header, private key; the single `token` hit is the dummy constant in `tests/test_footballdata_sync.py`). `.env` does not exist; `.env.example` has an empty key. **Personal data:** the owner's e-mail appears only in `config/contact.local`, which is ignored by `config/.gitignore` and excluded (the application sends it as the OpenLigaDB contact; a clone works without it when synchronisation is disabled); test files use `@footiq-test.local` addresses; two draft e-mails name a provider contact (`daniel@football-data.org`, public); the regulation text contains league e-mail addresses (excluded). The Windows user name `DELL` and absolute paths `C:\\Users\\DELL...` / `D:\\Foot IQ` appear in 12 and 144 evidence and log files (cosmetic). The database has no personal data. Football data names public players and clubs (public sports data).

## 8. Proposed `.gitignore` and `.gitattributes` changes (drafts in `p434/`)
- `.gitignore`: keep secrets, environments, caches and build output; **stop hiding** the included datasets and `data/snapshots`, `data/supervised` (tools and inputs); **add** explicit excludes for the non-redistributable data (StatsBomb files, football-data copies, regulation PDFs, `_raw_sources`, FIFA copy), the database and its WAL files, backups, test scratch and the regenerable intermediates, with `!` exceptions for `V_universe.pkl` and `features_v2_meta.json` (patterns written so Git can re-include them).
- `.gitattributes`: keep `data/raw/** -text` and the binary kinds; add LF normalisation for source text (removes the CRLF warnings) and the 8 explicit LFS lines (574 MiB). `*.pkl binary` stays; the V_universe LFS line is more specific.

## 9. Estimated upload size and missing reproducibility artifacts
- **Upload (without the database):** about **79 MB** of Git objects after compression (286 MB raw, 2,016 files) + about 8 MB for the generated CC0 extracts + **574 MiB LFS** = about **0.66 GB**. With the database through LFS: +218 MiB; as a Release asset: +32 MB outside the repository. The existing remote history is already 155 MB. Cloning everything: about 0.8 GB (LFS included).
- Excluded from the project folder: 1.93 GB (`exclusions_summary.csv`): regenerable pickles 0.9 GB, StatsBomb-derived 0.24 GB, backups, intermediates, copies of upstream repositories (36 MB, re-clonable), regulation PDFs (25 MB).
- Duplicates: none identical across the large datasets; **55 groups (7.8 MB)** of identical small files remain inside the proposed set (OpenLigaDB snapshot copies in four folders, repeated dry-run outputs; list in `duplicates_in_proposed_set.csv`): proposal to keep one copy each (needs a decision because phase reports cite paths).
- **Missing or unverified artifacts:** (1) `LICENSE` for the code and `DATA_LICENSES.md`/`NOTICE` with attributions and the StatsBomb credit; (2) the script that generates the CC0-only player extracts and a CLONE/SETUP section for LFS (`git lfs install`, `git lfs pull`), data acquisition (StatsBomb clone at the pinned commit, regulation PDFs by URL) and database initialisation (`build.py`, importer replay or the snapshot download); (3) the importer **replay** to the current state is documented but not verified; (4) `scipy==1.17.1` is missing from the requirements files (use the `requirements-final.txt` described in P4_32); (5) the Phase 4.7 text of some documents; (6) the final screenshots of the interface (none exist for the six-competition version); (7) the literature survey (not written). Not missing: frozen models, hashes (`ML_MODELS.md`), tests, evaluation metrics, provenance manifests, the baseline build inputs (verified by the simulated clone).

## 10. Recommended Git commands and commit message (not run)
Decisions needed first: (a) StatsBomb-derived files excluded with CC0-only extracts generated, yes or no; (b) database option A, B1 or C; (c) keep or remove the 19 API-Football-derived files in `data/processed`; (d) strip the football-data columns from the evidence CSVs or exclude those two evidence files; (e) code licence; (f) LFS for the 8 files.
```bash
git fetch origin
git switch -c feat/footiq-final-six-competitions        # from the current HEAD (same tree as origin/main)
git lfs install
# apply the approved .gitignore and .gitattributes drafts, add LICENSE and DATA_LICENSES.md, generate the CC0 extracts
git add .gitignore .gitattributes LICENSE DATA_LICENSES.md
git add app config frontend tests scripts scratch docs outputs README.md PROJECT.md README_SHARE.md requirements-final.txt
git add FootIQ_Club_Model_Baseline_v1 FootIQ_Club_Model_Development_v2 FootIQ_ML_Data_Readiness FootIQ_ML_Training_Preparation FootIQ_ML_Data_Verification FootIQ_Dataset_Submission data
git lfs ls-files                                       # must list exactly the 8 files
git status --short | head -50                          # confirm no excluded path is staged
git commit
git push --dry-run -u origin feat/footiq-final-six-competitions
git push -u origin feat/footiq-final-six-competitions  # then open a pull request into main; no force-push
```
Commit message proposal:
```
Add FootIQ six-competition application, data pipeline, models and datasets

- FastAPI backend, React frontend, SQLite store with verified importers (UCL league phase,
  domestic results, reconciliation), startup-only OpenLigaDB refresh
- Frozen club v1 / v2-r1 models, evaluation reports and metrics; points-only season
  simulator for the five domestic leagues
- CC0 / CC BY-SA / ODbL datasets with manifests, provenance and DATA_LICENSES.md;
  eight large files through Git LFS
- Tests (579 backend, 375 frontend) and final documentation
- StatsBomb-derived data, football-data copies and regulation PDFs are not redistributed:
  see the acquisition instructions in the README
```
