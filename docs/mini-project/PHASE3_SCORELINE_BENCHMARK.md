# Phase 3, M2: scoreline-method benchmark (the approval boundary)

Date: 2026-10-25. **Result: no candidate method met the predeclared acceptance criteria, so final league-position predictions stay disabled** (`config/season_sim.json`: `scoreline_method: null`). This document reports the failures, the limits of the test, and the options that need your decision. Nothing was tuned on the evaluation matches, no result below was adjusted, and no frozen model, training file, official prospective-evaluation file or sync setting was touched.

Reproduce (offline, no network): `app/seasonsim/m2_data.py` (build the match table), `m2_benchmark.py` (distribution criteria), `backtest.py` (end-to-end), `m2_rule_power.py` (noise of the rule), `m2_s4_tuning.py` (validation-only tuning of a proposed fourth candidate). Outputs are in `data/supervised/phase3/` (git-ignored).

## 1. What was tested

* **Data.** 14,590 completed matches of the five leagues, 2018-19 to 2026-10-24. Every match is featurised **only from results strictly before its own date** (the project's replay), exactly as a prospective fixture. Probabilities are the frozen club v1 model; expected goals come from the v2 feature generator.
* **Integrity check on the pipeline.** The recomputed v1 probabilities for the 5,504 matches that the frozen v1 evaluation also stored equal the stored predictions to 3.3e-16 (maximum difference), so the time-safe replay reproduces the frozen model exactly.
* **Fit window / evaluation window.** Scoreline parameters (only method S3 has any) are fitted on 10,781 matches before 2024-07-01. Evaluation uses the 3,809 matches from 2024-07-01 on (club v1's own test season and forward holdout, so out-of-sample for v1).
* **Methods (as specified in PHASE3_PLAN.md section 4):** S1 conditional Poisson, S2 outcome-matched Poisson (all 3,809 evaluation fixtures converged, 0 fallbacks), S3 empirical conditional bootstrap.

## 2. Predeclared criteria (written before any result was seen)

Per league, on the evaluation matches: **C1** mean goal margin in home wins and in away wins within ±0.10 goals of the actual mean; **C2** share of one-goal margins among home wins and among away wins within ±0.05 of the actual share. A method is acceptable only if C1 and C2 hold in **every one of the five leagues**, **and** (M2b) its simulated season goal differences cover the realised ones at 70-90% for the 10-90% interval.

## 3. M2a result: goal distributions and winning margins (deviation of the method from the actual value; red = outside the tolerance)

Actual values (n = evaluation matches): Premier League 820: margin in home wins 1.844, in away wins 1.742, one-goal share 0.465 / 0.542. La Liga 849: 1.761, 1.579, 0.553 / 0.617. Bundesliga 673: 2.117, 1.827, 0.420 / 0.498. Serie A 810: 1.717, 1.667, 0.570 / 0.582. Ligue 1 657: 1.884, 1.849, 0.464 / 0.478.

| League | Method | Margin, home wins | Margin, away wins | 1-goal share, home | 1-goal share, away | C1 | C2 | Pass |
|---|---|---|---|---|---|---|---|---|
| Premier League | S1 | **+0.156** | -0.008 | -0.024 | -0.006 | fail | ok | **no** |
| | S2 | +0.097 | +0.043 | -0.009 | -0.028 | ok | ok | yes |
| | S3 | **+0.113** | +0.092 | -0.019 | -0.046 | fail | ok | **no** |
| La Liga | S1 | **+0.142** | +0.088 | **-0.081** | **-0.054** | fail | fail | **no** |
| | S2 | **+0.126** | **+0.126** | **-0.078** | **-0.070** | fail | fail | **no** |
| | S3 | -0.003 | +0.033 | -0.023 | -0.034 | ok | ok | yes |
| Bundesliga | S1 | -0.036 | +0.007 | -0.000 | +0.003 | ok | ok | yes |
| | S2 | **-0.135** | -0.010 | +0.026 | +0.008 | fail | ok | **no** |
| | S3 | +0.085 | **+0.101** | -0.039 | -0.038 | fail (by 0.001) | ok | **no** |
| Serie A | S1 | +0.071 | -0.009 | **-0.060** | -0.018 | ok | fail | **no** |
| | S2 | **+0.163** | +0.038 | **-0.094** | -0.037 | fail | fail | **no** |
| | S3 | **+0.110** | +0.034 | **-0.065** | -0.030 | fail | fail | **no** |
| Ligue 1 | S1 | +0.090 | -0.088 | -0.016 | +0.046 | ok | ok | yes |
| | S2 | +0.025 | **-0.107** | +0.003 | **+0.054** | fail | fail | **no** |
| | S3 | +0.009 | **-0.163** | +0.026 | **+0.080** | fail | fail | **no** |

**Verdict under the predeclared rule: S1 fails (passes Bundesliga and Ligue 1 only), S2 fails (passes Premier League only), S3 fails (passes La Liga only). No method passes in every league.** For the two leagues in the approved initial scope: S1 passes the Bundesliga but fails La Liga; S3 passes La Liga but misses the Bundesliga by 0.001 goal; S2 passes neither. No single method passes both.

Pattern: for most leagues the models' margins are slightly **too large** and one-goal wins too rare, i.e. the team-specific expected goals spread the matches slightly too far apart. This is the opposite of a first league-average-goals check that I had run while planning (which suggested margins too small); the team-specific expected goals matter.

Other diagnostics (draw score shares, mean total goals, log score of the actual scoreline) are in `m2_distribution_report.json`. The log score ranks S2 best in three leagues (Premier League, Serie A, Ligue 1) and S1 best in two (La Liga, Bundesliga), and S3 worst in all five; it is a likelihood measure and not part of the pass rule.

## 4. M2b result: season goal difference, goals and points across cut-offs (end to end)

Frozen v1 at three cut-offs per season (1 Nov, 1 Jan, 1 Mar) in 2024-25 and 2025-26, all five leagues, 4,000 simulations per cut-off, ranking not involved (so no tie-break rules). 576 team-cut-off observations per method. Coverage of the realised value by the 10-90% simulated interval (nominal 80%):

| Method | Goal difference | Goals scored | Points (outcome-only) | Goal-difference error (mean absolute) |
|---|---|---|---|---|
| S1 | **73.3%** | 71.7% | 74.7% | 7.2 goals |
| S2 | **71.2%** | 72.9% | 75.0% | 7.1 goals |
| S3 | **74.0%** | 71.9% | 74.7% | 7.1 goals |

All three pooled values lie inside the 70-90% band, so M2b would pass for all three, but **all are below the nominal 80%** and, by league, goal-difference coverage is below 70% in the Premier League for all methods (S1 66.7%, S2 63.3%, S3 69.2%). Points coverage, which does not depend on any scoreline method at all, is also about 75%: the main reason the intervals are too narrow is probably **static strengths**, not the scoreline model. Observations at different cut-offs of the same season are correlated, so the effective sample is much smaller than 576.

## 5. How demanding is the predeclared rule? (important limitation)

If a model were **exactly true**, scores really drawn from its own distribution, how often would it still fail the rule because of sampling noise alone? Simulated 300 times with the evaluation sample sizes: pass probability per league **Premier League 81%, La Liga 80%, Bundesliga 64%, Serie A 81%, Ligue 1 64%**, and **all five leagues together only 22%**. So the predeclared tolerances are tighter than the noise in about 800 matches; failing them is weak evidence that a method is wrong, and a correct method would usually fail somewhere. I did not change the rule because of this. It is reported so you can decide.

For information only (post hoc, **not** an approved rule): if the criterion were "the method's statistic lies inside the 95% bootstrap interval of the actual statistic", S1 would pass the Bundesliga and Ligue 1, S2 the Premier League, Bundesliga and Ligue 1, S3 the Premier League, La Liga and Bundesliga. **Still no method passes all five leagues.**

## 6. A proposed fourth candidate was tested only on validation data, and does not help

S1 with expected goals shrunk towards the league mean (k = 1 is S1) was tuned on the 2023-24 validation season only (matches from 2024-07-01 were not read). The best k on validation is 1.0, i.e. shrinkage makes the margin criteria worse (worst normalised deviation 1.44 at k=1.0 to 2.64 at k=0.4). It is therefore not proposed.

## 7. Limitations of this benchmark

* The evaluation window is two seasons per league (about 650-850 matches each); the intervals above are wide.
* The three methods were compared on the same matches; picking one afterwards uses them for selection, so any later backtest on the same seasons is not fully independent of that choice.
* Expected goals come from the v2 feature generator, which is shared by v1 and v2-r1 and was trained for other purposes.
* Static strengths probably drive the under-coverage and are not a scoreline issue.
* Draw-heavy and low-scoring leagues respond differently; one method for all leagues is a simplification.

## 8. Options that need your decision (no final league-position prediction is enabled until you choose)

| # | Option | What it means | Risk |
|---|---|---|---|
| O1 | **Keep the rule and the gate closed (current state)** | Simulations stay disabled; everything else is built (eligibility, rule profiles, API, UI shell) | none, but no forecasts |
| O2 | Approve S1 for the Bundesliga and S3 for La Liga (each passes the predeclared criteria in that league) | Positions enabled for the two initial leagues, different methods per league | selected after seeing the same matches; different methods per league; S3 is not wired into the service yet |
| O3 | Replace the rule with a statistically calibrated one (for example "inside the 95% interval", or "fails only if outside by more than noise") and re-declare "every league" as "the leagues being enabled" | Under the 95%-interval version, S3 would qualify for La Liga and the Bundesliga | post hoc relative to results already seen; I would apply it to matches from 2026-09-21 onward as they arrive to limit that |
| O4 | Pre-register a new candidate (for example a negative-binomial or bivariate-Poisson score model) and test it once on the 2024+ matches | A genuine attempt to fix the margin pattern | the shrinkage variant failed on validation; no guarantee |
| O5 | Enable a **points-only mode** now: expected points and 10-90% point intervals for each club (no finishing positions, no tie-breaks, no scorelines), still gated by the data-quality gate and verified league scope | Useful and independent of the scoreline question; its coverage was 74.7% against a nominal 80% | needs your approval as a new product mode; intervals are somewhat too narrow |
| O6 | Address static strengths first (a dynamic-strength mode) | Likely improves coverage for every metric; was the planned optional M8 | more work, must beat static in a locked test |

**My recommendation:** do not enable positions yet. Take O5 now if you want a usable output, and decide between O3 and O4 for positions after reading section 5; do O6 in parallel because it addresses the larger calibration gap. These are recommendations, not approvals.
