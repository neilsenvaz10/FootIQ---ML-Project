# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 2.
- Final fixture statuses found: 2.
- Eligible pre-kickoff finals scored: 2.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: not enough finals yet.
- Internal ensemble accuracy: 100.00%.
- Average probability assigned to actual result: 44.11%.
- Average Brier score: 0.49028.
- Average log loss: 0.83687.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 0 | 0 | 0 |  |
| Pass | 2 | 2 | 2 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 1.
- Neutral pass: 1.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Portugal vs Spain | 2026-07-06 15:00 | FT | 0-1 | team2_win | Pass | pass | 52.51% | latest_pre_kickoff | possible_too_conservative |
| United States vs Belgium | 2026-07-06 20:00 | FT | 1-4 | team2_win | Pass | pass | 35.71% | latest_pre_kickoff | neutral_pass |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 10/100.
- Remaining before local stop: 75.
