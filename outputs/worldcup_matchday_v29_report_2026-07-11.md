# World Cup Matchday Runner v2.9

Snapshot: 2026-07-11T15:08:56-04:00

## Run Summary

- Matchday date: 2026-07-11.
- World Cup provider fixtures found: 0.
- Fixtures scored: 2.
- Weather rows with temperature: 0/2.
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 0.
- Passes: 2.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Norway vs England | 17:00 | LOCAL | Pass | England win | 19.75% | 36.04% | 44.21% | 1.039-1.273 | unavailable | 0 |
| Argentina vs Switzerland | 21:00 | LOCAL | Pass | Argentina win | 56.65% | 31.66% | 11.70% | 1.353-0.977 | unavailable | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Weather uses the U.S. National Weather Service first for U.S. venues, with Open-Meteo as fallback; Open-Meteo remains primary elsewhere.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 1/100.
- Remaining before local stop: 84.
