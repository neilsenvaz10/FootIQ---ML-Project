# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 1.
- Final fixture statuses found: 1.
- Eligible pre-kickoff finals scored: 1.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 0.00%.
- Internal ensemble accuracy: 0.00%.
- Average probability assigned to actual result: 27.82%.
- Average Brier score: 0.78368.
- Average log loss: 1.27945.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 1 | 1 | 1 | 0.00% |
| Pass | 0 | 0 | 0 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| France vs England | 2026-07-18 17:00 | FT | 4-6 | team2_win | Model Lean | draw | 27.82% | latest_pre_kickoff | pick_wrong |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 1/100.
- Remaining before local stop: 84.
