# World Cup Matchday Runner v2.9

Snapshot: 2026-07-14T14:09:11-04:00

## Run Summary

- Matchday date: 2026-07-14.
- World Cup provider fixtures found: 1.
- Fixtures scored: 1.
- Weather rows with temperature: 1/1.
- Lineup team rows available: 2.
- Strong Picks: 0.
- Model Leans: 0.
- Passes: 1.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| France vs Spain | 15:00 | NS | Pass | Draw | 20.84% | 39.98% | 39.17% | 1.108-1.039 | 29.4C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 2 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Weather uses the U.S. National Weather Service first for U.S. venues, with Open-Meteo as fallback; Open-Meteo remains primary elsewhere.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 2/100.
- Remaining before local stop: 83.
