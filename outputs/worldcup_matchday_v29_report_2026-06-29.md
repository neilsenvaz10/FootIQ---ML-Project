# World Cup Matchday Runner v2.9

Snapshot: 2026-06-29T10:57:08-04:00

## Run Summary

- Matchday date: 2026-06-29.
- World Cup provider fixtures found: 3.
- Fixtures scored: 3.
- Weather rows with temperature: 1/3.
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 0.
- Passes: 3.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Brazil vs Japan | 13:00 | NS | Pass | Brazil win | 37.75% | 36.43% | 25.82% | 1.114-0.981 | 34.6C | 0 |
| Germany vs Paraguay | 16:30 | NS | Pass | Germany win | 44.92% | 34.84% | 20.24% | 1.394-0.948 | neutral | 0 |
| Netherlands vs Morocco | 21:00 | NS | Pass | Draw | 34.42% | 37.18% | 28.41% | 1.162-1.138 | neutral | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 27/100.
- Remaining before local stop: 58.
