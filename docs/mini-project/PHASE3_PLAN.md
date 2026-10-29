# Phase 3 pre-implementation design and validation review: domestic league season simulator

Date: 2026-10-25. **Design only. Nothing is implemented, nothing is staged, committed or pushed, no frozen model, training file, official prospective-evaluation file or sync setting was touched, and no live request was made.** The only external reading was of public regulation pages (listed in section 14). Every number below that is labelled "measured" comes from the local database or the frozen model reports; every rule is labelled **verified** (primary source read), **partly verified** (official or league-run page, not the rulebook) or **unresolved**.

Contents: 1 What we examined and the main findings, 2 Simulation design, 3 Probabilities (v1 and v2-r1), 4 Scorelines, 5 Conditional-Poisson appropriateness and validation, 6 Tie-break and position rules per league, 7 Missing and stale data, 8 Postponements, date conflicts and kickoff times, 9 Output metrics, 10 Backtesting without leakage, 11 Integration into the database and UI, 12 Roadmap and required tests, 13 Risks, 14 Decisions needing your approval and sources, 15 **Simple explanation**.

---

## 1. What we examined and the main findings

Examined: the stored 2026-27 and historical results (5 leagues, 8 complete seasons), the frozen club v1 and v2-r1 reports and artifacts' training windows, the v2 feature generator, the Phase 2 forecast engine and time-safety rules, the existing World Cup simulator (seeded, same-seed-same-output), the store schema (the empty `simulation_runs` table already exists), and the official regulations of each league.

Main findings that shape the design:

1. **Only two of the five leagues are simulation-ready today.** Measured on 2026-10-25:

| League | Fixtures | Completed | Played-date but no verified result | Newest result | Days stale | Remaining to simulate |
|---|---|---|---|---|---|---|
| Bundesliga | 306 | 61 | 0 | 2026-10-24 | 1 | 245 |
| La Liga | 380 | 89 | 1 | 2026-10-21 | 4 | 291 |
| Premier League | 380 | 60 | 15 | 2026-10-12 | 13 | 320 |
| Serie A | 380 | 50 | 20 (+5 past-dated still "scheduled") | 2026-09-20 | 35 | 330 |
| Ligue 1 | 306 | 45 | 18 (+3) | 2026-09-20 | 35 | 261 |

2. **A clean historical backtest is only possible for 2024-25 and 2025-26** (section 10). Club v1 was trained on 2018-08-01 to 2023-06-30, tuned on 2023-24, tested once on 2024-07-01 to 2025-06-29 and checked on a forward holdout 2025-07-02 to 2026-09-20. Club v2-r1 was refit on everything up to 2026-09-20, so **no historical season is out-of-sample for it**.
3. **Tie-break rules differ by league and some are only partly verified.** Serie A's 2026-27 rule is verified from the federation's own decision (CU 244/A, 27 May 2026). La Liga is the weakest (section 6).
4. **The models give only home/draw/away probabilities.** Goal difference decides many tables, so a scoreline assumption is unavoidable and must be shown on the page (sections 4 and 5).
5. **A first data-only check of the conditional-Poisson idea** (14,282 completed matches, 2018-19 to 2025-26, league-average goal rates only, no model involved) is encouraging but not sufficient: it reproduces Serie A, La Liga and Ligue 1 well and under-states big wins in the Premier League and Bundesliga (section 5).
6. **Ligue 1 and Serie A are the leagues where data freshness blocks the simulator**, not the method.

## 2. How the Monte Carlo simulation predicts final standings

**Inputs (all read from the store, nothing from the network):** the season's completed matches (current table, goals, head-to-head results), the remaining fixtures (status `scheduled`, `awaiting_result`, `postponed`), per-fixture outcome probabilities and a scoreline distribution, and the league's rule profile (section 6).

**One simulated season**
1. Start from the real table at the data cut-off (points, goals for and against, and every played match, because head-to-head tie-breaks need them).
2. For each remaining fixture, draw an outcome (home, draw, away) from its probabilities, then a scoreline conditional on that outcome (section 4).
3. Add points and goals; rank all clubs with the league's full tie-break procedure (play-offs, where the rules require them, are simulated as stated in section 6).
4. Record each club's final points, goal difference, and final position.

**Repeat N times** (default 10,000, seeded, configurable up to a fixed cap such as 50,000). Sampling error of any probability p is about 1.96·√(p(1−p)/N): at most ±1.0 percentage point at N=10,000. The page shows this. Results are aggregated into the outputs in section 9.

