# 10 Reproducibility report (generated 2026-10-20 22:32)

## What was done
1. SHA-256 of 117 critical inputs, outputs, scripts and intermediates recorded in `_evidence/sha256_critical_inputs_outputs.csv`.
2. The Milestone 1 baseline: 522/522 original files unchanged (modified 0, missing 0). Note: the repository root contains additional untracked directories created by later milestones; they are outside the 522 files.
3. `FootIQ_Dataset_Submission.zip`: all 34 members byte-identical to the directory; the directory's CSVs match the ZIP, so the submission was not modified after zipping.
4. **Isolated rebuild**: the readiness pipeline (`s8_build_dataset.py`, `s9_outputs.py`) was copied to the session scratchpad, its intermediate pickles (`M_of`, `M_fill`, `M_wp`) and Wikipedia-derived tables were copied, and the dataset-building steps were re-run there. Nothing in the project was overwritten.
5. Independent re-implementation of every feature and of the 1X2 label derivation (see files 04 and 06): 0 differences on all 129,829 rows.

## Result of the isolated rebuild
| file | bytes_new | bytes_old | identical_bytes |
|---|---|---|---|
| 01_COMPETITION_SEASON_COVERAGE_MATRIX.csv | 198901 | 198901 | True |
| 02_MISSING_MATCH_INVENTORY.csv | 1624479 | 1624479 | False |
| 03_VERIFIED_SOURCE_AND_LICENSING_REPORT.md | 6524 | 6524 | False |
| 04a_LEAGUE_RESULTS_v1.0.csv | 64983647 | 64983647 | True |
| 04b_DOMESTIC_CUP_RESULTS_v1.0.csv | 3876905 | 3876905 | True |
| 04c_CONTINENTAL_AND_GLOBAL_RESULTS_v1.0.csv | 3911256 | 3911256 | True |
| 04d_COMBINED_CLUB_MATCHES_v1.0.csv | 72770752 | 72770752 | True |
| 04e_UNDATED_LEAGUE_RESULTS_2025-26_v1.0.csv | 488643 | 488643 | True |
| 05_CANONICAL_TEAM_IDENTITY_MAPPING.csv | 1548556 | 1548556 | True |
| 06_TRAINING_LABEL_VALIDATION_REPORT.md | 2123 | 2123 | False |
| 06_TRAINING_LABEL_VALIDATION_SUMMARY.csv | 222 | 222 | True |
| 07_TEMPORAL_LEAKAGE_AUDIT.md | 2613 | 2613 | False |
| 07_TEMPORAL_LEAKAGE_TESTS.csv | 1298 | 1298 | True |
| 08_TRAINING_DATASET_SCHEMA_v1.0.json | 1330 | 1330 | False |
| 08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv | 65335922 | 65335922 | True |
| 08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv | 63323515 | 63323515 | True |
| 09_ML_READINESS_REPORT.md | 7279 | 7279 | False |
| 10_TRAIN_INFER_FEATURE_MISMATCH_AUDIT.md | 2534 | 2534 | True |

* Byte-identical: 12 of 18 files, including `04a-04e`, `05`, `08_*_strict.csv`, `08_*_extended.csv`, `07_TEMPORAL_LEAKAGE_TESTS.csv`.
* `02_MISSING_MATCH_INVENTORY.csv` differs in row order only (equal after sorting - set iteration order); the Markdown reports differ by their generation timestamp; the schema JSON differs by its `created` timestamp.
* Row-level comparison of non-identical CSVs: [{'file': '02_MISSING_MATCH_INVENTORY.csv', 'same_shape': True, 'frames_equal': False, 'rows_new': 8830, 'rows_old': 8830}].
* Pickle comparison (`data_all.pkl`, key columns: record id, date, Elo, n_prior, labels, eligibility, split): rows 227,374 vs 227,374, equal: **True**.

## Not rebuilt
* Steps that need the network (Wikipedia fetch) were not repeated; the cached pages (103 files, aggregate hash recorded) are the input. Steps `s2-s5` (parse / identity / merge) were not re-executed because they would write into the existing `_build/work` folder; their outputs were verified instead by re-deriving labels, identities and cross-source comparisons independently.
* openfootball parsing (`build_club_matches.py`) was not re-run; instead every training row was traced to its raw `file:line` and re-parsed (0 failures of 128,101).
* Determinism: the builds use fixed sorting (`match_dt, competition_id, record_id`), seeded sampling (2026-10-20 / 7 / 11) and no randomness in features. Only unordered set iteration in the inventory step is non-deterministic (I-23).

## Verdict
Reproducible for the training datasets (byte-identical); inventory order and report timestamps are the only differences.
