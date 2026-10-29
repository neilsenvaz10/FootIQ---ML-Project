# Phase 3 implementation report: domestic league season simulator (controlled implementation)

> **Superseded in part on 2026-10-25 by [PHASE3_POINTS_ONLY_REPORT.md](PHASE3_POINTS_ONLY_REPORT.md):** final deciders are no longer simulated as a fair coin (decision D6: they stay unresolved and probabilities are withheld), and an Experimental points-only mode was added.

Date: 2026-10-25. Nothing is staged, committed or pushed. No frozen model, training file, official prospective-evaluation file, `config/sync.json` (`live_enabled` false) or production data was changed by this phase; the production store holds 0 saved simulations. No network request was made to any data provider (only public regulation documents were read).

## 1. Where this stopped, and why

**The scoreline acceptance rule failed for all three candidate methods, so final league-position predictions are disabled** (`config/season_sim.json`: `scoreline_method: null`). Everything that does not depend on that choice is built and tested; the Run button is switched off by the backend until you decide. Details and options: [PHASE3_SCORELINE_BENCHMARK.md](PHASE3_SCORELINE_BENCHMARK.md). The title / top-four / relegation backtest (M4) was **not run**, because it would score a method that has not been approved.

## 2. Reconciliation of D1-D12 with your instructions

| # | Decision in PHASE3_PLAN.md | Your instructions | Status |
|---|---|---|---|
| D1 | Approve the plan | Controlled implementation, Bundesliga and La Liga first, stop at the plan's approval boundaries | **Resolved, narrowed.** Built M0, M1, M2, M3, M5, M6, M7. M4 (position backtest) and M8 (dynamic strengths) not started |
| D2 | S1 default, S2/S3 challengers, chosen by the predeclared rule | Benchmark all three; do not auto-select S1; stop if none passes | **Resolved and executed: none passed, stopped** |
| D3 | Static probabilities first, dynamic mode only if justified | Not mentioned | **Not explicitly resolved.** Implemented static only (what "the planned engine" is); the dynamic mode is untouched. Please confirm |
| D4 | Eligibility thresholds (2% / 7 days Ready; 15% / 21 days Provisional) | "Use the proposed gates" | **Resolved.** Implemented as proposed. Today: Bundesliga and La Liga Ready; Premier League, Serie A, Ligue 1 Not eligible |
| D5 | Clean seasons only, or also refit research copies | Genuinely out-of-sample seasons only; do not retrain | **Resolved: clean seasons only** (2024-25 and 2025-26 for frozen v1). No refit copies were made |
| D6 | Simulate play-offs / neutral-ground deciders | Not mentioned | **Unresolved.** A final decider is simulated as a fair coin (placeholder) and its frequency is reported on every run; the Bundesliga 16th-place play-off is shown as a band, not simulated. Please decide |
| D7 | Treatment of cancelled / abandoned matches | Not mentioned | **Unresolved.** Any such fixture makes the league Not eligible until you decide (none exist today) |
| D8 | "Top four" means positions 1-4, not UEFA qualification | "Top-four finishing probabilities" | **Resolved.** Wording used throughout |
| D9 | Where the UI goes | Season Simulator tab on the existing Simulations page | **Resolved.** The existing World Cup page (previously the nav item "World Cup") is now the first tab, unchanged, under the nav item "Simulations" (routes `/worldcup` and `/simulations`). The nav label change is a small addition beyond "add a tab" |
| D10 | Save runs only on pressing the button, in `simulation_runs` | "Simulations must run only on explicit user action" | **Partly resolved.** Running and saving happen only on the button, as with the Phase 2 forecasts. Saving was not explicitly approved in this round; zero runs are saved in production. Please confirm |
| D11 | Read official 2026-27 rules for La Liga, Ligue 1, Bundesliga, Premier League | Approved; implement only verified rules; keep unresolved blocked | **Resolved and executed** (section 3) |
| D12 | Fresher sources for Premier League, Serie A, Ligue 1 | Research only; no new APIs, accounts or imports | **Resolved.** Research only (section 7) |

Conflicts with your approvals: none found. Items needing your confirmation: D3, D6, D7, D10.

## 3. Official 2026-27 rules (primary documents read; sha256 recorded under `data/supervised/rules_research/`, git-ignored)

