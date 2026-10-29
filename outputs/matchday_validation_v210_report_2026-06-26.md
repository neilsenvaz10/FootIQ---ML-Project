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
- Average probability assigned to actual result: 51.39%.
- Average Brier score: 0.390075.
- Average log loss: 0.6960433333333333.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 2 | 2 | 2 | 100.00% |
| Pass | 4 | 4 | 4 |  |

## Pass Reads

- Good pass from draw risk: 2.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 2.
- Neutral pass: 0.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Norway vs France | 2026-06-26 15:00 | FT | 1-4 | team2_win | Pass | pass | 54.17% | latest_pre_kickoff | possible_too_conservative |
| Senegal vs Iraq | 2026-06-26 15:00 | FT | 5-0 | team1_win | Pass | pass | 52.00% | latest_pre_kickoff | possible_too_conservative |
| Cape Verde vs Saudi Arabia | 2026-06-26 20:00 | FT | 0-0 | draw | Pass | pass | 36.82% | latest_pre_kickoff | good_pass_draw_risk |
| Uruguay vs Spain | 2026-06-26 20:00 | FT | 0-1 | team2_win | Model Lean | team2_win | 62.76% | latest_pre_kickoff | pick_correct |
| Egypt vs Iran | 2026-06-26 23:00 | FT | 1-1 | draw | Pass | pass | 34.82% | latest_pre_kickoff | good_pass_draw_risk |
| New Zealand vs Belgium | 2026-06-26 23:00 | FT | 1-5 | team2_win | Model Lean | team2_win | 67.76% | latest_pre_kickoff | pick_correct |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 6/100.
- Remaining before local stop: 79.
