# 04 Frozen model specification — Club v2-r1 (prospective candidate)

| Item | Value |
|---|---|
| Algorithm | Multinomial logistic regression (scikit-learn, lbfgs, L2, max_iter 3000, converged in 56 iterations) |
| Regularisation | C = 0.01 (development-selected; no new search) |
| Calibration | none (development evidence: vector scaling did not help) |
| Features | 62 development-approved v2 features, list in `artifacts/feature_contract_v2_final.json` (+4 missing indicators = 66 model inputs) |
| Preprocessing | median imputation + missing indicator (only columns with NaN in training) + standardisation, **refitted on the final training set** with the development-approved procedure |
| Feature generator | `_scripts/v2_features.py` after the same-day Elo update fix; Elo2 K=30, HA=50, season regression 0 (frozen from development grid; not re-tuned); Elo1 K=20/HA=60 |
| Classes | order H, D, A; confirmed 90-minute labels |
| Seed | 20261021 |
| Training data | dataset v1.1, extraction 2026-10-20, 116,854 rows, matches 2018-08-01 .. 2026-09-20 |
| Freeze timestamp | 2026-10-21 17:45:33 +05:30 |
| Training cutoff | last match date 2026-09-20 (last result in the snapshot) |
| Model artifact | `artifacts/club_v2_lr_final_candidate.pkl`, sha256 `55c1e4c53bcfefd39d5e90a1ce60a75bc697668f7894e425305bdc9a65b3e56c` |
| Other artifacts | `feature_contract_v2_final.json` sha256 `1d4fee41...0ca5`, `model_coefficients.json` sha256 `e3e67d44...a8e4`, `FROZEN.json` (full hashes, versions, code hashes) |
| Immutability | files set read-only; hashes recorded in `FROZEN.json` and `07_REPRODUCIBILITY_MANIFEST.json`; any change must be a new version (v2-r2) |
| Status | frozen research candidate; not deployed, not integrated, v1 not replaced |

Not performed: new hyperparameter search, feature re-selection, or any use of newer outcomes for choosing the configuration. The 2024-25..2026-09 outcomes (including v1's inspected test/holdout) are **training data only**; the v2-r1 model therefore has no unbiased evaluation on them.
