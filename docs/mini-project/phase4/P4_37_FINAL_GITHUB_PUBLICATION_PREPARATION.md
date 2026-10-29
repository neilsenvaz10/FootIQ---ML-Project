# Phase 4.37: final GitHub publication preparation

Nothing was staged, committed, pushed or force-pushed; Git history was not touched; no Git or LFS command that changes anything was run (`git diff --cached` is empty, `git lfs install` not run). The production database (`data/footiq.sqlite`, SHA-256 `5f38b226...` before and after), the frozen models and the production backend were not modified; every write went to private copies or to a simulated clone outside the project. No source-code licence was added.
Working files: `data/supervised/phase4/p437/` (scripts, `out/` manifests and logs).

## 1. Sanitized snapshot feasibility
**Verdict: a database built only from repository files is clean and reproducible; a single published SQLite file is not recommended, and nothing was published.**

*What I built (private copies).* `python scripts/rebuild_current_state.py <folder> snapshot` rebuilds the store from repository inputs in about 25 s. It replays the baseline, the saved OpenLigaDB snapshots, the Champions League inputs, the published evidence, and then the new explicit `--evidence attested` pass (Wikipedia-supported results the maintainer attests were cross-checked privately; stored with the provenance text "NOT independently reproducible from public data"; never the default; 7 new tests).

| Category in the store | Rows | Licence | Redistributable |
|---|---|---|---|
| openfootball | 219,968 | CC0 1.0 | yes |
| martj42/international_results | 2,491 | CC0 1.0 | yes |
| Wikipedia | 986 | CC BY-SA 4.0 | yes, with attribution and share-alike |
| OpenLigaDB | 61 (+954 confirmation links) | ODbL 1.0 | yes, with attribution and share-alike |
| World Cup 2026 rows from an API-Football provider file (99+9), news and FIFA pages (22+2) | 130 | "licence not asserted" | **no: removed** |
| match-source notes naming football-data.co.uk / FixtureDownload (43), run details (17), quarantine payloads (273), saved forecasts and simulations | | | **no: not present in the rebuilt store** (scanned: only the word "provider" in a tier name) |

*Result of the rebuild against production (six competitions, 17,303 rows):* 17,300 rows identical; **3 results not reproduced** (1 La Liga, 2 Ligue 1: their played day exists only in a restricted source, so I did not take it); 130 World Cup 2026 rows removed by design; teams (5,188), aliases (7,447), team mappings and the Champions League (54 + 90) identical.

*Simulator eligibility (all five domestic leagues):*

| League | Production | Rebuilt from repository files | Baseline only (CC0 inputs, no Wikipedia / OpenLigaDB / evidence) |
|---|---|---|---|
| Premier League | ready | ready, can run | not eligible (30 missing results) |
| La Liga | ready | ready, can run (2 missing) | not eligible (31) |
| Bundesliga | ready | ready, can run | not eligible (27) |
| Serie A | provisional | provisional, can run (3 missing) | not eligible (33) |
| Ligue 1 | ready | **provisional**, can run (2 missing) | not eligible (27) |

**All five simulators remain eligible in the rebuilt store; Ligue 1 drops from ready to provisional.** A CC0-only store would make none of them eligible, so a CC0-only snapshot cannot reproduce the simulators.

*Why not publish a SQLite file:* (1) it would mix ODbL rows (share-alike under the database licence) and CC BY-SA rows (share-alike under a different licence); no single licence satisfies both, and I did not decide that for you; (2) it adds nothing: the rebuild takes 25 s from files that are in the repository; (3) the 3 results above cannot be in it. If you still want a file, the safe options are a CC0-only convenience file (works but nothing is eligible) or a release asset with a legal opinion on point (1). Removing source columns was never treated as proof of rights: the clean result comes from tracing every stored value to its recorded source.

