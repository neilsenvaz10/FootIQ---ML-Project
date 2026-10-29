# World Cup Matchday Runner v2.9

Snapshot: 2026-07-05T11:27:06-04:00

## Run Summary

- Matchday date: 2026-07-05.
- World Cup provider fixtures found: 2.
- Fixtures scored: 2.
- Weather rows with temperature: 2/2.
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 0.
- Passes: 2.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Brazil vs Norway | 16:00 | NS | Pass | Brazil win | 43.27% | 34.74% | 21.99% | 1.203-0.955 | 28.9C; Weather friction from rain/wind; lowers scoring slightly. | 0 |
| Mexico vs England | 20:00 | NS | Pass | Draw | 29.21% | 36.70% | 34.10% | 1.043-1.188 | 18.2C; Weather friction from rain/wind; lowers scoring slightly. | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Weather uses the U.S. National Weather Service first for U.S. venues, with Open-Meteo as fallback; Open-Meteo remains primary elsewhere.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 3/100.
- Remaining before local stop: 82.
