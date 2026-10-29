# 02 Dataset integrity report (independent, generated 2026-10-20 22:32)

All numbers below were computed directly from the CSV files by `_scripts/v1_integrity.py`; no previous summary was reused.

## 1. Record counts versus the previous claims
| file | rows | claimed_rows | matches_claim | columns | date_min | date_max | unique_ids | duplicate_ids | competitions | seasons |
|---|---|---|---|---|---|---|---|---|---|---|
| SUB/01_Historical_International_Matches.csv | 49362 | 49362.0 | YES | 25 | 1872-11-30 | 2026-06-02 | 49362.0 | 0.0 | 222.0 |  |
| SUB/02_Historical_Club_Matches.csv | 223625 | 223625.0 | YES | 39 | 1888-09-08 | 2026-05-31 | 223625.0 | 0.0 | 160.0 | 62.0 |
| SUB/03_Recent_Match_Results.csv | 1482 | 1482.0 | YES | 32 | 2026-06-03 | 2026-10-06 | 1482.0 | 0.0 | 33.0 | 3.0 |
| RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv | 125858 | 125858.0 | YES | 49 | 2018-08-01 | 2026-09-20 | 125858.0 | 0.0 | 143.0 | 19.0 |
| RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv | 129829 | 129829.0 | YES | 49 | 2018-08-01 | 2026-09-20 | 129829.0 | 0.0 | 144.0 | 19.0 |

All five claimed counts are exactly reproduced. `04d` has 143,055 rows because it is restricted to seasons 2018 onward; the training sets draw on a wider universe (227,374 results since 2010-11), so strict/extended rows are **not** a subset of `04d` (157 strict rows belong to a 2017-18 Nigerian second-tier file dated 2018-09: see season-label issue).

## 2. Per-dataset integrity metrics
| file | rows | columns | date_min | date_max | unique_ids | duplicate_ids | unique_matches_natural_key | duplicate_natural_key_rows | competitions | seasons | missing_cell_pct | invalid_dates | invalid_scores_or_values | claimed_rows | matches_claim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SUB/01_Historical_International_Matches.csv | 49362 | 25 | 1872-11-30 | 2026-06-02 | 49362.0 | 0.0 | 49361 | 1 | 222.0 |  | 7.92 | 0.0 | 2 | 49362.0 | YES |
| SUB/02_Historical_Club_Matches.csv | 223625 | 39 | 1888-09-08 | 2026-05-31 | 223625.0 | 0.0 | 223625 | 0 | 160.0 | 62.0 | 22.58 | 0.0 | 0 | 223625.0 | YES |
| SUB/03_Recent_Match_Results.csv | 1482 | 32 | 2026-06-03 | 2026-10-06 | 1482.0 | 0.0 | 1482 | 0 | 33.0 | 3.0 | 25.54 | 0.0 | 0 | 1482.0 | YES |
| SUB/04_Football_Players.csv | 25288 | 18 | 1958-06-24 | 2026-05-25 | 25288.0 | 0.0 | 25288 | 0 |  |  | 24.69 | 0.0 | 0 |  |  |
| SUB/05_Player_Match_Statistics.csv | 180172 | 58 | 1958-06-24 | 2026-05-25 | 180172.0 | 0.0 | 180172 | 0 | 31.0 | 64.0 | 23.33 | 0.0 | 0 |  |  |
| SUB/06_Teams.csv | 5729 | 16 | 1893-04-01 | 2027-05-30 | 5729.0 | 0.0 | 5729 | 0 |  |  | 13.01 | 0.0 | 0 |  |  |
| SUB/07_Competitions.csv | 409 | 17 | 1892-04-30 | 2027-05-30 | 409.0 | 0.0 | 409 | 0 | 409.0 | 89.0 | 7.35 | 0.0 | 0 |  |  |
| SUB/08_Player_Team_Memberships.csv | 34277 | 22 | 1958-06-24 | 2026-05-25 | 34277.0 | 0.0 | 34277 | 0 | 61.0 | 66.0 | 20.46 | 0.0 | 0 |  |  |
| SUB/09_Upcoming_Fixtures.csv | 3793 | 21 | 2026-06-05 | 2027-05-30 | 3793.0 | 0.0 | 3793 | 0 | 18.0 | 3.0 | 8.5 | 0.0 | 0 |  |  |
| RDY/04a_LEAGUE_RESULTS_v1.0.csv | 128654 | 33 | 2018-03-02 | 2026-09-20 | 128654.0 | 0.0 | 128654 | 0 | 116.0 | 18.0 | 13.0 | 0.0 | 0 |  |  |
| RDY/04b_DOMESTIC_CUP_RESULTS_v1.0.csv | 7223 | 33 | 2018-07-20 | 2026-09-27 | 7223.0 | 0.0 | 7223 | 0 | 25.0 | 10.0 | 10.63 | 0.0 | 0 |  |  |
| RDY/04c_CONTINENTAL_AND_GLOBAL_RESULTS_v1.0.csv | 7178 | 33 | 2018-01-22 | 2026-09-17 | 7178.0 | 0.0 | 7178 | 0 | 12.0 | 18.0 | 11.67 | 0.0 | 0 |  |  |
| RDY/04d_COMBINED_CLUB_MATCHES_v1.0.csv | 143055 | 33 | 2018-01-22 | 2026-09-27 | 143055.0 | 0.0 | 143055 | 0 | 153.0 | 18.0 | 12.81 | 0.0 | 0 |  |  |
| RDY/04e_UNDATED_LEAGUE_RESULTS_2025-26_v1.0.csv | 1162 | 17 |  |  |  |  | 1162 | 0 | 6.0 | 1.0 | 5.88 | 0.0 | 0 |  |  |
| RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv | 125858 | 49 | 2018-08-01 | 2026-09-20 | 125858.0 | 0.0 | 125858 | 0 | 143.0 | 19.0 | 0.0 | 0.0 | 0 | 125858.0 | YES |
| RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv | 129829 | 49 | 2018-08-01 | 2026-09-20 | 129829.0 | 0.0 | 129829 | 0 | 144.0 | 19.0 | 0.0 | 0.0 | 0 | 129829.0 | YES |
| RDY/05_CANONICAL_TEAM_IDENTITY_MAPPING.csv | 6741 | 14 |  |  |  |  | 6741 | 0 |  |  | 22.32 |  | 0 |  |  |

