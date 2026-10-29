# Ad Hoc v2.7 Slate: June 10 Friendlies

This run uses the v2.7 calibrated ensemble for 1X2 probabilities and the Poisson/xG layer for scoreline estimates.

## Fixture Check

- API-Football lists these senior men's fixtures on Wednesday, June 10, 2026 ET.
- Confirmed lineups were not available at run time because all three matches were still `NS` / not started.
- Portugal-Nigeria uses Leiria weather and Portugal venue edge.
- England-Costa Rica uses Orlando/Inter&Co Stadium weather from public venue reports.
- Bolivia-Algeria had no provider venue coordinates, so weather is neutral.

## Predictions

| Match | v2.7 public | Internal lean | 1 | X | 2 | Predicted score | xG | Weather |
|---|---|---|---:|---:|---:|---|---|---|
| Portugal vs Nigeria | pass | team1_win | 56.66% | 32.00% | 11.34% | 1-0 | 1.319-1.002 | 18.3C |
| England vs Costa Rica | pass | team1_win | 67.86% | 26.26% | 5.88% | 1-0 | 1.54-0.809 | 24.9C |
| Bolivia vs Algeria | pass | team2_win | 18.66% | 35.66% | 45.69% | 0-1 | 1.054-1.255 | neutral |

## Scoreline Caveat

The predicted score is the highest-probability scoreline consistent with the v2.7 internal lean. The raw modal exact score is also saved in the CSV because exact scores are noisy and often cluster around 1-0, 1-1, or 2-0.

## Top Exact Scorelines

- Portugal vs Nigeria: 1-1 12.97%; 1-0 12.94%; 0-1 9.83%; 0-0 9.81%; 2-1 8.56%
- England vs Costa Rica: 1-0 14.69%; 1-1 11.89%; 2-0 11.32%; 0-0 9.54%; 2-1 9.16%
- Bolivia vs Algeria: 1-1 13.14%; 0-1 12.47%; 1-0 10.47%; 0-0 9.94%; 1-2 8.25%

## API Budget

- Used today: 3/100.
- Remaining before local stop: 82.
