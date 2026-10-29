# 16 Player-performance prediction readiness (generated 2026-10-20 22:32; no model trained)

## Targets that can be built from observed data
Next-observed-match goals, assists, shots, shots on target, xG, passes, tackles, interceptions and minutes (`TARGET_*` columns of the recent-form file). Features come only from strictly earlier matches.

## Data reality
* Rows with >= 5 prior observed matches (male): 51,138; of which previous match within 21 days: 44,142.
* Rows after 2018-12-31 with >= 5 priors: 36,448; after 2022-12-31: 22,695. Competition-seasons contributing: 66. Rows by year are very uneven ({'2014': 638, '2015': 13333, '2016': 21496, '2017': 915, '2018': 2497, '2019': 3500, '2020': 2874, '2021': 3770, '2022': 3609, '2023': 9653, '2024': 12278, '2025': 764}): two seasons (2015, 2016) contain 34,829 rows.
* Target properties: goals mean 0.0977, 91.3% zeros (sparse count -> Poisson-type models, not Linear Regression); minutes mean 72.7.

## Blocking issues
1. Coverage is a patchwork of selected competition-seasons; the "next observed match" is often weeks/months later or in a different competition.
2. No lineup, injury, suspension, opposition-strength or fixture-level context; minutes (the main driver) cannot be predicted without squad/lineup information.
3. A chronological split leaves almost no player with both history and held-out matches inside the same competition-season; a random split would leak player identity.
4. No transfer / team-change features; xA missing; women's and men's data mixed.
5. Minutes are derived (not independently verified); openfootball minutes are estimates and cannot be targets.

## Model families
| Model | Feasibility |
|---|---|
| Linear / Ridge / Lasso | Mechanically possible, statistically poor for zero-inflated counts; usable only as a baseline for minutes or xG per 90 on pooled data |
| Poisson / negative-binomial GLM, gradient boosting | More appropriate once the coverage issue is solved |
| Any "player rating" model | **Not possible**: no verified performance rating exists; do not invent one |

## Decision: BLOCKED for player-performance prediction. An exploratory baseline (Ridge on per-90 xG or minutes, split by competition-season) may be run only after explicit approval and must be labelled exploratory.
