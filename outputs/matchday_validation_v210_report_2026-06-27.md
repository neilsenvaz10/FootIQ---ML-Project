# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 6.
- Final fixture statuses found: 6.
- Eligible pre-kickoff finals scored: 6.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 100.00%.
- Internal ensemble accuracy: 83.33%.
- Average probability assigned to actual result: 51.80%.
- Average Brier score: 0.40551.
- Average log loss: 0.7264566666666666.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 4 | 4 | 4 | 100.00% |
| Pass | 2 | 2 | 2 |  |

## Pass Reads

- Good pass from draw risk: 1.
- Good pass protecting against wrong internal lean: 1.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Croatia vs Ghana | 2026-06-27 17:00 | FT | 2-1 | team1_win | Model Lean | team1_win | 70.15% | latest_pre_kickoff | pick_correct |
| Panama vs England | 2026-06-27 17:00 | FT | 0-2 | team2_win | Model Lean | team2_win | 63.07% | latest_pre_kickoff | pick_correct |
| Colombia vs Portugal | 2026-06-27 19:30 | FT | 0-0 | draw | Model Lean | draw | 38.59% | latest_pre_kickoff | pick_correct |
| DR Congo vs Uzbekistan | 2026-06-27 19:30 | FT | 3-1 | team1_win | Pass | pass | 26.40% | latest_pre_kickoff | good_pass_protected_wrong_internal |
| Algeria vs Austria | 2026-06-27 22:00 | FT | 3-3 | draw | Pass | pass | 38.10% | latest_pre_kickoff | good_pass_draw_risk |
| Jordan vs Argentina | 2026-06-27 22:00 | FT | 1-3 | team2_win | Model Lean | team2_win | 74.46% | latest_pre_kickoff | pick_correct |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 12/100.
- Remaining before local stop: 73.