**Implementation shape (for later):** pure NumPy, vectorised over simulations (a 380-fixture season at 10,000 runs is about 3.8 million draws, well under a second); a fast path for tables without ties and a slower exact path only for tied groups; a seeded `numpy.random.Generator`, so the same seed, inputs and rule version give byte-identical output; no model code runs inside the loop (probabilities are computed once per fixture before simulating).

**Static versus dynamic strengths.** The first version uses *static* probabilities fixed at the cut-off (as Phase 2 does), which slightly understates how simulated results change team strength and therefore slightly understates uncertainty. A *dynamic* mode (Elo updated after each simulated match) is an optional later stage that must beat the static mode in the backtest before it is offered.

## 3. Using the frozen probabilities (v1 primary, v2-r1 experimental)

* **Club v1 is the only default.** Its per-fixture probabilities come from the existing forecast engine (`app/predict.py`, same time-safe rules): the features of a fixture use only results dated strictly before the fixture, and for fixtures after the newest result the cached state at the cut-off is used (exactly equal to the day-by-day replay, tested in Phase 2). About 40 ms per fixture, so roughly 10-15 seconds for a full league, computed once and cached by an input hash (cut-off date, store content hash, model artifact hash).
* **Club v2-r1 stays experimental.** It can be run as a labelled *sensitivity* simulation beside v1, never as the default, never averaged with v1 and never described as validated; every v2-r1 result carries the existing "experimental, development-validated only" tag. It has no clean historical backtest (finding 2), so no accuracy claim is made for it.
* **Measured quality of v1 for these leagues** (frozen reports, log loss, lower is better; a constant 1/3 gives 1.099): test 2024-25 Bundesliga 1.018, Premier League 0.990, La Liga 0.978, Serie A 0.974, Ligue 1 0.967; forward holdout Bundesliga 0.964, Premier League 1.044, La Liga 0.976, Serie A 0.991, Ligue 1 1.006. Differences from the Elo baseline are tiny; v1 is a modest, well-calibrated model, so simulated title probabilities will be wide, and the page must say so.
* **No retraining, no recalibration, no change of any frozen file.** The simulator only reads probabilities.
* The model's draw probability is nearly flat (about 0.26) because draws are weakly predictable (documented draw AUC about 0.55). The simulator uses it as given.

## 4. Generating scorelines from home/draw/away probabilities

Goals matter for goal-difference and goals-scored tie-breaks (and, in practice, decide who is 2nd or 17th far more often than head-to-head). Three candidate methods are defined; the choice is made on data (section 5), not by preference.

