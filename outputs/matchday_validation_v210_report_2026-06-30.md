# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 3.
- Final fixture statuses found: 3.
- Eligible pre-kickoff finals scored: 3.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 100.00%.
- Internal ensemble accuracy: 66.67%.
- Average probability assigned to actual result: 53.80%.
- Average Brier score: 0.36088666666666674.
- Average log loss: 0.6574333333333333.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 2 | 2 | 2 | 100.00% |
| Pass | 1 | 1 | 1 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 1.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Ivory Coast vs Norway | 2026-06-30 13:00 | FT | 1-2 | team2_win | Model Lean | team2_win | 56.84% | latest_pre_kickoff | pick_correct |
| France vs Sweden | 2026-06-30 17:00 | FT | 3-0 | team1_win | Model Lean | team1_win | 69.17% | latest_pre_kickoff | pick_correct |
| Mexico vs Ecuador | 2026-06-30 21:00 | FT | 2-0 | team1_win | Pass | pass | 35.39% | latest_pre_kickoff | good_pass_protected_wrong_internal |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 7/100.
- Remaining before local stop: 78.
