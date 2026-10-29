# 01 Elo mismatch investigation (582 Zimbabwe rows)

## Finding
**Verified implementation defect in the v2 feature generator (lost same-day Elo update), now fixed. It was triggered by a source-data anomaly in Zimbabwe 2021-22 (the same club listed twice on one date). Team identities, Elo initialisation and chronological ordering of the contract were not the cause.**

## Evidence chain
1. The v1 feature contract (`FootIQ_ML_Training_Preparation/_build/feature_contract.py`) run on the same results universe reproduces the stored v1.1 feature file exactly (0 of 81,934 development rows differ, max 5.7e-14). So v1.1 data, identities, source and ordering are consistent with v1.
2. The v2 re-implementation of the same Elo (`elo1`, K=20, HA=60) differed from that contract for 582 rows, all in `world/africa:zw1` from 2021-11-06 on (max 26 Elo points; `elo2` max 39 points). Initial Elo (1500), team identities (26 `world/africa|...` entities, no SRCSCOPED ids involved) and source rows were identical on both sides.
3. v2 `V2State.apply_day` took a day-start snapshot of every rating and then wrote `rating = snapshot + delta` for each match. v1's contract updates ratings sequentially. The two only diverge when a club plays two rated matches on the same day: with the snapshot, the first match's rating change is overwritten (lost update). The rated-results universe contains exactly 16 such club-days. Five are Zimbabwe 2021-22 club-days inside one competition (e.g. Harare City on 2021-11-05, FC Platinum and Highlanders on 2021-11-06): the source file lists two different fixtures for the same club on the same date, which cannot both be correct (a source/date anomaly in `zw1` 2021-22, rows L12-L22 vs L436-L468). These are the only same-day cases that produced a mismatch inside the development window, and they explain all 582 mismatching rows (the error then propagates to clubs they later play). The other 11 club-days involve one club id appearing in two competitions on the same day (identity collisions, below); none produced a mismatch inside the development window.
   The lost update did not exist in v1, because v1 updates sequentially.
4. After changing the update step to use the current rating (fixtures still receive day-start features, so leakage safety is unchanged), v2 `elo1_diff` equals the v1 contract `elo_diff` for **all 81,934** development rows (max abs diff 0.0).

## Change made
`_scripts/v2_features.py`, `V2State.apply_day`: Elo1 and Elo2 updates read the club's current rating (and current league-mean-adjusted effective rating) at update time instead of the day-start snapshot. Goal-level quantities used only for opponent-adjusted attack/defence still use the day-start league average. No change to model-selection criteria, features, folds, Elo2 parameters (kept frozen at K=30, HA=50, regression 0, not re-tuned), hyperparameters or feature set. The pre-fix generator and feature table are preserved in `_work/pre_fix/`.

## Effect on development results (frozen configuration, re-evaluated; not re-selected)
582 development rows change in `elo1_diff`/`elo2_diff`. Fold log loss of the 62-feature LR moves by at most 6e-6 (fold 1: 1.024584 -> 1.024579; fold 2 1.017028 -> 1.017026; fold 3 1.007309 -> 1.007309). Table `02_postfix_fold_metrics.csv`. The older development tables (`04`, `05`, `08` and candidate pickles in the parent folder) were computed before the fix and are left untouched as historical records; their conclusions are unchanged at the reported precision.

## Re-run checks
Leakage (three future-scrambling cutoffs), v2-vs-v1 Elo consistency (now passes), result-placeholder parity: `02b_leakage_tests_rerun_after_fix.csv`, all pass. Further train/inference parity on four historical days in `02_corrected_validation_and_parity_results.csv`.

## Related data findings (recorded, NOT changed - changing them would alter dataset v1.1 and the frozen training set)
* **Identity collisions across countries** in the `world/` namespace (clubs with the same name in different countries share one entity id): *Police FC* (Rwanda rw1 and Uganda ug1, 202 dataset rows) and *Vision FC* (Ghana gh1 and Rwanda rw1, 57 rows) - about 259 rows (0.22%) of 116,854. All other multi-competition entities (Mexico, Israel, ...) are legitimate promotion/relegation within one country. Effect: two real clubs share one Elo/form history.
* **Zimbabwe 2021-22 duplicate-date anomaly** (above).
Both are small, flagged in the approval summary, and recommended for correction in a future dataset version (v1.2) with approval; they apply equally to v1 and v2.

## Verdict
Resolved and justified; no blocker for the refit.
