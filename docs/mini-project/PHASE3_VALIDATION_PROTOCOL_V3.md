# Validation Protocol v3 for scoreline methods: corrected PROPOSAL, not applied

Date: 2026-10-26. **Status: proposal only.** It has not been applied to any result. **The revised protocol was not run on the confirmation sets CA or CB** (no outcome of any CA or CB match was read for this document; the only CA information used is pre-match history depth, section 5), no scoreline method is selected, and the full final-position simulator stays disabled. **Benchmark v1, its hashes and its failed verdict are preserved** (section 9, with a test).

It replaces [Protocol v2](PHASE3_FINAL_VALIDATION_PROTOCOL.md) (which stays unedited below its correction banner) and corrects the statistical problems found in the independent review [PHASE3_PROTOCOL_V2_REVIEW.md](PHASE3_PROTOCOL_V2_REVIEW.md). All numbers come from offline scripts with fixed seeds and synthetic data: `app/seasonsim/m5_protocol_v3_planning.py`, `m5_design_effect.py` (outputs `data/supervised/phase3/m5_protocol_v3_planning.json`, `m5_design_effect.json`).

## 0. Why this matters less than it did, and what it is for
The experimental points-only mode now also shows **position ranges** (lower and upper bounds for title, top four and relegation) that need **no scoreline method at all** ([PHASE3_POSITION_BOUNDS_INTEGRATION.md](PHASE3_POSITION_BOUNDS_INTEGRATION.md)). A scoreline method is needed only if you later want **exact** title, top-four and relegation probabilities and a predicted table. This protocol is the gate for that, and it can be postponed without losing the ranges.

## 1. What was wrong in v2 and what v3 does (all corrections)

| # | Problem found | Evidence | v3 correction |
|---|---|---|---|
| 1 | **Sample sizes too small.** v2 used the one-sided power formula (z = 2.926) for an equivalence test that needs two one-sided tests (z = 3.29), and treated the four statistics one at a time although all four must pass | At v2's own sample sizes the simulated power of the correct model was **55% (1,158 matches, recommended margins), 57% (2,606, strict) and about 54% (652, lenient)**, not 90% | Power of the **whole decision rule** is simulated (section 6); algebra in section 6a |
| 2 | **"The fixed sequence preserves the family-wise 5%" was not established** for choosing among different methods | Review: sequence false-acceptance 0.3% to 0.9% in the opposite-direction case against 0.0% to 0.1% for Holm; no proof | **Holm over the three methods**; the simplest accepted method is chosen (section 4). Proved, not only simulated |
| 3 | **The league screen was a gate** (Holm over leagues, a flagged league excluded) | With the correct method it falsely flagged some league 8.7% of the time at 1,158 matches (2.7% at 4,321); at the margin boundary it flagged 53% to 100% | League results are **descriptive**: reported, never used to exclude a league (section 4); a league-specific claim needs a league-specific sample (section 8) |
| 4 | **CA is not representative** on history depth (standardised difference 4.9) and its earlier exposure cannot be fully certified | Audit; the 90th percentile of CA1 history depth is below the 10th percentile of the target leagues (section 5) | The claim a pass on CA supports is restricted; a history-depth stratum is pre-declared; the exposure is disclosed (section 5) |
| 5 | **CB (45 matches, 686 a season) cannot decide anything soon** | v2 said 1,158 matches (1.7 seasons); the corrected number is about **2,333 (3.4 seasons)** | CB is **monitoring only** until its target size is reached (section 7) |
| 6 | **The season-level criterion** clustered by team-season (ignores that clubs in a league share matches) and its power was never studied | league-season blocks are the unit of independence | cluster = **league-season**; the criterion stays **descriptive** until a power study exists (section 4) |
| 7 | **Dependence between matches** was assumed away | design effect measured on 10,781 development-window matches in 1,023 league-weeks: 0.96, 0.98, 0.99, 0.98 (no inflation) | analytic standard errors confirmed; a league-week block bootstrap is kept as a safeguard (section 6b) |
| 8 | **Reproducibility** documented only partly | same seed: identical; different seed: within Monte Carlo error (review) | lock file, script hashes and seeds fixed before any run (section 10) |
| 9 | **Benchmark v1 preservation** was a table in a document | | the six hashes are also asserted by `tests/test_benchmark_preserved.py` (section 9) |