Notes
* `duplicate_natural_key_rows` > 0 in 01 = 1 real same-day double-headers (e.g. Tahiti v New Caledonia 1974-02-17) with different scores, retained by the source.
* Null dates: 04e is intentionally undated (matrix results). Every other match file has zero null/invalid dates.
* Invalid scores = negative, non-integer or above 25 goals (minutes above 130 for 05). Reported value per file is in the table.
* Columns that are `object` but look numeric: see `_evidence/dataset_integrity_metrics.csv` (column `object_columns_that_look_numeric`).

## 3. Integrity of the preserved artefacts
* Milestone 1 baseline: 522 of 522 files in `docs/baseline/capture_2026-10-20/original_files.sha256` still match their recorded SHA-256 (modified: 0, missing: 0).
* `FootIQ_Dataset_Submission.zip`: 34 of 34 members are byte-identical to the files in `FootIQ_Dataset_Submission/`.
* The model artefact `data/model_artifacts/v27/live_match_model.pkl` and `data/raw/international_results/results.csv` are hashed in `_evidence/sha256_critical_inputs_outputs.csv` (117 hashed items).

## 4. Scripts that build the training data (inspected)
`FootIQ_Dataset_Submission/_build/{footballtxt,build_club_matches,build_players_openfootball,build_players_statsbomb,assemble_matches,assemble_players,validate_and_document,write_description}.py` and `FootIQ_ML_Data_Readiness/_build/{common,identity,labels,wiki_fetch,wp_parse,s2_fetch_wikipedia,s3_parse_wikipedia,s4_combine,s5_merge,s7_league_matrix,s8_build_dataset,s9_outputs}.py`. Hashes of all of them are in the hash file.

Data flow: openfootball clones + martj42 refresh -> `club_matches_all.csv` -> (+ Wikipedia fills, identity map) -> `data_all.pkl` -> `08_*_strict/extended.csv`.
