# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 4.
- Final fixture statuses found: 4.
- Eligible pre-kickoff finals scored: 4.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 66.67%.
- Internal ensemble accuracy: 75.00%.
- Average probability assigned to actual result: 46.10%.
- Average Brier score: 0.5813.
- Average log loss: 0.923205.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 3 | 3 | 3 | 66.67% |
| Pass | 1 | 1 | 1 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 1.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Portugal vs Uzbekistan | 2026-06-23 13:00 | FT | 5-0 | team1_win | Model Lean | team1_win | 58.27% | latest_pre_kickoff | pick_correct |
| England vs Ghana | 2026-06-23 16:00 | FT | 0-0 | draw | Model Lean | team1_win | 14.21% | latest_pre_kickoff | pick_wrong |
| Panama vs Croatia | 2026-06-23 19:00 | FT | 0-1 | team2_win | Pass | pass | 44.76% | latest_pre_kickoff | neutral_pass |
| Colombia vs DR Congo | 2026-06-23 22:00 | FT | 1-0 | team1_win | Model Lean | team1_win | 67.17% | latest_pre_kickoff | pick_correct |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 11/100.
- Remaining before local stop: 74.
