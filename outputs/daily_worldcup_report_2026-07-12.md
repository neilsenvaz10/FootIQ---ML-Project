# World Cup Daily Report - 12 July 2026

Updated: 2026-07-12 11:28 ET

## Sendable Summary

Validated July 11: both quarterfinals were correctly protected as Passes because both finished 1-1 after 90 minutes. Semifinal reads: France to qualify by a tiny edge over Spain; Argentina to qualify by a small edge over England. Neither semifinal is a confident 90-minute call yet.

## Validation - 11 July

| Fixture | Public gate | Best 90-minute read | Regulation result | Qualifier | Evaluation |
|---|---|---|---|---|---|
| Norway v England | Pass | England win | 1-1 | England after extra time | Correct Pass |
| Argentina v Switzerland | Pass | Argentina win | 1-1 | Argentina after extra time | Correct Pass |

Both matches landed exactly in the risk band the gate was designed to avoid: the internal winner lean did not land in 90 minutes, but the Pass protected the public call.

## Semifinal Forecasts

| Date | Fixture | Kickoff ET | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Weather/context |
|---|---|---:|---|---|---:|---|---|
| 14 July | France v Spain | 15:00 | Pass | Draw | 20.84 / 39.98 / 39.17 | France 52.63% | 31.1C; hot with rain/thunderstorm disruption risk |
| 15 July | England v Argentina | 15:00 | Pass | Argentina win | 20.18 / 35.80 / 44.01 | Argentina 54.11% | 29.4C; rain/wind friction lowers scoring slightly |

France-Spain is almost a pure coin flip after 90 minutes. The model's honest statement is France slightly likelier to advance, not France to win in regulation.

England-Argentina has a clearer 90-minute directional lean toward Argentina, but the draw band is still high enough to keep it at Pass.

## Current Title Picture

| Rank | Team | Title odds | Final odds |
|---:|---|---:|---:|
| 1 | France | 29.11% | 52.63% |
| 2 | Argentina | 25.73% | 54.11% |
| 3 | Spain | 25.23% | 47.37% |
| 4 | England | 19.93% | 45.89% |

## Data Notes

- July 11 validation uses regulation scores for model scoring: both games were 1-1 after 90 minutes.
- Knockout advancement is locked separately: England beat Norway 2-1 after extra time; Argentina beat Switzerland 3-1 after extra time.
- Semifinal lineups are not available yet.
- Weather data came through for both semifinal forecasts, but this is still forecast-level data. Rerun each match close to kickoff.
- The local rerun used the available sklearn-enabled Python environment and emitted sklearn version warnings. Treat this as an operational refresh, not a new model version.

## Sources Checked

- AP Norway-England match report.
- AP Argentina-Switzerland match report.
- Guardian Norway-England live report.
- talkSPORT Argentina-Switzerland report.
