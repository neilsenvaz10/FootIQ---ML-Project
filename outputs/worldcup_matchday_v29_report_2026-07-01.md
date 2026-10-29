# World Cup Matchday Runner v2.9

Snapshot: 2026-07-01T08:17:50-04:00

## Run Summary

- Matchday date: 2026-07-01.
- World Cup provider fixtures found: 3.
- Fixtures scored: 3.
- Weather rows with temperature: 2/3.
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 2.
- Passes: 1.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| England vs DR Congo | 12:00 | NS | Model Lean | England win | 69.08% | 24.03% | 6.88% | 1.377-0.808 | 33.5C | 0 |
| Belgium vs Senegal | 16:00 | NS | Pass | Belgium win | 37.20% | 35.27% | 27.52% | 1.266-1.044 | 17.0C | 0 |
| USA vs Bosnia & Herzegovina | 20:00 | NS | Model Lean | USA win | 62.15% | 27.53% | 10.32% | 1.423-0.929 | neutral | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 4/100.
- Remaining before local stop: 81.
