# Design proposal: a future dynamic-strength simulation mode (NOT implemented)

Date: 2026-10-25. Design only. No code, no frozen model, no production data and no setting was changed. Decision D3 keeps the first version static; this document describes what a later, separately approved, experimental mode could look like, how it would be validated, and what it would and would not fix.

## 1. The question
Today every remaining fixture keeps the probability it had at the data cut-off ("static strengths"): the outcome of a simulated match changes the table but never a club's strength. Real strengths move during a season (form, injuries, transfers, luck revealed as quality). The diagnostic in [PHASE3_VALIDATION_REVIEW.md](PHASE3_VALIDATION_REVIEW.md) part C found the simulated points intervals about 20% too narrow in spread (coverage 74.7% instead of 80%), most at 1 November (spread ratio 1.32) and nearly absent by 1 March (1.07), the signature of unmodelled strength change, with the expected points themselves unbiased (slope 0.96). A dynamic mode should widen the spread in the right places **without touching any frozen model**.

## 2. Hard constraints
* No retraining, no refitting and no edit of the frozen club v1 (primary) or v2-r1 (experimental) artifacts; they are read as they are, and their sha256 is recorded with every run as now.
* No new data source; no results beyond the cut-off; no leakage.
* Simulations remain seeded, reproducible and started only by the user.
* Must reduce to the static result exactly when the dynamic parameters are set to zero.

## 3. How a simulated result could change later probabilities without changing the model

