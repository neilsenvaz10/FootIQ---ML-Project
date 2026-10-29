# Phase 3: review of the scoreline acceptance rule, a proposed revised protocol, and the static-strength investigation

Date: 2026-10-25. **Nothing in this document changes the original benchmark outcome** (all three scoreline methods failed the predeclared rule; see [PHASE3_SCORELINE_BENCHMARK.md](PHASE3_SCORELINE_BENCHMARK.md)). The protocol in part B is a **proposal**: it has not been applied to the observed results, must be approved by you, and may not be used to pick a production scoreline method before that. Part C reports a diagnostic on points intervals; no frozen model, probability or setting was changed.

Reproduce offline: `app/seasonsim/m2_protocol.py` (parts A and B, simulations) and `app/seasonsim/m2_static_diag.py` (part C). Outputs: `data/supervised/phase3/m2_protocol.json`, `m2_static_diag.json`.

---

## A. Why a correct model passes the combined rule only about 22% of the time

**What the rule asked.** For each league, four statistics must each be within a fixed distance of the value seen in the real matches: the average goal margin in home wins (±0.10 goals), the average margin in away wins (±0.10), the share of one-goal wins among home wins (±0.05) and among away wins (±0.05). A method passes only if all four hold in **all five leagues**: 20 conditions in a row.

**The problem is noise in the real matches, not the model.** The "actual" value is itself an estimate from a few hundred wins. Its standard error (measured on the real sample sizes) is about 0.05-0.07 goals for the margins and 0.026-0.032 for the one-goal shares. The tolerances are therefore only **1.4 to 2.0 standard errors** wide:

| League (matches) | Margin, home wins | Margin, away wins | 1-goal share, home | 1-goal share, away |
|---|---|---|---|---|
| Premier League (820) | 1.58 SE | 1.71 SE | 1.91 SE | 1.68 SE |
| La Liga (849) | 1.75 | 1.71 | 1.96 | 1.66 |
| Bundesliga (673) | 1.53 | 1.35 | 1.83 | 1.45 |
| Serie A (810) | 1.89 | 1.72 | 1.90 | 1.55 |
| Ligue 1 (657) | 1.44 | 1.42 | 1.73 | 1.49 |

(tolerance divided by the standard error of the actual statistic). A tolerance of 1.5 standard errors is exceeded by chance about 13% of the time even if the model is exactly right.

**Combining them.** I treated the S1 score distributions as if they were the truth, drew 400 synthetic "seasons" of results with the real sample sizes, and applied the rule. A model that is exactly right passed: Premier League 77.5%, La Liga 80.2%, Bundesliga 65.0%, Serie A 81.2%, Ligue 1 67.5%, and **all five at once 24.2%** (the earlier 300-run estimate was 22%). If the four checks in a league were independent the all-five figure would be about 12%; they are positively correlated, which lifts it to about 22-24%. The product of five league probabilities of 0.65-0.81 is the whole explanation. It is the usual multiple-testing effect: **a conjunction of 20 conditions that are each tested without allowing for noise.**

Consequence: the failure of all three methods is **weak evidence** that they are wrong (a correct method would fail about three times in four), and equally the rule cannot confirm a good method. It also means the rule's per-league results mix signal and luck.

---

## B. Proposed revised validation protocol (for your approval; not yet used)

### B1. Principles
1. State the claim as **practical equivalence**: the method's deviation from reality is smaller than a margin that matters for the output, with an interval for the deviation, not a point comparison to a fixed tolerance.
2. **Pool** the information across the leagues the method will be used for (the noise falls with about the square root of the number of matches), and **screen** leagues individually for deviations that are both statistically detectable and larger than the margin.
3. Control multiplicity explicitly (below), fix everything in advance, use data not used for selection, and apply the protocol once.

