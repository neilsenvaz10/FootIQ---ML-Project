# World Cup Model Report - 30 June 2026

Updated: 2026-06-30 12:58 ET

## Executive Summary

- June 29 is fully validated against genuine pre-kickoff snapshots.
- Brazil advanced in regulation; Paraguay and Morocco advanced on penalties.
- All four completed Round-of-32 winners are locked into 50,000 remaining tournament paths.
- France remains the title favorite at 16.32%.
- Today's first match was captured at 12:54 ET with both confirmed starting XIs.
- Exact-score predictions remain hidden from public reports.

## June 29 Validation

| Fixture | Best 90-minute read | Regulation result | Advancement read | Actual qualifier | Evaluation |
|---|---|---|---|---|---|
| Brazil v Japan | Brazil win | Brazil 2-1 Japan | Brazil | Brazil | Correct |
| Germany v Paraguay | Germany win | 1-1 | Germany | Paraguay on penalties | Wrong |
| Netherlands v Morocco | Draw | 1-1 | Morocco | Morocco on penalties | Correct |

- Regulation best reads: 2/3 correct.
- Full-match advancement reads: 2/3 correct.
- Public confidence gates: three Passes, so no published picks entered the public-pick accuracy denominator.
- Two passes correctly identified draw risk; one was a neutral pass.

## Today - 30 June

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Live context |
|---|---|---|---|---|---|
| Ivory Coast v Norway | Model Lean | Norway win | 13.96 / 29.20 / 56.84 | Norway 63.44% | Both XIs confirmed |
| France v Sweden | Model Lean | France win | 69.17 / 24.76 / 6.07 | France 82.76% | Lineups pending |
| Mexico v Ecuador | Pass | Draw | 35.39 / 37.51 / 27.10 | Mexico 50.75% | 16.6C; lineups pending |

The confirmed-lineup shadow layer slightly strengthens Norway's position, but its stricter v2.11/v2.12 publishing policy remains a Pass because draw risk is still material. The production baseline remains a Norway model lean.

## Tomorrow - 1 July

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Weather |
|---|---|---|---|---|---|
| England v DR Congo | Model Lean | England win | 69.08 / 24.03 / 6.88 | England 75.87% | 34.6C |
| Belgium v Senegal | Pass | Belgium win | 37.20 / 35.27 / 27.52 | Belgium 61.17% | 17.6C |
| USA v Bosnia & Herzegovina | Model Lean | USA win | 62.15 / 27.53 / 10.32 | USA 67.72% | Weather pending |

Tomorrow's strongest straightforward read is England. Belgium is the best advancement read in its fixture, but the 90-minute market remains too compressed for a confident regulation pick.

## Live Title Standings

| Rank | Team | Champion | Reach final | Reach semi-final |
|---:|---|---:|---:|---:|
| 1 | France | 16.32% | 26.72% | 40.85% |
| 2 | Argentina | 13.37% | 23.64% | 41.39% |
| 3 | Brazil | 11.58% | 21.02% | 36.97% |
| 4 | Spain | 10.92% | 18.82% | 31.97% |
| 5 | Morocco | 7.14% | 15.21% | 29.59% |
| 6 | Colombia | 7.03% | 14.03% | 27.78% |
| 7 | England | 6.68% | 12.49% | 22.69% |
| 8 | Portugal | 4.29% | 8.68% | 17.52% |
| 9 | Belgium | 3.88% | 8.64% | 18.44% |
| 10 | Mexico | 2.47% | 5.44% | 11.56% |

Germany and the Netherlands are now at zero after their shootout eliminations. Morocco rises to fifth, while Brazil rises to third after reaching the Round of 16.

## Validation Record

- Genuine completed fixtures: 55.
- Public picks: 29.
- Correct public picks: 19.
- Public-pick accuracy: 65.52%.
- Internal best-read accuracy: 65.45% across all 55 eligible fixtures.
- June 29 did not change public-pick accuracy because all three calls were Passes.

## Audit Notes

- Shootout winners are stored separately from regulation outcomes.
- Verified knockout results now override simulated winners in downstream tournament paths.
- The confirmed-lineup identity layer matched 43 of 44 inspected starters across its eligible fixtures.
- Test suite: 22 passed.

## Files

- Full tournament simulation: `outputs/live_tournament_v213_report.md`
- June 29 validation: `outputs/matchday_validation_v210_report_2026-06-29.md`
- Today's report: `outputs/worldcup_matchday_v29_report_2026-06-30.md`
- Tomorrow's report: `outputs/worldcup_matchday_v29_report_2026-07-01.md`
- Verified knockout results: `data/processed/worldcup_2026_knockout_results_verified.csv`
