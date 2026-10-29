# Model v2.6 Bake-Off + Calibration

V2.6 compares match-prediction architectures on time-safe historical data. The production model should not be chosen by gut feel; it should beat simple baselines on recent unseen matches.

## Data Split

- Train: 2000-01-01 through 2018-12-31 (18164 matches).
- Calibration: 2019-01-01 through 2022-12-31 (3580 matches).
- Test: 2023-01-01 through 2026-12-31 (3491 matches).

## Best Model

- Best calibrated probability model: **ensemble** by log loss.
- Best public-pick gate after pass rules: **ensemble_logistic_consensus_gate** by accepted-pick accuracy.
- Recommended production shape: ensemble probabilities for the simulator, with a conservative public gate for match calls.

## Ensemble Weights

- elo_formula: 30.0%
- v25_poisson_lite: 0.0%
- logistic_regression: 20.0%
- gradient_boosting: 50.0%

## Test Metrics

| Model | Log loss | Brier | Argmax acc | ECE | Public coverage | Public pick acc | Pass messy rate | Draw precision | Draw recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ensemble | 0.85653 | 0.50425 | 0.60871 | 0.03034 | 0.60985 | 0.71771 | 0.56241 | 0.2 | 0.00125 |
| ensemble_logistic_consensus_gate | 0.85653 | 0.50425 | 0.60871 | 0.03034 | 0.4672 | 0.76824 | 0.53172 | 0.2 | 0.00125 |
| gradient_boosting | 0.86014 | 0.50513 | 0.6067 | 0.02042 | 0.57147 | 0.72832 | 0.55816 | 0.28571 | 0.005 |
| elo_formula | 0.87402 | 0.51359 | 0.60785 | 0.03891 | 0.62217 | 0.70442 | 0.55118 | 0.0 | 0.0 |
| random_forest | 0.87835 | 0.51734 | 0.57491 | 0.04511 | 0.46663 | 0.76243 | 0.69173 | 0.27843 | 0.23875 |
| logistic_regression | 0.88001 | 0.51812 | 0.57147 | 0.04058 | 0.47408 | 0.76495 | 0.72767 | 0.28167 | 0.28625 |
| v25_poisson_lite | 0.88503 | 0.52188 | 0.60097 | 0.02425 | 0.56001 | 0.70435 | 0.5306 | 0.0 | 0.0 |

## Pass Rule Meaning

A pass means the model refuses to sell the match as a public pick. It can still have an internal lean, but the confidence/gap/draw-risk combination is not strong enough. The consensus gate is stricter: it passes unless ensemble and logistic regression agree on the same non-pass public pick.

## Honest Read

This bake-off chooses the match model only. The World Cup tournament simulator remains a separate layer that will consume whichever match model wins.
