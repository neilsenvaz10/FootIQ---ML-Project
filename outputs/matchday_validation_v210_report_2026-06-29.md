# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 3.
- Final fixture statuses found: 3.
- Eligible pre-kickoff finals scored: 3.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: not enough finals yet.
- Internal ensemble accuracy: 66.67%.
- Average probability assigned to actual result: 36.59%.
- Average Brier score: 0.61599.
- Average log loss: 1.0059933333333333.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 0 | 0 | 0 |  |
| Pass | 3 | 3 | 3 |  |

## Pass Reads

- Good pass from draw risk: 2.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 1.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Brazil vs Japan | 2026-06-29 13:00 | FT | 2-1 | team1_win | Pass | pass | 37.75% | latest_pre_kickoff | neutral_pass |
| Germany vs Paraguay | 2026-06-29 16:30 | PEN | 1-1 | draw | Pass | pass | 34.84% | latest_pre_kickoff | good_pass_draw_risk |
| Netherlands vs Morocco | 2026-06-29 21:00 | PEN | 1-1 | draw | Pass | pass | 37.18% | latest_pre_kickoff | good_pass_draw_risk |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 7/100.
- Remaining before local stop: 78.
