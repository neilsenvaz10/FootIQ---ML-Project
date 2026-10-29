# 02 Chronological cross-validation protocol (frozen 2026-10-21 13:59 before any model experiment)

Frozen copy: `supporting_tables/protocol_frozen.json`. Fold sizes: `02b_CV_FOLD_SIZES.csv`. Seed 20261021.

## Data boundary
* Only rows with `match_date <= 2024-06-30` (train + validation partitions of dataset v1.1) are loaded. The state machine that builds features never sees a match after that date.
* The v1 test (2024-07-01..2025-06-30) and the v1 forward holdout (2025-07-01..2026-09-30) were inspected in the v1 experiment. They are **not used** for tuning, feature selection, calibration, promotion — and v2 is not evaluated on them. They are not renamed "fresh".

## Folds (expanding window, one year ahead)
| Fold | Train | Validation | Train rows | Validation (primary) |
|---|---|---|---|---|
| 1 | <= 2021-06-30 | 2021-07-01..2022-06-30 | 33,707 | 10,086 |
| 2 | <= 2022-06-30 | 2022-07-01..2023-06-30 | 46,184 | 9,703 |
| 3 | <= 2023-06-30 | 2023-07-01..2024-06-30 | 59,356 | 17,092 |

Validation "primary" = complete (or complete-through-cutoff) split-year league-seasons without identity-review flags (mirrors v1.1). Calendar-year leagues are reported separately (secondary; not pooled).

## Calibration windows
Within each fold the last 12 months of the training period form a separate calibration window; the base model for calibration experiments is fitted on the earlier "core" rows only (e.g. fold 1: core <= 2020-06-30, calibration 2020-07-01..2021-06-30). Uncalibrated reference models are fitted on the whole training window. Calibrators were never fitted on validation rows.

## Leakage controls
* Features for day D come from matches strictly before D; state updates after the whole day (same-day matches do not see each other).
* Imputation, standardisation and calibration are fitted on training windows only.
* Tests (`supporting_tables/leakage_parity_tests.csv`): scrambling every score on/after a cutoff and deleting later matches leaves all feature values for earlier rows bit-identical at three cutoffs (2019-12-31, 2021-12-31, 2023-06-30); placing a placeholder result on the last day's fixtures leaves their features unchanged (train/inference parity).

## Metrics and selection rule (frozen)
Primary: mean multiclass log loss across the 3 folds. Secondary: Brier, ECE, accuracy, macro-F1, class F1, draw metrics, fold standard deviation. A feature group is retained when it improves log loss by >= 0.0010 on average and in >= 2 of 3 folds without harming the other probe. Algorithm configurations: small fixed, pre-listed grids (LR C in {0.01,0.1,1}; 6 RF; 8 HGB configurations). Only three folds exist, so differences below ~0.001 are within fold noise (fold std ~0.008).
Paired uncertainty: cluster bootstrap over competition x season (130 clusters, 2,000 resamples).
