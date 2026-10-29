# World Cup Model Report - 3 July 2026

Updated: 2026-07-03 01:01 ET

## July 2 Validation

| Fixture | Best 90-minute read | Confidence gate | Result | Qualifier | Evaluation |
|---|---|---|---|---|---|
| Spain v Austria | Spain win | Model Lean | Spain won 3-0 | Spain | Correct |
| Portugal v Croatia | Portugal win | Pass | Portugal won 2-1 | Portugal | Correct internal read |
| Switzerland v Algeria | Switzerland win | Pass | Switzerland won 2-0 | Switzerland | Correct internal read |

- Raw best reads: 3/3 correct.
- Model Leans: 1/1 correct.
- Knockout qualification calls: 3/3 correct.
- Public-pick accuracy: 100% on the one published pick.

## Updated Accuracy

| Scope | Prediction set | Correct | Matches | Accuracy |
|---|---|---:|---:|---:|
| Entire genuine sample | Raw best read | 43 | 64 | 67.19% |
| Entire genuine sample | Model Lean | 23 | 31 | 74.19% |
| Third group matches onward | Raw best read | 26 | 36 | 72.22% |
| Third group matches onward | Model Lean | 16 | 19 | 84.21% |
| Knockout stage | Qualification calls | 11 | 12 | 91.67% |

The third-match cutoff remains 24 June at 15:00 ET. All figures exclude post-kickoff backfills.

## Today - 3 July

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Context |
|---|---|---|---|---|---|
| Australia v Egypt | Pass | Australia win | 39.78 / 35.29 / 24.94 | Egypt 52.08% | 33.9C and hot; AT&T roof status and lineups pending |
| Argentina v Cape Verde | Strong Pick | Argentina win | 84.30 / 11.89 / 3.80 | Argentina 83.55% | 30.6C with meaningful thunderstorm risk; lineups pending |
| Colombia v Ghana | Model Lean | Colombia win | 80.01 / 16.23 / 3.76 | Colombia 82.41% | 32.2C, warm and dry at kickoff; lineups pending |

Australia-Egypt remains the unusual fixture: Australia is the likeliest regulation winner, while Egypt has a tiny full-match advancement edge after extra time and penalties. The correct public treatment is Pass.

## Tomorrow - 4 July

| Fixture | Confidence gate | Best 90-minute read | Regulation 1/X/2 | Full-match advancement | Context |
|---|---|---|---|---|---|
| Canada v Morocco | Pass | Morocco win | 20.66 / 35.38 / 43.96 | Morocco 62.25% | 32-33C and humid outdoors; NRG roof status and lineups pending |
| Paraguay v France | Model Lean | France win | 10.76 / 27.18 / 62.06 | France 74.71% | 38-39C extreme heat with storm risk; lineups pending |

## Provisional - 5 July

The free API date window currently stops at 4 July. These qualification forecasts use the fixed bracket and current 50,000-path tournament simulation.

| Fixture | Qualification forecast |
|---|---:|
| Brazil v Norway | Brazil 60.35% |
| Mexico v England | England 55.45% |

The full fixture, weather, and lineup-aware July 5 run becomes available on 4 July.

## Live Title Standings

| Rank | Team | Champion |
|---:|---|---:|
| 1 | France | 18.88% |
| 2 | Spain | 13.06% |
| 3 | Argentina | 11.91% |
| 4 | Brazil | 10.10% |
| 5 | England | 8.12% |
| 6 | Morocco | 6.02% |
| 7 | Colombia | 6.02% |
| 8 | Portugal | 5.20% |
| 9 | Belgium | 5.02% |
| 10 | Mexico | 4.11% |

Thirteen Round-of-32 matches are complete. Portugal rises to eighth after qualifying, while France remains the title favorite.

## Data Status

- Today's fixtures and kickoff weather were refreshed at 11:21 ET.
- U.S. venue weather now uses the National Weather Service first and Open-Meteo as fallback.
- Tomorrow's full API fixture feed is available and archived.
- July 5 is provisional because it is outside today's free-plan date window.
- No confirmed starting lineups were available at snapshot time.
- Exact-score predictions remain hidden from public reports.

## Files

- July 2 validation: `outputs/matchday_validation_v210_report_2026-07-02.md`
- Today's predictions: `outputs/worldcup_matchday_v29_report_2026-07-03.md`
- Tomorrow's predictions: `outputs/worldcup_matchday_v29_report_2026-07-04.md`
- Live tournament simulation: `outputs/live_tournament_v213_report.md`
- Accuracy data: `data/processed/model_accuracy_summary_2026-07-03.csv`
- Advancement audit: `data/processed/knockout_advancement_validation_2026-07-03.csv`
