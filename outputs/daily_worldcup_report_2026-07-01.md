# World Cup Model Report - 1 July 2026

Updated: 2026-07-01 08:20 ET

## Executive Summary

- Seven of the 16 Round-of-32 matches are complete.
- France, Norway, and Mexico advanced on 30 June.
- Sweden, Ivory Coast, and Ecuador are eliminated and now have zero title probability.
- All seven completed knockout winners are locked into 50,000 remaining tournament paths.
- France remains the title favorite at 19.98%.
- Overall public-pick accuracy rises to 67.74% across 31 genuine picks.

## June 30 Validation

| Fixture | Public call | Result | Evaluation | Qualifier |
|---|---|---|---|---|
| Ivory Coast v Norway | Norway win; Model Lean | Norway won 2-1 | Correct | Norway |
| France v Sweden | France win; Model Lean | France won 3-0 | Correct | France |
| Mexico v Ecuador | Draw; Pass | Mexico won 2-0 | Pass protected the wrong internal read | Mexico |

- Published picks: 2/2 correct.
- Public-pick accuracy: 100%.
- Internal best reads: 2/3 correct.
- The Mexico-Ecuador pass prevented an uncertain draw read from becoming a published pick.

## Today - 1 July

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Live context |
|---|---|---|---|---|---|
| England v DR Congo | Model Lean | England win | 69.08 / 24.03 / 6.88 | England 76.22% | 33.5C; lineups pending |
| Belgium v Senegal | Pass | Belgium win | 37.20 / 35.27 / 27.52 | Belgium 60.92% | 17.0C; lineups pending |
| USA v Bosnia & Herzegovina | Model Lean | USA win | 62.15 / 27.53 / 10.32 | USA 67.81% | Weather and lineups pending |

England is today's strongest read. Belgium is favored to advance, but its 90-minute market is almost level with the draw and therefore remains a Pass.

## Tomorrow - 2 July

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Live context |
|---|---|---|---|---|---|
| Spain v Austria | Model Lean | Spain win | 64.33 / 27.40 / 8.28 | Spain 72.37% | Weather unavailable; lineups pending |
| Portugal v Croatia | Pass | Portugal win | 42.86 / 31.93 / 25.21 | Portugal 61.14% | 24.3C; lineups pending |
| Switzerland v Algeria | Pass | Switzerland win | 41.89 / 35.77 / 22.34 | Switzerland 59.93% | 14.3C; lineups pending |

Portugal remains the likeliest regulation winner and a meaningful favorite to advance. The regulation confidence gate stays at Pass because the draw remains too probable for a clean 90-minute recommendation.

## Live Title Standings

| Rank | Team | Champion | Reach final | Reach semi-final |
|---:|---|---:|---:|---:|
| 1 | France | 19.98% | 31.99% | 49.10% |
| 2 | Argentina | 13.19% | 23.59% | 41.60% |
| 3 | Brazil | 10.80% | 19.78% | 34.99% |
| 4 | Spain | 10.47% | 18.01% | 31.84% |
| 5 | Colombia | 6.82% | 13.93% | 27.30% |
| 6 | Morocco | 6.54% | 13.61% | 27.21% |
| 7 | England | 6.34% | 12.08% | 22.06% |
| 8 | Mexico | 4.67% | 10.54% | 22.37% |
| 9 | Portugal | 4.05% | 8.51% | 17.44% |
| 10 | Belgium | 3.79% | 8.43% | 18.59% |
| 11 | Norway | 3.04% | 8.82% | 18.88% |
| 12 | Switzerland | 2.26% | 5.33% | 12.78% |

France is now nearly a one-in-five title favorite. Mexico rises after qualifying, while Norway moves to 11th. Portugal remains ninth overall before facing Croatia.

## Eliminated Teams

The completed Round-of-32 matches have eliminated:

- South Africa
- Germany
- Netherlands
- Japan
- Sweden
- Ivory Coast
- Ecuador

## Validation Record

- Genuine completed fixtures: 58.
- Public picks: 31.
- Correct public picks: 21.
- Public-pick accuracy: 67.74%.
- Internal best-read accuracy: 65.52% across all 58 eligible fixtures.

## Data Status

- Today's fixtures and weather were refreshed at 08:17 ET.
- Tomorrow's official API fixture feed is now available.
- No confirmed starting lineups were available for today's or tomorrow's fixtures at the snapshot time.
- Yesterday's hotter Portugal-Croatia weather estimate is superseded by the current 24.3C forecast.
- Exact-score predictions remain hidden from public reports.

## Files

- Full tournament simulation: `outputs/live_tournament_v213_report.md`
- June 30 validation: `outputs/matchday_validation_v210_report_2026-06-30.md`
- Today's predictions: `outputs/worldcup_matchday_v29_report_2026-07-01.md`
- Tomorrow's predictions: `outputs/worldcup_matchday_v29_report_2026-07-02.md`
- Verified knockout results: `data/processed/worldcup_2026_knockout_results_verified.csv`
