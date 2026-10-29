# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 6.
- Final fixture statuses found: 6.
- Eligible pre-kickoff finals scored: 6.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 75.00%.
- Internal ensemble accuracy: 66.67%.
- Average probability assigned to actual result: 46.13%.
- Average Brier score: 0.5166416666666667.
- Average log loss: 0.9291616666666668.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 4 | 4 | 4 | 75.00% |
| Pass | 2 | 2 | 2 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 1.
- Possible too conservative: 0.
- Neutral pass: 1.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Bosnia & Herzegovina vs Qatar | 2026-06-24 15:00 | FT | 3-1 | team1_win | Pass | pass | 41.11% | latest_pre_kickoff | neutral_pass |
| Switzerland vs Canada | 2026-06-24 15:00 | FT | 2-1 | team1_win | Pass | pass | 30.61% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Morocco vs Haiti | 2026-06-24 18:00 | FT | 4-2 | team1_win | Model Lean | team1_win | 67.46% | latest_pre_kickoff | pick_correct |
| Scotland vs Brazil | 2026-06-24 18:00 | FT | 0-3 | team2_win | Model Lean | team2_win | 62.52% | latest_pre_kickoff | pick_correct |
| Czech Republic vs Mexico | 2026-06-24 21:00 | FT | 0-3 | team2_win | Model Lean | team2_win | 63.89% | latest_pre_kickoff | pick_correct |
| South Africa vs South Korea | 2026-06-24 21:00 | FT | 1-0 | team1_win | Model Lean | team2_win | 11.18% | latest_pre_kickoff | pick_wrong |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 13/100.
- Remaining before local stop: 72.
