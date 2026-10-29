# Dynamic-strength points simulation: offline prototype results (2026-10-25)

**Status: research prototype. Dynamic mode is not wired to the API or the interface and stays disabled in production.** Frozen club v1 coefficients are only read. All runs use a private copy of the database; nothing was written to the production store, `config/sync.json` has `live_enabled` false, and no network request was made.

Code: `app/seasonsim/dynamic.py` (prototype); tests `tests/test_dynamic.py` (7 pass); scripts `m4_dynamic_inputs.py`, `m4_dynamic_eval.py`, `m4_dynamic_ci.py`, `m4_dynamic_level3.py`. Outputs (git-ignored): `data/supervised/phase3/dyn_choice.json`, `dyn_eval.json`, `dyn_ci.json`, `dyn_level3.json`.

## 1. What was built
The static simulation draws every remaining match from probabilities computed once at the cut-off date. Real clubs change during the rest of the season: a team that wins early becomes stronger in the model's eyes (higher Elo), so its later matches get better odds.

The dynamic prototype adds that feedback **without touching the model**:
* Frozen v1 is a multinomial logistic regression on standardised features, three of which are Elo-based. Because it is linear, a change of `d` Elo points for a club changes that club's win/draw/loss log-odds by exactly `d` times a number computed from the stored coefficients and training standard deviations (read, never refitted).
* In each simulated season, matches are processed in date order. A match is drawn with the **same random numbers** as the static simulation; afterwards both clubs' Elo offsets are updated with v1's own Elo rule (K=20, home advantage 60, expected-score formula; goal-margin multiplier is 1 because no scores exist). Later fixtures of those clubs have their cut-off probabilities tilted by the current offsets.
* Parameters: `kappa` scales the Elo update (0 means no feedback), `tau` adds optional random weekly drift (Elo points), `tilt` scales sensitivity (1 = the frozen coefficients exactly). With kappa=0 and tau=0 the result equals the static points-only simulation exactly (tested).
* **Limits of the idea:** only the Elo channel moves; the model's form features (points per game over the last matches) would also react in reality; and no scores are used.

## 2. Protocol (fixed in the script's docstring before the evaluation seasons were run)
* **Development seasons** 2020-21 to 2023-24: the only data used to choose parameters (1,170 team-cut-offs).
* **Evaluation seasons** 2024-25 and 2025-26 (frozen v1 out-of-sample): run **once** with the chosen configuration (576 team-cut-offs: 5 leagues, cut-offs 1 November, 1 January, 1 March). No parameter was tuned on them.
* **Grid:** kappa in {0, 0.5, 1, 1.5, 2} times tau in {0, 6, 12}; rule: among configurations whose mean CRPS is not worse than static by more than 0.5%, take the one whose pooled 80% (10th to 90th percentile) coverage is closest to 0.80; configurations within 0.01 of the best count as tied and the simpler one wins. Chosen: **kappa 0.5, tau 6** (tau 12 reached 0.801 but is within the tie band, so the simpler option won).
* **Metrics** per team and cut-off: realised final points against the simulated distribution: 10-90, 25-75 and 5-95 interval coverage, CRPS (lower is better), standardised error, probability-integral transform (PIT). 2,000 simulations per cut-off, seed 2026.

## 3. Results
Evaluation seasons (out of sample), static versus chosen dynamic:

| | Static | Dynamic (kappa 0.5, tau 6) |
|---|---|---|
| 80% interval coverage (nominal 0.80) | 0.750 | 0.780 |
| 50% interval coverage (nominal 0.50) | 0.481 | 0.523 |
| 90% interval coverage (nominal 0.90) | 0.854 | 0.889 |
| CRPS (points) | 3.625 | 3.591 |
| Standardised error (ideal 1.0) | 1.203 | 1.100 |
| Mean 80% interval width (points) | 13.4 | 14.6 |
| Mean error of expected points | -0.08 | -0.08 |

