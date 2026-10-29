# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 103.
- Final fixture statuses found: 101.
- Eligible pre-kickoff finals scored: 80.
- Backfill finals not scored: 21.
- Pending/live fixtures: 2.
- Provider errors: 0.
- Public pick accuracy: 69.23%.
- Internal ensemble accuracy: 62.50%.
- Average probability assigned to actual result: 45.32%.
- Average Brier score: 0.5354702499999999.
- Average log loss: 0.8895700000000002.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 6 | 6 | 4 | 25.00% |
| Model Lean | 46 | 45 | 35 | 74.29% |
| Pass | 51 | 50 | 41 |  |

## Pass Reads

- Good pass from draw risk: 15.
- Good pass protecting against wrong internal lean: 8.
- Possible too conservative: 5.
- Neutral pass: 13.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Mexico vs South Africa | 2026-06-11 15:00 | FT | 2-0 | team1_win | Model Lean | team1_win | 77.39% | latest_pre_kickoff | pick_correct |
| South Korea vs Czech Republic | 2026-06-11 22:00 | FT | 2-1 | team1_win | Pass | pass | 42.53% | latest_pre_kickoff | neutral_pass |
| Canada vs Bosnia & Herzegovina | 2026-06-12 15:00 | FT | 1-1 | draw | Model Lean | team1_win | 20.95% | latest_pre_kickoff | pick_wrong |
| USA vs Paraguay | 2026-06-12 21:00 | FT | 4-1 | team1_win | Pass | pass | 35.22% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Qatar vs Switzerland | 2026-06-13 15:00 | FT | 1-1 | draw | Strong Pick | team2_win | 18.89% | latest_pre_kickoff | pick_wrong |
| Brazil vs Morocco | 2026-06-13 18:00 | FT | 1-1 | draw | Pass | pass | 37.27% | latest_pre_kickoff | good_pass_draw_risk |
| Haiti vs Scotland | 2026-06-13 21:00 | FT | 0-1 | team2_win | Pass | pass | 51.12% | latest_pre_kickoff | possible_too_conservative |
| Australia vs Turkey | 2026-06-14 00:00 | FT | 2-0 | team1_win | Pass | pass | 23.18% | fallback_latest_available | backfill_not_scored |
| Germany vs Curaçao | 2026-06-14 13:00 | FT | 7-1 | team1_win | Strong Pick | team1_win | 81.67% | fallback_latest_available | backfill_not_scored |
| Netherlands vs Japan | 2026-06-14 16:00 | FT | 2-2 | draw | Pass | pass | 36.86% | fallback_latest_available | backfill_not_scored |
| Ivory Coast vs Ecuador | 2026-06-14 19:00 | FT | 1-0 | team1_win | Model Lean | team2_win | 11.25% | latest_pre_kickoff | pick_wrong |
| Sweden vs Tunisia | 2026-06-14 22:00 | FT | 5-1 | team1_win | Pass | pass | 37.44% | latest_pre_kickoff | neutral_pass |
| Spain vs Cape Verde | 2026-06-15 12:00 | FT | 0-0 | draw | Strong Pick | team1_win | 10.82% | latest_pre_kickoff | pick_wrong |
| Belgium vs Egypt | 2026-06-15 15:00 | FT | 1-1 | draw | Pass | pass | 35.40% | latest_pre_kickoff | good_pass_draw_risk |
| Saudi Arabia vs Uruguay | 2026-06-15 18:00 | FT | 1-1 | draw | Model Lean | team2_win | 24.59% | latest_pre_kickoff | pick_wrong |
| Iran vs New Zealand | 2026-06-15 21:00 | FT | 2-2 | draw | Pass | pass | 32.02% | latest_pre_kickoff | good_pass_draw_risk |
| France vs Senegal | 2026-06-16 15:00 | FT | 3-1 | team1_win | Model Lean | team1_win | 60.65% | fallback_latest_available | backfill_not_scored |
| Iraq vs Norway | 2026-06-16 18:00 | FT | 1-4 | team2_win | Model Lean | team2_win | 65.82% | fallback_latest_available | backfill_not_scored |
| Argentina vs Algeria | 2026-06-16 21:00 | FT | 3-0 | team1_win | Model Lean | team1_win | 65.76% | latest_pre_kickoff | pick_correct |
| Austria vs Jordan | 2026-06-17 00:00 | FT | 3-1 | team1_win | Pass | pass | 45.66% | fallback_latest_available | backfill_not_scored |
| Portugal vs DR Congo | 2026-06-17 13:00 | FT | 1-1 | draw | Model Lean | team1_win | 26.51% | fallback_latest_available | backfill_not_scored |
| England vs Croatia | 2026-06-17 16:00 | FT | 4-2 | team1_win | Pass | pass | 47.81% | fallback_latest_available | backfill_not_scored |
| Ghana vs Panama | 2026-06-17 19:00 | FT | 1-0 | team1_win | Model Lean | team2_win | 11.38% | fallback_latest_available | backfill_not_scored |
| Uzbekistan vs Colombia | 2026-06-17 22:00 | FT | 1-3 | team2_win | Model Lean | team2_win | 63.73% | fallback_latest_available | backfill_not_scored |
| Czech Republic vs South Africa | 2026-06-18 12:00 | FT | 1-1 | draw | Pass | pass | 35.22% | fallback_latest_available | backfill_not_scored |
| Switzerland vs Bosnia & Herzegovina | 2026-06-18 15:00 | FT | 4-1 | team1_win | Model Lean | team1_win | 73.03% | latest_pre_kickoff | pick_correct |
| Canada vs Qatar | 2026-06-18 18:00 | FT | 6-0 | team1_win | Model Lean | team1_win | 76.89% | latest_pre_kickoff | pick_correct |
| Mexico vs South Korea | 2026-06-18 21:00 | FT | 1-0 | team1_win | Pass | pass | 51.15% | latest_pre_kickoff | possible_too_conservative |
| USA vs Australia | 2026-06-19 15:00 | FT | 2-0 | team1_win | Pass | pass | 37.54% | fallback_latest_available | backfill_not_scored |
| Scotland vs Morocco | 2026-06-19 18:00 | FT | 0-1 | team2_win | Pass | pass | 51.49% | fallback_latest_available | backfill_not_scored |
| Brazil vs Haiti | 2026-06-19 20:30 | FT | 3-0 | team1_win | Pass | pass | 73.47% | fallback_latest_available | backfill_not_scored |
| Turkey vs Paraguay | 2026-06-19 23:00 | FT | 0-1 | team2_win | Pass | pass | 27.66% | fallback_latest_available | backfill_not_scored |
| Netherlands vs Sweden | 2026-06-20 13:00 | FT | 5-1 | team1_win | Model Lean | team1_win | 62.91% | fallback_latest_available | backfill_not_scored |
| Germany vs Ivory Coast | 2026-06-20 16:00 | FT | 2-1 | team1_win | Model Lean | team1_win | 59.10% | fallback_latest_available | backfill_not_scored |
| Ecuador vs Curaçao | 2026-06-20 20:00 | FT | 0-0 | draw | Strong Pick | team1_win | 15.37% | fallback_latest_available | backfill_not_scored |
| Tunisia vs Japan | 2026-06-21 00:00 | FT | 0-4 | team2_win | Model Lean | team2_win | 64.44% | fallback_latest_available | backfill_not_scored |
| Spain vs Saudi Arabia | 2026-06-21 12:00 | FT | 4-0 | team1_win | Strong Pick | team1_win | 83.19% | latest_pre_kickoff | pick_correct |
| Belgium vs Iran | 2026-06-21 15:00 | FT | 0-0 | draw | Pass | pass | 36.09% | latest_pre_kickoff | good_pass_draw_risk |
| Uruguay vs Cape Verde | 2026-06-21 18:00 | FT | 2-2 | draw | Model Lean | team1_win | 22.36% | latest_pre_kickoff | pick_wrong |
| New Zealand vs Egypt | 2026-06-21 21:00 | FT | 1-3 | team2_win | Pass | pass | 46.75% | latest_pre_kickoff | neutral_pass |
| Argentina vs Austria | 2026-06-22 13:00 | FT | 2-0 | team1_win | Model Lean | team1_win | 63.57% | fallback_latest_available | backfill_not_scored |
| France vs Iraq | 2026-06-22 17:00 | FT | 3-0 | team1_win | Model Lean | team1_win | 73.90% | latest_pre_kickoff | pick_correct |
| Norway vs Senegal | 2026-06-22 20:00 | FT | 3-2 | team1_win | Pass | pass | 41.65% | latest_pre_kickoff | neutral_pass |
| Jordan vs Algeria | 2026-06-22 23:00 | FT | 1-2 | team2_win | Pass | pass | 45.32% | latest_pre_kickoff | neutral_pass |
| Portugal vs Uzbekistan | 2026-06-23 13:00 | FT | 5-0 | team1_win | Model Lean | team1_win | 58.27% | latest_pre_kickoff | pick_correct |
| England vs Ghana | 2026-06-23 16:00 | FT | 0-0 | draw | Model Lean | team1_win | 14.21% | latest_pre_kickoff | pick_wrong |
| Panama vs Croatia | 2026-06-23 19:00 | FT | 0-1 | team2_win | Pass | pass | 44.76% | latest_pre_kickoff | neutral_pass |
| Colombia vs DR Congo | 2026-06-23 22:00 | FT | 1-0 | team1_win | Model Lean | team1_win | 67.17% | latest_pre_kickoff | pick_correct |
| Bosnia & Herzegovina vs Qatar | 2026-06-24 15:00 | FT | 3-1 | team1_win | Pass | pass | 41.11% | latest_pre_kickoff | neutral_pass |
| Switzerland vs Canada | 2026-06-24 15:00 | FT | 2-1 | team1_win | Pass | pass | 30.61% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Morocco vs Haiti | 2026-06-24 18:00 | FT | 4-2 | team1_win | Model Lean | team1_win | 67.46% | latest_pre_kickoff | pick_correct |
| Scotland vs Brazil | 2026-06-24 18:00 | FT | 0-3 | team2_win | Model Lean | team2_win | 62.52% | latest_pre_kickoff | pick_correct |
| Czech Republic vs Mexico | 2026-06-24 21:00 | FT | 0-3 | team2_win | Model Lean | team2_win | 63.89% | latest_pre_kickoff | pick_correct |
| South Africa vs South Korea | 2026-06-24 21:00 | FT | 1-0 | team1_win | Model Lean | team2_win | 11.18% | latest_pre_kickoff | pick_wrong |
| Curaçao vs Ivory Coast | 2026-06-25 16:00 | FT | 0-2 | team2_win | Model Lean | team2_win | 60.15% | latest_pre_kickoff | pick_correct |
| Ecuador vs Germany | 2026-06-25 16:00 | FT | 2-1 | team1_win | Model Lean | draw | 28.25% | latest_pre_kickoff | pick_wrong |
| Japan vs Sweden | 2026-06-25 19:00 | FT | 1-1 | draw | Model Lean | team1_win | 30.83% | latest_pre_kickoff | pick_wrong |
| Tunisia vs Netherlands | 2026-06-25 19:00 | FT | 1-3 | team2_win | Model Lean | team2_win | 66.83% | latest_pre_kickoff | pick_correct |
| Paraguay vs Australia | 2026-06-25 22:00 | FT | 0-0 | draw | Pass | pass | 35.73% | latest_pre_kickoff | good_pass_draw_risk |
| Turkey vs USA | 2026-06-25 22:00 | FT | 3-2 | team1_win | Pass | pass | 32.77% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Norway vs France | 2026-06-26 15:00 | FT | 1-4 | team2_win | Pass | pass | 54.17% | latest_pre_kickoff | possible_too_conservative |
| Senegal vs Iraq | 2026-06-26 15:00 | FT | 5-0 | team1_win | Pass | pass | 52.00% | latest_pre_kickoff | possible_too_conservative |
| Cape Verde vs Saudi Arabia | 2026-06-26 20:00 | FT | 0-0 | draw | Pass | pass | 36.82% | latest_pre_kickoff | good_pass_draw_risk |
| Uruguay vs Spain | 2026-06-26 20:00 | FT | 0-1 | team2_win | Model Lean | team2_win | 62.76% | latest_pre_kickoff | pick_correct |
| Egypt vs Iran | 2026-06-26 23:00 | FT | 1-1 | draw | Pass | pass | 34.82% | latest_pre_kickoff | good_pass_draw_risk |
| New Zealand vs Belgium | 2026-06-26 23:00 | FT | 1-5 | team2_win | Model Lean | team2_win | 67.76% | latest_pre_kickoff | pick_correct |
| Croatia vs Ghana | 2026-06-27 17:00 | FT | 2-1 | team1_win | Model Lean | team1_win | 70.15% | latest_pre_kickoff | pick_correct |
| Panama vs England | 2026-06-27 17:00 | FT | 0-2 | team2_win | Model Lean | team2_win | 63.07% | latest_pre_kickoff | pick_correct |
| Colombia vs Portugal | 2026-06-27 19:30 | FT | 0-0 | draw | Model Lean | draw | 38.59% | latest_pre_kickoff | pick_correct |
| DR Congo vs Uzbekistan | 2026-06-27 19:30 | FT | 3-1 | team1_win | Pass | pass | 26.40% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Algeria vs Austria | 2026-06-27 22:00 | FT | 3-3 | draw | Pass | pass | 38.10% | latest_pre_kickoff | good_pass_draw_risk |
| Jordan vs Argentina | 2026-06-27 22:00 | FT | 1-3 | team2_win | Model Lean | team2_win | 74.46% | latest_pre_kickoff | pick_correct |
| South Africa vs Canada | 2026-06-28 15:00 | FT | 0-1 | team2_win | Model Lean | team2_win | 65.68% | fallback_latest_available | backfill_not_scored |
| Brazil vs Japan | 2026-06-29 13:00 | FT | 2-1 | team1_win | Pass | pass | 37.75% | latest_pre_kickoff | neutral_pass |
| Germany vs Paraguay | 2026-06-29 16:30 | PEN | 1-1 | draw | Pass | pass | 34.84% | latest_pre_kickoff | good_pass_draw_risk |
| Netherlands vs Morocco | 2026-06-29 21:00 | PEN | 1-1 | draw | Pass | pass | 37.18% | latest_pre_kickoff | good_pass_draw_risk |
| Ivory Coast vs Norway | 2026-06-30 13:00 | FT | 1-2 | team2_win | Model Lean | team2_win | 56.84% | latest_pre_kickoff | pick_correct |
| France vs Sweden | 2026-06-30 17:00 | FT | 3-0 | team1_win | Model Lean | team1_win | 69.17% | latest_pre_kickoff | pick_correct |
| Mexico vs Ecuador | 2026-06-30 21:00 | FT | 2-0 | team1_win | Pass | pass | 35.39% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| England vs DR Congo | 2026-07-01 12:00 | FT | 2-1 | team1_win | Model Lean | team1_win | 69.08% | latest_pre_kickoff | pick_correct |
| Belgium vs Senegal | 2026-07-01 16:00 | AET | 2-2 | draw | Pass | pass | 35.27% | latest_pre_kickoff | good_pass_draw_risk |
| USA vs Bosnia & Herzegovina | 2026-07-01 20:00 | FT | 2-0 | team1_win | Model Lean | team1_win | 62.15% | latest_pre_kickoff | pick_correct |
| Spain vs Austria | 2026-07-02 15:00 | FT | 3-0 | team1_win | Model Lean | team1_win | 64.33% | latest_pre_kickoff | pick_correct |
| Portugal vs Croatia | 2026-07-02 19:00 | FT | 2-1 | team1_win | Pass | pass | 42.86% | latest_pre_kickoff | neutral_pass |
| Switzerland vs Algeria | 2026-07-02 23:00 | FT | 2-0 | team1_win | Pass | pass | 41.89% | latest_pre_kickoff | neutral_pass |
| Australia vs Egypt | 2026-07-03 14:00 | PEN | 1-1 | draw | Pass | pass | 35.29% | latest_pre_kickoff | good_pass_draw_risk |
| Argentina vs Cape Verde | 2026-07-03 18:00 | AET | 1-1 | draw | Strong Pick | team1_win | 11.89% | latest_pre_kickoff | pick_wrong |
| Colombia vs Ghana | 2026-07-03 21:30 | FT | 1-0 | team1_win | Model Lean | team1_win | 80.01% | latest_pre_kickoff | pick_correct |
| Canada vs Morocco | 2026-07-04 13:00 | NS |  |  | Pass | pass |  | latest_pre_kickoff | pending |
| Paraguay vs France | 2026-07-04 17:00 | NS |  |  | Model Lean | team2_win |  | latest_pre_kickoff | pending |
| Brazil vs Norway | 2026-07-05 16:00 | FT | 1-2 | team2_win | Pass | pass | 21.99% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Mexico vs England | 2026-07-05 20:00 | FT | 2-3 | team2_win | Pass | pass | 34.10% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Portugal vs Spain | 2026-07-06 15:00 | FT | 0-1 | team2_win | Pass | pass | 52.51% | latest_pre_kickoff | possible_too_conservative |
| United States vs Belgium | 2026-07-06 20:00 | FT | 1-4 | team2_win | Pass | pass | 35.71% | latest_pre_kickoff | neutral_pass |
| Argentina vs Egypt | 2026-07-07 12:00 | FT | 3-2 | team1_win | Model Lean | team1_win | 67.09% | latest_pre_kickoff | pick_correct |
| Switzerland vs Colombia | 2026-07-07 16:00 | PEN | 0-0 | draw | Pass | pass | 33.16% | latest_pre_kickoff | good_pass_draw_risk |
| France vs Morocco | 2026-07-09 16:00 | FT | 2-0 | team1_win | Pass | pass | 44.22% | latest_pre_kickoff | neutral_pass |
| Spain vs Belgium | 2026-07-10 15:00 | FT | 2-1 | team1_win | Model Lean | team1_win | 58.69% | latest_pre_kickoff | pick_correct |
| Norway vs England | 2026-07-11 17:00 | AET | 1-1 | draw | Pass | pass | 36.04% | latest_pre_kickoff | good_pass_draw_risk |
| Argentina vs Switzerland | 2026-07-11 21:00 | AET | 1-1 | draw | Pass | pass | 31.66% | latest_pre_kickoff | good_pass_draw_risk |
| France vs Spain | 2026-07-14 15:00 | FT | 0-2 | team2_win | Pass | pass | 39.17% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| England vs Argentina | 2026-07-15 15:00 | FT | 1-2 | team2_win | Pass | pass | 44.01% | latest_pre_kickoff | neutral_pass |
| France vs England | 2026-07-18 17:00 | FT | 4-6 | team2_win | Model Lean | draw | 27.82% | latest_pre_kickoff | pick_wrong |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 1/100.
- Remaining before local stop: 84.