## 2. Data: what is independent and what is not
| Set | Content | Status |
|---|---|---|
| **D0** development | matches before 2024-07-01 | used for fitting and for the design-effect check; never for acceptance |
| **D1** Benchmark v1 window | 2024-07-01 to 2026-09-20, five leagues, 3,809 matches | **seen**: S1, S2, S3 were compared on it. Exploratory only, never confirmatory |
| **CA1** | ten other European first divisions with at least 300 matches each in the window (Netherlands, Portugal, Turkey, Belgium, Austria, Czech Republic, Scotland, Greece, Romania, Poland): **4,321 matches** | scoreline statistics **never computed**; list frozen with a hash (`ca_manifest.json`) |
| **CA2** | the other 37 leagues of the window: 6,703 matches | reserved for a replication or a new candidate; never used together with CA1 for the same decision |
| **CB** | Bundesliga and La Liga matches after 2026-09-20: 45 played, 686 more per season | unseen; monitoring only (section 7) |

Each confirmation set is **used once**; the match list and a sha256 of the input table are recorded before any scoreline statistic is computed. Probabilities and expected goals use features strictly before each match date.

## 3. Statistics and margins (definitions unchanged from v2)
Mean winning margin in home wins and in away wins; share of one-goal wins among home wins and among away wins. Estimand `d = model value - actual value`. Practical margins `(goal margin, one-goal share)`: strict 0.10 / 0.05, **recommended 0.15 / 0.075**, lenient 0.20 / 0.10 (**your decision**). At the recommended margin a coupled simulation changes any club's title, top-four or relegation probability by at most 0.3 percentage points now (0.4 late in the season), although final positions change in 17% to 37% of seasons through tie-breaks (review, question 2); the margins are statements about match-level bias, not about positions.

## 4. Decision rule (what "pass" means in v3)
For each method `m` in {S1, S2, S3} (fixed simplicity order S1 < S2 < S3) and each statistic `k`:
1. **Estimate** `d(m,k)` and its standard error. The analytic standard error (as in `m2_protocol.sample_actual`) is used; a **league-week block bootstrap** standard error is computed as well and the **larger** of the two is used (the design effect on development data is below 1, so the safeguard should not bind).
2. **Two one-sided tests** of "bias <= -margin" and "bias >= +margin" at 5% each (the 90% interval lies inside the margin). The method's p-value `p(m)` is the **largest** of its four statistics' larger one-sided p-values (**intersection-union**: all four must pass).
3. **Holm over the three methods:** order `p(1) <= p(2) <= p(3)`; accept in turn while `p(i) <= 0.05 / (3 - i + 1)` (0.0167, 0.025, 0.05); stop at the first failure.
4. **Choice:** among the accepted methods take the **simplest** (S1 before S2 before S3). If none is accepted, the answer is "no method accepted".
5. **Pooling:** inverse-variance weights across the leagues in the set, as in v2. **A pass is a statement about the average league**: biases of opposite sign in different leagues can offset; the league-level estimates and intervals are reported next to it (descriptive, never a gate), together with the number of leagues whose 90% interval lies inside twice the margin.
6. **Season-level criterion** (points coverage minus goal-difference coverage of the simulated 10-90% intervals at the three cut-offs, target at most 0.05; goal-difference coverage within 0.70-0.90): reported with a **league-season block bootstrap**, **descriptive** until a power study shows it can fail a wrong method and pass a right one.
7. **Two confirmation sets** (CA1 and, when it reaches its size, CB) are combined by **intersection-union**: both must accept the same method.

**What is proved, simulated and assumed.**
* *Proved:* the intersection-union test of equivalence has size at most 5% for each method (it rejects only if every component rejects); Holm controls the probability of accepting any non-equivalent method at 5% under **any** dependence between the three methods' p-values; choosing the simplest accepted method after that cannot create a false acceptance.
* *Simulated (synthetic data, section 6):* power, and false acceptance in chosen worst cases. Observed false acceptance: **at most 0.1%** when every method sits just outside the margin (1.08 to 1.17 times the margin) and **0.1%** under Holm in the opposite-direction case (sequence of v2: 0.3% to 0.9%).
* *Assumed:* the normal approximation of the four estimators (large samples), the analytic standard errors (checked on development data: design effect 0.96 to 0.99), and that the 5-league development-window behaviour applies to the confirmation set.

