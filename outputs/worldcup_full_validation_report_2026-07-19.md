# World Cup Model Full Validation - Pre-Final

Generated: 2026-10-20T15:34:34+05:30

The final is excluded by request. Group matches are graded on the best 90-minute 1/X/2 read. Knockout matches are graded only on the full-match qualifier or placement winner after extra time and penalties.

## Executive Answer

| Scope | Correct | Scored | Accuracy | 95% Wilson interval |
|---|---:|---:|---:|---:|
| Entire pre-final product target | 59 | 82 | 71.95% | 61.41% to 80.52% |
| Group-stage best 90-minute read | 34 | 52 | 65.38% | 51.80% to 76.85% |
| Group-stage published calls only | 19 | 29 | 65.52% | 47.34% to 80.06% |
| Knockout full-match advancement | 25 | 30 | 83.33% | 66.44% to 92.66% |

Bottom line: the honest combined record is **59/82 (71.95%)**. This is a hybrid product metric, not a claim that the model picked 59 regulation winners. The target changes from 90-minute result in groups to full-match advancement in knockouts.

## Coverage And Integrity

- Completed fixtures before the final: 103 (72 group matches and 31 knockout/placement matches).
- Genuine pre-kickoff predictions scored: 82/103 (79.61%).
- Excluded: 20 group fixtures whose local rows were collected after kickoff, plus South Africa-Canada in the Round of 32, which had no archived pre-kickoff advancement call.
- Excluded rows remain in the fixture audit for transparency but do not enter any accuracy denominator.
- The final is not included anywhere in this report.

### Literal 72/72 Group Baseline

The static v2.3 group sheet was frozen on 4 June, before the tournament, and covered every group fixture. It scored **48/72 (66.67%)**. This is useful as a full-coverage baseline, but it is not mixed into the primary live-model total because it predates the v2.6-v2.9 ensemble, weather, lineup, and confidence-gate pipeline.

## Group Stage

Best-read accuracy across every honestly frozen group prediction: **34/52 (65.38%)**.

### Confidence Gate

| Gate attached to fixture | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Strong Pick | 1 | 3 | 33.33% |
| Model Lean | 18 | 26 | 69.23% |
| Pass | 15 | 23 | 65.22% |

The published slate was Strong Pick plus Model Lean: **19/29 (65.52%)**. Pass rows were not public picks; their internal reads are shown only to test whether the gate separated clean situations from uncertain ones.

### By Each Team's Group Match Number

| Team match number | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| 1 | 6 | 14 | 42.86% |
| 2 | 11 | 14 | 78.57% |
| 3 | 17 | 24 | 70.83% |

The first-match number is weak and incomplete: only 14/24 opening fixtures had valid pre-kickoff snapshots. All 24 final group fixtures were captured, which is why the later sample is operationally cleaner.

### By Actual Outcome

| Actual regulation outcome | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Team 1 win | 16 | 23 | 69.57% |
| Draw | 5 | 16 | 31.25% |
| Team 2 win | 13 | 13 | 100.00% |

Draws were the main failure mode. The model called 9 draws and got 5 right (precision 55.56%), while 16 matches actually drew and only 5 were caught (recall 31.25%).

### Probability Quality

- Mean probability assigned to the actual 1/X/2 result: 45.88%.
- Three-class Brier score: 0.5388 (lower is better; uniform probabilities score 0.6667).
- Log loss: 0.8925 (lower is better; uniform probabilities score 1.0986).

## Knockout Stage

Full-match advancement accuracy: **25/30 (83.33%)**. This is the model's clearest positive result, but 30 calls still produce a wide confidence interval.

### By Round

| Round | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Round of 32 | 14 | 15 | 93.33% |
| Round of 16 | 6 | 8 | 75.00% |
| Quarter-final | 4 | 4 | 100.00% |
| Semi-final | 1 | 2 | 50.00% |
| Third place | 0 | 1 | 0.00% |

### By Attached Regulation Gate

| Gate attached to fixture | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Strong Pick | 1 | 1 | 100.00% |
| Model Lean | 9 | 10 | 90.00% |
| Pass | 15 | 19 | 78.95% |

The gate was designed for 90-minute publishing, not for advancement. This table is diagnostic: a Pass can still have a useful full-match qualifier because extra time and penalties remove the draw outcome.

### By Advancement Probability

| Predicted qualifier probability | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| 50-55% | 4 | 5 | 80.00% |
| 55-65% | 12 | 15 | 80.00% |
| 65%+ | 9 | 10 | 90.00% |

- Mean probability assigned to the actual qualifier: 60.30%.
- Binary two-class Brier score: 0.3474 (a flat 50/50 forecast scores 0.5000).
- Log loss: 0.5295 (a flat 50/50 forecast scores 0.6931).

