# World Cup Model Report - 2 July 2026

Updated: 2026-07-02 02:12 ET

## Accuracy Answer

The first teams began their third group matches on **24 June at 15:00 ET**. This cutoff was derived from all 48 teams' actual fixture order.

| Scope | Prediction set | Correct | Matches | Accuracy |
|---|---|---:|---:|---:|
| Entire genuine sample | Raw best read; ignore confidence gate | 40 | 61 | 65.57% |
| Entire genuine sample | Model Lean only | 22 | 30 | 73.33% |
| Third matches onward | Raw best read; ignore confidence gate | 23 | 33 | 69.70% |
| Third matches onward | Model Lean only | 15 | 18 | 83.33% |

The raw best read is the model's top 90-minute 1/X/2 outcome on every fixture, including fixtures marked Pass. This is the confidence-gate-free accuracy requested.

The 33-match post-cutoff sample contains every genuine pre-kickoff prediction from 24 June at 15:00 ET through 1 July. South Africa-Canada is excluded because its local snapshot was collected after the match and cannot honestly enter accuracy.

## Full Confidence Breakdown

| Scope | Tier | Correct | Matches | Accuracy |
|---|---|---:|---:|---:|
| Entire sample | Strong Pick | 1 | 3 | 33.33% |
| Entire sample | Model Lean | 22 | 30 | 73.33% |
| Entire sample | Pass-row internal read | 17 | 28 | 60.71% |
| Third matches onward | Strong Pick | 0 | 0 | Not applicable |
| Third matches onward | Model Lean | 15 | 18 | 83.33% |
| Third matches onward | Pass-row internal read | 8 | 15 | 53.33% |

The Strong Pick sample is only three fixtures and is too small to support a reliable claim. Model Lean is currently the strongest proven publishing tier.

## Knockout Advancement Accuracy

| Period | Correct | Genuine calls | Accuracy |
|---|---:|---:|---:|
| 29 June through 1 July | 8 | 9 | 88.89% |

The only incorrect advancement call was Germany over Paraguay. The 28 June Canada result is excluded because the matchup was backfilled after kickoff.

## July 1 Validation

| Fixture | Best 90-minute read | Regulation result | Advancement read | Qualifier |
|---|---|---|---|---|
| England v DR Congo | England win | England won 2-1 | England | England |
| Belgium v Senegal | Belgium win | 2-2 | Belgium | Belgium after extra time |
| USA v Bosnia & Herzegovina | USA win | USA won 2-0 | USA | USA |

- Raw 90-minute best reads: 2/3 correct.
- Model Leans: 2/2 correct.
- Advancement calls: 3/3 correct.
- Belgium-Senegal is correctly scored as a regulation draw, not as Belgium's 3-2 extra-time result.

## Today - 2 July

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Context |
|---|---|---|---|---|---|
| Spain v Austria | Model Lean | Spain win | 64.33 / 27.40 / 8.28 | Spain 72.16% | Weather unavailable; lineups pending |
| Portugal v Croatia | Pass | Portugal win | 42.86 / 31.93 / 25.21 | Portugal 61.48% | 34.5C; lineups pending |
| Switzerland v Algeria | Pass | Switzerland win | 41.89 / 35.77 / 22.34 | Switzerland 59.69% | 14.5C; lineups pending |

## Tomorrow - 3 July

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Context |
|---|---|---|---|---|---|
| Australia v Egypt | Pass | Australia win | 39.78 / 35.29 / 24.94 | Egypt 52.44% | Weather and lineups pending |
| Argentina v Cape Verde | Strong Pick | Argentina win | 84.30 / 11.89 / 3.80 | Argentina 83.45% | Weather and lineups pending |
| Colombia v Ghana | Model Lean | Colombia win | 80.01 / 16.23 / 3.76 | Colombia 81.94% | 27.8C; lineups pending |

Australia-Egypt is the unusual one: Australia is the likeliest 90-minute winner, but the knockout engine gives Egypt a narrow extra-time/penalty advancement edge. It is a Pass.

## First Round of 16 Day

| Fixture | Qualification forecast |
|---|---:|
| France v Paraguay | France 73.96% |
| Canada v Morocco | Morocco 61.97% |

These are bracket-level advancement forecasts. The full API/weather run for 4 July becomes available when the free-plan rolling window advances.

## Live Title Standings

| Rank | Team | Champion |
|---:|---|---:|
| 1 | France | 19.32% |
| 2 | Argentina | 13.01% |
| 3 | Brazil | 10.16% |
| 4 | Spain | 9.99% |
| 5 | England | 8.27% |
| 6 | Colombia | 6.78% |
| 7 | Morocco | 6.39% |
| 8 | Belgium | 5.66% |
| 9 | Mexico | 4.21% |
| 10 | Portugal | 3.67% |

Ten Round-of-32 matches are complete. France remains the favorite, while England and Belgium rise after qualifying.

## Integrity Notes

- AET/PEN validation now uses the provider's regulation full-time score.
- AET/PEN fixtures without a regulation score are withheld rather than guessed.
- Exact-score predictions remain hidden from public reports.
- Test suite: 24 passed.

## Files

- Accuracy data: `data/processed/model_accuracy_summary_2026-07-02.csv`
- Advancement audit: `data/processed/knockout_advancement_validation_2026-07-02.csv`
- July 1 validation: `outputs/matchday_validation_v210_report_2026-07-01.md`
- Today's predictions: `outputs/worldcup_matchday_v29_report_2026-07-02.md`
- Tomorrow's predictions: `outputs/worldcup_matchday_v29_report_2026-07-03.md`
- Live tournament simulation: `outputs/live_tournament_v213_report.md`