## 5. CA: what a pass supports, and its limits
* **Representativeness (pre-match information only).** CA matches resemble the target on win probabilities but not on history depth: clubs in CA1 have a median of **145** earlier matches in the model history (quartiles 64 and 203, 90th percentile 267); the Bundesliga and La Liga matches since 2024-07-01 have a median of **514** (10th percentile 431) for the less experienced of the two clubs. **No CA match reaches the typical depth of the target.**
* **Depth strata (CA1; both clubs must have at least T earlier matches):** T = 30: 3,947 matches; 60: 3,346; **100: 2,790 (65%)**; 150: 2,054 (48%); 200: 1,132 (26%); 300: 353 (8%).
* **Recommendation (needs your decision):** primary set = **CA1 with both clubs at least 100 earlier matches (2,790 matches)**, which still has enough power for the recommended margins (section 6: about 95% under Holm in the worst case); the full CA1 (4,321) is reported as a sensitivity set, and a result is called "supported by CA" only if both agree in direction. The threshold is fixed now, from pre-match counts only.
* **What a pass supports:** "the method is not systematically biased, on average, in other European first divisions with moderately long histories". It does **not** support a statement about the Bundesliga or La Liga; that needs CB.
* **Exposure disclosure.** The frozen club v1 was trained before 2024-07-01 and tested on all competitions then in the store; if its original test report scored CA matches of 2024-25, those matches were seen in that evaluation of the **match model**. **No scoreline statistic has ever been computed on CA** and no scoreline method was developed on it.

## 6. Sample sizes (corrected)
**6a. Algebra.** For one statistic with standard error `c / sqrt(n)` (`c` = 1.740, 1.733, 0.749, 0.872 for the four statistics, measured on the evaluation matches) and margin `D`, the equivalence test at 5% each side has power `2 * Phi(D / se - 1.645) - 1` when the model is exactly right, so 90% power needs `z = 1.645 + 1.645 = 3.29`, not the `1.645 + 1.282 = 2.926` of v2: **every sample size of v2 was too small by a factor 1.264 even for one statistic**, and by up to 1.75 if the four statistics were independent (they are positively correlated, so the truth lies between).

| Margins | v2 (one-sided z) | correct z, binding statistic | all four independent (upper bound) |
|---|---|---|---|
| strict 0.10 / 0.05 | 2,605 | 3,292 | 4,558 |
| **recommended 0.15 / 0.075** | 1,158 | 1,463 | 2,026 |
| lenient 0.20 / 0.10 | 652 | 823 | 1,140 |

**6b. Simulated power of the whole rule** (500 replications per point, seed 41; the model is exactly right; Monte Carlo error about 1 to 2 percentage points):

| Margins | One method alone: matches for 80% / 90% power | **Holm over three methods, worst case** (only one method right): 80% / 90% | Holm, best case (all three nearly right): 90% |
|---|---|---|---|
| strict 0.10 / 0.05 | 3,497 / 4,321 | 4,423 / **not reached at 5,000 (87%)** | 4,660 |
| **recommended 0.15 / 0.075** | 1,507 / 1,874 | **1,974 / 2,333** | 2,175 |
| lenient 0.20 / 0.10 | 848 / 1,028 | 1,123 / 1,300 | 1,199 |

Power by number of matches for the **recommended** margins (Holm, worst case): 686 matches 0.2%; 1,158 27%; 1,800 72%; 2,200 85%; 2,606 93%; 3,300 99.6%. For comparison the v2 sequence at 1,158 matches had 67% for *some* method accepted, but without a proven error rate (item 2 of section 1).

**6c. Dependence check (development window only).** 10,781 matches in 1,023 league-weeks: design effect of the four standard errors 0.956, 0.978, 0.987, 0.982. No sample-size inflation is needed; the block bootstrap of section 4 stays as a safeguard.

## 7. Timing
* **CA1 (primary, 2,790 matches with depth at least 100):** large enough for the recommended and lenient margins under Holm; not for the strict margins (79% at 4,321 even for all of CA1). It can be analysed once you approve the protocol.
* **CB (Bundesliga and La Liga, 686 a season):** the recommended margins need about **2,333 matches = 3.4 seasons** (2.7 for one method alone, 3.2 in the best case); lenient margins 1,300 (1.9 seasons); strict margins more than seven seasons. CB is therefore **monitored, not decided**: an interim descriptive table with intervals once a season, no pass or fail, until the target is reached. **The claim "validated for the Bundesliga and La Liga" cannot be made within this project's time frame**; the honest status after a CA pass is "supported by other European leagues; target-league confirmation pending".

