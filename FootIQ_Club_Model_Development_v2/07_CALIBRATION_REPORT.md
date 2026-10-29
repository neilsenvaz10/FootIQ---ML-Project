# 07 Calibration report

Method: per fold, base model fitted on the "core" window (training period minus its last 12 months), vector scaling (multinomial LR on log-probabilities, C=10) fitted on the last-12-months calibration window, evaluated on the next-year validation fold. Table: `supporting_tables/calibration_summary.csv` and `calibration_by_fold.csv`.

| Model | Variant | Log loss (mean of 3 folds) | Brier | ECE (one-vs-rest, 10 bins) | |mean pD - draw rate| |
|---|---|---|---|---|---|
| v2 LR full | uncalibrated (core fit) | 1.01696 | 0.6094 | 0.0098 | 0.0029 |
| v2 LR full | vector-scaled | 1.01718 | 0.6096 | 0.0131 | 0.0076 |
| v2 LR selected | uncalibrated | 1.01808 | 0.6102 | 0.0096 | 0.0026 |
| v2 LR selected | vector-scaled | 1.01826 | 0.6103 | 0.0137 | 0.0084 |
| v2 HGB full | uncalibrated | 1.02051 | 0.6116 | 0.0099 | 0.0018 |
| v2 HGB full | vector-scaled | 1.02025 | 0.6116 | 0.0132 | 0.0090 |
| v2 RF full | uncalibrated | 1.01845 | 0.6103 | 0.0115 | 0.0033 |
| v2 RF full | vector-scaled | 1.01861 | 0.6105 | 0.0140 | 0.0088 |
| v1 LR 25 | uncalibrated | 1.01939 | 0.6110 | 0.0107 | 0.0047 |
| v1 LR 25 | vector-scaled | 1.01975 | 0.6113 | 0.0143 | 0.0089 |

Findings:
* All models are already well calibrated (ECE about 0.01); a 12-month calibration window (about 13k matches) adds estimation noise that is not repaid: vector scaling made ECE and log loss slightly worse for every model except HGB (-0.0003 log loss, ECE still worse). **Calibration is not recommended** for the v2 candidate; none of the differences exceed fold noise.
* The core-fit rows above use less training data than the full-training results in `05_ALGORITHM_COMPARISON.csv` (which is why LR full is 1.0170 here vs 1.0163 there).
* Calibration was fitted only on dev data windows preceding each validation year; no v1 test/holdout rows were involved.
* By-group calibration of the draw class: v2 LR deciles are within ~0.01 of observed (report 06). Per-league calibration is not reported beyond league log-loss in `08_LEAGUE_GROUP_PERFORMANCE.csv` because most competitions have under 1,500 validation matches.
