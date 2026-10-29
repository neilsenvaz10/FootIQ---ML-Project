# Confidence Gate v2.8

V2.8 is a product confidence upgrade on top of v2.7. It does not retrain the prediction model.

## Tiers

| Tier | Meaning |
|---|---|
| Strong Pick | Ensemble and logistic safety gate agree. |
| Model Lean | Ensemble has a usable signal, but the safety gate blocks a strong call. |
| Pass | Edge is too weak, too draw-heavy, or data quality is too low. |

## Historical Calibration

| Tier | Matches | Coverage | Accuracy |
|---|---:|---:|---:|
| Strong Pick | 1631 | 46.72% | 76.82% |
| Model Lean | 499 | 14.29% | 55.31% |
| Pass | 1361 | 38.99% |  |

## Known Live Validation

| Tier | Matches | Coverage | Accuracy |
|---|---:|---:|---:|
| Strong Pick | 0 | 0.0% |  |
| Model Lean | 0 | 0.0% |  |
| Pass | 7 | 100.0% |  |

## Current v2.8 Live Labels

| Match | v2.7 public | v2.8 tier | v2.8 pick | Top prob |
|---|---|---|---|---:|
| Portugal vs Chile | pass | Pass | pass | 64.21% |
| Germany vs USA | pass | Pass | pass | 38.65% |
| Bolivia vs Scotland | pass | Pass | pass | 44.60% |
| Brazil vs Egypt | pass | Pass | pass | 60.04% |
| Argentina vs Honduras | pass | Pass | pass | 76.36% |
| Morocco vs Norway | pass | Pass | pass | 39.04% |
| Colombia vs Jordan | pass | Pass | pass | 62.37% |
| Argentina vs Iceland | pass | Model Lean | team1_win | 80.97% |

## Ad Hoc June 10 Slate With v2.8

| Match | v2.8 tier | v2.8 pick | v2.7 internal | Predicted score |
|---|---|---|---|---|
| Portugal vs Nigeria | Model Lean | team1_win | team1_win | 1-0 |
| England vs Costa Rica | Model Lean | team1_win | team1_win | 1-0 |
| Bolivia vs Algeria | Pass | pass | team2_win | 0-1 |

## Honest Read

Strong Pick is the product-grade call. Model Lean is useful but should be shown with softer language because its historical accuracy is much closer to a directional edge than a locked pick. This solves the v2.7 problem where useful ensemble signals were hidden behind Pass.
