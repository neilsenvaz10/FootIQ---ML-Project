# World Cup Matchday Runner v2.9

Snapshot: 2026-07-10T14:09:02-04:00

## Run Summary

- Matchday date: 2026-07-10.
- World Cup provider fixtures found: 1.
- Fixtures scored: 1.
- Weather rows with temperature: 1/1.
- Lineup team rows available: 2.
- Strong Picks: 0.
- Model Leans: 1.
- Passes: 0.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Spain vs Belgium | 15:00 | NS | Model Lean | Spain win | 58.69% | 30.13% | 11.18% | 1.224-1.0 | 27.2C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 2 |

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
