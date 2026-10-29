# World Cup Matchday Runner v2.9

Snapshot: 2026-07-18T15:53:37-04:00

## Run Summary

- Matchday date: 2026-07-18.
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
| France vs England | 17:00 | NS | Model Lean | Draw | 32.80% | 39.38% | 27.82% | 1.128-0.994 | 32.8C; Warm conditions; lowers tempo slightly and nudges draw risk up. | 0 |

## Confirmed-Lineup Overlay

API-Football returned 0 lineup rows, so this overlay uses the user-provided 365Scores lineup screenshots.

| Match | Lineup-adjusted 90-min read | Adjusted 1/X/2 | Full-match bronze |
|---|---|---|---|
| France vs England | Draw | France 31.53 / Draw 43.06 / England 25.41 | France 58.83 / England 41.17 |

Lineup impact: France confirmed XI is -3.67 vs baseline; England confirmed XI is -5.22 vs baseline. England are rotated more heavily, so France's full-match bronze edge increases.

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
