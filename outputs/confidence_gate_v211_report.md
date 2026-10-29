# Confidence Gate v2.11

Frozen for shadow evaluation: 2026-06-22T16:22:42-04:00

V2.11 is a challenger publishing layer. It does not retrain or replace the v2.7 probability ensemble.

## What Changed

- Extreme probabilities are softened with temperature scaling and a small group-stage draw uplift.
- Strong Pick now requires calibrated separation, low draw risk, xG separation, high data quality, and confirmed live lineups.
- Model Lean must survive an explicit draw-risk screen.
- V2.8 remains the baseline while v2.11 runs in shadow mode.

## Historical Holdout Comparison

| Version | Matches | Public picks | Coverage | Accuracy | Strong accuracy | Lean accuracy |
|---|---:|---:|---:|---:|---:|---:|
| v2.8 | 3491 | 2130 | 61.01% | 71.78% | 76.82% | 55.31% |
| v2.11 | 3491 | 1553 | 44.49% | 78.04% | 90.00% | 69.20% |

## Current World Cup Diagnostic

These completed matches informed v2.11, so this is an in-sample diagnostic rather than production proof.

| Version | Genuine finals | Public picks | Coverage | Accuracy | Strong accuracy | Lean accuracy |
|---|---:|---:|---:|---:|---:|---:|
| v2.8 | 64 | 34 | 53.12% | 70.59% | 33.33% | 74.19% |
| v2.11 | 64 | 11 | 17.19% | 81.82% | 100.00% | 80.00% |

## Frozen Shadow Results

Only fixtures that kicked off after the original v2.11 freeze enter this unbiased challenger comparison.

| Version | Frozen finals | Public picks | Coverage | Accuracy |
|---|---:|---:|---:|---:|
| v2.8 | 43 | 23 | 53.49% | 82.61% |
| v2.11 | 43 | 6 | 13.95% | 83.33% |

