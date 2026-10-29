# LAFC vs Sporting Kansas City

Pre-kickoff snapshot: 25 July 2026 at 4:44 PM ET  
Kickoff: 10:30 PM ET / 7:30 PM PT, BMO Stadium

## Model Read

- Best 90-minute read: **Los Angeles FC win**
- Confidence gate: **Strong Pick**
- Confidence: **High**
- Model 1/X/2: **LAFC 74.82% / Draw 16.94% / Sporting KC 8.24%**
- Market no-vig check: **LAFC 74.74% / Draw 14.95% / Sporting KC 10.31%**

The calibrated ensemble and logistic safety model both independently clear the LAFC home-win gate.

## Market Odds

- Median decimal odds: **LAFC 1.255 / Draw 6.275 / Sporting KC 9.10**
- Approximate American odds: **LAFC -392 / Draw +528 / Sporting KC +810**
- Twelve API-Football bookmakers were available at snapshot time.

## Inputs

- Club Elo: LAFC 1651, Sporting KC 1430.
- Home-field adjustment: 55 Elo points.
- Last-five points per game: LAFC 1.80, Sporting KC 1.80.
- Season context: LAFC 9-3-5 with +12 goal difference; Sporting KC 4-2-10 with -22.
- Matchup context: LAFC has won four straight meetings and is unbeaten in the last ten across all competitions.
- Weather: 26.1 C, 0% precipitation, 8.1 km/h wind.
- Weather tempo factor: 0.970; warm conditions slightly lower tempo.
- Confirmed lineups: not available at snapshot time.
- LAFC availability: Igor Jesus and S. Palencia missing; T. Tillman questionable.
- Sporting KC availability: T. Calheira, Diego Borges, and J. Reynolds missing.

## Model Composition

- Gradient boosting: 50%
- Elo formula: 30%
- Logistic regression: 20%
- Poisson-lite: 0% in the 1/X/2 ensemble

## Limitation

The saved v2.7 ensemble was trained and calibrated on international matches. This run uses MLS club Elo and form inputs, but remains an experimental cross-domain application until an MLS-specific model is trained. Market odds are used only as an independent diagnostic check.
