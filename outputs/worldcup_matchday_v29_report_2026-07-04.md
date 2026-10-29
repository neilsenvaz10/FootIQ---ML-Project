# World Cup Matchday Runner v2.9

Snapshot: 2026-07-03T01:03:09-04:00

## Run Summary

- Matchday date: 2026-07-04.
- World Cup provider fixtures found: 2.
- Fixtures scored: 2.
- Weather rows with temperature: 2/2 (public-forecast fallback; Open-Meteo timed out).
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 1.
- Passes: 1.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Canada vs Morocco | 13:00 | NS | Pass | Morocco win | 20.66% | 35.38% | 43.96% | 0.950-1.181 | 32-33C, hot/humid; NRG roof status pending | 0 |
| Paraguay vs France | 17:00 | NS | Model Lean | France win | 10.76% | 27.18% | 62.06% | 0.772-1.306 | 38-39C, extreme heat; storm risk | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.
- Open-Meteo timed out during this run. Weather was recovered from current public forecasts; it reduces projected scoring tempo but does not change either directional call.

## API Budget

- Used today: 20/100.
- Remaining before local stop: 65.