| League | Result | Source | Used? |
|---|---|---|---|
| Bundesliga | **Verified.** Goal difference, goals scored, head-to-head aggregate, head-to-head away goals, total away goals, neutral-ground decider; 2 relegated, 3rd-last plays the 2. Bundesliga third in two legs | DFL Spielordnung (SpOL), Stand 11.06.2026, para 2 no. 3 c) and para 3 no. 2 | Yes |
| La Liga | **Verified.** Two clubs: head-to-head goal difference, overall goal difference, goals scored, fair play, neutral-ground match. More than two: mini-table points, mini-table goal difference, overall goal difference, goals scored, fair play, neutral-ground match. Positions 18-20 relegated | RFEF, Normas reguladoras y bases de competicion, Primera y Segunda Division, temporada 2026-2027, art. 10 and art. 8 no. 7. **Access note:** rfef.es refuses automated downloads (Cloudflare), so the text came from the Internet Archive copy of the same URL; please re-check it against the live federation page | Yes |
| Premier League | **Verified.** Goal difference (C.5), goals scored (C.6), head-to-head points (C.17.1), head-to-head away goals (C.17.2), two-club play-off (C.17.3); bottom three relegated (C.14) | Premier League Handbook 2026/27 | Yes (data-gated: Not eligible, outside the initial scope) |
| Serie A | Tie-break order **verified** (FIGC CU 244/A, 27 May 2026) but the number of relegated clubs is not in it and the title and 17th/18th play-off procedures are not implemented | FIGC | **Blocked** |
| Ligue 1 | The **2026/27** LFP regulation could not be located; the official **2025/26** text (art. 518 ter) was read but is a different season | LFP | **Blocked** |

Where the text is silent the engine follows the literal wording and reports the interpretation (for example, three-club ties for the head-to-head criteria, and the fair-play criterion, for which FootIQ holds no card data). All of this is shown in the app's assumptions panel and stored with every run.

## 4. What was built

| Piece | Files |
|---|---|
| Rule profiles (versioned, status-gated, with source hashes) | `config/season_rules.json`, `app/seasonsim/rules.py` |
| Monte Carlo engine: seeded sampling of score distributions, table rebuild, league-specific tie-break procedures, outputs (title, top four, relegation, play-off band, expected points with 10-90% interval, expected rank, position matrix, tie-resolution frequencies) | `app/seasonsim/engine.py` |
| Scoreline methods S1, S2, S3 | `app/seasonsim/scoreline.py` |
| Eligibility gate (Ready / Provisional / Not eligible, reasons, scope, rule and scoreline gates) | `app/seasonsim/eligibility.py`, `config/season_sim.json`, `settings.py` |
| Probabilities from the frozen v1 (primary) and v2-r1 (experimental comparison), run persistence in `simulation_runs` (no schema change), run history | `app/seasonsim/service.py` |
| API | `GET /api/season/status`, `POST /api/season/simulate`, `GET /api/season/runs`, `GET /api/season/run` (see API_REFERENCE.md) |
| Benchmark and backtest harness (time-safe cut-off states) | `m2_data.py`, `m2_benchmark.py`, `backtest.py`, `m2_rule_power.py`, `m2_s4_tuning.py` |
| UI | `frontend/src/pages/SeasonSimulator.jsx`, `Simulations.jsx` (tabs), nav and routes |
| Tests | `tests/test_seasonsim_engine.py` (12), `tests/test_seasonsim_service.py` (10), `frontend/tests/season.test.jsx` (6) |

**Today's gate results** (`GET /api/season/status`, 2026-10-25): Bundesliga Ready (61 results, newest 1 day old); La Liga Ready (1 fixture without a result, 4 days old); Premier League Not eligible (15 of 75 played-date fixtures without a result, 13 days old); Serie A and Ligue 1 Not eligible (about 29% missing, 35 days old). **Every league is still blocked from running**, because no scoreline method is approved. Premier League, Serie A and Ligue 1 are additionally outside the approved initial scope and are never presented as reliable.

## 5. Scoreline benchmark in one table

| | Bundesliga | La Liga | Premier League | Serie A | Ligue 1 | Passes every league |
|---|---|---|---|---|---|---|
| S1 conditional Poisson | pass | fail | fail | fail | pass | **no** |
| S2 outcome-matched Poisson | fail | fail | pass | fail | fail | **no** |
| S3 empirical bootstrap | fail by 0.001 | pass | fail | fail | fail | **no** |