* **Paired cluster-bootstrap (10 league-season blocks, 4,000 resamples):** CRPS improves by **0.034 points** (95% interval -0.052 to -0.018), better in 100% of resamples and in 9 of 10 blocks; 80% coverage rises by **2.95 points** (95% interval +1.7 to +4.3).
* **By cut-off:** the 1 November cut-off gains most (80% coverage 0.708 to 0.766; standardised error 1.314 to 1.163); 1 March least (0.786 to 0.797).
* **By league (80% coverage, static to dynamic):** Bundesliga 0.796 to 0.833, Premier League 0.658 to 0.700, La Liga 0.758 to 0.775, Ligue 1 0.759 to 0.796, Serie A 0.783 to 0.800. **The Premier League stays clearly under-covered.**
* **Development seasons** agree: coverage 0.757 to 0.791, CRPS 3.565 to 3.552.
* **The gap is narrowed, not closed:** coverage is still 2 points under nominal pooled and the standardised error 1.10 is above 1.0. The extreme deciles of the probability-integral transform are still a little over-full (0.123 and 0.113 versus 0.100 ideal; static 0.142 and 0.137), so the intervals remain somewhat too narrow.

### Sensitivity to the Elo-update assumptions (reporting only, never used for choice)
| Variation (from kappa 0.5, tau 6) | Development: coverage / CRPS | Evaluation: coverage / CRPS |
|---|---|---|
| chosen | 0.791 / 3.552 | 0.780 / 3.591 |
| K = 10 | 0.781 / 3.554 | 0.771 / 3.601 |
| K = 30 | 0.805 / 3.553 | 0.799 / 3.582 |
| home advantage 40 | 0.791 / 3.552 | 0.781 / 3.591 |
| home advantage 80 | 0.791 / 3.551 | 0.781 / 3.591 |
| tilt x0.5 | 0.774 / 3.557 | 0.769 / 3.606 |
| tilt x1.5 | 0.815 / 3.553 | 0.807 / 3.580 |
| kappa 2.0 | 0.869 / 3.594 | 0.870 / 3.583 |

* Coverage is **sensitive to how strongly Elo feeds back** (K, tilt, kappa move it by 2 to 9 points), but CRPS barely moves and stays better than static (3.625) for every variation on the evaluation seasons. Home advantage (40 to 80) does not matter.
* **Honest reading:** the amplitude of the feedback cannot be pinned down from this data. Larger amplitude gives nominal coverage but wider, not sharper, intervals; it improves calibration at the cost of sharpness.

## 4. Level-3 check: is the Elo shortcut a good approximation of the real model?
Test (`m4_dynamic_level3.py`, private copy, Bundesliga cut-off 2025-03-01): for six clubs, add one hypothetical completed match (the club wins 2-0 or loses 0-2 at home against its next opponent, dated the day before the cut-off), recompute the frozen v1 probabilities of the club's **later** fixtures **exactly** with the project's own feature code (so the form features react too), and compare the change with what the Elo shortcut predicts. 36 fixture comparisons.

| Measure | Value |
|---|---|
| Mean absolute change of a win/draw/loss probability, exact model | 0.0132 |
| Same, Elo shortcut | 0.0089 |
| Mean absolute difference between the two | 0.0062 |
| Correlation of the two sets of changes | 0.90 |
| Exact change divided by shortcut change (regression slope) | 1.36 |
| Share of the exact change explained by the shortcut | 76% |

**Reading:** the direction is right (correlation 0.90) but the shortcut captures only about three quarters of the real reaction: the form features add roughly a further third, so the shortcut at amplitude 1 **understates** the feedback. This is consistent with the sensitivity table (larger amplitude gives better-calibrated coverage) and is the reason the amplitude is reported as uncertain rather than tuned. It is a small test (six clubs, one date, one league, a single hypothetical result); it is not used to choose any parameter.

## 5. Limitations
* Only the Elo channel is modelled; the form channel (and squad changes, injuries, transfers) are not.
* No goal-margin multiplier in the Elo update (scores are not drawn); this slightly understates updates after big wins.
* The 5-league, 2-season evaluation has 10 league-season blocks; the confidence intervals above treat blocks as independent.
* Selection used a rule fixed beforehand, but the grid is coarse and the evaluation seasons are few. Different amplitudes remain plausible.
* The Premier League is under-covered in both modes; dynamic strength does not fix league-specific problems.
* Parameters were not fitted to maximise a score; they were chosen by a stated rule on development seasons only.

## 6. Recommendation (needs your decision)
Keep the static points-only simulator in production. If you want dynamic mode, the evidence supports a modest, labelled experimental option (kappa 0.5, tau 6) with wider intervals in the interface, and a forward test on the 2026-27 season as it unfolds; it does not support replacing the static mode. Nothing was enabled.
