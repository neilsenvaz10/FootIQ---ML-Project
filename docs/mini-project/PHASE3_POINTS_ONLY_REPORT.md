# Phase 3 follow-up: Experimental points-only simulation, validation review, static-strength investigation

Date: 2026-10-25. Nothing is staged, committed or pushed. No frozen model, training file, official prospective-evaluation file, `config/sync.json` (`live_enabled` false) or production data was changed. The production store holds 0 saved simulations. **The complete final-position simulator stays disabled** (`config/season_sim.json: scoreline_method null`).

> **Update (2026-10-25, later).** This report describes the points-only mode as first built: **no title, top-four, relegation or position output of any kind**, which was accurate then and is still true of the points table and of every exact probability. After your approval the mode gained a separate, clearly labelled output: **position ranges** (lower and upper bounds for title, top four and relegation, Bundesliga and La Liga only), described in [PHASE3_POSITION_BOUNDS_INTEGRATION.md](PHASE3_POSITION_BOUNDS_INTEGRATION.md). Statements below that say the mode returns no position output refer to the first build. The current state of every capability is in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), which also corrects a later chat explanation of mine that wrongly said the first build already gave title, top-four and relegation chances.

## 1. Your decisions, as implemented

| Decision | Implementation |
|---|---|
| D3 static probabilities | Unchanged: static only; no dynamic-strength mode exists |
| D6 no coin for deciders | The engine no longer decides ties at random. A tie that no supported rule separates (play-off, neutral-ground match, lots, fair play without card data) is **unresolved**: the clubs keep a stable bookkeeping order only; every title / top-four / relegation probability touched by it is withheld (`null`) and only a lower and upper bound is given; exact-position probabilities exclude the unresolved simulations and report the unresolved share; `final_position_probabilities_supported` becomes false. The rule profiles say `unresolved_not_simulated` |
| D7 cancelled / abandoned fixtures | A league with any such fixture is Not eligible (both modes) until the official rules and fixture outcomes are verified |
| D10 saving | A run is saved only when the user presses the Run button; the server refuses a wrong action word and saves nothing |
| Scoreline method | **None approved.** The full simulator stays disabled and all three methods keep their "failed" result |

## 2. What was built: Experimental points-only simulation (option O5)

* **Method.** Frozen club v1 probabilities at the data cut-off; each remaining fixture is drawn as home win / draw / away win and awards 3 / 1 / 0 points (`app/seasonsim/pointsonly.py`, same seeded NumPy approach as the existing engine, 10,000 simulations by default, 1,000-50,000 allowed).
* **Output per club.** Current points, matches left, expected final points, standard deviation, 10th / 25th / median / 75th / 90th percentiles, minimum and maximum, and the full distribution of final points. Clubs are listed by expected points only: **no rank, table, tie-break, title, top-four, relegation or exact-position probability exists in this mode**, in the data or on the page.
* **Label.** "Experimental — Points-only simulation" on the page, in the saved run and in the API.
* **Gates.** Bundesliga and La Liga only (approved scope) and only when the data quality is Ready or Provisional (Not eligible disables it with the reasons). It needs no tie-break rules and no scoreline method. Today: Bundesliga and La Liga can run; Premier League, Serie A and Ligue 1 cannot (data quality and scope).
* **Saving and provenance.** On the explicit button press only, into the existing `simulation_runs` table (no schema change) with the timestamp, seed, simulation count, model id and artifact hash, data cut-off, source freshness (last sync, result sources), eligibility snapshot, input fingerprint and the limitations, including that the backtest intervals were about 75% instead of 80%.
* **API.** `POST /api/season/points`; `GET /api/season/status` gained `points_only`; run history gained `mode` (see API_REFERENCE.md).
* **UI.** The Season simulator tab opens on "Points-only (experimental)" with a prominent label and warning; the second mode "Final positions (disabled)" keeps its disabled button and explains why. The World Cup tab is unchanged.

## 3. Reviews you asked for

* **Why a correct model passes the combined criteria only about 22% of the time, and a proposed revised protocol with intervals and multiple-testing control:** [PHASE3_VALIDATION_REVIEW.md](PHASE3_VALIDATION_REVIEW.md), parts A and B. The original outcome is untouched, the protocol is **not approved and not used**, and its operating characteristics were obtained only on synthetic data.
* **Do static strengths explain the under-coverage of the points intervals:** same document, part C. Short answer: **largely yes, but only partly directly**. Coverage is 74.7% instead of 80%; the expected points are unbiased (mean error -0.08 points) and calibrated (slope 0.96); the over-dispersion is largest early in the season (standard deviation of the standardised error 1.32 at 1 Nov, 1.07 at 1 Mar); the drift in probabilities accounts directly for about 31% of the missing variance, and once probabilities may update (an oracle with hindsight) the remaining variance (25.8) is no larger than the simulated variance (28.2). A dynamic mode (not implemented) would be the test of whether the gap really closes.
* **La Liga regulation:** rechecked 2026-10-25. The live federation URL still refuses automated access (HTTP 403, Cloudflare); I did not try to bypass that. The text I used is the Internet Archive capture of that exact URL taken **2026-07-14 11:27:22 UTC** (origin last modified 2026-06-30), and a search index of the live URL confirms the same document title and that Article 10 (tie-break) is on page 6. The profile stays **verified** with this access note recorded, and I ask you to confirm it against the live page. Ligue 1 (2026/27 text not found) and Serie A (relegation count and play-off procedures) stay **blocked**; no rule was guessed.