## 2. Dataset licence verification (terms read 2026-10-29)
Full table in [DATA_LICENSES.md](../../../DATA_LICENSES.md) (rewritten as the proposed final). Summary:
- **openfootball, martj42: CC0 1.0** (licence texts read earlier, hashes recorded).
- **Wikipedia: CC BY-SA 4.0**, attribution and share-alike; scope for extracted scores unresolved.
- **OpenLigaDB: ODbL 1.0**, confirmed by the API page statement; the `/lizenz` page did not render, so the attribution wording was not re-read from the site.
- **World Bank: CC BY 4.0 by default**, with extra terms and possible third-party indicator labels; the two indicators' own labels are not checked.
- **football-data.co.uk:** "private individuals only", no commercial, bot, scraper or AI use, no redistribution grant: restricted.
- **FixtureDownload:** terms forbid distribution, reproduction and storing on another site apart from personal use: restricted.
- **football-data.org:** terms page returned 404, **not read**; permission requested and not granted: restricted.
- **API-Football:** terms page returned 403, **not read**: restricted until read.
- **StatsBomb:** user agreement 1.2.1 forbids providing the data to third parties; logo credit 1.4: restricted.
I did not invent any permission; where a page could not be read the entry says so.

## 3. Restricted-file removal plan (forward-only)
`out/restricted_removal_plan.csv` (path, category, tracked, in Git history, in HEAD, action, reason). The content scan of all 2,000+ proposed files found **more than the earlier audits listed**:

| Category | Tracked now | In history | Action |
|---|---|---|---|
| A API-Football-derived data (19 listed earlier + 49 more in `data/processed`: matchday validation, snapshots, feature / prediction files carrying provider identifiers) | 68 | yes, commit `edb6e0a` | `git rm --cached` |
| B StatsBomb files | 134 | yes, `edb6e0a` | `git rm --cached` |
| C FIFA page copy `data/raw/fifa` | 1 | yes, `edb6e0a` | `git rm --cached` |
| E news / FIFA-compiled World Cup results (`worldcup_manual_results.csv`) | 1 | yes, `edb6e0a` | `git rm --cached` |
| M dashboard CSVs with 130 provider / news rows (`matches.csv`, `data_audit.csv`; `season_coverage.csv` replaced with them) | 2 (+1) | yes, `c3a6fb1` | replace by sanitized copies |
| D football-data.co.uk / FixtureDownload / football-data.org values (p420 / p423 / p424 reports, raw copies, ledger) | 0 | no | never add (ignore rules) |
| X regenerable intermediates and pilot pickles (not a licence issue) | 67 | yes | optional `git rm --cached` |

Tracked restricted files to remove going forward: **204** (`out/git_rm_paths_restricted.txt`); optional 67 (`out/git_rm_paths_optional_regenerable.txt`). **The remote already holds them:** `origin/main` and `origin/feat/club-ml-v2` contain commits `edb6e0a`, `c3a6fb1` and `970f461`, so removal going forward does not remove the files from history. I could not read the repository's visibility (`gh` is not installed); please check whether it is public. See blocker 1.
Files that only name a source (code, documents, labels such as `tactical_data_status = statsbomb_...`) are kept; the final re-scan shows only such label or mention hits (37 files, listed in `out/final_totals.json`).

## 4. Player extract verification
`python scripts/build_cc0_player_extracts.py` writes `FootIQ_Dataset_Submission/cc0_extracts/` (originals untouched; one extra README and manifest with SHA-256):

| Table | Original rows | CC0 rows kept | Dropped |
|---|---|---|---|
| 04 players | 25,288 | 15,382 | 9,906 |
| 05 player-match statistics | 180,172 | 66,549 | 113,623 |
| 06 teams | 5,729 | 5,375 | 354 |
| 07 competitions | 409 | 385 | 24 |
| 08 memberships | 34,277 | 15,972 | 18,305 |

Checks: 0 cells mention StatsBomb; every kept row's recorded source is openfootball or martj42; players in 05 and 08 all exist in 04; no player without a row; the appearance counter in 04 equals the count in the extract for every player (so the counters were not computed over mixed sources). Caveat: `same_name_key_as_other_team_ids` in 06 may list team ids that also exist in the StatsBomb table (identifiers only, no StatsBomb value). Tests cover it (`tests/test_attested_snapshot.py`).

