# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 3.
- Final fixture statuses found: 3.
- Eligible pre-kickoff finals scored: 3.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 50.00%.
- Internal ensemble accuracy: 33.33%.
- Average probability assigned to actual result: 42.40%.
- Average Brier score: 0.73177.
- Average log loss: 1.1312733333333334.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 1 | 1 | 1 | 0.00% |
| Model Lean | 1 | 1 | 1 | 100.00% |
| Pass | 1 | 1 | 1 |  |

## Pass Reads

- Good pass from draw risk: 1.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Australia vs Egypt | 2026-07-03 14:00 | PEN | 1-1 | draw | Pass | pass | 35.29% | latest_pre_kickoff | good_pass_draw_risk |
| Argentina vs Cape Verde | 2026-07-03 18:00 | AET | 1-1 | draw | Strong Pick | team1_win | 11.89% | latest_pre_kickoff | pick_wrong |
| Colombia vs Ghana | 2026-07-03 21:30 | FT | 1-0 | team1_win | Model Lean | team1_win | 80.01% | latest_pre_kickoff | pick_correct |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 3/100.
- Remaining before local stop: 82.
