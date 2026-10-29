# World Cup Matchday Runner v2.9

Snapshot: 2026-07-02T02:09:18-04:00

## Run Summary

- Matchday date: 2026-07-02.
- World Cup provider fixtures found: 3.
- Fixtures scored: 3.
- Weather rows with temperature: 2/3.
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 1.
- Passes: 2.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Spain vs Austria | 15:00 | NS | Model Lean | Spain win | 64.33% | 27.40% | 8.28% | 1.344-0.984 | neutral | 0 |
| Portugal vs Croatia | 19:00 | NS | Pass | Portugal win | 42.86% | 31.93% | 25.21% | 1.172-0.932 | 34.5C | 0 |
| Switzerland vs Algeria | 23:00 | NS | Pass | Switzerland win | 41.89% | 35.77% | 22.34% | 1.198-1.084 | 14.5C | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 10/100.
- Remaining before local stop: 75.
