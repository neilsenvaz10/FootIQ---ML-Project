# World Cup Matchday Runner v2.9

Snapshot: 2026-07-15T13:09:22-04:00

## Run Summary

- Matchday date: 2026-07-15.
- World Cup provider fixtures found: 1.
- Fixtures scored: 1.
- Weather rows with temperature: 1/1.
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 0.
- Passes: 1.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| England vs Argentina | 15:00 | NS | Pass | Argentina win | 20.18% | 35.80% | 44.01% | 1.028-1.108 | 30.0C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 0 |

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
