# Final proposed validation protocol for scoreline methods (Protocol v2): PROPOSAL, not applied

Date: 2026-10-25. **Status: proposal only.** It has not been applied to any result, no scoreline method is approved, and the full final-position simulator stays disabled. Nothing in it changes the original benchmark ("Benchmark v1", all three methods failed the predeclared rule). Builds on [PHASE3_SCORELINE_BENCHMARK.md](PHASE3_SCORELINE_BENCHMARK.md) and [PHASE3_VALIDATION_REVIEW.md](PHASE3_VALIDATION_REVIEW.md); all numbers below come from `app/seasonsim/m2_protocol.py`, `m2_confirmation_planning.py` and `m3_tie_bound_widths.py` (outputs in `data/supervised/phase3/`), which use synthetic samples or counts only.

> **Superseded (2026-10-26) by [Protocol v3](PHASE3_VALIDATION_PROTOCOL_V3.md), a corrected proposal that fixes the problems listed in the review: sample sizes (about twice as large under Holm), Holm over methods instead of the fixed sequence, descriptive league screen, CA depth stratum, CB as monitoring only, and a hash register with a test for Benchmark v1.** This document is kept unedited below the banners so the change is visible; do not use its sample sizes or its fixed-sequence claim.
>
> **Corrections after independent review (2026-10-25; details in [PHASE3_PROTOCOL_V2_REVIEW.md](PHASE3_PROTOCOL_V2_REVIEW.md)).** (1) The sample sizes in section 4 were computed with a one-sided z-value and are **too small**; use the simulated power curve of the review (for margins 0.15 / 0.075: 14% power at 686 matches, 60% at 1,158, 91% at 1,800, 98% at 2,606). (2) The sentence "the family-wise 5% is preserved" for the fixed sequence in section 6 is **not established** for selecting among different methods; observed false-acceptance rates were 0.3% to 0.9% in the simulated cases, Holm over methods 0.0% to 0.1%. Prefer Holm over methods. (3) CB (45 matches now, 686 per season) is too small to decide anything alone; about 1,800 matches are needed. (4) CA is not representative of the target on history depth (standardised difference 4.9). Nothing has been run on CA or CB.

## 1. What the protocol has to fix

| Weakness of Benchmark v1 | How Protocol v2 answers it |
|---|---|
| Tolerances only 1.4-2.0 standard errors wide: a correct model passed all five leagues about 22-24% of the time | Equivalence testing with intervals; pooled across the leagues in scope (section 5); sample size set in advance (section 4) |
| 20 conditions combined without allowing for chance | Explicit multiplicity design (section 6) |
| Margins not tied to anything | Margins linked to the size of goal-difference error that matters (section 3) |
| The 2024-07-01 onward matches were used to compare the methods | Fresh confirmation data that no method has been compared on (section 2) |
| One method for all leagues assumed | Rules for when league-specific methods are allowed (section 7) |
| No plan for failure | Section 9 |

## 2. Data: what is independent and what is not

| Set | Content | Status |
|---|---|---|
| **D0** development | matches before 2024-07-01 (S3 fitted, S4 tuned here) | used; never for acceptance |
| **D1** Benchmark v1 window | 2024-07-01 to 2026-09-20, five leagues, 3,809 matches | **seen**: used to compare S1, S2, S3. Exploratory only, never confirmatory |
| **CA** "transfer" confirmation | the same window, **47 other European first divisions** (11,024 matches; 10 leagues with at least 300 matches give 4,321: Netherlands, Portugal, Turkey, Belgium, Austria, Czech Republic, Scotland, Greece, Romania, Poland) | **never examined for any scoreline question** (the benchmark used five leagues only). Frozen v1 probabilities exist for them (v1 was evaluated on them once, never tuned on them) |
| **CB** forward target-league data | Bundesliga and La Liga matches dated after 2026-09-20 | unseen. 45 played so far (Bundesliga 25, La Liga 20); 686 more per season for the two leagues |

Rules: probabilities and expected goals for every confirmation match are computed time-safely (features strictly before the match date) from the frozen artifacts; the match list and a sha256 of the input table are recorded before any scoreline statistic is computed; each confirmation set is **used once**: whatever method is tested on it, the set is then "seen" and a later candidate needs fresh data (CA can be split in advance into CA1 = the ten leagues with 300+ matches and CA2 = the rest, so there are two independent looks).
Caveat that must be reported with CA: these leagues have different goal rates and weaker model quality, so CA supports a statement about the method in general, not directly about the Bundesliga or La Liga.

