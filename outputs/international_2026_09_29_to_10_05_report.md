# International Model Report: 29 September-5 October 2026

**Generated:** Tuesday, September 29, 2026 at 10:31 AM EDT

## Accuracy audit

- Frozen public record across the current international run: **4 hits from 5 completed published selections (80%)**.
- UEFA-only published record: **3/4 (75%)**; the Malta friendly lean also won 2-0.
- On the latest 23 completed matches, the raw largest-probability outcome was correct 47.8% of the time.
- Internal favorites on matches labelled Pass were correct only 45.5% of the time, supporting the strict publication gate.
- Probability metrics: log loss 1.009, multiclass Brier 0.600. Uniform baselines are 1.099 and 0.667 respectively.

## Model decision

Keep the core v2.7 ensemble and v2.11 gate unchanged for now. Five completed public picks are too few for a responsible retune. Shadow-test a rule that downgrades 60-70% favorites when calibrated draw risk is at least 27%, but require historical backtesting before promoting it; this would address the Iceland profile without post-hoc overfitting.

League-phase internationals behave more like a World Cup group stage than a knockout round: more rotation, more draws and less stable incentives. The strict gate—not raw pick accuracy—is the relevant product layer here.

## Ranked model leans

| Date/time ET | Match | Pick | 1 | X | 2 | Status | Weather |
|---|---|---|---:|---:|---:|---|---|
| 2026-09-29 14:45 | San Marino vs Albania | **Albania** (Model Lean) | 1.5% | 7.3% | 91.2% | Current; XI pending | 18.5C; low |
| 2026-09-29 14:45 | Spain vs Croatia | **Spain** (Model Lean) | 66.7% | 25.7% | 7.6% | Current; XI pending | 26.5C; watch |
| 2026-09-29 14:45 | Czechia vs England | **England** (Model Lean) | 9.4% | 25.1% | 65.5% | Current; XI pending | 17.5C; low |
| 2026-10-01 12:00 | Azerbaijan vs Liechtenstein | **Azerbaijan** (Model Lean) | 83.2% | 13.5% | 3.3% | Current; XI pending | 20.2C; low |
| 2026-10-01 14:45 | Malta vs Gibraltar | **Malta** (Model Lean) | 67.8% | 23.8% | 8.4% | Current; XI pending | 21.9C; low |
| 2026-10-02 10:00 | Kazakhstan vs Moldova | **Kazakhstan** (Model Lean) | 60.9% | 28.3% | 10.8% | Provisional after Tuesday results | 14.0C; low |
| 2026-10-03 12:00 | Belarus vs San Marino | **Belarus** (Model Lean) | 88.5% | 9.4% | 2.1% | Provisional; prior matchday pending | 21.0C; low |
| 2026-10-03 14:45 | Spain vs Czechia | **Spain** (Model Lean) | 78.2% | 17.8% | 3.9% | Provisional; prior matchday pending | 16.8C; low |
| 2026-10-03 14:45 | Switzerland vs Slovenia | **Switzerland** (Model Lean) | 66.5% | 26.0% | 7.5% | Provisional; prior matchday pending | 17.9C; low |
| 2026-10-04 12:00 | Malta vs Andorra | **Malta** (Model Lean) | 67.1% | 24.6% | 8.4% | Provisional; prior matchday pending | 24.7C; low |

## Full slate

