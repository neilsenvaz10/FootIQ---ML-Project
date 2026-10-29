# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 1.
- Final fixture statuses found: 1.
- Eligible pre-kickoff finals scored: 1.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: not enough finals yet.
- Internal ensemble accuracy: 100.00%.
- Average probability assigned to actual result: 44.01%.
- Average Brier score: 0.48241.
- Average log loss: 0.82073.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 0 | 0 | 0 |  |
| Pass | 1 | 1 | 1 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 1.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| England vs Argentina | 2026-07-15 15:00 | FT | 1-2 | team2_win | Pass | pass | 44.01% | latest_pre_kickoff | neutral_pass |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 1/100.
- Remaining before local stop: 84.
