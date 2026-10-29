# Joachim Klement 2026 World Cup Prediction Notes

## What is public

Joachim Klement's 2026 note identifies the Netherlands as the predicted World Cup winner. The public note gives the conceptual model, group-stage top-two probabilities, likely best third-place qualifiers, and the predicted knockout path.

The full model is not public. Klement describes it as a proprietary econometric model, so the exact dataset, coefficients, random seed, simulation count, and match-probability transformation are not available from the public sources I found.

## Variables Klement says the model uses

- GDP per capita: proxy for national resources, football infrastructure, academies, and player development. Klement says the effect is not simply "richer is always better"; it eventually declines.
- Population size: proxy for talent pool. The underlying academic work finds this matters especially where football is culturally mainstream.
- Temperature: climate proxy. Klement cites an ideal average annual temperature of about 14 C.
- Host-country effect: home crowd and tournament location advantage, though he argues it may be weaker in 2026 because the tournament is split across three countries and a large continent.
- FIFA ranking points: Klement's add-on for current squad strength.
- Luck/randomness: he says the variables explain only part of World Cup success, so the model includes chance when deciding match outcomes.

## 2026 forecast output in this bundle

- `klement_2026_group_top2_probabilities.csv`: the published top-two probabilities from Figure 1, plus the predicted group finish/advancement path inferred from the note.
- `klement_2026_knockout_path.csv`: the predicted knockout bracket from round of 32 to final.
- `world_cup_prediction_public_data_sources.csv`: public data sources you can use to build a Klement-style model.

## Reconstructing a similar model

A practical clone should be treated as "Klement-inspired", not Klement's actual model:

1. Build a country-season table for every World Cup participant.
2. Pull GDP per capita (`NY.GDP.PCAP.CD`) and population (`SP.POP.TOTL`) from World Bank WDI.
3. Pull mean annual temperature from the World Bank Climate Change Knowledge Portal (`tas`, annual climatology).
4. Pull FIFA ranking points from the last official ranking before the tournament.
5. Add host/co-host flags.
6. Fit a historical model on World Cup outcomes or team ratings. Include nonlinear terms such as GDP per capita squared and temperature distance from 14 C.
7. Convert team strength to match probabilities.
8. Simulate the tournament many times, including penalties/extra time or a generic randomness term for knockouts.

## Caution

Klement repeatedly warns readers not to treat the forecast as betting advice. Correctly picking three winners in a row is impressive, but it is also a tiny sample. In knockout football, injuries, refereeing, penalties, and one bad day can dominate the model signal.
