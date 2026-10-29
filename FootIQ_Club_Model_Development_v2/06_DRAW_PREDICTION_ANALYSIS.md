# 06 Draw prediction analysis

Stacked out-of-sample predictions over the three development folds (36,881 primary matches; actual draw rate 26.11%). Tables: `supporting_tables/draw_*.csv`. Nothing here uses the v1 test or holdout.

## Probability quality (draw probability as a probability)
| Model | mean pD | pD range | draw AUC | binary draw log loss | argmax draws predicted |
|---|---|---|---|---|---|
| v1 Elo mapping | 0.263 | 0.065-0.290 | 0.543 | 0.5705 | 0 |
| v1 LR (25 feat.) | 0.263 | 0.074-0.491 | 0.555 | 0.5697 | 52 |
| v2 LR full | 0.262 | 0.056-0.418 | **0.565** | **0.5684** | 293 |
| v2 HGB full | 0.258 | 0.053-0.479 | 0.564 | 0.5688 | 308 |
| v2 RF full | 0.262 | 0.052-0.363 | 0.562 | 0.5689 | 24 |

* Draw probabilities are **well calibrated** for v1 Elo and v2 LR (decile table `draw_calibration_deciles.csv`: predicted vs observed within about 0.01 in every decile for v2 LR). The v1 problem was not mis-calibration; it was that the model could not discriminate draws and its draw probability cannot exceed ~0.29, so a draw is never the argmax class.
* Draw likelihood falls with strength gap (`draw_vs_elo_diff.csv`): actual draw rate 29.4% when |Elo2 diff| <= 25, 22.5% at 150-200, 14.5% above 300. The v1 mapping overestimates draws for large gaps (0.169 predicted vs 0.145 actual above 300); v2 LR is somewhat closer but still over by 0.024.
* Draw rates differ by competition from 21.6% to 31.7% (`draw_rate_by_competition.csv`), which v2's league draw-rate features partly capture.
* Discrimination of draws remains weak (AUC 0.565): draws are mostly unpredictable from these inputs. The v2 improvement (+0.022 AUC over v1 Elo) is real but small.

## Decision policy (separate from probability estimation)
Hard class labels are a policy applied on top of probabilities. Policy tested: multiply the draw probability by w and take argmax; w tuned on folds 1-2 (maximising macro-F1), evaluated on fold 3 only (tuned w=1.45 for all three models):

| Model | Rule | Accuracy | Macro-F1 | Draws predicted | Draw precision | Draw recall | Draw F1 |
|---|---|---|---|---|---|---|---|
| v1 Elo | argmax | 0.4965 | 0.361 | 0 | - | 0.000 | 0.000 |
| v1 Elo | w=1.45 | 0.4633 | 0.421 | 5,025 | 0.281 | 0.322 | 0.300 |
| v2 LR | argmax | 0.5023 | 0.373 | 106 | 0.321 | 0.008 | 0.015 |
| v2 LR | w=1.45 | 0.4844 | 0.442 | 3,922 | 0.309 | 0.276 | 0.291 |
| v2 HGB | w=1.45 | 0.4813 | 0.441 | 3,888 | 0.306 | 0.271 | 0.287 |

Interpretation: a draw-weighted rule buys macro-F1 (+0.07) by giving up ~1.8pp accuracy; draw precision (0.31) is only a little above the base rate (0.26). Neither choice changes log loss. The rule should be chosen by product need (do users need a hard label? an F1-oriented one costs accuracy) and is **not** part of the model: the deliverable is the calibrated probability triple.
Draw-specific loss weighting inside the model was not used: the LR/HGB probabilities are already calibrated, and class weighting would distort them; the decision-weight route keeps probabilities untouched.
