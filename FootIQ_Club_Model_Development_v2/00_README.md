# FootIQ Club Match Prediction ML v2 — development folder

Status: research/development only. Branch `feat/club-ml-v2`. Nothing committed, pushed, merged or deployed. v1 is not replaced. Start with `12_FINAL_V2_DEVELOPMENT_REPORT.md`.

| File | Content |
|---|---|
| 01_BASELINE_DIAGNOSTIC_REPORT.md | Why v1 behaves as it does |
| 02_CHRONOLOGICAL_CV_PROTOCOL.md (+02b fold sizes) | Frozen leakage-safe protocol |
| 03_FEATURE_ENGINEERING_REPORT.md (+03b Elo grid) | Feature groups |
| 04_FEATURE_ABLATION_RESULTS.csv | Group ablation with decisions |
| 05_ALGORITHM_COMPARISON.csv | LR / RF / HGB / baselines, all configurations |
| 06_DRAW_PREDICTION_ANALYSIS.md | Draw probability vs decision policy |
| 07_CALIBRATION_REPORT.md | Calibration on separate windows |
| 08_LEAGUE_GROUP_PERFORMANCE.csv | Tier, cold-start, fold, per-competition |
| 09_MODEL_SELECTION_REPORT.md | Candidate, roles, bootstrap |
| 10_PROSPECTIVE_EVALUATION_PLAN.md | What must happen before promotion |
| 11_REPRODUCIBILITY_MANIFEST.json | Versions, seeds, hashes, folds, hyperparameters |
| 12_FINAL_V2_DEVELOPMENT_REPORT.md | Summary |
| `_scripts/`, `_work/`, `artifacts/`, `supporting_tables/` | Code, intermediates, candidate pickles (unpickling requires `_scripts` on the path), extra tables |

Data boundary: only matches dated <= 2024-06-30 were used. v1 test and forward holdout outcomes were never loaded.
