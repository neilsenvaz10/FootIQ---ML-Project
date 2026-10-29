# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 2.
- Final fixture statuses found: 2.
- Eligible pre-kickoff finals scored: 2.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 100.00%.
- Internal ensemble accuracy: 50.00%.
- Average probability assigned to actual result: 50.13%.
- Average Brier score: 0.43348000000000003.
- Average log loss: 0.75147.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
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
| Argentina vs Egypt | 2026-07-07 12:00 | FT | 3-2 | team1_win | Model Lean | team1_win | 67.09% | latest_pre_kickoff | pick_correct |
| Switzerland vs Colombia | 2026-07-07 16:00 | PEN | 0-0 | draw | Pass | pass | 33.16% | latest_pre_kickoff | good_pass_draw_risk |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 2/100.
- Remaining before local stop: 83.
