# New York Red Bulls vs Charlotte FC

Pre-kickoff snapshot: 25 July 2026 at 12:28 PM ET  
Kickoff: 6:30 PM ET, Sports Illustrated Stadium

## Model Read

- Best 90-minute read: **New York Red Bulls win**
- Confidence gate: **Pass**
- Model 1/X/2: **New York 43.60% / Draw 27.51% / Charlotte 28.89%**
- Market no-vig check: **New York 42.87% / Draw 24.29% / Charlotte 32.84%**

The model leans New York, but the edge is not large enough for a Strong Pick or Model Lean under the calibrated publication rules.

## Inputs

- Club Elo: New York 1533, Charlotte 1551.
- Home adjustment: 55 Elo points, turning the matchup-adjusted Elo edge toward New York.
- Last-five points per game: New York 2.00, Charlotte 1.60.
- Table context: both clubs have 22 points after 16 MLS matches.
- Weather: 26.7 C, 0% precipitation, 14.5 km/h wind.
- Weather tempo factor: 0.966; warm conditions slightly lower tempo and raise draw risk.
- Confirmed lineups: not yet available.
- API-Football availability flags: A. Marcucci missing and R. Mosquera questionable for New York; A. John missing and A. Saint-Maximin questionable for Charlotte.

## Model Composition

- Gradient boosting: 50%
- Elo formula: 30%
- Logistic regression: 20%
- Poisson-lite: 0% in the 1/X/2 ensemble

## Limitation

The saved v2.7 ensemble was trained and calibrated on international matches. This run uses verified MLS club Elo and form inputs, but it is an experimental cross-domain application, not yet an MLS-trained production model. The market comparison is a diagnostic check and is not blended into the model probabilities.
