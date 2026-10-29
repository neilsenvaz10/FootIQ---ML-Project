# World Cup Matchday Runner v2.9

Snapshot: 2026-07-03T11:21:32-04:00

## Run Summary

- Matchday date: 2026-07-03.
- World Cup provider fixtures found: 3.
- Fixtures scored: 3.
- Weather rows with temperature: 3/3.
- Lineup team rows available: 0.
- Strong Picks: 1.
- Model Leans: 1.
- Passes: 1.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Australia vs Egypt | 14:00 | NS | Pass | Australia win | 39.78% | 35.29% | 24.94% | 1.034-1.066 | 33.9C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 0 |
| Argentina vs Cape Verde | 18:00 | NS | Strong Pick | Argentina win | 84.30% | 11.89% | 3.80% | 1.569-0.71 | 30.6C; Hot conditions with meaningful rain/thunderstorm risk; lowers tempo and raises disruption risk. | 0 |
| Colombia vs Ghana | 21:30 | NS | Model Lean | Colombia win | 80.01% | 16.23% | 3.76% | 1.479-0.767 | 32.2C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Weather uses the U.S. National Weather Service first for U.S. venues, with Open-Meteo as fallback; Open-Meteo remains primary elsewhere.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 24/100.
- Remaining before local stop: 61.
