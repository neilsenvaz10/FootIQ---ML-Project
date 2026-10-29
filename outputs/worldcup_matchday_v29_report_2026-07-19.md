# World Cup Matchday Runner v2.9

Snapshot: 2026-07-19T12:41:26-04:00

## Run Summary

- Matchday date: 2026-07-19.
- World Cup provider fixtures found: 1.
- Fixtures scored: 1.
- Weather rows with temperature: 1/1.
- Lineup team rows available: 0.
- Strong Picks: 0.
- Model Leans: 1.
- Passes: 0.

## Predictions

| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |
|---|---:|---|---|---|---:|---:|---:|---|---|---:|
| Spain vs Argentina | 15:00 | NS | Model Lean | Draw | 30.99% | 39.75% | 29.26% | 1.099-1.113 | 27.2C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 0 |

## Final/Trophy Overlay

API-Football returned 0 confirmed lineup rows at 12:41 ET, so this is the current base final model with weather but without confirmed-XI adjustment.

| Match | Best 90-minute read | Regulation 1/X/2 | Full-match champion |
|---|---|---|---|
| Spain vs Argentina | Draw | Spain 30.99 / Draw 39.75 / Argentina 29.26 | Spain 51.27 / Argentina 48.73 |

Read: Spain remain the trophy pick, but only by a very thin edge. The model expects a tight final with high extra-time/penalty risk.

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