Season-level (M2b): pooled goal-difference coverage 73.3% / 71.2% / 74.0% (S1 / S2 / S3) against a nominal 80%; below 70% in the Premier League for all methods. Points coverage, which involves no scoreline model, is also about 75%, pointing to static strengths as the main cause. **A model that was exactly right would pass the predeclared rule in all five leagues only 22% of the time**, so the failure is weak evidence against the models; I did not relax the rule. A shrinkage variant (S4) was tested on validation data only and does not help.

## 6. Verification

| Check | Result |
|---|---|
| Backend, whole suite in one run | **123 passed** (101 earlier + 22 new) |
| Frontend with the live backend (private copy of the database) | **54 of 54 passed** (the 9 live-contract tests included); the 6 new Season simulator tests included |
| Production build | succeeds |
| Pipeline integrity | recomputed v1 probabilities equal the frozen evaluation's stored predictions on 5,504 matches (maximum difference 3.3e-16) |
| Leakage control | a test replaces every result dated on or after a cut-off with random scores and requires bit-identical probabilities |
| Frozen models, original CSVs, prospective-log files, sync config | 17 tracked files identical before and after (sha256) |
| Production database | table fingerprints identical to the post-import values; `integrity_check` ok; `simulation_runs` 0; `forecast_runs` 0 |
| Live access | `live_enabled` false; request ledgers unchanged (4 and 1 lines) |
| Browser check (desktop and 375 px) | disabled state for Bundesliga and Premier League, and, on a private copy with a clearly marked test configuration, a full run with standings, probabilities, position heat-map and assumptions; no horizontal page overflow |

Honest notes: the browser results view was exercised only with a **test-only configuration on a private copy** (the result carries a red "Scoreline method not approved: diagnostic output" chip); the shipped configuration cannot run a simulation. The first backtest-style runs took several minutes because each cut-off replays the full history.

## 7. Data-freshness research (research only; no API contacted, no account, no import)

* **OpenLigaDB:** already investigated; covers the Premier League (about 13 days behind) and La Liga, not Serie A or Ligue 1.
* **football-data.org:** secondary sources say the free tier covers 12 competitions including the Premier League, Serie A and Ligue 1, with delayed scores and 10 requests per minute. The provider's own terms and attribution rules could not be read here; using it needs your reading of its terms, an account and a key (a separate approval).
* **football-data.co.uk (CSV files):** described by third parties as free historical and current results; its licence text was not found; it was marked "do not use" in the earlier investigation and stays so until its terms are read.
* **openfootball:** our stored Serie A and Ligue 1 results stop at 2026-09-20, which shows the repository is not keeping up; its help page promises no update schedule.
* Nothing in this research changes any data or setting.

## 8. Blocked or open

* No scoreline method is approved (your decision; options O1-O6 in the benchmark document).
* Ligue 1 and Serie A rule profiles are blocked; Premier League, Serie A and Ligue 1 data are not eligible; the first of these needs fresher results, the others need sources.
* D3, D6, D7, D10 await your confirmation.
* Static strengths probably under-state uncertainty (coverage about 75% against 80%).
* The position backtest (title, top-four, relegation calibration against baselines) is not run.
* La Liga's rule text should be re-checked by you against the live RFEF page.

---

## What We Did, Problems Faced, and How We Solved Them — Explained Simply

**1. What was implemented and why.** We built the machinery for a "season simulator": a program that takes every match still to be played in a league, uses our football model's win/draw/loss chances, plays the rest of the season thousands of times on the computer, and counts how often each club ends up champion, in the top four, or relegated. We also built the checks that decide whether a league's data is good enough (Ready / Provisional / Not eligible), a library of each league's official tie-break rules (only used when we have checked them against the official 2026-27 documents), the website pages and buttons, and the saved history. We built it carefully because a season forecast built on old or missing results, or on rules we are not sure about, would mislead people.

