# 03 Matched v1 refit report

Script `_scripts/e2_matched_v1_refit.py`; artifacts in `artifacts/` (read-only): `matched_v1_lr_refit.pkl` (sha256 `33bd80f6a3268256e250294f4c9b4ffc4f530489c332878fd70655fea145ec34`), `matched_v1_preprocessing.json` (`77a30670...b61`), `matched_v1_coefficients.json` (`10aae472...91c`), `MATCHED_V1_FROZEN.json`.

## Recipe (the original v1 recipe, nothing new)
* 25 v1 contract features (`feature_contract_v1.1.json`), recomputed leak-safely from the results universe with the unchanged v1 contract code and compared with the stored v1.1 feature file: max abs difference 4.5e-13, identical NaN pattern. No v2-only feature is imported.
* Preprocessing rule of `b2_fit_select_freeze.py`: training medians, mean/std (ddof 0), missing indicators for columns with NaN plus both `venue_ppg5` columns (identical indicator set to the original v1 artifact), fitted on the matched training set.
* Multinomial LR, C=100, L2, lbfgs, max_iter 3000, seed 20261020 (original v1 values taken from `multinomial_logreg_coefficients.json`; not re-selected, no grid, no look at any v2 result or evaluation outcome).
* Training data: the same 116,854 rows, cutoff 2026-09-20, as frozen v2 (report 05). Converged in 29 iterations; in-sample log loss 1.0205 (sanity only).
* The original v1 artifact is untouched (hash verified); coefficient correlation between original v1 and the matched refit is 0.986, i.e. the refit is a faithful update of the same model.

## Use
Comparator only (`v1_matched` in the protocol). It does not replace v1 and is not deployed.
