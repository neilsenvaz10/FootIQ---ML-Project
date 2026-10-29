# FootIQ_Club_Model_Baseline_v1

Controlled baseline experiment (club domestic-league 90-minute 1X2, dataset v1.1). Models: always-home, Elo ordered-logit mapping, multinomial logistic regression. One experiment, executed once (see `EVALUATION_LOCK.json`, `artifacts/FROZEN.json`).

Read in this order: `01_TRAINING_EXECUTION_REPORT.md`, `02_MODEL_COMPARISON_REPORT.md`, `04_TEST_METRICS.csv`, `05_FORWARD_HOLDOUT_METRICS.csv`, `06_LEAGUE_WISE_PERFORMANCE_REPORT.md`, `07_CALIBRATION_AND_CONFUSION_ANALYSIS.md`, `08_MISSING_HISTORY_SENSITIVITY_REPORT.md`, `10_REPRODUCIBILITY_MANIFEST.json`.
Artifacts (model, preprocessing, parameters, coverage categories): `artifacts/`. Predictions: `predictions_validation.csv`, `predictions_validation_test_holdout.csv`. Scripts: `_scripts/` (b1 checks, b2 fit/select/freeze, b3 locked evaluation, b4 reports).
The preserved international model, the original datasets and the v1.1 preparation files were not modified (verified by hash in `_pretraining_checks.json`).