### B2. The protocol
* **Scope and data.** Declare the leagues being enabled (for example Bundesliga and La Liga) and the evaluation window before looking at results. Use only matches dated after the fitting window and not previously used to choose between methods (see B5).
* **Statistics.** The same four (margins and one-goal shares in home and away wins), plus the season-level check (M2b: goal-difference interval coverage) as a second, separate criterion.
* **Estimand.** `d = model value minus actual value`, estimated with its standard error (analytic, or a bootstrap over matchdays to allow for dependence).
* **Primary criterion (pooled equivalence, two one-sided tests, α = 0.05).** Combine the leagues by inverse-variance weighting. The method is acceptable if, for every statistic, the 90% confidence interval of the pooled `d` lies inside the practical margin ±Δ.
* **League screen (Holm).** Over the family of 4 statistics × L leagues, test `d = 0` with Holm correction at familywise 5%. A league is **flagged and excluded** if some statistic is both significant and larger than Δ. A flagged league is not "failed" overall: the method can still be enabled for the other leagues.
* **Method multiplicity.** Methods are tested in a pre-fixed order (simplest first: S1, S2, S3) as a **fixed-sequence procedure**: the next method is looked at only if the previous one failed. This keeps the overall error at 5% without splitting α. If all three must be tested together, use 96.7% intervals (Bonferroni over 3).
* **Practical margin Δ.** To be chosen by you. The original ±0.10 goals / ±0.05 share is the natural default. Whether the data can support it depends on the sample (B4).
* **Season-level criterion (M2b).** Coverage of the simulated 10-90% goal-difference interval must be within 70-90%, with a 95% interval for the coverage computed by resampling whole team-seasons (cut-offs of one team-season are strongly correlated), not by treating each cut-off as independent.
* **Reporting.** Every deviation with its 95% interval and sample size, by league, whether or not the criterion passes. No re-tuning after seeing results; one lock file and one run.

### B3. Operating characteristics (simulated; the protocol has not been applied to the real results)
Acceptance probability, five leagues, evaluation sizes as in the benchmark (3,809 matches), 400 repetitions per case. "Bias" is how far the model's margin is from the synthetic truth (the model's expected goals spread by a factor of 0.8 / 0.6 / 0.4 around the league mean):

| Truth | Margin bias (home wins) | Original rule (all five) | **Proposed: pooled equivalence + league screen (all five)** | Per-league equivalence, Δ = 0.20 / 0.08 (all five) | Per-league Holm non-rejection + bound, Δ = 0.20 / 0.08 (all five) |
|---|---|---|---|---|---|
| model exactly right | 0 | 24.2% | **85.0%** | 2.8% | 90.5% |
| mild bias | 0.01-0.06 | 9.0% | 47.5% | 0.7% | 78.7% |
| moderate bias | 0.02-0.11 | 0.5% | **7.7%** | 0.0% | 47.7% |
| larger bias | 0.02-0.15 | 0.0% | **0.3%** | 0.0% | 16.8% |

Reading: the proposed pooled protocol accepts a correct model 85% of the time (the original rule: 24%) and still rejects a model that is off by about 0.1 goals 92% of the time. A per-league equivalence test (each league on its own) is not workable at these sample sizes (it accepts a correct model only 3% of the time); a per-league "failure to reject" test is permissive (it accepts a model biased by 0.1 goals almost half of the time) because with about 700 matches it cannot detect such a difference.

### B4. Sample size for the two-league scope (Bundesliga and La Liga)
Those two leagues contributed 1,522 evaluation matches. At the original margins (0.10 goals / 0.05 share) the pooled protocol accepts a correct model only **11.5%** of the time, because 1,522 matches cannot demonstrate a margin that tight. About 2,600 matches are needed for 90% power at ±0.10 goals (measured in `m2_confirmation_planning.py`; an earlier rough figure of 3,100 here was too high); the two leagues produce only 686 matches a season, so confirmation data from them alone would take about 3.8 seasons. With **±0.15 goals / ±0.075 share**, a correct model is accepted **79%** of the time, a mildly biased one (about 0.05 goals) 66%, a moderately biased one (about 0.09) 26% and a clearly biased one (about 0.12) 5.5%. Either a wider margin has to be accepted for a two-league scope, or the scope pooled with the other leagues' matches (which would make a statement about the method in general, not about those leagues).