| Match | Actual | v2.8 | v2.11 |
|---|---|---|---|
| France vs Iraq | 3-0 (team1_win) | Model Lean: team1_win | Model Lean: team1_win |
| Norway vs Senegal | 3-2 (team1_win) | Pass: pass | Pass: pass |
| Jordan vs Algeria | 1-2 (team2_win) | Pass: pass | Pass: pass |
| Portugal vs Uzbekistan | 5-0 (team1_win) | Model Lean: team1_win | Pass: pass |
| England vs Ghana | 0-0 (draw) | Model Lean: team1_win | Model Lean: team1_win |
| Panama vs Croatia | 0-1 (team2_win) | Pass: pass | Pass: pass |
| Colombia vs DR Congo | 1-0 (team1_win) | Model Lean: team1_win | Pass: pass |
| Bosnia & Herzegovina vs Qatar | 3-1 (team1_win) | Pass: pass | Pass: pass |
| Switzerland vs Canada | 2-1 (team1_win) | Pass: pass | Pass: pass |
| Morocco vs Haiti | 4-2 (team1_win) | Model Lean: team1_win | Pass: pass |
| Scotland vs Brazil | 0-3 (team2_win) | Model Lean: team2_win | Pass: pass |
| Czech Republic vs Mexico | 0-3 (team2_win) | Model Lean: team2_win | Pass: pass |
| South Africa vs South Korea | 1-0 (team1_win) | Model Lean: team2_win | Pass: pass |
| Curaçao vs Ivory Coast | 0-2 (team2_win) | Model Lean: team2_win | Pass: pass |
| Ecuador vs Germany | 2-1 (team1_win) | Model Lean: draw | Pass: pass |
| Japan vs Sweden | 1-1 (draw) | Model Lean: team1_win | Pass: pass |
| Tunisia vs Netherlands | 1-3 (team2_win) | Model Lean: team2_win | Model Lean: team2_win |
| Paraguay vs Australia | 0-0 (draw) | Pass: pass | Pass: pass |
| Turkey vs USA | 3-2 (team1_win) | Pass: pass | Pass: pass |
| Norway vs France | 1-4 (team2_win) | Pass: pass | Pass: pass |
| Senegal vs Iraq | 5-0 (team1_win) | Pass: pass | Pass: pass |
| Cape Verde vs Saudi Arabia | 0-0 (draw) | Pass: pass | Pass: pass |
| Uruguay vs Spain | 0-1 (team2_win) | Model Lean: team2_win | Pass: pass |
| Egypt vs Iran | 1-1 (draw) | Pass: pass | Pass: pass |
| New Zealand vs Belgium | 1-5 (team2_win) | Model Lean: team2_win | Model Lean: team2_win |
| Croatia vs Ghana | 2-1 (team1_win) | Model Lean: team1_win | Pass: pass |
| Panama vs England | 0-2 (team2_win) | Model Lean: team2_win | Pass: pass |
| Colombia vs Portugal | 0-0 (draw) | Model Lean: draw | Pass: pass |
| DR Congo vs Uzbekistan | 3-1 (team1_win) | Pass: pass | Pass: pass |
| Algeria vs Austria | 3-3 (draw) | Pass: pass | Pass: pass |
| Jordan vs Argentina | 1-3 (team2_win) | Model Lean: team2_win | Model Lean: team2_win |
| Brazil vs Japan | 2-1 (team1_win) | Pass: pass | Pass: pass |
| Germany vs Paraguay | 1-1 (draw) | Pass: pass | Pass: pass |
| Netherlands vs Morocco | 1-1 (draw) | Pass: pass | Pass: pass |
| Ivory Coast vs Norway | 1-2 (team2_win) | Model Lean: team2_win | Pass: pass |
| France vs Sweden | 3-0 (team1_win) | Model Lean: team1_win | Model Lean: team1_win |
| Mexico vs Ecuador | 2-0 (team1_win) | Pass: pass | Pass: pass |
| England vs DR Congo | 2-1 (team1_win) | Model Lean: team1_win | Pass: pass |
| Belgium vs Senegal | 2-2 (draw) | Pass: pass | Pass: pass |
| USA vs Bosnia & Herzegovina | 2-0 (team1_win) | Model Lean: team1_win | Pass: pass |
| Spain vs Austria | 3-0 (team1_win) | Model Lean: team1_win | Pass: pass |
| Portugal vs Croatia | 2-1 (team1_win) | Pass: pass | Pass: pass |
| Switzerland vs Algeria | 2-0 (team1_win) | Pass: pass | Pass: pass |

## Upcoming Shadow Slate

| Match | Kickoff ET | v2.8 | v2.11 | Calibrated 1/X/2 | Reason |
|---|---:|---|---|---|---|
| Australia vs Egypt | 2026-07-03 14:00 | Pass: pass | Pass: pass | 37.6/37.3/25.1 | Draw Watch: calibrated draw risk is high relative to the expected-goal separation. |
| Argentina vs Cape Verde | 2026-07-03 18:00 | Strong Pick: team1_win | Pass: pass | 78.9/15.8/5.3 | Consensus favorite is not published before confirmed-lineup verification. |
| Colombia vs Ghana | 2026-07-03 21:30 | Model Lean: team1_win | Model Lean: team1_win | 74.4/20.4/5.2 | Directional edge survives probability calibration and draw-risk screening. |
| Canada vs Morocco | 2026-07-04 13:00 | Pass: pass | Pass: pass | 21.3/37.5/41.2 | Draw Watch: calibrated draw risk is high relative to the expected-goal separation. |
| Paraguay vs France | 2026-07-04 17:00 | Model Lean: team2_win | Pass: pass | 12.4/30.6/57.0 | Draw Watch: calibrated draw risk is high relative to the expected-goal separation. |

## Diagnostic Tier Changes

- Completed genuine/backfill rows with a changed tier: 35.
- Future fixtures frozen for unbiased v2.11 shadow evaluation: 5.

## Production Rule

Do not promote v2.11 from shadow mode based on the improved diagnostic score. Its rules were designed after observing the current World Cup sample. Promotion requires future, untouched results and comparison against v2.8 on the same fixtures.