| Date/time ET | Competition | Match | Internal read | 1 | X | 2 | Public decision |
|---|---|---|---|---:|---:|---:|---|
| 2026-09-29 12:00 | UEFA Nations League | Finland vs Belarus | Finland | 44.4% | 35.7% | 19.9% | Pass |
| 2026-09-29 12:00 | UEFA Nations League | Moldova vs Faroe Islands | Faroe Islands | 30.6% | 33.7% | 35.7% | Pass |
| 2026-09-29 14:45 | UEFA Nations League | Czechia vs England | England | 9.4% | 25.1% | 65.5% | Model Lean: England |
| 2026-09-29 14:45 | UEFA Nations League | Spain vs Croatia | Spain | 66.7% | 25.7% | 7.6% | Model Lean: Spain |
| 2026-09-29 14:45 | UEFA Nations League | Scotland vs Switzerland | Switzerland | 19.7% | 36.6% | 43.7% | Pass |
| 2026-09-29 14:45 | UEFA Nations League | Slovenia vs North Macedonia | Slovenia | 49.1% | 33.6% | 17.3% | Pass |
| 2026-09-29 14:45 | UEFA Nations League | San Marino vs Albania | Albania | 1.5% | 7.3% | 91.2% | Model Lean: Albania |
| 2026-09-29 14:45 | UEFA Nations League | Slovakia vs Kazakhstan | Slovakia | 61.2% | 29.1% | 9.7% | Pass |
| 2026-09-29 14:45 | UEFA Nations League | Bulgaria vs Estonia | Bulgaria | 52.2% | 32.6% | 15.2% | Pass |
| 2026-09-29 14:45 | UEFA Nations League | Luxembourg vs Iceland | Iceland | 25.8% | 35.9% | 38.3% | Pass |
| 2026-09-29 12:00 | International Friendly | Russia vs Iran | Draw | 34.2% | 40.8% | 24.9% | Pass |
| 2026-09-29 20:00 | International Friendly | United States vs Chile | United States | 47.4% | 37.3% | 15.3% | Pass |
| 2026-09-29 21:00 | International Friendly | Mexico vs Peru | Mexico | 57.0% | 33.2% | 9.8% | Pass |
| 2026-09-30 12:00 | International Friendly | Lithuania vs Andorra | Lithuania | 61.4% | 29.6% | 9.0% | Pass |
| 2026-10-01 12:00 | UEFA Nations League | Azerbaijan vs Liechtenstein | Azerbaijan | 83.2% | 13.5% | 3.3% | Model Lean: Azerbaijan |
| 2026-10-01 14:45 | UEFA Nations League | Germany vs Serbia | Germany | 60.1% | 29.9% | 10.0% | Pass |
| 2026-10-01 14:45 | UEFA Nations League | Greece vs Netherlands | Netherlands | 18.2% | 37.4% | 44.4% | Pass |
| 2026-10-01 14:45 | UEFA Nations League | Denmark vs Portugal | Portugal | 22.2% | 36.8% | 41.0% | Pass |
| 2026-10-01 14:45 | UEFA Nations League | Wales vs Norway | Norway | 15.4% | 33.7% | 50.9% | Pass |
| 2026-10-01 14:45 | UEFA Nations League | Israel vs Kosovo | Kosovo | 24.0% | 32.0% | 44.1% | Pass |
| 2026-10-01 14:45 | UEFA Nations League | Republic of Ireland vs Austria | Austria | 23.9% | 35.4% | 40.7% | Pass |
| 2026-10-01 14:45 | UEFA Nations League | Malta vs Gibraltar | Malta | 67.8% | 23.8% | 8.4% | Model Lean: Malta |
| 2026-10-02 10:00 | UEFA Nations League | Kazakhstan vs Moldova | Kazakhstan | 60.9% | 28.3% | 10.8% | Model Lean: Kazakhstan |
| 2026-10-02 12:00 | UEFA Nations League | Cyprus vs Armenia | Cyprus | 35.2% | 34.4% | 30.4% | Pass |
| 2026-10-02 12:00 | UEFA Nations League | Latvia vs Montenegro | Montenegro | 24.3% | 32.7% | 43.0% | Pass |
| 2026-10-02 14:45 | UEFA Nations League | Belgium vs Türkiye | Belgium | 52.0% | 33.2% | 14.7% | Pass |
| 2026-10-02 14:45 | UEFA Nations League | France vs Italy | France | 58.0% | 31.6% | 10.4% | Pass |
| 2026-10-02 14:45 | UEFA Nations League | Hungary vs Georgia | Hungary | 44.9% | 36.1% | 19.0% | Pass |
| 2026-10-02 14:45 | UEFA Nations League | Ukraine vs Northern Ireland | Ukraine | 44.8% | 37.2% | 18.0% | Pass |
| 2026-10-02 14:45 | UEFA Nations League | Bosnia & Herzegovina vs Sweden | Sweden | 24.5% | 37.7% | 37.8% | Pass |
| 2026-10-02 14:45 | UEFA Nations League | Poland vs Romania | Poland | 47.1% | 35.6% | 17.2% | Pass |
| 2026-10-02 14:45 | UEFA Nations League | Faroe Islands vs Slovakia | Slovakia | 11.9% | 30.1% | 58.0% | Pass |
| 2026-10-03 09:00 | UEFA Nations League | Finland vs Albania | Draw | 34.3% | 34.4% | 31.3% | Pass |
| 2026-10-03 12:00 | UEFA Nations League | Belarus vs San Marino | Belarus | 88.5% | 9.4% | 2.1% | Model Lean: Belarus |
| 2026-10-03 12:00 | UEFA Nations League | Croatia vs England | England | 17.0% | 36.9% | 46.1% | Pass |
| 2026-10-03 12:00 | UEFA Nations League | Estonia vs Luxembourg | Draw | 30.5% | 35.4% | 34.0% | Pass |
| 2026-10-03 12:00 | UEFA Nations League | Iceland vs Bulgaria | Iceland | 49.6% | 34.8% | 15.7% | Pass |
| 2026-10-03 14:45 | UEFA Nations League | North Macedonia vs Scotland | Scotland | 20.0% | 33.7% | 46.4% | Pass |
| 2026-10-03 14:45 | UEFA Nations League | Spain vs Czechia | Spain | 78.2% | 17.8% | 3.9% | Model Lean: Spain |
| 2026-10-03 14:45 | UEFA Nations League | Switzerland vs Slovenia | Switzerland | 66.5% | 26.0% | 7.5% | Model Lean: Switzerland |
| 2026-10-04 09:00 | UEFA Nations League | Azerbaijan vs Lithuania | Azerbaijan | 45.4% | 34.3% | 20.3% | Pass |
| 2026-10-04 12:00 | UEFA Nations League | Kosovo vs Austria | Austria | 19.6% | 34.7% | 45.8% | Pass |
| 2026-10-04 12:00 | UEFA Nations League | Malta vs Andorra | Malta | 67.1% | 24.6% | 8.4% | Model Lean: Malta |
| 2026-10-04 14:45 | UEFA Nations League | Greece vs Germany | Germany | 24.3% | 35.9% | 39.8% | Pass |
| 2026-10-04 14:45 | UEFA Nations League | Netherlands vs Serbia | Netherlands | 64.2% | 27.5% | 8.4% | Pass |
| 2026-10-04 14:45 | UEFA Nations League | Portugal vs Norway | Portugal | 41.4% | 36.8% | 21.8% | Pass |
| 2026-10-04 14:45 | UEFA Nations League | Republic of Ireland vs Israel | Republic of Ireland | 43.3% | 38.7% | 18.0% | Pass |
| 2026-10-04 14:45 | UEFA Nations League | Wales vs Denmark | Denmark | 19.4% | 35.2% | 45.3% | Pass |
| 2026-10-05 12:00 | UEFA Nations League | Cyprus vs Latvia | Cyprus | 44.4% | 34.8% | 20.8% | Pass |
| 2026-10-05 14:45 | UEFA Nations League | France vs Belgium | France | 46.9% | 35.3% | 17.8% | Pass |
| 2026-10-05 14:45 | UEFA Nations League | Italy vs Türkiye | Italy | 44.7% | 34.5% | 20.8% | Pass |
| 2026-10-05 14:45 | UEFA Nations League | Northern Ireland vs Georgia | Draw | 37.4% | 38.3% | 24.2% | Pass |
| 2026-10-05 14:45 | UEFA Nations League | Ukraine vs Hungary | Draw | 36.4% | 38.2% | 25.5% | Pass |
| 2026-10-05 14:45 | UEFA Nations League | Bosnia & Herzegovina vs Poland | Draw | 31.9% | 39.9% | 28.1% | Pass |
| 2026-10-05 14:45 | UEFA Nations League | Romania vs Sweden | Sweden | 23.0% | 35.1% | 41.9% | Pass |
| 2026-10-05 14:45 | UEFA Nations League | Montenegro vs Armenia | Montenegro | 49.6% | 34.0% | 16.4% | Pass |

## Operating rules

- Probabilities are 90-minute 1/X/2 only.
- Squad availability is checked as a confidence gate; player absences do not receive invented subjective weights.
- Starting XIs should be checked 60-75 minutes before kickoff. A lean may be downgraded, never upgraded merely to increase the number of picks.
- Saturday-through-Monday probabilities are early baselines because those teams have another matchday first; rerun after each intervening round.
- Weather is a small tempo/risk modifier. Exact scores remain hidden.
- Do not treat several individually plausible selections as a guaranteed parlay; joint hit probability falls quickly.

## Data freshness and sources

- Team strength rebuilt from 49,603 senior results through 2026-09-28, including 56 recent official/provider overlays.
- [UEFA official Nations League fixtures](https://www.uefa.com/uefanationsleague/news/02a2-1fea18abbcbc-456e846509e7-1000--2026-27-uefa-nations-league-all-the-league-phase-fixtures/)
- API-Football cache for current results and near-term fixture status.
- [Open-Meteo](https://open-meteo.com/) for venue forecasts.