## 8. League-specific methods
Only with all of: a pre-registered heterogeneity test (Cochran's Q per statistic across leagues, Holm-corrected) that rejects "the same bias in every league"; a pooled-best method that fails in that league and an alternative that passes it within Holm; and the sample size of section 6b **in that league alone** (about 2,333 matches, i.e. six La Liga seasons). With 700 matches per league the smallest detectable between-league difference is 0.26 goals, larger than the differences between methods seen in Benchmark v1, so **current data cannot justify league-specific methods**.

## 9. Benchmark v1 is preserved (files, hashes, verdict)
Benchmark v1 is frozen as it was; its files were hashed on 2026-10-25, **before Protocol v2 or v3 existed, and re-verified unchanged on 2026-10-26** (and by `tests/test_benchmark_preserved.py`, which also checks that `scoreline_method` is still null and the recorded status is `failed_predeclared_criteria`):

| File | sha256 |
|---|---|
| `docs/mini-project/PHASE3_SCORELINE_BENCHMARK.md` | `48ebb7b05c9bb1ed2f1a4a616928adb9f63de24cacf2a45384c20028f81a8997` |
| `data/supervised/phase3/m2_distribution_report.json` | `05fe9b100b782f65be27beda2a431d2c3d107beea661548d5b135aa35da97b97` |
| `data/supervised/phase3/m2b_report.json` | `23741826680ed67cb091f03aaf2d3d31d868915e051ac4d069b84ec9b04765d3` |
| `data/supervised/phase3/m2_rule_power.json` | `777934c0f3a7e12eb3551f80927a14baf8863c594b3141c09a0e48a965bee93a` |
| `data/supervised/phase3/m2_s4_tuning.json` | `5bd8dc1fbb13b45a051aaed08fb49d43e2d97e0ec9dd222de8b71ada1b6e4158` |
| `data/supervised/phase3/m2_matches.pkl` | `3c381bd303f0cb77033bd6474c45569b5dc36c2c53804a55056268ace3878f2a` |

**Verdict: no method passed the predeclared rule.** It is never relabelled. Protocol v3 results go in a new, separately named report ("Protocol v3 confirmation") and in separate tables; neither benchmark nor protocol is re-run or re-tuned on seen data.

## 10. Governance and steps (nothing starts without your approval)
1. You approve or change: margins, the CA1 depth threshold, Holm over methods with the simplicity order, CB as monitoring only, the descriptive status of the league screen and the season-level criterion.
2. I write a **lock file** before any run: protocol version, match lists and sha256 of the input tables, analysis script hash (`m5_protocol_v3_planning.py` is planning only; the analysis script is new), frozen-model hashes, seeds. A regression test must show that the script reproduces Benchmark v1's numbers on D1 exactly (a check, not a selection).
3. Run on **CA1 once**, with the primary and sensitivity sets; report in full, including failures.
4. You review before any configuration changes. Any relaxation of a margin or rule after seeing results needs a new pre-registration on untouched data.

## 11. Known gaps that remain (stated, not hidden)
* The power numbers assume the truth is one of the three methods' own distributions; a real league's goal process may differ.
* The season-level criterion has no power analysis; the pooled claim can hide offsetting league biases.
* The normal approximation and the analytic standard errors were checked on development data only.
* The margins are about match-level bias; their effect on exact position probabilities was measured only in simulation.
* CB cannot give a target-league answer for several years.

## 12. Decisions I need from you
1. Margins: 0.15 / 0.075 (recommended; 1,974 to 2,333 matches under Holm), 0.10 / 0.05 (not reachable with the data), or 0.20 / 0.10 (1,123 to 1,300).
2. Holm over methods with the simplest-accepted choice (replacing the v2 sequence), and the league screen and season-level criterion as descriptive.
3. CA1 depth threshold 100 for the primary set (2,790 matches), full CA1 as sensitivity.
4. CB as monitoring only.
5. Whether to run the protocol on CA1 at all now, given that the position ranges already provide rigorous statements without a scoreline method (a separate approval; nothing is run).
