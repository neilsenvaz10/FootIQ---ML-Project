# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 6.
- Final fixture statuses found: 6.
- Eligible pre-kickoff finals scored: 6.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 50.00%.
- Internal ensemble accuracy: 50.00%.
- Average probability assigned to actual result: 42.43%.
- Average Brier score: 0.5570616666666667.
- Average log loss: 0.916135.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 4 | 4 | 4 | 50.00% |
| Pass | 2 | 2 | 2 |  |

## Pass Reads

- Good pass from draw risk: 1.
- Good pass protecting against wrong internal lean: 1.
- Possible too conservative: 0.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Curaçao vs Ivory Coast | 2026-06-25 16:00 | FT | 0-2 | team2_win | Model Lean | team2_win | 60.15% | latest_pre_kickoff | pick_correct |
| Ecuador vs Germany | 2026-06-25 16:00 | FT | 2-1 | team1_win | Model Lean | draw | 28.25% | latest_pre_kickoff | pick_wrong |
| Japan vs Sweden | 2026-06-25 19:00 | FT | 1-1 | draw | Model Lean | team1_win | 30.83% | latest_pre_kickoff | pick_wrong |
| Tunisia vs Netherlands | 2026-06-25 19:00 | FT | 1-3 | team2_win | Model Lean | team2_win | 66.83% | latest_pre_kickoff | pick_correct |
| Paraguay vs Australia | 2026-06-25 22:00 | FT | 0-0 | draw | Pass | pass | 35.73% | latest_pre_kickoff | good_pass_draw_risk |
| Turkey vs USA | 2026-06-25 22:00 | FT | 3-2 | team1_win | Pass | pass | 32.77% | latest_pre_kickoff | good_pass_protected_wrong_internal |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 20/100.
- Remaining before local stop: 65.
