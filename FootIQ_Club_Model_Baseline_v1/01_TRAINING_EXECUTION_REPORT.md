# 01 Training execution report - FootIQ club baseline v1 (generated 2026-10-20 23:25)

## 1. Protocol (fixed before any metric was computed)
1. `_scripts/b1_pretraining_checks.py` - mandatory verification (stop on failure).
2. `_scripts/b2_fit_select_freeze.py` - fit on **train**, select on **validation primary rows**, freeze artifacts. Test and forward-holdout labels are masked in this script (set to NaN right after loading) and were not read for any decision.
3. `_scripts/b3_locked_evaluation.py` - loads the frozen artifacts (SHA-256 re-verified), creates `EVALUATION_LOCK.json` and evaluates test and forward holdout **once**; it refuses to run again.
4. `_scripts/b4_reports.py` - writes the reports from saved tables.
No model, setting or rule was changed after step 3.

## 2. Pre-training verification (17/17 checks passed)
| check | passed | detail |
|---|---|---|
| eligible matches == 116,854 (dataset file) | True | 116854 |
| eligible matches == 116,854 (feature file) and identical record ids | True |  |
| exactly 25 approved features in contract order | True | ['home_elo', 'away_elo', 'elo_diff', 'home_n_prior', 'away_n_prior', 'home_ppg5', 'away_ppg5', 'home_ppg10', ' |
| feature dictionary lists the same 25 features in the same order | True |  |
| no target / outcome / meta / future-derived field among the model inputs | True | [] |
| meta_* and label columns are outside the feature list | True |  |
| split boundaries and row counts equal the manifest | True | {'train': (59356, '2018-08-01', '2023-06-30'), 'validation': (22578, '2023-07-01', '2024-06-30'), 'test': (260 |
| splits are chronologically ordered without overlap | True |  |
| every row is a confirmed 90-minute label of a domestic league | True |  |
| no cup / international / Wikipedia record in the training data | True |  |
| primary evaluation flags available (validation/test/holdout) | True | {'train': 0, 'validation': 17092, 'test': 15645, 'forward_holdout': 5770} |
| v1.1 preparation files are unchanged since they were documented (README hashes) | True | [] |
| Milestone 1 baseline files unchanged (incl. preserved international model artifact) | True | 522 files, changed 0 |
| original submission, readiness and verification outputs unchanged | True | [] |
| international model artifact exists and is not in the output folder | True |  |
| forward-holdout and test labels are masked in all training code paths | True | b2 loads labels for train/validation only; test and holdout labels are never read before the frozen evaluation |
| learned preprocessing is fitted on split == train only | True | b2 computes medians / means / stds on train rows; verified again after fitting by recomputation |

## 3. Data
* Dataset v1.1 `01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv` SHA-256 `0d7b73117b442298e4e050f690c55e32c1d25798e244052ec12e41b54ff10da7`; feature file SHA-256 `4e74c21586bc31651462d7408637cd3f894fd21d034a8f6236c6b34cff54be19`.
* Eligible matches 116,854: train 59,356, validation 22,578, test 26,000, forward holdout 8,920.
* **Exact training sample: 59,356 matches** (2018-08-01 to 2023-06-30, domestic leagues only; no cup, continental or international record).
* Evaluation sets: validation primary 17,092; test primary 15,645; forward-holdout primary 5,770; calendar-year leagues are secondary sets reported separately (test 3,449; holdout 570).
* Features (25, contract order): home_elo, away_elo, elo_diff, home_n_prior, away_n_prior, home_ppg5, away_ppg5, home_ppg10, away_ppg10, home_gf5, home_ga5, away_gf5, away_ga5, home_gf10, home_ga10, away_gf10, away_ga10, home_venue_ppg5, away_venue_ppg5, ppg5_diff, gd5_diff, home_days_rest, away_days_rest, rest_diff, league_tier.

## 4. Preprocessing (fitted on train only, `artifacts/preprocessing_train_fitted.json`)
Median imputation (train medians) with missing indicators for ['away_venue_ppg5', 'home_venue_ppg5']; standardisation with train mean and standard deviation (population std). No target encoding, no categorical features, no scaling of the label. Recomputation of the statistics from the train rows reproduced them exactly.

## 5. Models
| model | specification |
|---|---|
| Always-home | predicts H for every match; its probabilities are the train class frequencies {'H': 0.4359121234584541, 'D': 0.2649268818653548, 'A': 0.2991609946761911} (needed for log loss / Brier) |
| Elo ordered logit | one parameter set mapping `elo_diff` to H/D/A: scale 0.4935 per 100 Elo, thresholds -0.9108 and 0.2794; fitted by maximum likelihood on train (L-BFGS-B, converged: True) |
| Multinomial logistic regression | scikit-learn 1.5.1, `LogisticRegression(penalty=l2, solver=lbfgs, max_iter=3000, random_state=20261020)`, 27 inputs (25 standardised features + 2 missing indicators); C selected on validation |

C grid on validation primary rows (log loss is the selection criterion):
| C | accuracy | macro_f1 | log_loss | brier | n_validation_primary | iterations |
|---|---|---|---|---|---|---|
| 0.0001 | 0.4988 | 0.3614 | 1.0164 | 0.6087 | 17092 | 10 |
| 0.0010 | 0.5002 | 0.3657 | 1.0121 | 0.6058 | 17092 | 19 |
| 0.0100 | 0.5011 | 0.3669 | 1.0118 | 0.6056 | 17092 | 28 |
| 0.1000 | 0.5010 | 0.3669 | 1.0118 | 0.6056 | 17092 | 28 |
| 1.0000 | 0.5009 | 0.3668 | 1.0118 | 0.6056 | 17092 | 28 |
| 10.0000 | 0.5009 | 0.3668 | 1.0118 | 0.6056 | 17092 | 28 |
| 100.0000 | 0.5009 | 0.3668 | 1.0118 | 0.6056 | 17092 | 28 |

Selected C = 100. Log loss differs by less than 1e-6 for C >= 1 (the L2 penalty is no longer active), so the choice among these values is immaterial; the tie-break picked the numerically lowest loss.
Best model on validation primary log loss: **multinomial_logreg**.

## 6. Freeze record
Frozen at 2026-10-20 23:22:58; evaluation executed once between 2026-10-20 23:23:38 and 2026-10-20 23:23:44. Artifact SHA-256 values are in `10_REPRODUCIBILITY_MANIFEST.json`.

## 7. Dependencies and seeds
{'numpy': '1.26.4', 'pandas': '2.2.1', 'scikit-learn': '1.5.1', 'scipy': '1.17.1'}; seed 20261020 (numpy seed, `random_state`, bootstrap generator). Training is deterministic (lbfgs, no sampling).