## 5. Evidence CSV sanitization
`python scripts/sanitize_evidence_csvs.py` → `data/evidence/sanitized/` (12 files: the 11 listed earlier plus `P4_13B_DATE_VERIFICATION_SHEET.csv`, which also carried provider dates) and `SANITIZATION_MANIFEST.json` (source SHA-256, kept and dropped columns, withheld counts). Rules: whitelist of columns; derived columns dropped (`diff_days`, `shift_days` would reveal a provider date); a date or score kept only if a redistributable source in the same row carries the same value (blanked otherwise: 2 + 62 + 68 dates); free text mentioning a provider dropped; the tier name `provider_assisted` renamed.
Verification (`verify_sanitized.py`): 0 restricted words in column names or cells; 0 columns shared with the 12 local football-data.co.uk raw files (up to 114 columns each, 880 rows in total); no provider column such as odds or referee survives; the only fixtures and values present are public facts that Wikipedia, openfootball or OpenLigaDB also carry. The originals stay local and ignored.

## 6. Reproducibility test results
Method: `simulate_clone_final.py` copied only the files of `out/final_inclusion_manifest.csv` (1,997 files at test time, 923.8 MB including the 573.6 MiB LFS files) to a folder outside the project, with no production database and no restricted file; everything below ran from that clone with the project's Python.

| Check | Result |
|---|---|
| Rebuild (`rebuild_current_state.py ... snapshot`) | all steps exit 0 in 25 s; 17,300 / 17,303 six-competition rows identical to production |
| Store scan | no restricted source, no provider or news URL, no World Cup 2026 row; `provider` appears only in a quarantined tier name |
| Backend from the clone (port 8003, sync disabled) | **37 of 37 live checks**: health and models, exactly the six competitions, dashboard and fixtures per competition, one prediction per competition (probabilities sum to 1, secondary and Elo models present, Validated labels; UCL "Not validated"), UCL 54 + 90, five archived competitions excluded, simulator status for all five leagues, UCL not offered |
| Monte Carlo (points-only, 1,000 simulations, private clone store) | HTTP 200 for Premier League, La Liga, Bundesliga, Serie A, Ligue 1 |
| Frontend in the clone | `npm ci` ok, build ok, **375 tests passed, 13 skipped**; dev server rendered the home page against the clone backend (next match, gameweek fixtures, sync panel) |
| Importer and evidence tests | 99 passed (68 existing importer tests + 24 published-evidence + 7 new) |
| Full backend suite in the clone | **551 passed, 57 skipped, 3 failed** (11 min; log `out/clone_pytest.txt`). The 3 failures are all in `tests/test_seasonsim_service.py` and assert the maintainer's exact counts: La Liga "1 result missing" (clone: 2) and the Ligue 1 accounting / "ready" state (clone: provisional). They are the known consequence of the 3 results that cannot be reproduced, not a defect; I did not change the tests. The 57 skips are tests whose local-only inputs (restricted staging, saved production simulations, archived pipelines) are not in the clone. The production-side suite (603 passed, 8 skipped) is unchanged |

*Reproducible from GitHub:* the store, the six competitions, predictions with the frozen models, the Champions League, the five simulators (Premier League, La Liga, Bundesliga ready; Serie A, Ligue 1 provisional), the frontend, and the Bundesliga / La Liga start-up refresh (needs your own contact string).
*Needs external restricted data:* 3 results (1 La Liga, 2 Ligue 1) and Ligue 1 "ready" status; the exact maintainer-identical store (`... local`); player statistics from StatsBomb; World Cup 2026 results and the API-Football pipelines (archived, off the six); independent re-verification of the 80 attested results. The clone test used a manifest 4 files smaller than the final one (the later additions are one test file and tool scripts).

## 7. Git LFS readiness
Final manifests: `out/final_inclusion_manifest.csv` (**2,001 files: 1,993 Git, 8 LFS**; 322.4 MB uncompressed, about 80.5 MB compressed; largest normal file under 50 MiB), `out/final_exclusion_manifest.csv` (2,483 files, 1.95 GB, with reasons), `out/proposed.gitignore` (tested: no file of the add list is ignored), `out/proposed.gitattributes`.

