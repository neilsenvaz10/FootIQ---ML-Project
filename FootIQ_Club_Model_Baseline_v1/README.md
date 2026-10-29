# FootIQ Club Model Baseline v1

This directory contains the code, configurations, frozen artifacts, evaluation metrics, and audit reports for the **FootIQ Club Model Baseline v1** controlled experiment.

The objective of this milestone is to establish a rigorous, leak-free, chronological baseline for predicting domestic club league regulation-time match outcomes (Home / Draw / Away — 1X2) prior to building advanced gradient-boosted or deep neural network architectures.

---

## 1. Dataset Scope & Provenance

### Source & Licensing
* **100% CC0-1.0 (Public Domain):** All club match records and ground truth labels are derived exclusively from the [openfootball](https://github.com/openfootball) repositories (extracted 2026-10-20), carrying the Creative Commons CC0 1.0 Universal public domain dedication.
* **License Purity & Exclusions:**
  * **Wikipedia data excluded:** 1,571 matches in earlier exploration derived from English Wikipedia were excluded due to CC BY-SA 4.0 share-alike and attribution complexities. (Wikipedia was only used for cup/continental matches, which are out of scope here).
  * **Commercial / Scraped data excluded:** Third-party proprietary sources such as Football-Data.co.uk (which prohibits automated and machine learning usage) and StatsBomb event data are strictly excluded from club baseline training.
  * **Competition Scope:** Domestic regular round-robin league matches only. All cup ties, international matches, promotion/relegation play-offs, and tournament finals were filtered out.

### Data Cleaning & Verification
* **Source-Level Calendar Audit:** Match dates were re-resolved and verified against repository calendar windows. 7,607 matches from Nigerian competitions with unverifiable dotted dates (`DD.MM.`) were excluded.
* **Duplicate Elimination:** Removed 240 Russian second-tier (ru2) 2019–20 duplicate matches where file contents were identical to the top tier (ru1), and excluded 8 ambiguous same-day duplicate fixtures.
* **Season Label Validation:** Reconciled 706 historically flagged season labels (e.g. Belgian first division folder `2021-22` corrected to `2020-21` based on source title and verified match dates).
* **Confirmed 90-Minute Results:** Every included record has a confirmed regulation-time score with zero extra-time or shootout distortion.

---

## 2. Dataset Split & Chronological Methodology

The dataset is partitioned into strictly chronological, non-overlapping windows to prevent lookahead and temporal leakage:

```
[--- Train (59,356) ---] [--- Validation (22,578) ---] [--- Test (26,000) ---] [--- Forward Holdout (8,920) ---]
2018-08-01    2023-06-30 2023-07-01        2024-06-30 2024-07-01   2025-06-30 2025-07-01            2026-09-30
```

### Eligible Matches Breakdown (116,854 Total Matches)

| Split | Date Range | Total Eligible Matches | Primary Evaluation Matches | Secondary Calendar-Year Matches | Unused / Excluded from Eval |
|---|---|---|---|---|---|
| **Train** | 2018-08-01 to 2023-06-30 | **59,356** | — *(used for fitting)* | — | — |
| **Validation** | 2023-07-01 to 2024-06-30 | **22,578** | 17,092 | 5,015 | 471 |
| **Test** | 2024-07-01 to 2025-06-30 | **26,000** | 15,645 | 3,449 | 6,906 |
| **Forward Holdout** | 2025-07-01 to 2026-09-30 | **8,920** | 5,770 | 570 | 2,580 |
| **Total** | | **116,854** | **38,507** | **9,034** | **9,957** |

* **Primary Evaluation Sets:** Complete split-year league seasons with verified historical completeness and no unresolved team identity splits.
* **Secondary Evaluation Sets:** Calendar-year leagues (e.g. Nordic and South American summer leagues); reported separately to avoid seasonal boundary artifacts.
* **Excluded from Evaluation:** Incomplete seasons (75 league-seasons still ongoing or missing fixtures at cutoff) and records under identity review.

---

## 3. Training & Preprocessing (59,356 Training Matches)

All models and transformations were trained strictly on the **59,356 training matches**:

1. **Features (25 Contract Features + 2 Missing Indicators):**
   * **Ratings:** `home_elo`, `away_elo`, `elo_diff`
   * **Experience / Depth:** `home_n_prior`, `away_n_prior`
   * **Short-Term Form (5 matches):** `home_ppg5`, `away_ppg5`, `home_gf5`, `home_ga5`, `away_gf5`, `away_ga5`, `ppg5_diff`, `gd5_diff`
   * **Medium-Term Form (10 matches):** `home_ppg10`, `away_ppg10`, `home_gf10`, `home_ga10`, `away_gf10`, `away_ga10`
   * **Venue-Specific Form:** `home_venue_ppg5`, `away_venue_ppg5`
   * **Schedule & Context:** `home_days_rest`, `away_days_rest`, `rest_diff`, `league_tier`
   * **Missing Indicators:** `missing_indicator__home_venue_ppg5`, `missing_indicator__away_venue_ppg5`
2. **Leak-Free Preprocessing (`artifacts/preprocessing_train_fitted.json`):**
   * Imputation medians and standardization statistics (mean and population standard deviation) were calculated **exclusively on the training split**.
   * Test and forward-holdout labels were masked (`NaN`) during training and tuning code paths to eliminate inadvertent data snooping.

---

## 4. Models & Controlled Evaluation Protocol

Three baselines were evaluated:
1. **Always-Home Baseline:** Predicts the home win for every match. Predictive probabilities are fixed to the training set class frequencies ($P(H) \approx 0.4359, P(D) \approx 0.2649, P(A) \approx 0.2992$).
2. **Elo Ordered Logit Baseline:** A single-feature ordinal logistic regression model mapping `elo_diff` to 1X2 probabilities with learned home/draw cut points ($scale = 0.4935$ per 100 Elo points; thresholds $\theta_1 = -0.9108, \theta_2 = 0.2794$).
3. **Multinomial Logistic Regression:** Scikit-learn multinomial logistic regression (L2 regularization, L-BFGS solver, `max_iter=3000`, `random_state=20261020`) trained on all 27 inputs. Hyperparameter $C$ was selected over a grid $\{10^{-4}, 10^{-3}, 10^{-2}, 10^{-1}, 1, 10, 100\}$ on validation primary log loss ($C=100$ selected; unpenalized regime).

### Controlled One-Time Freeze Protocol
* **Step 1 (`_scripts/b1_pretraining_checks.py`):** Verified 17 critical integrity checks before fitting.
* **Step 2 (`_scripts/b2_fit_select_freeze.py`):** Fit models on train, chose $C$ on validation, and froze all model artifacts in `artifacts/FROZEN.json` with cryptographic SHA-256 signatures.
* **Step 3 (`_scripts/b3_locked_evaluation.py`):** Evaluated the frozen artifacts against test and forward holdout **once** and created `EVALUATION_LOCK.json`. The script refuses to run again if the lock exists.
* **Step 4 (`_scripts/b4_reports.py`):** Generated immutable benchmark reports.

---

## 5. Benchmark Performance

*Note: For Log Loss and Brier Score, lower is better. For Accuracy and Macro F1, higher is better. Chance baseline for 3-class uniform prediction: Log Loss $\approx 1.0986$, Brier $\approx 0.6667$.*

### Summary Metrics Across Splits

| Split | Model | Sample Size ($N$) | Accuracy | Macro F1 | Multiclass Log Loss | Brier Score |
|---|---|---|---|---|---|---|
| **Validation (Primary)** | Always-Home | 17,092 | 43.62% | 0.2025 | 1.0737 | 0.6496 |
| | Elo Ordered Logit | 17,092 | 49.65% | 0.3606 | 1.0154 | 0.6081 |
| | **Multinomial LogReg** | 17,092 | **50.09%** | **0.3668** | **1.0118** | **0.6056** |
| **Test (Primary, 2024–25)** | Always-Home | 15,645 | 43.16% | 0.2010 | 1.0758 | 0.6511 |
| | Elo Ordered Logit | 15,645 | 50.00% | 0.3672 | 1.0097 | 0.6042 |
| | **Multinomial LogReg** | 15,645 | **50.16%** | **0.3707** | **1.0073** | **0.6026** |
| **Forward Holdout (Primary, 2025–26+)** | Always-Home | 5,770 | 43.81% | 0.2031 | 1.0753 | 0.6504 |
| | Elo Ordered Logit | 5,770 | **49.60%** | **0.3643** | 1.0112 | 0.6058 |
| | **Multinomial LogReg** | 5,770 | 49.43% | 0.3630 | **1.0071** | **0.6032** |
| **Test (Secondary Calendar-Year)** | Elo Ordered Logit | 3,449 | 48.33% | 0.3479 | 1.0197 | 0.6111 |
| | **Multinomial LogReg** | 3,449 | **48.68%** | **0.3493** | **1.0155** | **0.6085** |
| **Forward Holdout (Secondary)** | Elo Ordered Logit | 570 | **52.28%** | **0.3814** | 0.9997 | 0.5985 |
| | **Multinomial LogReg** | 570 | 51.93% | 0.3749 | **0.9921** | **0.5941** |

### Paired Bootstrap Significance (2,000 Resamples)
* **Test Primary (`multinomial_logreg` vs `elo_ordered_logit`):** Mean log-loss difference = $-0.00239$ ($95\%\text{ CI: } [-0.00384, -0.00092]$).
* **Forward Holdout Primary:** Mean log-loss difference = $-0.00407$ ($95\%\text{ CI: } [-0.00641, -0.00163]$).
* **Interpretation:** While the logistic regression shows a statistically significant edge in log loss over Elo alone ($p < 0.05$), the magnitude of the improvement is tiny ($0.2\% - 0.4\%$ of total loss). The 22 additional form and rest features provide negligible predictive gain over a well-calibrated Elo rating difference.

---

## 6. Critical Findings & Limitations

1. **Draw Prediction Failure:**
   * Both learned models almost never predict a draw. On the primary test set of 15,645 matches (which included 4,059 actual draws), multinomial logistic regression predicted a draw in only **14 matches** (Recall: 0.12%, Precision: 35.7%, F1: 0.0025). Elo ordered logit predicted **0 draws** (Recall: 0%, F1: 0.0000).
   * Predicted draw probabilities remain clustered near the historical prior ($\sim 26\%$) across matches because pre-match rolling form features lack the discriminatory power to separate tight draws from narrow wins.
2. **Restricted League Coverage & Generalization:**
   * Performance varies substantially by competition structure. In top European leagues (e.g., Premier League, Serie A, La Liga), test log loss is $\sim 0.97 - 0.99$, whereas in lower tiers (e.g. tier-3 and regional leagues), log loss degrades to $1.04 - 1.06$.
   * Matches involving clubs with shallow historical ratings ($< 63$ rated matches) show higher variance, though rolling form features help compensate where Elo ratings are young.
3. **Observed Baseline Performance:**
   * Across all evaluated splits, top-line accuracy for these specific baselines remained around **50.1% - 50.2%**.
   * This represents the observed performance level of simple linear and ordinal models trained exclusively on basic pre-match historical rolling form and Elo ratings; it does not represent an intrinsic ceiling for football match forecasting with richer feature engineering, market consensus, or advanced model families.

---

## 7. Directory Structure & Key Files

```
FootIQ_Club_Model_Baseline_v1/
├── README.md                                    # This comprehensive guide
├── 00_README.md                                 # Original manifest summary
├── 01_TRAINING_EXECUTION_REPORT.md              # Pre-training verification & fit report
├── 02_MODEL_COMPARISON_REPORT.md                # Primary & secondary comparison tables
├── 02b_PAIRED_BOOTSTRAP_LOGLOSS_DIFFERENCES.csv # Bootstrap confidence intervals
├── 03_VALIDATION_METRICS.csv                    # Validation metrics table
├── 03_VALIDATION_METRICS_RECOMPUTED.csv         # Recomputed validation metrics verification
├── 03b_VALIDATION_C_GRID.csv                    # Hyperparameter grid search log
├── 04_TEST_METRICS.csv                          # Primary & secondary test metrics
├── 05_FORWARD_HOLDOUT_METRICS.csv               # Primary & secondary holdout metrics
├── 06_LEAGUE_WISE_PERFORMANCE_REPORT.md         # League tier and individual league metrics
├── 06a_LEAGUE_WISE_METRICS.csv                  # League-by-league metrics
├── 06b_LEAGUE_GROUP_METRICS.csv                 # Metrics by tier group (G1 to G5)
├── 06c_LEAGUE_WISE_LOGREG_VS_BASELINES.csv      # LogReg vs Elo by league
├── 07_CALIBRATION_AND_CONFUSION_ANALYSIS.md     # Confusion matrices & Expected Calibration Error
├── 07a_PER_CLASS_PERFORMANCE.csv                # Precision, recall, and F1 by outcome
├── 07b_CONFUSION_MATRICES.csv                   # Confusion matrices by split
├── 07c_CALIBRATION_BINS.csv                     # 10-bin reliability diagram data
├── 07d_CALIBRATION_ECE.csv                      # Expected Calibration Error values
├── 08_MISSING_HISTORY_SENSITIVITY_REPORT.md     # Analysis by history depth and league coverage
├── 08a_COVERAGE_GROUP_METRICS.csv               # Coverage group performance
├── 08b_HISTORY_DEPTH_METRICS.csv                # History depth performance
├── 10_REPRODUCIBILITY_MANIFEST.json             # Cryptographic hashes of all inputs & outputs
├── EVALUATION_LOCK.json                         # Execution timestamp & freeze record
├── _evaluation_split_hashes.json                # SHA-256 hashes of record IDs per split
├── _eval_tables.pkl                             # Pickled evaluation summary metrics
├── _pretraining_checks.json                     # JSON results of 17 pre-training checks
├── artifacts/
│   ├── FROZEN.json                              # Frozen artifact hash manifest
│   ├── baseline_parameters.json                 # Always-home and Elo parameter values
│   ├── coverage_categories.json                 # League coverage & history depth cut points
│   ├── multinomial_logreg.pkl                   # Trained scikit-learn model artifact (1.3 KB)
│   ├── multinomial_logreg_coefficients.json     # Feature coefficients and intercepts
│   └── preprocessing_train_fitted.json          # Train-fitted imputation medians, means, stds
└── _scripts/
    ├── common.py                                # Shared helper functions & metrics (repo-relative)
    ├── b1_pretraining_checks.py                 # 17 pre-training verification checks
    ├── b2_fit_select_freeze.py                  # Train fitting, C selection, artifact freezing
    ├── b3_locked_evaluation.py                  # Single-run locked evaluation on test & holdout
    └── b4_reports.py                            # Report & documentation generator
```

*(Note: Raw match prediction CSV files `predictions_validation.csv` [5.7 MB] and `predictions_validation_test_holdout.csv` [15.4 MB] are intentionally excluded from the Git repository to keep the repository lightweight. Their exact SHA-256 signatures are preserved in `10_REPRODUCIBILITY_MANIFEST.json` and they can be regenerated by running the locked evaluation script with the source datasets).*

---

## 8. Reproducibility & Verification

To verify or reproduce the experiment:

### Level 1: Fully Self-Contained Verification (Directly from Git)
All files required to verify the frozen model, inspect coefficients, review evaluation metrics, and run inference are included in this repository:
1. **Load Trained Model Artifact:**
   ```python
   import pickle, json
   with open("FootIQ_Club_Model_Baseline_v1/artifacts/multinomial_logreg.pkl", "rb") as f:
       model = pickle.load(f)
   with open("FootIQ_Club_Model_Baseline_v1/artifacts/multinomial_logreg_coefficients.json") as f:
       coefficients = json.load(f)
   print("Classes:", model.classes_, "Number of features:", model.n_features_in_)
   ```
2. **Inspect Preprocessing & Baseline Parameters:**
   Examine `artifacts/preprocessing_train_fitted.json` for train-fitted medians, means, and standard deviations, and `artifacts/baseline_parameters.json` for the fitted Elo ordered logit parameters.
3. **Regenerate Markdown Reports:**
   ```bash
   python FootIQ_Club_Model_Baseline_v1/_scripts/b4_reports.py
   ```
   This generates the full suite of comparison, league-wise, calibration, and sensitivity markdown reports directly from `_eval_tables.pkl`.

### Level 2: End-to-End Retraining (Requires External Datasets)
Full end-to-end retraining from raw inputs requires the input match and feature CSVs:
1. **Acquire/Build Documented Datasets:**
   Obtain `01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv` and `02_CORRECTED_FEATURE_DATASET_v1.1.csv` (built from openfootball CC0-1.0 repositories via `FootIQ_ML_Training_Preparation/_build/`).
2. **Verify Cryptographic Signatures:**
   Confirm file hashes match `10_REPRODUCIBILITY_MANIFEST.json`:
   - `01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv`: `0d7b73117b442298e4e050f690c55e32c1d25798e244052ec12e41b54ff10da7`
   - `02_CORRECTED_FEATURE_DATASET_v1.1.csv`: `4e74c21586bc31651462d7408637cd3f894fd21d034a8f6236c6b34cff54be19`
3. **Execute Verification & Training Pipeline:**
   - Run `python FootIQ_Club_Model_Baseline_v1/_scripts/b1_pretraining_checks.py` (verifies 17 data invariants).
   - If refitting is intended, remove `artifacts/FROZEN.json` and run `_scripts/b2_fit_select_freeze.py`.
   - If re-evaluating is intended, remove `EVALUATION_LOCK.json` and run `_scripts/b3_locked_evaluation.py`.

