# World Cup Daily Report - 11 July 2026

Updated: 2026-07-11 15:09 ET

## Sendable Summary

Validated again: Spain 2-1 Belgium stayed a correct Model Lean. Today: England to qualify vs Norway, Argentina to qualify vs Switzerland, but both remain public Passes because draw/weather risk is too live. France-Spain early semifinal read remains France to qualify by a small edge, with 90-minute draw as the best regulation read.

## Validation

| Date | Fixture | Public gate | Model read | Result | Evaluation |
|---|---|---|---|---|---|
| 10 July | Spain v Belgium | Model Lean | Spain win | Spain 2-1 Belgium | Correct |

Public pick accuracy: 100%. Internal ensemble accuracy: 100%. Actual-result probability: 58.69%.

## Today - 11 July

| Fixture | Kickoff ET | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Weather/context |
|---|---:|---|---|---:|---|---|
| Norway v England | 17:00 | Pass | England win | 19.75 / 36.04 / 44.21 | England 58.25% | Miami heat: about 33C, feels 40-44C with humidity; storm delay risk |
| Argentina v Switzerland | 21:00 | Pass | Argentina win | 56.65 / 31.66 / 11.70 | Argentina 65.09% | Kansas City fixture confirmed; lineups/weather feed pending |

The model runner did not receive provider weather rows for today's local-fallback fixture rows, but external matchday reporting is strong enough to manually flag the Miami conditions. That weather context supports keeping Norway-England at Pass: the heat can lower tempo, increase fatigue, and make the draw/late-chaos band more meaningful.

## Semifinal - France v Spain

| Fixture | Date | Kickoff ET | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Context |
|---|---|---:|---|---|---:|---|---|
| France v Spain | 14 July | 15:00 | Pass | Draw | 20.84 / 39.98 / 39.17 | France 52.35% | Dallas/AT&T Stadium; weather feed pending, likely reduced outdoor-weather relevance if roof/climate control is used |

This is still an early forecast. The honest read is not "France win in 90"; it is "France slightly likelier to advance, but 90 minutes is almost level between draw and Spain."

## Current Title Picture

| Rank | Team | Title odds |
|---:|---|---:|
| 1 | France | 34.30% |
| 2 | Spain | 26.89% |
| 3 | Argentina | 17.78% |
| 4 | England | 13.27% |
| 5 | Switzerland | 4.54% |
| 6 | Norway | 3.22% |

## Data Notes

- API validation confirmed Spain-Belgium again.
- API-Football did not return lineup rows for today's two matches at this run.
- The script's weather field came back unavailable for today's local-fallback rows, so Miami weather was overlaid from live match reporting.
- Rerun Norway-England roughly one hour before kickoff for confirmed lineups.
- Rerun Argentina-Switzerland close to 20:00 ET for lineups and late weather.

## Sources Checked

- API-Football validation/status feed.
- AP Spain-Belgium match report.
- Guardian Norway-England live coverage.
- talkSPORT Norway-England weather forecast.
- Guardian July 11 fixture guide.