## 3. Statistics and the practical margin

* **Statistics (unchanged):** mean goal margin in home wins and in away wins; share of one-goal wins among home wins and among away wins. Estimand `d = model value − actual value`, with a standard error from a bootstrap that resamples whole matchdays (allows for dependence), checked against the analytic one.
* **Season-level criterion (the quantity users see):** for the cut-off backtest (1 Nov, 1 Jan, 1 Mar), report the coverage of the simulated 10-90% goal-difference interval and, **separately, the coverage of the simulated points interval, which involves no scoreline model**. The scoreline method is judged on the **difference** (points coverage minus goal-difference coverage, target at most 0.05), with cluster-bootstrap intervals by team-season. This isolates what the scoreline step adds and stops the known static-strength under-coverage (about 75%) from being blamed on it. (Under Benchmark v1 that difference was 0.014 for S1, 0.038 for S2, 0.007 for S3; reported for information only.)
* **Practical margin Δ (needs your decision).** A margin bias δ in wins shifts a club's simulated season goal difference by about δ times (wins minus losses), roughly 20 for a title or relegation contender. At δ = 0.15 goals that is about 3 goals a season, below the usual 5-10 goal gap between neighbouring clubs; at δ = 0.10 about 2 goals; at 0.20 about 4. The one-goal-share margin is set at half the goal margin in comparable units (0.05 / 0.075 / 0.10).

| Choice | Margins (goals / share) | Matches needed for 90% power (correct model) | Bundesliga + La Liga alone |
|---|---|---|---|
| Strict | 0.10 / 0.05 | **2,606** | 3.8 seasons |
| **Recommended** | **0.15 / 0.075** | **1,158** | **1.7 seasons** |
| Lenient | 0.20 / 0.10 | 652 | 1.0 season |

## 4. Sample size and timing
* CA (4,321 matches in the ten larger leagues) is already large enough for even the strict margins: it can be run as soon as the protocol is approved.
* CB at the recommended margins needs about 1,158 Bundesliga + La Liga matches: roughly the 2026-27 and 2027-28 seasons (686 per season, 45 already played). At the strict margins about 3.8 seasons.
* The smallest difference between two leagues of 700 matches each that a test could detect with 80% power is about 0.26 goals (margins) and 0.11 (one-goal share); with 1,400 each 0.18 and 0.08 (section 7).

## 5. Decision rule (what "pass" means)

For the leagues in scope L and one method:
1. **Pooled equivalence (primary).** Combine the leagues by inverse-variance weights. Pass if, for **each of the four statistics**, the 90% confidence interval of the pooled `d` lies inside ±Δ (two one-sided tests at 5%).
2. **League screen.** Holm correction over the 4 × L tests of `d = 0` at familywise 5%. A league is **flagged** if some statistic is both statistically detectable and larger than Δ. A flagged league is excluded for that method; it does not fail the method for the other leagues.
3. **Season-level criterion** of section 3 (points coverage minus goal-difference coverage within 0.05, and goal-difference coverage within 0.70-0.90).
4. All three must hold on **CA** (transfer) and, for a claim about Bundesliga and La Liga, on **CB** (target) as well. Before CB reaches its pre-set size the status is "supported by CA only; target-league confirmation pending", and the final-position simulator stays disabled unless you decide otherwise.

