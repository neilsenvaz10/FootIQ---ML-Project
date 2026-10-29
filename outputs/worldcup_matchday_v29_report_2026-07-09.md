# World Cup Matchday Runner v2.9

Snapshot: 2026-07-09T08:49:34-04:00

## Run Summary

- Matchday date: 2026-07-09.
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
| France vs Morocco | 16:00 | NS | Pass | France win | 44.22% | 35.61% | 20.17% | 1.202-0.958 | 31.1C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 0 |

## Operational Notes

- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.
- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.
- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.
- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.
- Weather uses the U.S. National Weather Service first for U.S. venues, with Open-Meteo as fallback; Open-Meteo remains primary elsewhere.
- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.

## API Budget

- Used today: 4/100.
- Remaining before local stop: 81.
