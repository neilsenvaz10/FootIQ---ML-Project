# World Cup Model Report - 29 June 2026

Updated: 2026-06-29 10:57 ET

## Executive Summary

- All 72 group-stage results are locked.
- The official FIFA Round-of-32 bracket is loaded for all 16 fixtures.
- Canada's 1-0 win over South Africa is locked into every remaining tournament path.
- The tournament simulation ran 50,000 times.
- France is the current title favorite at 14.05%, narrowly ahead of Argentina at 13.79%.
- The free API plan currently exposes live fixture data only through 30 June. July 1-3 forecasts below use the verified bracket and base tournament engine, without current weather or confirmed lineups.

## Today - 29 June

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement |
|---|---|---|---|---|
| Brazil v Japan | Pass | Brazil win | 37.75 / 36.43 / 25.82 | Brazil 56.21% |
| Germany v Paraguay | Pass | Germany win | 44.92 / 34.84 / 20.24 | Germany 66.92% |
| Netherlands v Morocco | Pass | Draw | 34.42 / 37.18 / 28.41 | Morocco 50.10% |

The best read always states the likeliest regulation outcome. `Pass` means the read is not separated enough to recommend confidently. Netherlands-Morocco is effectively a coin flip after extra time and penalties.

Brazil-Japan currently carries a 34.6C heat input. The weather adjustment lowers the expected scoring rate but does not create enough separation for a confident public pick.

## Tomorrow - 30 June

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement |
|---|---|---|---|---|
| Ivory Coast v Norway | Model Lean | Norway win | 13.96 / 29.20 / 56.84 | Norway 63.70% |
| France v Sweden | Model Lean | France win | 69.17 / 24.76 / 6.07 | France 81.99% |
| Mexico v Ecuador | Pass | Draw | 35.39 / 37.51 / 27.10 | Mexico 50.57% |

Only Mexico-Ecuador currently has a usable weather observation: 16.4C and comfortable conditions. No confirmed starting lineups were available at the snapshot time.

## Later Round-of-32 Forecasts

These are full-match advancement probabilities from the base tournament engine. They are not yet live-weather or confirmed-lineup forecasts.

| Date | Fixture | Advancement forecast |
|---|---|---|
| 1 July | England v DR Congo | England 75.79% |
| 1 July | USA v Bosnia & Herzegovina | USA 68.06% |
| 1 July | Belgium v Senegal | Belgium 60.80% |
| 2 July | Portugal v Croatia | Portugal 61.36% |
| 2 July | Spain v Austria | Spain 71.99% |
| 2 July | Switzerland v Algeria | Switzerland 59.52% |
| 3 July | Argentina v Cape Verde | Argentina 83.13% |
| 3 July | Colombia v Ghana | Colombia 82.15% |
| 3 July | Australia v Egypt | Egypt 52.25% |

## Live Title Standings

| Rank | Team | Champion | Reach final | Reach semi-final |
|---:|---|---:|---:|---:|
| 1 | France | 14.05% | 22.72% | 34.99% |
| 2 | Argentina | 13.79% | 24.39% | 41.62% |
| 3 | Spain | 10.48% | 18.18% | 31.58% |
| 4 | Colombia | 7.07% | 14.14% | 27.45% |
| 5 | England | 6.80% | 12.65% | 23.28% |
| 6 | Brazil | 6.49% | 11.85% | 20.87% |
| 7 | Germany | 4.94% | 9.89% | 18.32% |
| 8 | Portugal | 4.20% | 8.56% | 17.40% |
| 9 | Belgium | 3.78% | 8.38% | 18.56% |
| 10 | Netherlands | 3.57% | 7.33% | 14.21% |

France remains first, but the race is effectively France-Argentina at this checkpoint. Argentina has the better final and semi-final reach rates; France has a marginally higher conversion rate to champion in the simulated bracket.

## Validation

- Genuine completed fixtures: 52.
- Public picks: 29.
- Correct public picks: 19.
- Public-pick accuracy: 65.52%.
- Internal ensemble accuracy: 65.38% across all 52 eligible fixtures.
- June 26 public picks: 2/2 correct.
- June 27 public picks: 4/4 correct.
- South Africa-Canada was collected after the match and is correctly excluded from accuracy.

## Model Integrity Changes

- Recovered three official group results whose local schedule dates were stale by one day, using a unique-pairing fallback.
- Replaced the old greedy third-place resolver with the official resolved FIFA Round-of-32 bracket.
- Added support for locking completed knockout winners into all downstream simulations.
- Added tests for exact-date matching, safe pairing fallback, ambiguity rejection, and knockout winner locking.
- Removed predicted scores and exact-score rankings from public matchday reports while retaining them internally.
- Added a plain-English best read to every fixture, including passes.
- Test suite: 20 passed.

## Files

- Full tournament simulation: `outputs/live_tournament_v213_report.md`
- Tomorrow's live forecast: `outputs/worldcup_matchday_v29_report_2026-06-30.md`
- Today's live forecast: `outputs/worldcup_matchday_v29_report_2026-06-29.md`
- Verified Round-of-32 bracket: `data/processed/worldcup_2026_round_of_32_resolved.csv`
