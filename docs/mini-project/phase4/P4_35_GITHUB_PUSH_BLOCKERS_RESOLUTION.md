# Phase 4.35: resolving the GitHub push blockers

**Nothing was staged, committed, pushed or rewritten; no remote, history, production data, frozen model or running service was changed.** Files created or edited in the working tree (all untracked or unstaged): `DATA_LICENSES.md` (new), `scripts/rebuild_current_state.py` (new), `app/requirements.txt` (one line added), and evidence under `data/supervised/phase4/p434` and `p435`. Production database hash during the whole phase: `5f38b226...` (it changed only through your own saves before the phase started; no write by me).

## 1. Licensing decisions applied and what stays unresolved
Applied exactly as you decided (manifest: `p434/proposed_manifest.csv`, rules in `proposed_manifest.py`): StatsBomb-derived data excluded (user agreement 1.2.1 read in full: no distribution to third parties); football-data.co.uk / FixtureDownload / football-data.org raw copies and evidence columns excluded; the 19 API-Football files excluded from the new commit; regulation PDFs and text excluded (URLs and SHA-256 stay in `config/season_rules.json`); CC0 (openfootball, martj42) and CC BY-SA / ODbL material kept with attribution in `DATA_LICENSES.md`.
**Unresolved** (also listed in `DATA_LICENSES.md` section 5): the Wikipedia share-alike scope (cautious reading adopted: files with Wikipedia rows are CC BY-SA 4.0); ODbL + CC BY-SA mixed in one database (so the database is not published in the repository); World Bank licence not recorded (CC BY 4.0 presumed, to be confirmed); whether aggregated player statistics are "the data" under StatsBomb 1.2.1; openfootball's own upstream sources; the code licence.

## 2. Dataset inclusion / exclusion manifest (`proposed_manifest.csv`, re-run today)
- **Include:** 2,018 files: 2,010 through normal Git (284 MB raw, about 78 MB compressed) and 8 through LFS (601 MB / 573.6 MiB). CC0: `04a`, `02_Historical_Club_Matches` (100% openfootball CC0), `01` international, `03`, `09`, martj42 data. CC0 + Wikipedia rows (CC BY-SA): `04d` (2.1% Wikipedia), `08` extended/strict, `01`/`03` of Training Preparation, `V_universe.pkl`. OpenLigaDB snapshots (ODbL). Frozen models, evaluation reports, tests, documentation.
- **Exclude (2,398 files, 1.93 GB):** StatsBomb-derived (152 files), API-Football-derived (19), restricted-column evidence (11 CSV) and raw provider copies (17), regulation PDFs and text (25 MB), upstream repository copies (1,890 files; re-clone from the manifest), regenerable pickles, backups, caches, `.venv`, `node_modules`, the SQLite database.
- No excluded path remains in the include list (checked).

## 3. API-Football tracked-file remediation plan
The 19 files already on GitHub (exact paths, also in `p435/tracked_api_football_tier1_19.txt`):
`data/processed/` `confidence_gate_v212_lineup_audit.csv`, `friendlies_v24_confirmed_lineups.csv`, `friendlies_v24_predictions.csv`, `friendlies_v24_provider_fixture_matches.csv`, `friendlies_v24_weather_context.csv`, `road_to_26_v24_provider_fixture_matches.csv`, `v25_confirmed_lineups_live.csv`, `v25_data_quality_live.csv`, `v25_fixtures_live.csv`, `v25_match_predictions_live.csv`, `v25_odds_snapshot_live.csv`, `v25_player_availability_live.csv`, `v25_postmatch_results_live.csv`, `v25_provider_status_live.csv`, `v25_team_strength_live.csv`, `v25_weather_context_live.csv`, `v27_v25_comparison.csv`, `worldcup_matchday_v29_lineup_snapshots.csv`, `worldcup_matchday_v29_lineups.csv` (about 94 KB of provider-derived content in total).
**Recommendation (forward-only, no history rewrite):** while redistribution rights stay unverified, remove them from tracking in the new commit with `git rm --cached -- <19 paths>` and list them in `.gitignore`; the files stay on your disk. They remain visible in old commits (a GitHub history cannot be edited here; if you ever want them gone from history that is a separate, explicit decision). A broader tier of 43 further files in `data/processed` (prediction/validation outputs) only carries provider identifiers and status columns (`provider_fixture_id`, `provider_status`); I did **not** include them in the removal and recommend keeping them, or dropping those columns in a later pass if you prefer.
**Also already tracked and restricted, same forward-only removal recommended:** 134 StatsBomb files (`data/raw/statsbomb/**` 131 files, 2 in `data/processed`, 1 script: the script is code and stays; list `p435/tracked_statsbomb.txt`) and `data/raw/fifa/*` (1 FIFA page copy). No football-data/FixtureDownload file is tracked today (those exist only untracked).

