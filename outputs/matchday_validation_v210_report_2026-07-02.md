# Matchday Validation v2.10

Snapshot source: `data/processed/worldcup_matchday_v29_snapshots.csv`

## Summary

- Fixture predictions selected: 3.
- Final fixture statuses found: 3.
- Eligible pre-kickoff finals scored: 3.
- Backfill finals not scored: 0.
- Pending/live fixtures: 0.
- Provider errors: 0.
- Public pick accuracy: 100.00%.
- Internal ensemble accuracy: 100.00%.
- Average probability assigned to actual result: 49.69%.
- Average Brier score: 0.40554.
- Average log loss: 0.7194733333333333.

## Tier Counts

| Tier | Selected | Final | Eligible final | Accuracy when picked |
|---|---:|---:|---:|---:|
| Strong Pick | 0 | 0 | 0 |  |
| Model Lean | 1 | 1 | 1 | 100.00% |
| Pass | 2 | 2 | 2 |  |

## Pass Reads

- Good pass from draw risk: 0.
- Good pass protecting against wrong internal lean: 0.
- Possible too conservative: 0.
- Neutral pass: 2.

## Fixture Validation

| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |
|---|---|---|---|---|---|---|---:|---|---|
| Spain vs Austria | 2026-07-02 15:00 | FT | 3-0 | team1_win | Model Lean | team1_win | 64.33% | latest_pre_kickoff | pick_correct |
| Portugal vs Croatia | 2026-07-02 19:00 | FT | 2-1 | team1_win | Pass | pass | 42.86% | latest_pre_kickoff | neutral_pass |
| Switzerland vs Algeria | 2026-07-02 23:00 | FT | 2-0 | team1_win | Pass | pass | 41.89% | latest_pre_kickoff | neutral_pass |

## Notes

- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.
- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.
- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.
- AET/PEN matches are flagged because the current model is a regulation-result model.

## API Budget

- Used today: 7/100.
- Remaining before local stop: 78.