### B5. Independence from the earlier look
The 2024-07-01 onward matches have already been used to compare the three methods. A confirmatory test must therefore use **matches not yet seen**: results dated after 2026-09-20 accumulate (about 45 per week across the five leagues once the data sources are fresh, about 13 per week for Bundesliga plus La Liga), or the method's performance is judged on the older seasons with the explicit statement that the same data informed the choice. I recommend the forward data for confirmation and the older data for planning only.

### B6. What needs your approval before any use
(1) The pooled-equivalence design in B2 and the fixed-sequence ordering of methods. (2) The practical margin Δ (0.10 / 0.05 or 0.15 / 0.075) and the scope. (3) The confirmation sample (forward data after 2026-09-20). (4) That the season-level criterion uses the team-season block resampling. Until then **no method is selected and the full final-position simulator stays disabled**.

---

## C. Do static team strengths explain the under-coverage of the simulated points intervals?

**Background.** In the M2b backtest the 10-90% simulated interval for final points contained the real value in **74.7%** of the 576 team-cut-off cases (nominal 80%). The simulation gives every remaining fixture the probability it had at the cut-off.

**Method (no model or probability changed).** For each team-cut-off, E_static is the simulated expected final points. E_dyn is the expected final points if each remaining match had its pre-match probability from the same frozen v1 model **at the match's own date** (an "oracle": it knows the results played in between, so it cannot be used at the cut-off; it only shows how much probabilities drift). Zero of the 576 cases had to be skipped (totals match the database).

**Findings (pooled; by cut-off in the table):**

| | All | 1 Nov | 1 Jan | 1 Mar |
|---|---|---|---|---|
| Coverage of the 10-90% interval | 74.7% | 70.3% | 75.0% | 78.6% |
| Std. deviation of (real - expected) / simulated sd | 1.20 | 1.32 | 1.20 | 1.07 |
| Real squared error (variance of real minus E_static) | 42.7 | 67.7 | 41.7 | 18.8 |
| Simulated variance | 28.2 | 39.4 | 28.7 | 16.5 |
| Variance of the drift (E_dyn minus E_static) | 4.6 | 9.4 | 3.6 | 0.6 |
| Variance left when probabilities may drift (real minus E_dyn) | **25.8** | 35.3 | 26.9 | 15.3 |

* The expected points are **not biased** (mean error -0.08 points) and **well calibrated** (slope of real on expected remaining points 0.96).
* The intervals are too narrow by about 20% in standard-deviation terms (1.20), most at the 1 Nov cut-off (1.32) and almost not at all by 1 Mar (1.07): the gap shrinks as fewer matches remain, exactly the pattern expected if probabilities drift as the season goes on. The drift variance per remaining match grows with the number of matches left (0.06 with 12 or fewer left, 0.16, 0.30, and 0.39 with 29 to 40 left), so drift is larger than proportional to the horizon.
* Directly, the drift accounts for about **31%** of the missing variance (14.5). In a second view, the variance left after letting the probabilities update with hindsight (25.8) is **no larger than the simulated variance (28.2, ratio 0.92)**: once probabilities are allowed to move, no extra over-dispersion remains. The remainder between the two views is the correlation between how probabilities move and what then happens (teams that do better than expected are then given higher probabilities).
* By league the effect differs: Bundesliga coverage 78.7% (drift explains most of the gap), Premier League 65.8%, La Liga 75.8%, Serie A 77.5%, Ligue 1 75.9%.

**Conclusion (and its limit).** Static strengths are a **sufficient and plausible explanation** for the under-coverage: the over-dispersion is largest where most matches remain, is gone when the oracle may update, and the point forecasts are unbiased. The direct drift variance accounts for only about a third of the gap, so I cannot say it is the only contributor, and the oracle is a diagnostic, not a method. Whether a dynamic mode actually closes the gap without hindsight is untested and, per your decision D3, not implemented. **For the points-only mode this means the intervals are somewhat too narrow (about 75% instead of 80%), which is stated on the page.**