## 4. `DATA_LICENSES.md`
Written at the repository root (draft, untracked). It lists every source with licence, how the licence was verified, attribution and share-alike conditions, what is included and excluded, reconstruction instructions for each excluded source, and the seven unresolved questions. It calls a dataset CC0 only where the upstream licence text was read (openfootball: 16 `LICENSE.md` files hashed; martj42: the repository's own CC0 file).

## 5. Source-code licence recommendation (no licence added)
The code has no licence, so by default all rights are reserved: others may view and fork on GitHub but may not copy, modify or reuse it. Options:
| Option | Effect | Fit |
|---|---|---|
| **None (leave as is)** | nobody may legally reuse the code; simplest; examiners can still read it | fine for a college submission you want to keep private-ish |
| **MIT** | anyone may use, modify, sell, with the copyright notice | maximum reuse, minimal text; no patent grant |
| **Apache-2.0** | same plus an explicit patent grant and notice requirements | common for ML/data projects |
| **GPL-3.0 / AGPL-3.0** | reuse only if derivative works are also open (AGPL covers network use) | if you want improvements shared back |
| **CC BY-NC / source-available** | not an OSI open-source licence; limits commercial use | if you want to prevent commercial reuse |
Points specific to FootIQ: a code licence does not cover the data (each dataset keeps its own licence in `DATA_LICENSES.md`); the frozen models are trained on CC0 and CC BY-SA rows, so the unresolved share-alike question touches them as well; third-party code under `node_modules` and the `openfootball` sources keep their own licences. My suggestion if you want to share: MIT or Apache-2.0 for the code and a separate statement for models and data; if you want to keep options open: no licence for now. **Nothing was added.**

## 6. Rebuilding the current six-competition database (private copies only)
**Why the clean rebuild is behind.** `app/store/build.py` creates only the **baseline** store (data to 2026-09-20; the same inputs reproduce it byte for byte except timestamps: Phase 4.33). The current state was reached by 6 further steps that the clone did not perform: (1) five reviewed OpenLigaDB team aliases accepted on 25 Oct (the 25 Oct offline import without them quarantined 154 instead of 24 La Liga rows); (2) the 25 Oct offline import of the saved Premier League and La Liga OpenLigaDB snapshots (10 EPL and 24 La Liga results); (3) the Bundesliga and La Liga feeds (61 rows in total from OpenLigaDB); (4) `uefa_import.py` with the verified-results gate and the verified-fixtures gate (**Champions League 18 -> 54 results and 0 -> 90 fixtures**); (5) `league_results_import.py` (71 Wikipedia results, cross-checked: Premier League 50 -> 80 together with step 6); (6) `reconcile_import.py` strong tier (43 corrections). The simulator was "not eligible" only because 30 Premier League fixtures past their date had no result in the baseline.
**Procedure and result.** `scripts/rebuild_current_state.py <folder>` (about 3 minutes) replays steps 0-6 onto a new `replay.sqlite` and compares it with production read-only. Result (three runs, identical): **17,303 of 17,303 six-competition rows exist; 17,285 are identical on every content column; 18 future fixtures differ by one day in date/kickoff** (date decisions of the Phase 4.13-4.15 review, not replayed). Completed 2026-27 results match production exactly: Premier League 80, La Liga 99, Bundesliga 63, Serie A 80, Ligue 1 72, Champions League 54; scheduled 300 / 280 / 243 / 300 / 234 / 90. Production hash unchanged by the replay.
**Legal limit found.** The two Wikipedia-based importers **require** the football-data.co.uk / FixtureDownload cross-check columns (they accept a result only when at least two sources agree). With those columns blanked, **all 71 domestic results and 103 of 104 reconciliation proposals are rejected** ("sources_disagree_on_score", "scores_not_two_source_verified"), tested on a private copy. Exact reconstruction therefore needs either the restricted cross-check data or a change of the importers. Lawful alternatives, in order of preference:
1. **Published-evidence mode (needs your approval: a code change in two importers plus tests):** publish sanitized staging files that keep Wikipedia's score and date (CC BY-SA) and **our own recorded verification outcome** (`sources_agreeing = 3`, `verification_tier = strong`, no provider values); add an option `--trust-recorded-verification` to `league_results_import.py` and `reconcile_import.py` that accepts a row when that outcome is present. The scores and dates are the same facts; no provider column is redistributed.
2. **Private acquisition:** every user downloads the football-data.co.uk files for private use (`p420/fetch_sources.py`), regenerates the staging with `stage_leagues.py` and runs the full importers: lawful per user, but results later than 28 Oct would also appear (not identical).
3. **No domestic replay:** publish only the baseline plus the OpenLigaDB and UEFA steps (which need no restricted data): the clone would show Bundesliga, La Liga and Champions League current, and the other three leagues at baseline.
The Champions League and OpenLigaDB steps use only Wikipedia/UEFA-verified and ODbL data and are reproducible as published today. Database snapshot as a Release asset remains an option (section 7 of the Phase 4.34 report), with the licence limits stated there.

## 7. Dependency verification
`scipy` is imported directly (`app/seasonsim/scoreline.py`: `scipy.optimize`, `scipy.stats`; `d11_prospective_logger.py`: `scipy.special`). Compatible version: **`scipy==1.17.1`**, the version the project ran and tested with; scipy 1.17.1 requires NumPy, and with the pinned `numpy==1.26.4` `pip check` reports "No broken requirements found". **Edit made:** `scipy==1.17.1` appended to `app/requirements.txt` (not staged). Verification in a new virtual environment (Python 3.12.12) with `pip install -r requirements-share.txt -r app/requirements.txt`: install succeeded, `pip check` clean, versions fastapi 0.159.1, uvicorn 0.54.0, httpx 0.28.1, numpy 1.26.4, pandas 2.2.1, scikit-learn 1.5.1, scipy 1.17.1; targeted tests in a simulated clone (`test_seasonsim_engine`, `test_pointbounds`, `test_store`, `test_baseline_hash`, `test_phase417_evidence`): 43 passed, 22 skipped (tests that need the full current store); `import d11_prospective_logger, seasonsim.scoreline, main` succeeds.

## 8. Git LFS readiness
- **Installed:** git-lfs 3.7.1 (Git 2.52.0); LFS endpoint resolves to your repository (`.../info/lfs`, no credentials needed to read the configuration). Not configured: no `git lfs install`, no tracking, `git lfs ls-files` empty.
- **The eight files** (`p434`, sizes in MiB): `V_universe.pkl` 111.6 (over GitHub's 100 MiB block, required: `app/store/baseline.py`), `02_Historical_Club_Matches.csv` 99.1, `04d_COMBINED_CLUB_MATCHES` 69.4, `08_..._extended` 62.3, `04a_LEAGUE_RESULTS` 62.0, `08_..._strict` 60.4, `03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG` 56.8, `01_CORRECTED_LEAGUE_TRAINING_DATASET` 52.1; **total 573.6 MiB**.
- **Redistribution permission per file:** `02` and `04a`: openfootball CC0 only (all rows); `04d`: openfootball CC0 plus 2,969 Wikipedia rows (CC BY-SA); `08` extended/strict and `01`: same family (about 1.2% Wikipedia) with row-level provenance; `03`: correction log of those rows; `V_universe.pkl`: derived from the same rows. No StatsBomb, football-data or API-Football rows (checked by source column). All carry the conditions in `DATA_LICENSES.md`.
- **GitHub limits (docs.github.com, read today):** warn at 50 MiB, block at 100 MiB; LFS maximum file size 2 GB on Free and Pro (4 GB Team); **Free plan: 10 GiB LFS storage and 10 GiB bandwidth per month**; downloads (clones, pulls, Actions, source archives with LFS objects) count against the repository owner; over quota without a payment method: storage full = pointer files only and no pushes, bandwidth full = LFS disabled until next month. Your account's current usage cannot be read without GitHub credentials, so confirm in Settings > Billing before the push.
- **Feasibility:** 574 MiB is about 5.6% of the storage; one full clone downloads about 0.56 GiB, so about 17 full clones per month. The simulated clone (`simulate_clone.py`) built the store and started the application from these files.
- **Proposed `.gitattributes`:** `p434/proposed.gitattributes` (8 explicit LFS lines, LF normalisation for source text, `data/raw/** -text`). Not applied.

## 9. Remaining blockers
1. **Decision on the reconstruction route** (section 6): approve the published-evidence mode (code change in two importers plus tests and sanitized staging files), or choose the private-acquisition or baseline-only alternative.
2. **Source-code licence** (section 5): your choice; none added.
3. **Forward-only removal of tracked restricted files** (19 API-Football, 131+2 StatsBomb data files, 1 FIFA file): needs your approval before `git rm --cached`.
4. **CC0-only player extracts** (generated from `04-08` by licence column): script not written yet; the player tables stay out of the commit until then.
5. **Sanitized copies of the 11 evidence CSVs** (and decision on the 17 raw provider copies, already excluded).
6. **Confirm the World Bank licence**; accept or change the cautious CC BY-SA reading for Wikipedia-derived rows.
7. **Account checks:** LFS quota in GitHub settings; whether `FootIQ_Dataset_Submission/02` (99.1 MiB) should rather be kept out of Git altogether (close to the 100 MiB block).
8. Final screenshots and the literature survey (outside Git).

## 10. Exact proposed Git commands (not run; need your approval first)
```bash
git fetch origin
git switch -c feat/footiq-final-six-competitions             # from HEAD; its tree equals origin/main
git lfs install
# 1. apply the approved drafts
cp data/supervised/phase4/p434/proposed.gitignore .gitignore        # review the diff first
cp data/supervised/phase4/p434/proposed.gitattributes .gitattributes
# 2. forward-only removal of restricted files from tracking (they stay on disk; history is untouched)
git rm --cached -r -- data/raw/statsbomb data/raw/fifa
git rm --cached -- $(cat data/supervised/phase4/p435/tracked_api_football_tier1_19.txt)
git rm --cached -- $(grep -i statsbomb data/supervised/phase4/p435/tracked_statsbomb.txt | grep -v '^scripts/' | grep -v '^data/raw/statsbomb')
# 3. add the approved content (explicit lists; never `git add -A`)
git add .gitignore .gitattributes DATA_LICENSES.md README.md PROJECT.md README_SHARE.md app/requirements.txt requirements-share.txt
git add app config frontend tests scripts scratch docs outputs
git add FootIQ_Club_Model_Baseline_v1 FootIQ_Club_Model_Development_v2 FootIQ_ML_Data_Readiness FootIQ_ML_Training_Preparation FootIQ_ML_Data_Verification FootIQ_Dataset_Submission data
git lfs ls-files                    # must list exactly the 8 files
git status --short | grep -i -E "statsbomb|api_football|footballdata|rules_research|contact.local|\.sqlite" && echo "STOP: a restricted path is staged"
git diff --cached --stat | tail -3
git commit                           # message below
git push --dry-run -u origin feat/footiq-final-six-competitions
git push -u origin feat/footiq-final-six-competitions      # then open a pull request into main; never force-push
```
Commit message proposal:
```
Add FootIQ six-competition application, pipeline, models and licensed datasets

- Backend, React frontend, SQLite store with verified importers (UEFA league phase,
  domestic results, reconciliation) and the offline rebuild script
- Frozen club models, evaluation reports; points-only simulator for five leagues
- CC0 / CC BY-SA / ODbL datasets with DATA_LICENSES.md; eight large files via Git LFS
- scipy added to app/requirements.txt
- Forward-only removal from tracking of StatsBomb, FIFA-page and API-Football-derived files;
  no history rewrite. Restricted sources are documented with reconstruction steps.
```