The frozen v1 is a linear multinomial model on 25 standardised features. The strength-related ones are `home_elo`, `away_elo` and `elo_diff` (the project's v1 Elo state: start 1500, K = 20, home advantage 60, with a goal-margin multiplier; read from `feature_contract.py`; the separate Elo used by v2-r1 has K = 30 and home advantage 50). Because the model is linear in those features, **the effect of a change in a club's Elo on that club's later match probabilities can be written with the model's own, read-only coefficients**: dividing each coefficient by its stored training standard deviation gives the change in log-odds per Elo point. For example, adding 50 Elo points to the home club moves the log-odds by about **+0.132 (home win), −0.007 (draw), −0.125 (away win)**; the corresponding change for a stronger away club follows from `away_elo` and `elo_diff` in the same way. Nothing is fitted: the coefficients are read, not changed.

### Level 1: random strength drift (no feedback from simulated results)
Give each club an Elo-equivalent offset `u` that evolves as a random walk with weekly standard deviation τ. A club's later match probabilities are the cut-off probabilities tilted by the log-odds shift of its offset difference with the opponent. This widens the points distribution exactly where the horizon is long. It has one parameter, τ, which would be set from historical drift measured on **data not used for judging the simulator** (section 6). Cheap and easy to explain, but results do not feed back into strength.

### Level 2: Elo-in-the-loop (feedback from simulated results; recommended)
Process the remaining fixtures in date order (matches on the same day are updated together). In each simulation, after a match is drawn, update the two clubs' offsets with the frozen v1 Elo rule (K = 20, home advantage 60); the rule's goal-margin multiplier (1.0 for a one-goal margin, 1.5 for two, then (11 + margin) / 8) needs scores, so it is set to 1.0 until a scoreline method is approved, which slightly under-states the update after big wins, then tilt later probabilities of those clubs by the frozen coefficients. Implemented as vector operations over all simulations at once (arrays of shape simulations × clubs), this costs roughly the same as the static run (a few seconds for 10,000 simulations), because the expensive model features are computed **once** at the cut-off and only the tilt is recomputed. Properties: a club that wins early becomes more likely to win later (momentum), which adds the right kind of correlation, and no new fitted parameter is needed apart from an optional amplitude factor κ (default 1) to check that K = 20 is the right strength of reaction.

### Level 3: exact re-featurisation inside the simulation (not recommended)
Re-run the project's state machines after each simulated match to recompute all 25 features for later fixtures. It is exact, but recomputing features costs about 40 ms per fixture, i.e. about 12 seconds per simulated season, so 10,000 simulations would take over a day. It is useful only as a **small test** (a few hundred simulations) to measure the error of the Level 2 approximation.

## 4. What it would change, conceptually

| | Static (now) | Level 1: drift | Level 2: Elo-in-the-loop | Level 3: exact |
|---|---|---|---|---|
| Strength during the season | fixed at cut-off | random walk, no feedback | updated by simulated results | updated by simulated results, all features |
| Spread of final points | too narrow (about 75% coverage) | wider, tuned by τ | wider, with momentum; no tuned parameter except optional κ | wider |
| Correlation between a club's results | none beyond the fixed probabilities | through the shared offset | through form and Elo | through all features |
| Uses frozen model | read only | read only (coefficients) | read only (coefficients) | read only |
| Cost per 10,000 simulations | about 1-10 s | about the same | about 5-30 s | over a day |
| Explainability | simplest | simple | simple ("winners get stronger") | complex |
| Main risk | under-dispersion | τ chosen on poor data | approximation of form features; K may not suit the strength of reaction | cost |

What it would **not** fix: a model that is wrong about a particular club at the cut-off (misspecification persists), the scoreline question (final-position probabilities remain blocked by that), missing results, or the points-tie ambiguity. Form features (points per game over the last 5 and 10 matches) also move after a match; the tilt covers only the Elo channel, so Level 2 probably still under-states the feedback somewhat, which the validation would reveal.

## 5. Back-of-envelope scale (from the diagnostic and the frozen coefficients; untested)
A 50-Elo difference changes a club's expected points per match by about 0.14, so a constant strength offset `u` changes its expected final points by about 0.077 u over 27 remaining matches. The variance missing from the intervals (14.5 points squared on average) would need a standard deviation of **about 50 Elo points** in strength change over the rest of the season; the oracle drift measured directly (4.6 points squared) corresponds to about 28 Elo points. Both are within the range of ordinary season-long changes in an Elo system with K = 20, so the idea is plausible; it is not a result.

## 6. Validation plan (to be approved before building)
* **Scheme:** a locked, once-only backtest in the style of the points-interval backtest, comparing static, Level 1 and Level 2 on the out-of-sample seasons 2024-25 and 2025-26, three cut-offs per season, five leagues (points only, so no scoreline method is needed), cluster-bootstrap intervals by team-season.
* **No tuning on the evaluation seasons.** Any τ or κ is chosen on **independent data**: the roughly 11,000 matches of the other 47 European first divisions dated 2024-07-01 to 2026-09-20 (never examined for these questions), with a predeclared grid.
* **Criteria (predeclared when approved):** coverage of the 10-90% points interval pooled over the five leagues within 0.77-0.83 and its cluster interval containing 0.80; mean continuous ranked probability score no worse than static; the spread ratio of the standardised error between 0.9 and 1.1 at each cut-off; expected points unbiased (slope within 0.9-1.1); no league worse than static by more than a stated margin.
* **Tests:** with τ = 0 and K feedback off the output equals the static output exactly; determinism for a fixed seed; the club-level sum of points is conserved; monotonicity; zero remaining fixtures; a leakage test (scrambling results dated after the cut-off changes nothing); frozen-artifact hashes unchanged; Level 2 versus Level 3 on a small sample (approximation error reported).
* **If it fails** (coverage not improved, or worse log score): the static mode stays and the finding is reported.

## 7. Where it would fit in the product
A third, separately labelled, "Experimental — dynamic strengths" option in the points-only mode only (positions stay blocked by the scoreline decision), shown beside the static run, never replacing it, with the parameters, the validation result and the limitations in the assumptions panel, and saved only when the user presses Run (`simulation_runs`, `mode = "points_dynamic"`; no schema change).

## 8. Roadmap and what needs your approval
1. Approve the design direction and the validation plan (including the independent calibration data and the criteria).
2. Build Level 2 offline with tests (no UI), reproduce static exactly at zero.
3. Run the locked backtest once; report in full.
4. Only if it passes, add the experimental option to the points-only mode.
Level 1 is the fallback if Level 2's validation fails but drift alone is enough. None of this is started.