Operating characteristics of rules 1-2 (synthetic; five leagues, 3,809 matches): a correct model is accepted 85% of the time; a model off by about 0.05 goals 47%; by about 0.09 goals 8%; by about 0.12 goals 0.3% (Benchmark v1's rule: 24%, 9%, 0.5%, 0%). For the two-league scope at 1,522 matches: strict margins accept a correct model 11.5%, recommended margins 79%, and reject a 0.09-goal bias 74%.

## 6. Multiple comparisons
* **Four statistics:** intersection-union (all four must pass); this needs no adjustment because a pass requires every test to pass.
* **Leagues:** one pooled primary test; the per-league screen uses Holm over 4 × L tests.
* **Methods:** a **fixed-sequence procedure in the order S1, S2, S3**, fixed now: S2 is looked at only if S1 failed, S3 only if S2 failed. The family-wise 5% is preserved with no splitting of α. Reporting all three results regardless is allowed but only the sequence decides. If you prefer to test all three at once, intervals widen to 96.7% (Bonferroni over 3): at the recommended margins a correct model is accepted much less often, so I advise against it.
* **Two confirmation sets:** CA and CB are combined by intersection-union (both must pass), not averaged.
* **Looks:** one analysis per confirmation set, at the pre-registered size; no interim peeks that influence the decision; if sample sizes are not reached the status stays "pending".

## 7. Can league-specific methods be justified?
Only rarely. A different method for a league needs **all** of: (a) a pre-registered heterogeneity test (Cochran's Q across the leagues, per statistic, Holm-corrected) that rejects "the same bias in every league" on confirmation data; (b) the pooled-best method flagged in that league and an alternative passing it, within the fixed sequence; (c) at least the sample size of section 4 **in that league alone** (about 1,158 matches, i.e. three seasons of La Liga). With about 700 matches per league the smallest detectable between-league difference is 0.26 goals, larger than the 0.1-0.2 differences between methods seen in Benchmark v1, so **current data cannot justify league-specific methods**, and choosing the best of three per league multiplies the number of tests by three. Default: one method for all enabled leagues; revisit after at least three seasons of target-league data.

## 8. How Benchmark v1 stays unchanged and separately reported
* Benchmark v1 is frozen as-is (sha256, recorded 2026-10-25):

| File | sha256 |
|---|---|
| `docs/mini-project/PHASE3_SCORELINE_BENCHMARK.md` | `48ebb7b05c9bb1ed2f1a4a616928adb9f63de24cacf2a45384c20028f81a8997` |
| `data/supervised/phase3/m2_distribution_report.json` | `05fe9b100b782f65be27beda2a431d2c3d107beea661548d5b135aa35da97b97` |
| `data/supervised/phase3/m2b_report.json` | `23741826680ed67cb091f03aaf2d3d31d868915e051ac4d069b84ec9b04765d3` |
| `data/supervised/phase3/m2_rule_power.json` | `777934c0f3a7e12eb3551f80927a14baf8863c594b3141c09a0e48a965bee93a` |
| `data/supervised/phase3/m2_s4_tuning.json` | `5bd8dc1fbb13b45a051aaed08fb49d43e2d97e0ec9dd222de8b71ada1b6e4158` |
| `data/supervised/phase3/m2_matches.pkl` | `3c381bd303f0cb77033bd6474c45569b5dc36c2c53804a55056268ace3878f2a` |

* Its verdict stays "no method passed the predeclared rule". Protocol v2 results go in a **new, separately named report** ("Protocol v2 confirmation") and in separate tables; the app and documents show both, labelled, if a method is ever approved.
* Neither protocol is re-run or re-tuned on seen data; no pass/fail label of Benchmark v1 is ever changed.

## 9. If no method passes Protocol v2
1. The points-only mode stays as it is, and the full simulator stays disabled.
2. **Position probabilities as ranges from points alone (new idea, needs your approval, no scores needed):** a club "surely" reaches a band if it does even when every tie on points goes against it, and "possibly" reaches it if it does when ties go for it. Because the true probability lies between the two whatever the tie-break rules say, no scoreline method and no coin are needed. Measured on the current simulation (10,000 runs, Bundesliga and La Liga): the title range is 0.1 percentage points wide on average (at most 1.2), top four 1.1 and 0.7 (at most 4.8), relegation 1.8 and 1.6 (at most 5.5), and the Bundesliga relegation play-off place 3.9 (at most 10.6). Widths will grow late in the season as points ties become more decisive.
3. Candidates, if any, are pre-registered (at most two), limited by the amount of fresh data (CA2, then later CB), with the same decision rule.
4. Margins or rules are never relaxed after seeing results; any relaxation needs a new pre-registration and untouched data.
5. Report the outcome honestly, including failures.

## 10. Governance and steps (nothing starts without your approval)
1. You approve or change: margins Δ, scope, CA/CB use, fixed-sequence order, season-level criterion (section 11).
2. I write a lock file (protocol version, data lists and hashes, code hash, frozen-model hashes) and freeze the analysis script; tests prove the script reproduces Benchmark v1's numbers exactly on D1 (a regression, not a selection).
3. Run on CA once; report in full. Run on CB only when its pre-set size is reached.
4. You review before any production configuration is changed.

## 11. Decisions I need from you
1. Practical margin: 0.15 goals / 0.075 share (recommended), 0.10 / 0.05, or 0.20 / 0.10.
2. Approve the pooled-equivalence design and the fixed-sequence order S1, S2, S3.
3. Approve CA (independent European leagues) as the first confirmation, and CB (Bundesliga and La Liga after 2026-09-20) as the target confirmation.
4. Approve the season-level criterion based on points coverage minus goal-difference coverage.
5. Whether to explore the points-range position probabilities of section 9 (a separate approval; nothing built).
