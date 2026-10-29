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
- Internal ensemble accuracy: 0.00%.
- Average probability assigned to actual result: 28.04%.
- Average Brier score: 0.785425.
- Average log loss: 1.29536.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 0 | 0 | 0 |  |
| Pass | 2 | 2 | 2 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 2.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Brazil vs Norway | 2026-07-05 16:00 | FT | 1-2 | team2_win | Pass | pass | 21.99% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Mexico vs England | 2026-07-05 20:00 | FT | 2-3 | team2_win | Pass | pass | 34.10% | latest_pre_kickoff | good_pass_protected_wrong_internal |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 6/100.
- Remaining before local stop: 79.
