# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 1.
- Final fixture statuses found: 1.
- Eligible pre-kickoff finals scored: 0.
- Backfill finals not scored: 1.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: not enough finals yet.
- Internal ensemble accuracy: not enough finals yet.
- Average probability assigned to actual result: not enough finals yet.
- Average Brier score: not enough finals yet.
- Average log loss: not enough finals yet.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 1 | 1 | 0 |  |
| Pass | 0 | 0 | 0 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| South Africa vs Canada | 2026-06-28 15:00 | FT | 0-1 | team2_win | Model Lean | team2_win | 65.68% | fallback_latest_available | backfill_not_scored |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 23/100.
- Remaining before local stop: 62.