* **S1 Conditional Poisson (the plan's proposal).** Draw the outcome from the v1 probabilities. Then draw the scoreline from independent Poisson goals with expected goals λ_home, λ_away, **restricted to scorelines consistent with the drawn outcome** (probability ∝ Pois(h; λ_home)·Pois(a; λ_away) over cells with the right result), truncated at a high goal count. λ comes from the v2 feature generator's attack/defence strengths (`lambda_home`, `lambda_away`), which are computed with the same time-safe state. Because v1 fixes the outcome, v1's probabilities are reproduced exactly; only the margin and total goals come from λ. Weakness: when v1 and λ disagree about who is favoured, the conditional margin is somewhat off.
* **S2 Outcome-matched Poisson.** Solve for λ_home, λ_away so that an independent Poisson reproduces v1's P(home) and P(away) exactly (two equations, two unknowns), anchor the total goals to the league mean, then sample scores directly. Consistent by construction; total goals can drift.
* **S3 Empirical conditional bootstrap.** Sample a real historical scoreline from the same league (fallback: pooled leagues), the same outcome, and the nearest bucket of the strength gap (v1's P(home)−P(away)), using only matches **before** the cut-off. Non-parametric, so it keeps fat margin tails and the real 0-0/1-1 draw shares; needs enough matches per bucket (about 14,000 league matches exist).

Scoreline caps (e.g. no more than 9 goals per team) are explicit, and a fixture with an unknown λ (new club, thin history) falls back to league-average rates with a flag.

## 5. Is conditional Poisson appropriate, and how will it be validated?

**Judgement before data: appropriate as a first model, not proven.** It is conditioned on v1's outcome, so the known weakness of independent Poisson (draw frequency off) does not enter. Remaining weaknesses: independence of goals, a single λ pair per match, no allowance for the fatter margin tails of real football.

**Measured sanity check (no model, league-average goal rates, completed matches 2018-19 to 2025-26, pooled by league).** Share of 1-goal margins among home wins (Poisson / actual): Serie A 0.517/0.510, La Liga 0.511/0.538, Ligue 1 0.506/0.488, **Premier League 0.500/0.449, Bundesliga 0.466/0.395**; mean goal margin in home wins: Premier League 1.79/1.93, Bundesliga 1.88/2.16, Serie A 1.75/1.82, Ligue 1 1.77/1.88, La Liga 1.76/1.75. Draws split into 0-0 / 1-1 / larger well in most leagues (Bundesliga 1-1 share 0.450/0.483). So with league-average λ the margin is slightly **too small in the Premier League and Bundesliga**; team-specific λ will spread margins and may close part of that gap, which is exactly what the validation must show. This was a check of the idea, not a validation of S1.

**Validation protocol (offline, data-only, run in milestone M2, before the simulator is built):**
1. Fit nothing on the v1 test or holdout labels. Any scoreline parameters or buckets use matches dated before 2024-07-01 only.
2. Score S1, S2, S3 on matches 2024-07-01 onward (the same windows as section 10), using each fixture's real pre-match v1 probabilities and λ computed time-safely.
3. Metrics, per league: (a) mean and distribution of goal difference given each outcome (Kolmogorov-Smirnov or chi-square against actual, with a bootstrap interval); (b) share of 1-goal wins and of 0-0, 1-1, 2+ draws; (c) mean total goals; (d) the log score of the actual scoreline (which also checks consistency with v1); (e) **end-to-end:** team-season goal difference and goals scored, simulated versus actual, over the backtest cut-offs (mean error, interval coverage).
4. **Pre-registered acceptance rule** (written before the run): a method is acceptable if, in every league, mean goal margin given an outcome is within ±0.10 goals of actual and 1-goal-win share within ±0.05, and its simulated season goal differences cover the real ones at about 80% for the 10-90% interval (acceptable 70-90%). The method with the better end-to-end score among acceptable ones is chosen; if none is acceptable, S3 is the fallback.
5. **Sensitivity of the answers:** run the full simulator under all three methods; if title, top-four and relegation probabilities differ by less than the Monte Carlo error (about 1 point), the choice is immaterial and S1 stays for simplicity; otherwise the spread is shown on the page.

## 6. Official tie-break and position rules (per league, season specific)

Engine design: each league is a **versioned rule profile** (season range, ordered criteria, play-off rules, relegation and position bands, source, date retrieved, status). The profile in force for the *season being simulated* is used, so past seasons (backtest) use their own rules. Mini-table (head-to-head) criteria apply to the clubs still tied. **Unresolved for every league:** whether, after a multi-club tie is partly resolved, the procedure restarts from the first criterion for the remaining clubs; the plan is to implement the written text literally and to flag any league where the text is silent. Criteria needing data we do not hold (cards for fair-play) are treated as unresolvable and fall through to the last resort; the effect is negligible and is measured.

| League | Order for clubs level on points | Play-offs / last resort | Status of the source |
|---|---|---|---|
| **Premier League** | 1 goal difference, 2 goals scored, 3 points in head-to-head matches, 4 away goals in head-to-head matches | one-off play-off at a neutral venue (title, European place or relegation decided) if still level; never needed in the league's history | **Partly verified.** Premier League explainer pages for 2025/26 and an official article for 2019/20; the Handbook page could not be retrieved (404). 2026/27 text not read |
| **Bundesliga** | 1 goal difference, 2 goals scored, 3 head-to-head aggregate score, 4 away goals in head-to-head, 5 total away goals | decider on a neutral ground; during the season, with both head-to-head matches not yet played, only 1-2 apply and clubs can share a place | **Partly verified.** bundesliga.com article of 15.04.2024; DFL regulations (2026-27) not read |
| **La Liga** | two clubs: head-to-head first (goal difference of the two matches) then overall goal difference, then goals scored; three or more clubs: head-to-head points, head-to-head goal difference, overall goal difference, goals scored, then fair-play | tie-break match on neutral ground if still level (older RFEF text) | **Unresolved.** Only secondary sources and an RFEF article quoted through them (older editions); a LaLiga article about the second division confirms head-to-head goal difference before overall goal difference. Whether two clubs use head-to-head points or goal difference first, the exact current text and the fair-play step must be confirmed from the RFEF General Regulations |
| **Serie A** | 2026-27, verified: for ties of more than two clubs, and for all other positions, a mini-table ("classifica avulsa") on **a** points in head-to-head matches, **b** goal difference in head-to-head, **c** overall goal difference, **d** overall goals scored, **e** drawing of lots | **Title:** two clubs level on points play one match at the home ground of the better avulsa-ranked club (no extra time, straight to penalties). **17th/18th level:** two legs, the better avulsa-ranked club hosts the second leg, more goals over two legs wins, else penalties. Special rule if a club is a UEFA finalist | **Verified** from FIGC Comunicato Ufficiale 244/A (27 May 2026) |
| **Ligue 1** | for 2025/26: 1 overall goal difference, 2 head-to-head points, 3 head-to-head goal difference, 4 best attack, 5 most wins, 6 most away wins, 7 fewest discipline points (yellow 1, red 3), 8 drawing of lots; away-goals criteria removed in 2025 | drawing of lots | **Partly verified** from ligue1.com (8 July 2025, for 2025/26). 2026/27 text not read. Seasons before 2025/26 used older criteria with away goals (backtest needs those) |

**Position bands (what "top four" and "relegation" mean).**
* **Title:** final position 1 (with the play-off rules above).
* **Top four:** final position 1-4. The page says "finishing in the top four", **not** "qualifying for the Champions League", because the number of European places depends on UEFA's allocation, which varies by year and is not sourced here (decision D8).
* **Relegation:** Premier League positions 18-20 (three clubs, verified on the Premier League page). Bundesliga positions 17-18 direct, **16th plays a two-legged play-off** against the 2. Bundesliga third place (secondary description; shown as its own band, "relegation play-off place", never as relegated). Serie A: the FIGC text confirms a 17th/18th play-off on equal points; **the number of relegated clubs and the 2026-27 relegation rule beyond that text are unresolved**. La Liga (three clubs expected) and Ligue 1 (18 clubs; direct places and play-off) are **unresolved** pending sourcing.
* Play-off outcomes (title, 17th/18th, 16th) are simulated as one match or two legs using the club probabilities at a neutral or home venue as the rule says; where this is a modelling assumption (decision D6) it is shown on the page. A play-off was only ever triggered by exact ties after all criteria, so the probability of it occurring is reported with each result.

## 7. Missing or stale results: eligibility and reliability

* **No result is invented.** Fixtures dated in the past without a verified result stay in the remaining set and are **simulated like future fixtures** (with a flag), because their true results exist but are unknown to us. This widens the answer honestly instead of silently pretending those games did not happen.
* **Reliability states (proposed thresholds, decision D4):**
  * **Ready:** at most 2% of fixtures dated up to today lack a verified result, newest result at most 7 days old.
  * **Provisional:** at most 15% missing and newest result at most 21 days old; every output shows a "Provisional" banner and the reasons.
  * **Not eligible:** otherwise; the run button is disabled by default (an explicit "run anyway" shows an "Unreliable: missing results" watermark and is saved as such).
  * Also provisional or not eligible: unresolved team identities, quarantined fixtures that change the table, a rule profile marked unresolved.
* **Applied to today's data:** Bundesliga Ready; La Liga Ready (one missing result, 1.1%, the held Rayo Vallecano v Athletic Club postponement; shown as a flag); Premier League **Not eligible** (15 of 75 played-date fixtures, 20%, newest result 13 days old; it would be Provisional if the threshold were 20%); Serie A and Ligue 1 **Not eligible** (about 29-33% of played-date fixtures without a result, 35 days stale). These classifications would change as soon as fresher data are approved; the simulator itself does not need to change.
* **What staleness does to the numbers:** the model state is as old as the newest result, so form and ratings lag; fixtures many weeks away use that state (known limit, shown). Missing results do not enter the table, so points totals of affected clubs are understated until recovered; the banner states how many matches and which clubs are affected.

## 8. Postponed matches, date conflicts and unknown kickoff times

* **Postponed (status `postponed`) and unplayed fixtures with a placeholder date** (for example Rayo Vallecano v Athletic Club, held at 2026-10-10 in the store versus 2027-05-30 in the source): the match must still be played before the season ends, so it is simulated as a remaining fixture, **regardless of its date**. Season-end results do not depend on dates when strengths are static.
* **Cancelled, abandoned or awarded matches:** treated by status (awarded results count; abandoned and cancelled without a decision are excluded and flagged). Needs an explicit rule per case (decision D7).
* **Date conflicts** (the 55 held fixtures, and any future ones): the store date is used for ordering and for the "strictly before" feature rule; the conflict is shown as a flag. In the static mode a date conflict cannot change a result probability, only the dynamic mode's order of updates, and the effect is bounded by the one or two days involved. Fixtures whose two dates straddle the cut-off (the five La Liga Matchday 10 games with a held result) are flagged as "result possibly available but not imported".
* **Unknown kickoff times:** the Phase 2 rule is kept: a fixture is featurised from results dated strictly before its own date, so a same-day result can never leak into it. Kickoff time changes nothing else. "Played already today" cannot be decided without a kickoff, so fixtures dated on the cut-off day with no result are treated as remaining.
* **Played earlier than the stored date** (source says played, store says later): the real table is unchanged until the result is imported; the flag appears with the eligibility banner.

## 9. Outputs and how each is calculated

Let `rank_i^(s)` be club i's final position in simulation s (after tie-breaks), N the number of simulations.
* **Position distribution:** P(rank=k) = fraction of simulations with rank k, a clubs × positions matrix whose rows and columns each sum to 1 (a test).
* **Title probability:** P(rank=1); the column sums to 1 across clubs.
* **Top-four probability:** P(rank ≤ 4). **Relegation probability:** P(rank ≥ N_clubs − r + 1) with r the relegated places for the league; **relegation play-off place** reported separately where it exists (Bundesliga 16th, Serie A 17th/18th decider).
* **Expected points:** mean final points, with the 10th-90th percentile interval; also expected goal difference and expected rank (and its interval).
* **"Mathematically decided" flags** where probability is exactly 0 or 1 (with the game states shown), and the share of simulations in which a tie-break beyond goal difference or a play-off was needed.
* **Run metadata always shown:** league, season, cut-off date, number of simulations, seed, model id and artifact hash, scoreline method, rule profile and its source/date, eligibility state and reasons, number of missing/simulated-played fixtures, and the standard error.

## 10. Backtesting on completed seasons without future-data leakage

**What is truly out-of-sample.** Club v1: 2024-07-01 to 2025-06-29 (test, evaluated once and locked) and 2025-07-02 onward (forward holdout, including the complete 2025-26 season). 2023-24 is the validation season used to pick the regularisation constant, so it is shown only as "validation (lightly selected)". Seasons up to 2022-23 are in-sample for v1's weights. **Club v2-r1 has no out-of-sample season.**

**Proposed primary backtest (no new fitting):** club v1, five leagues, seasons 2024-25 and 2025-26 (plus 2023-24 labelled), 10 league-seasons, cut-offs after 25%, 50% and 75% of the fixtures (and one after the first 10 matchdays). A secondary, **separately approved** option (decision D5) would refit **copies** of the v1 specification, same hyperparameters, expanding-window per season (train strictly before each season), to extend the evidence back to 2020-21; the copies are research-only and never replace any frozen artifact. The refit option makes no claim about the shipped model.

**Leakage controls (each has a test):**
1. For a cut-off date D, the state is rebuilt from results dated **strictly before** D only; every remaining fixture's probabilities come from that state. A test replaces all results dated on or after D with random scores and asserts **bit-identical** probabilities and simulation output.
2. Remaining fixtures are the season's real fixture list (known in advance); only their results are hidden.
3. Standings at D are computed from results before D only; the realised final table comes from the full season afterwards and is used only for scoring.
4. The season's own rule profile is used for both simulation and the realised ranking (Ligue 1 before 2025/26 used away goals, so older rules must be sourced; where a realised event depends on an unsourced tie-break, that team-event is excluded and counted).
5. Scoreline method and any threshold are fixed **before** the backtest using pre-2024 data; the backtest is run once under a lock file with input hashes, in the manner of the v1 evaluation lock, and its report is labelled "retrospective evidence, not the official prospective evaluation". No official prospective file is read or written.
6. No tuning on results: if a method fails the pre-registered rule, the result is reported as a failure and is not re-tuned on the same seasons.

**Metrics.** For each event (title, top four, relegation): Brier score and log loss of the simulated probabilities against what happened; reliability (calibration) table pooled over cut-offs; for points: mean absolute error and bias of expected points, and coverage of the 10-90% interval (target near 80%); for positions: the ranked probability score of each club's position distribution. **Baselines:** (a) current points-per-game extrapolation, (b) the same simulator with Elo-only probabilities, (c) equal-strength simulation. The simulator must beat (a) and (c) to be called useful; (b) is the closest comparison.

**Honest limits.** Ten to fifteen league-seasons contain only about 10-15 titles and about 30-45 relegations, so confidence intervals will be wide; calibration claims are indicative at best, and the report states the sample sizes next to every metric.

## 11. Integration into the existing FootIQ database and UI

**Database.** The `simulation_runs` table already exists (`created_utc, competition_key, season, n_simulations, seed, model_id, data_cutoff_date, assumptions_json, result_json`). Proposal: **no schema change**; `assumptions_json` stores method, rule profile id and source, eligibility, input hash and artifact hashes; `result_json` stores per-club expected points, probabilities and the position matrix (at most 20×20 numbers). A run is **saved only when the user presses "Run season simulation"**, as with gameweek forecasts, is never overwritten, and is labelled "Application simulation, not the official prospective evaluation". Nothing is written to research folders. Rule profiles live in a versioned config file in the repository, with a test that every profile has a source and retrieval date.

**API (new, read-only unless the POST is called):**
* `GET /api/season/status?key=&season=`: eligibility state, reasons, rule profile and its verification status, assumptions; computes nothing.
* `POST /api/season/simulate` with `user_action="simulate_season_button"`, league, season, n (capped), optional seed and method: validates eligibility, computes, saves, returns the run. Wrong `user_action` returns 422 and saves nothing.
* `GET /api/season/runs` and `GET /api/season/run?id=`: history and a stored run.
* Uniform `{"detail"}` errors, as elsewhere. The existing World Cup simulator, bracket and every current endpoint are unchanged.

**UI (reusing the existing design system).** A **Season** tab on the Simulator page (or its own page, decision D9) for the five domestic leagues: league and season selectors; an eligibility banner (Ready, Provisional, Not eligible, with reasons and a link to the data-freshness panel); predicted final table (expected points with the 10-90% interval, expected rank); probability bars for title, top four and relegation (plus play-off place); a position heat-map (club × position) with accessible text alternative; an "Assumptions and method" drawer (model and version, scoreline method in plain words, rule profile and source with verification status, simulation count, seed, cut-off date, standard error, missing-result list); saved-run history; v2-r1 sensitivity shown only as a separate, labelled "Experimental" comparison. Mobile-first (cards instead of wide tables below 640 px, no horizontal overflow). Wording avoids "will win" and betting language.

## 12. Implementation roadmap and required tests

| Milestone | Content | Exit criteria |
|---|---|---|
| **M0 Decisions and sources** | your answers to section 14; obtain the RFEF/LaLiga, DFL, Premier League Handbook, LFP 2026-27 rule texts, relegation counts and play-off formats; write the rule profiles as data | every profile has a verified source or is explicitly marked unresolved and blocked |
| **M1 Engine core** (no models) | table builder, scoreline sampler interface, vectorised simulation, tie-break engine, outputs, seeded determinism | all engine tests pass; same seed byte-identical |
| **M2 Scoreline study** | the validation protocol of section 5 on pre-2024 and 2024+ data, written report | pass/fail against the pre-registered rule; method chosen |
| **M3 Probability provider and eligibility** | per-fixture v1 probabilities and λ at a cut-off, caching by input hash, eligibility classifier, flags | equals the Phase 2 forecast engine on the same fixtures; time-safety test passes |
| **M4 Backtest harness and one locked run** | section 10, lock file, report | report with sample sizes; no leakage test fails |
| **M5 Persistence and API** | save-on-press, history, validation, caps | API contract tests; production store untouched until you approve |
| **M6 UI** | Season tab, drawer, history, mobile | component and live-contract tests; browser check at 375 px and desktop |
| **M7 Regression and documentation** | full backend and frontend suites, build, hashes, report with a simple explanation | all green; frozen hashes unchanged |
| **M8 Optional dynamic mode** | only if M4 shows static mode is under-dispersed | beats static in a locked backtest |

**Required tests (to be written with the code):**
* *Engine:* zero remaining fixtures gives the real table with probability 1; every probability matrix is row- and column-stochastic; title probabilities sum to 1; probabilities in [0,1]; same seed gives identical output and different seeds differ; convergence between 10,000 and 50,000 runs is within sampling error; monotonicity (raising a club's win probabilities never lowers its expected points).
* *Tie-breaks:* constructed tables for each league covering two-club and multi-club ties, criteria in order, head-to-head with both legs played and not played, the Serie A mini-table and its title and 17th/18th play-offs, Ligue 1 deeper criteria (and the lots fallback), Bundesliga shared place in-season, Premier League play-off trigger, La Liga variants (each unresolved reading in a clearly named test).
* *Scorelines:* conditional sampler returns only scores consistent with the outcome; outcome frequencies reproduce the input probabilities within sampling error; goal caps respected; fallback when λ is missing.
* *Probabilities and leakage:* equality with the forecast engine; scrambling results dated at or after the cut-off leaves output bit-identical; same-day results are excluded; postponed and placeholder-dated fixtures are simulated once and only once; a fixture with a held date conflict is flagged.
* *Eligibility:* thresholds at the boundaries; unresolved identity, quarantined fixture and unresolved rule profile each downgrade the state; today's five leagues classify as in section 7.
* *Persistence and API:* GET never saves; POST with a wrong `user_action` is 422 and saves nothing; each press adds a run; no write under any research folder (fingerprint test); caps on simulation count; production and frozen-model hashes unchanged.
* *Backtest:* lock file prevents a second run; metrics reproduce on stored predictions; sample sizes reported.
* *UI:* banner states, drawer contents, saved-run history, 375 px layout without horizontal scroll, accessible names, no betting or certainty wording.

## 13. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Stale or incomplete data (3 of 5 leagues today) | the simulator is correct but the inputs are not | eligibility gating, simulating missing fixtures, visible banners; fresher sources need your approval |
| Unresolved or unverified tie-break text (La Liga, Ligue 1 2026-27, DFL, Handbook) | wrong order in tied cases (small but real for goal-difference battles) | versioned profiles, literal implementation, "unresolved" blocks, sensitivity runs under each reading |
| Scoreline assumption | biased goal difference changes tied positions | M2 validation, three methods, sensitivity shown |
| v1 is a modest model | wide probabilities, little separation | honest wording, calibration shown, no "prediction of the champion" claims |
| Static strengths | under-dispersed outcomes | stated limitation, optional dynamic mode, backtest coverage check |
| Tiny backtest sample (10-15 league-seasons) | cannot prove calibration | report sample sizes; call the evidence indicative; optional refit copies (D5) |
| v2-r1 has no out-of-sample season | cannot be validated | stays experimental, labelled |
| Relegation and European slots vary by season and league | wrong band definitions | bands only where sourced; "top four" never called qualification |
| Play-off format assumptions | small, but affects title/17th-18th probabilities | explicit assumption, reported frequency of occurrence |
| Performance (first probabilities about 10-15 s) | slow first click | cache by input hash, precompute at request time with progress |
| Scope creep into live sync | would break the approval boundary | the simulator reads the store only; sync settings untouched |

## 14. Decisions needing your approval

| # | Decision | Recommendation |
|---|---|---|
| D1 | Approve this design as the Phase 3 scope (engine, scoreline study, backtest, API, UI) | approve milestones M0-M7; M8 later |
| D2 | Scoreline method: S1 conditional Poisson as default, S2/S3 as challengers, chosen by the pre-registered rule | approve |
| D3 | Static probabilities first, dynamic mode only if justified | approve |
| D4 | Eligibility thresholds (2%/7 days Ready; 15%/21 days Provisional; else blocked with "run anyway" watermark) | approve; note it blocks Premier League, Serie A, Ligue 1 today |
| D5 | Backtest scope: frozen v1 on 2024-25 and 2025-26 only (clean), or also refit research copies back to 2020-21 | clean only first; copies only if you want more history |
| D6 | Play-off assumption: simulate title, 17th/18th and 16th play-offs from club probabilities (home ground per the rule) | approve, with the occurrence rate shown |
| D7 | Rule for cancelled and abandoned matches | exclude and flag; awarded counts |
| D8 | Wording: "finishing in the top four" and position bands only, no European qualification claims until UEFA allocation is sourced | approve |
| D9 | UI placement: Season tab on the Simulator page, or its own page | tab first |
| D10 | Save runs only on pressing the button, in `simulation_runs`, no schema change | approve |
| D11 | Sourcing: allow me to read official regulation texts for La Liga, Ligue 1 2026-27, Bundesliga, Premier League Handbook and relegation counts (public pages only, no sync) | approve; until read, those profiles stay marked unresolved |
| D12 | Whether a data-freshness source for the Premier League, Serie A and Ligue 1 should be pursued before or in parallel with Phase 3 | in parallel, as a separate approval |

**Sources read for the rules** (retrieved 2026-10-25; none replaces the rulebook for the season being simulated):
* Premier League, relegation and tie-break explainer 2025/26: [premierleague.com](https://www.premierleague.com/en/news/4638928/the-run-in-202526-your-relegation-questions-answered); head-to-head and play-off order (2019/20): [premierleague.com](https://www.premierleague.com/en/news/1262217). The Handbook itself was not retrieved.
* Bundesliga tie-break order (15 Apr 2024): [bundesliga.com](https://www.bundesliga.com/de/bundesliga/news/meisterschaft-bundesliga-punkt-tor-gleich-kriterien-torverhaltnis-direkter-vergleich-2921); relegation play-off overview: [bundesliga.com](https://www.bundesliga.com/en/news/Bundesliga/noblmd34-what-is-the-relegation-promotion-play-off.jsp) (title only was confirmed).
* Serie A 2026/27 (primary): FIGC Comunicato Ufficiale 244/A, Federal Council 26 May 2026, published 27 May 2026: [figc.it](https://files.figc.it/version/c:ZmUzYzk0MzUtMzU0Zi00:YTk3YzZiZGEtYmExYi00/244%20-%20Deroga%20art.%2051%20NOIF%20-%20Determinazione%20classifica%20Campionato%20Serie%20A%20ss%202026%20-%202027.pdf). Number of relegated clubs not stated in it.
* Ligue 1 criteria for 2025/26 (8 Jul 2025): [ligue1.com](https://ligue1.com/en/articles/l1_article_2830-).
* La Liga (indicative only): [laliga.com, 28 May 2024, second division](https://www.laliga.com/en-GB/news/the-laliga-hypermotion-drama-continues-direct-promotion-playoff-places-and-survival-all-on-the-line); [Goal.com on the RFEF article (LaLiga 2022-23)](https://www.goal.com/es/noticias/como-se-decide-que-equipo-queda-delante-en-la-liga-en-2022-2023-en-caso-de-empate-e-igualdad-de-puntos/blt7a7117a8ceba628c). The RFEF General Regulations text was not retrieved.

---

## 15. Simple explanation

**What we examined.** How many results each league has, how fresh they are, how the models were trained and tested, what our prediction models can and cannot say, and what the official rules say when two clubs finish on the same points. We also checked, with real past matches, whether a simple way of inventing scores looks believable.

**The problem we are solving.** Fans ask "who will win the league, who finishes in the top four, who gets relegated?" Our models only say, match by match, how likely a home win, a draw or an away win is. Nobody can read a final table off 300 separate match chances. A season simulator turns those chances into a final-table forecast.

**The challenges we found.**
1. Three of the five leagues are missing recent results, so a forecast today would rest on old information. We plan to block or warn instead of pretending.
2. League tables are often decided by goal difference, but our models do not predict goals. We have to invent scores in a way that is honest, and show that we did.
3. Each league breaks ties differently, and the rules change from year to year. Serie A's 2026-27 rule is confirmed from the federation's own document; La Liga's is not yet confirmed.
4. We can only test the simulator fairly on seasons the model never saw during training: two seasons per league. That is a small test, so we will say so.

**How the simulator would work, with a football example.** Imagine La Liga today. Barcelona have 27 points after 9 games and 29 games remain. For each remaining game the model gives chances; take an *invented* example: Barcelona v Sevilla, 62% Barcelona win, 22% draw, 16% Sevilla win. The simulator rolls a weighted dice for that game. Say it rolls "Barcelona win"; it then picks a believable score that fits a Barcelona win, such as 2-0 (it never picks 1-1, because the dice said "win"). It does this for all 29 Barcelona games and all remaining games of every club, adds up points and goals, and sorts the table using the official rules (for example, if two clubs are level, goal difference or head-to-head decides, depending on the league). That is one imagined season. It repeats this 10,000 times with different dice rolls. If Barcelona finish first in 6,100 of the 10,000 imagined seasons, we show "title chance about 61%, give or take 1 point". The same counting gives the chance of finishing in the top four, the chance of relegation, the average points and a chart of every possible final position. These numbers are illustrative; no real forecast has been produced yet. We will test the whole machine on past seasons by pretending to stand at, say, matchday 10 with only the information available then, and comparing our forecast with what actually happened.

**What remains to be decided.** Your approval of the plan and of the choices in section 14: how strict to be about missing data, which score-invention method to use, whether to test only on the clean seasons, how to word "top four", and permission to read and record the official rules for La Liga, Ligue 1, the Bundesliga and the Premier League. A separate decision is still needed on getting fresh data for the Premier League, Serie A and Ligue 1.

**Viva-ready explanation (about 40 seconds).** "Our models only give win, draw and loss probabilities for each match. To forecast the final league table I use Monte Carlo simulation: for every remaining fixture I roll a weighted dice from the model's probabilities, pick a score that fits the result, update the table with each league's official tie-break rules, and repeat that 10,000 times. Counting how often a club finishes first, in the top four or in the relegation places gives the probabilities. The models are never changed; the simulator only reads their probabilities. It refuses or warns when results are missing, because stale data would mislead. I will test it only on past seasons the model never trained on, standing at a mid-season date with the information available then, and I will report the small sample honestly. The score-inventing step is an explicit, tested assumption, and the page shows every assumption it makes."
