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
- Average probability assigned to actual result: 33.85%.
- Average Brier score: 0.722625.
- Average log loss: 1.08542.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 0 | 0 | 0 |  |
| Pass | 2 | 2 | 2 |  |

## Pass Reads

- Good pass from draw risk: 2.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Norway vs England | 2026-07-11 17:00 | AET | 1-1 | draw | Pass | pass | 36.04% | latest_pre_kickoff | good_pass_draw_risk |
| Argentina vs Switzerland | 2026-07-11 21:00 | AET | 1-1 | draw | Pass | pass | 31.66% | latest_pre_kickoff | good_pass_draw_risk |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 0/100.
- Remaining before local stop: 85.