**2. How Monte Carlo simulation works, with a football example.** Imagine La Liga today. Barcelona and every other club have matches left. For one match, say Barcelona v Sevilla, the model might say (invented numbers) 62% Barcelona win, 22% draw, 16% Sevilla win. The computer rolls a weighted dice: perhaps it gives "Barcelona win", then it picks a believable score for a Barcelona win, such as 2-0. It does that for every remaining match in the league, adds up the points and goals, and sorts the table with the league's rules (for example, if two clubs have the same points, goal difference or the games between them decides, depending on the league). That is one imagined season. It repeats 10,000 times. If Barcelona finish first in 6,100 of them, we show "about a 61% title chance, give or take 1 point". Nothing here is a guarantee.

**3. What problems occurred.** (a) The official rules: some rule documents were hard to get. The La Liga federation's website blocks automated downloads, and the French league's 2026/27 rulebook could not be found. (b) The model only says win/draw/loss, but league tables are often decided by goals, so we need a way to invent scores. We tested three ways, and none passed our strict, pre-written test in every league. (c) Three of the five leagues have missing or old results. (d) The test we wrote is itself very strict: even a perfect model would pass in all five leagues only about 1 time in 5. (e) A first idea to improve the scores by "shrinking" the model's goal estimates did not work. (f) A test of an eligibility rule failed once because I forgot that fixtures dated in the past without results count as "missing" (a mistake in my test, not in the data).

**4. How each problem was fixed or safely handled.** (a) The Bundesliga, La Liga and Premier League rules were read from the official 2026-27 documents and recorded with a fingerprint; La Liga's came from an archived copy of the federation's own file, so we ask you to re-check it; Ligue 1 and Serie A stay **blocked**. (b) Because none of the three score methods passed, the simulation is **switched off** and the options are written up for you; we did not pretend it passed. (c) Leagues with missing or old data are labelled Not eligible, and the button is disabled. (d) We measured how noisy our test is and reported it, but did not change the test. (e) We tried the shrinking idea only on older data, saw that it did not help, and dropped it. (f) The test was corrected and rerun. The Bundesliga, La Liga, Premier League checks, the leakage protection and the whole test suite all pass (123 backend and 54 frontend tests).

**5. Which leagues can now be simulated.** **None can run yet**, because the score method is not approved. Bundesliga and La Liga have good data and verified rules, so they are the first to switch on once you decide. Premier League data is not good enough yet; Serie A and Ligue 1 have neither enough data nor confirmed rules.

**6. Which features remain blocked and why.** Final-position predictions (blocked until you approve a score method). Serie A and Ligue 1 (rules not confirmed for 2026-27; data too old). The Premier League, Serie A and Ligue 1 in general (outside the approved first step and, for now, not eligible). The "did it work in past seasons" test for title and relegation chances (it would test a method that has not been approved). Anything that needs live data or a new data source (not approved).

**7. What changed in the FootIQ interface.** The old "World Cup" menu item is now "Simulations". It has two tabs: "World Cup" (exactly as before) and "Season simulator". The new tab lets you pick a league and season, shows a coloured data-quality banner (Ready, Provisional or Not eligible) with reasons and the newest result date, says whether the league's rules are verified, lets you choose the number of simulations, and has a Run button that stays disabled and explains why. When a run is allowed it will show the projected table with expected points, title, top-four and relegation chances, a finishing-position chart and a panel that explains the model and its limits.

**8. What should be developed next.** Your decision on the score method (or on re-writing the test so that it allows for random noise). A "dynamic strengths" mode, which should make the uncertainty more honest. The title/top-four/relegation test on past seasons once a method is approved. Fresher data for the Premier League, Serie A and Ligue 1 (needs your approval for any source), and the 2026/27 Ligue 1 and Serie A rule details. Optionally a points-only view, which does not need score-inventing.

**Viva-ready explanation (about 45 seconds).** "Our models only say how likely a win, draw or loss is in each match. To forecast a final league table I built a Monte Carlo simulator: it plays the rest of the season thousands of times, rolling a weighted dice for each remaining match, inventing a believable score, and ranking the table with the league's official tie-break rules. The share of simulated seasons in which a club finishes first, in the top four or in the relegation places is its probability. Before switching it on I tested three ways of inventing scores against a rule I wrote in advance. None passed in every league, and I also showed that the rule is so strict that even a perfect model would usually fail it, so I left the simulator switched off and put the options to my supervisor instead of claiming success. It also refuses to run when results are missing or the official rules for that season are not verified. The frozen models were never changed, nothing runs without a button press, and every run records its assumptions, data freshness and timestamp."
