# World Cup Matchday Runner v2.9

Snapshot: 2026-06-30T12:54:16-04:00

## Run Summary

- Matchday date: 2026-06-30.
- World Cup provider fixtures found: 3.
- Fixtures scored: 3.
- Weather rows with temperature: 1/3.
- Lineup team rows available: 2.
- Strong Picks: 0.
- Model Leans: 2.
- Passes: 1.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Ivory Coast vs Norway | 13:00 | NS | Model Lean | Norway win | 13.96% | 29.20% | 56.84% | 1.064-1.243 | neutral | 2 |
| France vs Sweden | 17:00 | NS | Model Lean | France win | 69.17% | 24.76% | 6.07% | 1.601-0.826 | neutral | 0 |
| Mexico vs Ecuador | 21:00 | NS | Pass | Draw | 35.39% | 37.51% | 27.10% | 1.145-1.098 | 16.6C | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 4/100.
- Remaining before local stop: 81.