## 4. Verification

| Check | Result |
|---|---|
| Backend, whole suite in one run | **130 passed** (123 earlier + 7 new: points-only engine and service, API refusals, unresolved ties) |
| Frontend with the live backend (private copy of the database) | **57 of 57 passed**, three repeated runs, including the 9 live-contract tests and 9 Season simulator tests |
| Production build | succeeds |
| Leakage check | passes: results dated on or after a cut-off are replaced by random scores and the cut-off probabilities stay bit-identical |
| Frozen models, original CSVs, prospective logs, sync config | 17 tracked files identical (sha256) |
| Production database | table fingerprints identical to the post-import values, `integrity_check` ok, `simulation_runs` 0 |
| Live access, ledgers | `live_enabled` false; request ledgers unchanged (4 and 1 lines) |
| Browser check | points-only run on a private copy at desktop and 375 px: label, table, distribution chart, assumptions; no horizontal overflow |

Honest notes: in the live-backend runs, 2 of the first 3 attempts had a timing failure (once a live-contract test, once a Season simulator test) while the backend was still warming up; both pass when the backend is warm, and the Season simulator tests now allow more time. The browser run used a **private copy** of the database, so production saved nothing. The points-only intervals are somewhat too narrow (about 75% coverage against 80%) and the page says so.

## 5. Still needs your approval

1. **Any scoreline method** and the **revised validation protocol** (margins, scope, confirmation data, fixed-sequence order): see the validation review, section B6. Until then the final-position simulator is disabled.
2. Confirmation of the **La Liga** regulation against the live federation page.
3. Treatment of **cancelled and abandoned** fixtures, the **Serie A** relegation places and play-off procedures, and the **2026/27 Ligue 1** regulation (all still blocked).
4. Fresher **Premier League, Serie A and Ligue 1** data (sources need your approval).
5. Whether to build a **dynamic-strength** mode (D3 keeps it out of the first version).

---

## What We Did, Problems Faced, and How We Solved Them — Explained Simply

**What was implemented.** A new, clearly labelled **"Experimental — Points-only simulation"** for the Bundesliga and La Liga. It also tightened the main simulator so that it never settles a tie with a coin, and it produced two reviews: one of our own validation test and one of why the uncertainty bars were a bit too narrow.

**What the scoreline-model problem was.** League tables are often decided by goal difference, but our models only say how likely a win, draw or loss is. To rank clubs we have to invent scores. We tested three ways of inventing them against a rule we wrote in advance; none passed in every league. We also found that the rule was so strict that a perfect method would fail it three times out of four, so the result is weak evidence either way. We did not change the rule or the result.

**Why the simulator was disabled.** Because we cannot yet show that any way of inventing scores is good enough, a final table, title chance or relegation chance would rest on an unproven assumption. So the full simulator stays switched off, and ties that the rules cannot settle are marked "unresolved" instead of being decided by a coin.

**What points-only simulation means, with a football example.** It plays the rest of the season only as wins, draws and losses. Take Bayern: 14 points after 6 games, 28 to play. Each match is a weighted dice roll from the model (for example 70% win, 18% draw, 12% loss); a win adds 3 points, a draw 1, a loss 0. Repeat the whole season 10,000 times and look at the spread of Bayern's final points: here about 85 on average, and in 8 of 10 simulated seasons between 78 and 91. That says how many points a club may end with. It does **not** say who finishes first, because ties on points and goal difference are not involved at all.

**Problems faced and how they were handled.**
* The old code broke ties with a coin; you asked for unresolved outcomes, so it now withholds the affected probabilities and shows bounds.
* The main test was too strict; I explained why with numbers and proposed a better test but did not apply it, so the old result stands.
* The uncertainty bars were too narrow (75% instead of 80%); I showed that letting team strengths change during the season removes the excess, so I say on the page that the bars are a little too narrow.
* The Spanish federation's website still blocks automated downloads; I used a dated archive copy, said so, and ask you to confirm it.
* Two UI tests failed once while the backend was still starting; I made the tests wait longer and repeated the full run three times.

**What users can do now.** In the Season simulator tab (Simulations menu), pick the Bundesliga or La Liga, check the data-quality banner, press "Run points-only simulation", and read each club's expected final points, uncertainty range and points distribution. Runs are saved only when they press the button. Other leagues and the final-position mode are disabled with reasons shown.

**What still needs approval.** A score-inventing method and a fairer validation test (so final tables and title/relegation chances can be switched on), confirmation of the La Liga rules page, the unresolved rules for Serie A and Ligue 1, fresher data for three leagues, and whether to add a dynamic-strength mode.

**Viva explanation (about 45 seconds).** "Our models give win, draw and loss chances for each match. For the first usable season simulator I only simulate those outcomes, 3, 1 or 0 points, so I can show how many points each club may finish with and how uncertain that is, without needing scores or tie-break rules. The full league-table simulator is switched off because the way of inventing scores for goal difference did not pass a test I set in advance, and I showed that the test itself was too strict instead of changing it. Ties the rules cannot settle are left unresolved, never decided by a coin. I also checked why the uncertainty bars were slightly too narrow: team strengths change during a season, and the simulator holds them fixed. Everything runs only when a user presses the button, the frozen models are untouched, and every run records its assumptions, data freshness and timestamp."