### Advancement Misses

| Match | Round | Model qualifier | Model probability | Actual qualifier |
|---|---|---|---:|---|
| Germany v Paraguay | Round of 32 | Germany | 66.92% | Paraguay |
| Brazil v Norway | Round of 16 | Brazil | 60.34% | Norway |
| Switzerland v Colombia | Round of 16 | Colombia | 59.18% | Switzerland |
| France v Spain | Semi-final | France | 52.63% | Spain |
| France v England | Third place | France | 58.83% | England |

## Combined Gate View

| Gate attached to fixture | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Strong Pick | 2 | 4 | 50.00% |
| Model Lean | 27 | 36 | 75.00% |
| Pass | 30 | 42 | 71.43% |

This combines different targets, so it is useful for product monitoring but not for scientific comparison between gates.

## France-England Postmortem

- Official scorecard: wrong. The 90-minute read was Draw, the full-match bronze pick was France, and England won 6-4 in regulation.
- The final pre-kickoff regulation distribution was France 32.80%, Draw 39.38%, England 27.82%. The lineup-adjusted full-match distribution was France 58.83%, England 41.17%.
- That means England winning was an upset, not an impossible outcome. The model still has to take the loss; missed chances cannot be used to relabel it as correct.
- The user-reported Olise big chances are relevant to process quality, but they need event-level xG or post-shot xG before they can support a formal claim that the read was unlucky rather than structurally wrong.
- The larger warning is total-goal calibration. The base model expected about 2.12 total goals (1.128 plus 0.994), while the match produced 10. The third-place context, rotated defenders, open tactics, and game-state feedback created far more variance than the model allowed.

## What This World Cup Says About The Model

1. **Advancement is the strongest product.** The knockout engine went 25/30 and handled extra time/penalty paths much better than regulation outcome calls alone.
2. **Model Lean is the most useful current gate.** It returned 18/26 in groups and 9/10 on attached knockout advancement calls. Strong Pick was only 1/3 in the group stage and is not validated by that tiny sample.
3. **Draw calibration needs work.** The model caught only 5 of 16 genuine group-stage draws. This is the clearest repeatable technical weakness.
4. **Pass is sensible but not sharply separated.** Pass-row internal group reads were 15/23 versus 18/26 for Model Lean. The gate reduced overstatement, but it has not yet created a huge accuracy gap.
5. **Late tournament probabilities were directionally useful but volatile.** The model was perfect in the quarterfinals, split the semifinals, and missed the third-place game. That is promising, not proof of an 83% true future hit rate.
6. **Operational capture improved during the tournament.** The model stored every third group fixture before kickoff, but missed the honest freeze on 20 earlier group matches. A production model cannot leave that coverage gap.

## Business Verdict

This is a credible research-stage model with a promising knockout-advancement product. It is not yet ready for a commercial accuracy claim. The combined 71.95% is real under the stated scoring rule, but it covers 82 of 103 pre-final fixtures, mixes two targets, has no closing-market benchmark, and has wide statistical uncertainty.

The defensible external wording is: **'On 82 frozen pre-kickoff World Cup calls, the model recorded 65.38% group-stage 90-minute accuracy and 83.33% knockout advancement accuracy; the final was excluded.'**

## Recommended Changes

1. Freeze an automated T-75 prediction for every fixture, then a separate T-10 lineup update. Never overwrite either snapshot.
2. Rebuild the draw layer as its own calibrated classifier and test it against low-xG, low-margin, and heat/tempo regimes.
3. Suspend the Strong Pick label or raise its evidence requirement until it has at least 100 genuinely frozen calls with calibration evidence.
4. Add a third-place/open-knockout variance regime so rotation and low defensive incentives affect total-goal variance, not just average team strength.
5. Add event xG, big-chance, shot-location, and post-shot xG data for process reviews. That is how Olise-type misses can be measured rather than argued from memory.
6. Benchmark every call against Elo-only and no-vig closing market probabilities. Accuracy without those baselines does not establish a sellable edge.

## Audit Files

- Fixture-level audit: `data\processed\worldcup_full_validation_fixture_audit_2026-07-19.csv`
- Summary metrics: `data\processed\worldcup_full_validation_summary_2026-07-19.csv`
- Frozen knockout call ledger: `data\processed\worldcup_knockout_advancement_predictions_frozen.csv`
- Group validation source: `data\processed\matchday_validation_v210.csv`
- Static 72-game baseline: `data\processed\model_v23_group_match_predictions.csv`
- Verified knockout results: `data\processed\worldcup_2026_knockout_results_verified.csv`
- Official result cross-check: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums
