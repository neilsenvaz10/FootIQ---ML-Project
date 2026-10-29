# Live Predictions v2.7

V2.7 plugs the calibrated v2.6 ensemble into the live v2.5 tables. The old v2.5 hand-weighted prediction remains visible only as a comparison layer.

## What Changed

- Final model artifacts are saved under `data/model_artifacts/v27/`.
- Live fixtures are converted into the same feature schema used by the v2.6 bakeoff.
- Public picks use the v2.6 consensus gate: ensemble and logistic regression must agree on the same non-pass result.
- The Poisson-style layer stays useful for tournament path simulation, but it is no longer the primary live 1X2 decision engine.

## Artifact

- Training rows: 25,235.
- Training date range: 2000-01-04 to 2026-06-02.
- Ensemble weights: elo 30.0%, logistic 20.0%, gradient boosting 50.0%, Poisson 0.0%.

## Live Run Summary

- Fixtures scored: 8.
- Public non-pass picks: 0 (0.0%).
- V2.5 vs v2.7 changed calls: 8.
- Rows with missing Elo/form features: 0.
- Scored final non-pass picks: none yet.

## V2.7 Public Picks

| Fixture | V2.7 public call | Internal lean | Team 1 | Draw | Team 2 | Data quality |
|---|---|---|---:|---:|---:|---:|
| Portugal vs Chile | Pass | team1_win | 64.21% | 28.77% | 7.01% | 43 |
| Germany vs USA | Pass | draw | 35.81% | 38.65% | 25.54% | 43 |
| Bolivia vs Scotland | Pass | team2_win | 20.21% | 35.19% | 44.60% | 43 |
| Brazil vs Egypt | Pass | team1_win | 60.04% | 30.84% | 9.12% | 43 |
| Argentina vs Honduras | Pass | team1_win | 76.36% | 19.79% | 3.85% | 43 |
| Morocco vs Norway | Pass | draw | 33.74% | 39.04% | 27.21% | 43 |
| Colombia vs Jordan | Pass | team1_win | 62.37% | 29.25% | 8.38% | 43 |
| Argentina vs Iceland | Pass | team1_win | 80.97% | 15.99% | 3.04% | 78 |

## Comparison vs v2.5

| Fixture | v2.5 call | v2.7 public call | v2.7 internal lean |
|---|---|---|---|
| Portugal vs Chile | No strong edge | Pass | team1_win |
| Germany vs USA | No strong edge | Pass | draw |
| Bolivia vs Scotland | Draw lean | Pass | team2_win |
| Brazil vs Egypt | Brazil avoid defeat | Pass | team1_win |
| Argentina vs Honduras | Argentina win lean | Pass | team1_win |
| Morocco vs Norway | Draw risk / no strong edge | Pass | draw |
| Colombia vs Jordan | Colombia win lean | Pass | team1_win |
| Argentina vs Iceland | Argentina win lean | Pass | team1_win |

## Honest Caveat

This is a production-integration step, not a new accuracy claim. The historical accuracy claim still comes from the v2.6 time-safe test; v2.7 retrains final artifacts on all available historical data after the architecture was selected.
