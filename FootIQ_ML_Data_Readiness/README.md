# FootIQ_ML_Data_Readiness - dataset version v1.0

Built 2026-10-20 from the (unmodified) FootIQ_Dataset_Submission plus Wikipedia (CC BY-SA 4.0) gap fills. No model was trained; no existing model/artifact or the original submission ZIP was touched. Start with `09_ML_READINESS_REPORT.md`.

Wikipedia-derived rows are CC BY-SA 4.0 (attribute English Wikipedia; page titles/revisions are in the `provenance` column). openfootball rows are CC0.
Undated Wikipedia matrix results (04e) cannot be used for chronological training. 2026-27 results are limited to dates before 2026-10-01 (and the sources end 2026-09-20).
Coverage rows: 614 competition-seasons; scripts in `_build/` (run s2..s9 in order); cached Wikipedia pages in `raw_external/`.

| File | Bytes | sha256 (first 16) |
|---|---|---|
| 01_COMPETITION_SEASON_COVERAGE_MATRIX.csv | 198,901 | 9753241dbd3068db |
| 02_MISSING_MATCH_INVENTORY.csv | 1,624,479 | 8dd76dc2bda3c40f |
| 03_VERIFIED_SOURCE_AND_LICENSING_REPORT.md | 6,524 | 89bb8b13418297eb |
| 04a_LEAGUE_RESULTS_v1.0.csv | 64,983,647 | f1d232a689177de1 |
| 04b_DOMESTIC_CUP_RESULTS_v1.0.csv | 3,876,905 | 648dcd7e57a5827a |
| 04c_CONTINENTAL_AND_GLOBAL_RESULTS_v1.0.csv | 3,911,256 | f3562401469cb988 |
| 04d_COMBINED_CLUB_MATCHES_v1.0.csv | 72,770,752 | 53c6ca4521e31297 |
| 04e_UNDATED_LEAGUE_RESULTS_2025-26_v1.0.csv | 488,643 | 8da2a9fd6af4febe |
| 05_CANONICAL_TEAM_IDENTITY_MAPPING.csv | 1,548,556 | f480f503ad0a41e6 |
| 06_TRAINING_LABEL_VALIDATION_REPORT.md | 2,123 | 9843601a9c8a363a |
| 06_TRAINING_LABEL_VALIDATION_SUMMARY.csv | 222 | a2b7a49dc46c46d0 |
| 07_TEMPORAL_LEAKAGE_AUDIT.md | 2,613 | c067f7076ecba81f |
| 07_TEMPORAL_LEAKAGE_TESTS.csv | 1,298 | ddf25926725e1ac8 |
| 08_TRAINING_DATASET_SCHEMA_v1.0.json | 1,330 | 796e838b2b7c98eb |
| 08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv | 65,335,922 | 605117ae6f90d0e9 |
| 08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv | 63,323,515 | a09ecbe29cd0451c |
| 09_ML_READINESS_REPORT.md | 7,279 | 3ed6bab281562d28 |
| 10_TRAIN_INFER_FEATURE_MISMATCH_AUDIT.md | 2,534 | dc2ce63202284b57 |