| LFS file | MiB |
|---|---|
| FootIQ_ML_Training_Preparation/_build/work/V_universe.pkl | 111.6 |
| FootIQ_Dataset_Submission/02_Historical_Club_Matches.csv | 99.1 |
| FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv | 69.4 |
| FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv | 62.3 |
| FootIQ_ML_Data_Readiness/04a_LEAGUE_RESULTS_v1.0.csv | 62.0 |
| FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv | 60.4 |
| FootIQ_ML_Training_Preparation/03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv | 56.8 |
| FootIQ_ML_Training_Preparation/01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv | 52.1 |
| **Total** | **573.6** |

Quota (GitHub Free as recorded in Phase 4.35: 10 GiB storage, 10 GiB bandwidth per month): 573.6 MiB of storage (about 5.6%); every full clone with `git lfs pull` downloads 573.6 MiB, so about 17 full clones or CI runs per month fit; each later change to an LFS file stores a new full copy. Git LFS 3.7.1 is installed. Current plan limits must be confirmed in the GitHub settings (not verifiable from here).

## 8. Remaining blockers (need your decision)
1. **Files already on the remote.** Categories A, B, C, E (204 files) are in commit `edb6e0a`, the dashboard CSVs in `c3a6fb1`, already pushed. Removal going forward does not purge them. Check the repository visibility. Options: (a) make the repository private, (b) accept the exposure for a coursework repository, (c) rewrite history or publish from a fresh repository (not done; needs your explicit approval).
2. **Attested results:** do you accept 80 results that are supported by Wikipedia only, labelled "attested, not independently reproducible", plus the 3 results not reproduced and Ligue 1 provisional? The alternative is `published` mode (83 results and 31 date corrections missing, three simulators not eligible).
3. **Wikipedia share-alike and ODbL** stance (DATA_LICENSES section 6.1 and 6.2); no SQLite is proposed until decided.
4. **Replacing the local dashboard CSVs** with the sanitized copies (originals kept in `data/local_private/`, ignored): part of the commit commands.
5. **Source-code licence:** none added.
6. **API-Football and football-data.org terms** unread (403 / 404); World Bank indicator labels; StatsBomb-derived aggregate tactical adjustments in archived tables.
7. **Git LFS quota** of your GitHub account.
8. Documentation (`README.md`, `docs/mini-project/final/SETUP_AND_RUN.md`) still describes the Phase 4.36 `published` rebuild; the `snapshot` mode is documented in `DATA_LICENSES.md` section 4 and needs the same line there before publication.

## 9. Exact recommended Git commands
Not run. The sequence is in `data/supervised/phase4/p437/out/git_commands.sh.txt`; the commit message in `out/proposed_commit_message.txt`:

```bash
git switch -c release/github-publication
mkdir -p data/local_private/miniproject
cp data/miniproject/matches.csv data/miniproject/data_audit.csv data/miniproject/season_coverage.csv data/local_private/miniproject/
cp data/release_candidates/miniproject/*.csv data/miniproject/
cp data/supervised/phase4/p437/out/proposed.gitignore .gitignore
cp data/supervised/phase4/p437/out/proposed.gitattributes .gitattributes
git lfs install
git rm --cached --pathspec-from-file=data/supervised/phase4/p437/out/git_rm_paths_restricted.txt
git add --pathspec-from-file=data/supervised/phase4/p437/out/git_add_paths.txt
git lfs ls-files | wc -l
git diff --cached --name-only | grep -Ei 'statsbomb|footballdatauk|fixturedownload|matchday_validation_v210|data/raw/fifa|data/snapshots/footballdata' && echo STOP || echo clean
git commit -F data/supervised/phase4/p437/out/proposed_commit_message.txt
git push -u origin release/github-publication
```
Run the first block only after blockers 1 to 4 are decided; the push last.

## Changes made in this phase (all uncommitted)
`app/store/published_evidence.py`, `league_results_import.py`, `reconcile_import.py` (opt-in `attested` mode; defaults unchanged, 68 existing tests pass), `scripts/rebuild_current_state.py` (`snapshot` mode), `scripts/sanitize_evidence_csvs.py`, `scripts/build_cc0_player_extracts.py`, `scripts/prepare_release_files.py`, `tests/test_attested_snapshot.py`, `data/evidence/sanitized/`, `FootIQ_Dataset_Submission/cc0_extracts/`, `data/release_candidates/miniproject/`, `DATA_LICENSES.md`, this report, and `data/supervised/phase4/p437/`.
