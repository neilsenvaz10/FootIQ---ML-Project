# Position ranges in the experimental points-only simulator: controlled integration (2026-10-25 to 2026-10-26)

**Scope of your approval, as implemented:** the validated position-probability bounds are now part of the existing **experimental points-only simulation** for the **Bundesliga and La Liga**: guaranteed, possible and unresolved probability fields for **title, top four and relegation**, labelled as lower and upper bounds, not exact probabilities. The points distributions are unchanged. The final-position simulator, every scoreline method and dynamic mode stay disabled. Nothing is staged, committed or pushed.

Read first: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) (what exists, including a correction of my earlier explanation) and [PHASE3_POSITION_BOUNDS_PROTOTYPE.md](PHASE3_POSITION_BOUNDS_PROTOTYPE.md) (the prototype and its method).

## 1. What a user sees
After pressing **Run points-only simulation** the page shows the unchanged "Expected final points" table and, below it, **"Where could each club finish?"** (badge: "Position ranges: lower and upper bounds, not exact probabilities"):
* a plain-language box "How to read these ranges" with a worked example taken from the run itself;
* for every club, three ranges (Title, Top four, Relegation) as `lower to upper` percentages with a bar (solid = lower bound, lighter = what only the unplayed scores could decide); values below 0.05% show as `<0.1%`, never as a plain 0.0%;
* a click on a club opens its details: lower bound, upper bound, unresolved share and the 95% sampling error of the simulation;
* for La Liga a visible warning that the live-document confirmation of the rules is still pending;
* a collapsible "Method, rules used and limitations of the ranges" (method, definitions, tie-break criteria actually used, tie statistics, sources, every rule limitation).
If the ranges are switched off, unavailable, or fail an internal check the page says so and shows no numbers; a saved run from before this change shows a note that it has no ranges. The pre-run "How the simulation works" text now describes the points-only mode (it previously showed the final-position text).

## 2. What changed

| File | Change |
|---|---|
| `app/seasonsim/pointbounds.py` | From prototype to production module: reading-independent criteria for three or more clubs (section 4), integer counts so lower <= upper holds exactly, `band_counts` |
| `app/seasonsim/service.py` | `build_position_bounds`; `run_points_only` adds `result.position_bounds` and `assumptions.position_bounds`; new limitation texts; a failure inside the ranges (any exception) is logged and reported as `unavailable`, so the approved points results never depend on the experimental ranges. `pointsonly.py` and `engine.py` are **untouched** |
| `app/seasonsim/eligibility.py` | `points_only.position_bounds` availability and blockers in `GET /api/season/status`; new note text |
| `app/seasonsim/rules.py`, `config/season_rules.json` | `bounds_multi_club_prefix` (Bundesliga 2, La Liga 1) and `bounds_notes` (league-specific disclosures) |
| `config/season_sim.json` | `points_only.position_bounds {enabled: true, scope: [BUNDESLIGA, LALIGA]}` (the switch) |
| `app/seasonsim/m5_bounds_validation.py` | Validation helpers and report (exhaustive and realistic checks against the real engine) |
| `frontend/src/pages/SeasonSimulator.jsx` | The ranges section, explanations, validity guard, updated notices |
| Tests | `tests/test_pointbounds.py` (14), `tests/test_pointbounds_exhaustive.py` (12), ten new tests in `tests/test_seasonsim_service.py` (24 in the file), `tests/test_dynamic.py` (one new: dynamic mode is not wired in), `tests/test_benchmark_preserved.py` (7), eight new tests in `frontend/tests/season.test.jsx` (17 in the file) |

## 3. API contract (`POST /api/season/points`, also `GET /api/season/run`)
`result.summary` is exactly as before (no position field in any club row). New: `result.position_bounds`:

```
status            "available" | "unavailable"        (unavailable: reason; no numbers)
label             "Experimental — position ranges (lower and upper bounds, not exact probabilities)"
kind              "lower_and_upper_bounds"
meaning           {guaranteed, possible, unresolved}  plain-language definitions
method            how the bounds are computed
bands             [{id: title|top4|relegation, label, positions [first, last], places}]
clubs[]           {entity_id, name, title|top4|relegation: {guaranteed, possible, unresolved, se_guaranteed, se_possible}}   same order as the points table
checks            {lower_never_above_upper, all_values_between_0_and_100_percent, places_sums_consistent, places_sums}
ties              {tie_groups, tie_groups_fully_decided, simulations}
rules             {profile_id, status, sources[], live_confirmation, criteria_used {two_clubs, three_or_more_clubs}, deciders_never_simulated, interpretation_notes}
limitations[]     common limitations + the league's own
monte_carlo       {simulations, seed, standard_error_max}
```
All probabilities are fractions between 0 and 1. `guaranteed` (lower bound) <= `possible` (upper bound); `unresolved` = `possible` - `guaranteed`. The same fields are saved with the run in `simulation_runs.result_json`. `GET /api/season/status` adds `points_only.position_bounds {available, blockers, bands}`. There is **no** `p_title`, `p_top4`, `p_relegation`, `position_probabilities` or `expected_rank` anywhere in a points-only response (tested).

## 4. How the bounds respect the verified rules (and one change from the prototype)
Per simulated season the code computes, for each club, the best and the worst final position that **any** scores consistent with the real results and the simulated win / draw / loss pattern could give under the league's tie-break order (a win adds a goal margin of at least +1, a draw 0, a loss at most -1; goal difference and goals scored become intervals; points-based head-to-head is exact). A club is "definitely above" another only if the intervals force it; otherwise the order is **unresolved**, never decided by chance. `guaranteed` counts seasons in which even the worst case is in the band, `possible` those in which the best case is.

* **Two clubs level on points:** the league's full two-club list (Bundesliga: goal difference, goals scored, head-to-head goal difference, head-to-head away goals, away goals; La Liga: head-to-head goal difference, goal difference, goals scored; fair play and the neutral-ground match are never simulated and stay unresolved).
* **Three or more clubs level on points:** only the criteria whose application does not depend on how the rule text is read (`bounds_multi_club_prefix`): Bundesliga overall goal difference then goals scored (the text does not say how the head-to-head criteria work for three clubs); La Liga the points of the mini-table among the tied clubs (article 10 passes to the next criterion only "if two clubs remain level", and is silent about a pair that remains level inside a group of three, or about a cycle). Everything beyond stays unresolved.
* **Why this changed from the prototype:** the prototype followed one reading (head-to-head over the *original* tied group). The engine can also apply them over the clubs *still* tied, and a third reading is conceivable. With the La Liga rules the readings really can disagree: a hand-built case (`reading_case` in `tests/test_pointbounds.py`: A, B, C on 8 points; A and B level on 7 mini-table points) puts A above B under one reading (+4 v +3 goal difference over the group) and B above A under the other (+2 v -2 between the two). The prototype's bounds would have been wrong under the second reading; the integrated bounds contain both. A random search of 80 leagues per league found no such case (they are rare), which is why the deterministic case exists. The cost is small: 4 of 25,693 simulated La Liga tie groups (0.016%) are less decided and the band figures did not change to four decimals.
* **Not simulated (stay unresolved, counted in `unresolved`):** fair play (no card data), the neutral-ground match, a three-club tie beyond the criteria above, and the Bundesliga relegation play-off (16th place is **not** part of the "relegation" band, which means direct relegation, places 17 and 18).
* **Not in our data:** points deductions or sanctions; results of abandoned matches (leagues with cancelled or abandoned fixtures stay Not eligible).

## 5. Validation
The oracle is the **real tie-break engine** (`engine._rank_all`, the function the disabled simulator ranks with), driven by explicit score sets; a test shows the helper returns exactly the positions of `engine.simulate` on one-hot score distributions. Soundness means: every position the engine can produce lies inside [best, worst].

**Exhaustive small leagues** (`m5_bounds_validation.py`, 80 random leagues of 4 or 5 clubs per league, 3 or 4 unplayed matches, results with 0 to 2 goals and many draws so that ties are frequent): every win / draw / loss pattern (5,022 per league) x every score completion with up to 3 goals per team in each unplayed match (3,584,000 per league), ranked by the engine under **both readings** of the head-to-head scope:

| | Bundesliga | La Liga |
|---|---|---|
| Club-position checks (both readings) | 41,634 | 41,634 |
| Violations (position outside the bounds) | **0** | **0** |
| Violations with the bounds that ignore the known results ("naive") | 0 | 0 |
| Share of bounds exactly equal to the extremes the engine reached ("tight") | 99.3% | 99.5% |
| Tie groups of two clubs / of three or more clubs | 2,572 / 165 | 2,494 / 158 |
| Unresolved deciders produced by the engine | 5,893 | 57,919 |

**Realistic scale** (the real 2026-27 state on 2026-10-25 read from the store; 1,500 random win / draw / loss patterns with random consistent scores per league; both readings): Bundesliga 54,000 club-position checks, La Liga 60,000, **0 violations**. In those random seasons the final position of a club was exactly known (best = worst) for 55% (Bundesliga) and 87% (La Liga) of clubs.

**Invariants** (every league, random leagues and the real runs): lower bound never above upper bound; every value between 0 and 100%; `unresolved` = upper - lower; the lower bounds of a band add up to at most its number of places and the upper bounds to at least that number (exactly 1 / 4 / 2 or 3 clubs fill the band in every season); a title range nests inside the top-four range; a finished season with no ties has no unresolved share; the ranges are reproducible for a seed. If any of these ever failed, the service returns `status: "unavailable"` with the reason instead of numbers (tested with injected faults).

**Does it change the points results?** No: with the ranges switched on or off the saved `summary` is identical (test), and `pointsonly.py` was not touched.

**Limits of the validation:** the exhaustive part caps goals at 3 per team per unplayed match and uses small leagues (the cap can only make the oracle's reachable set smaller, so a violation would still show; tightness is a lower estimate); the realistic part samples rather than enumerates; neither can say anything about model error. The engine itself is trusted as the statement of the rules (its own tests, the sources in `config/season_rules.json`).

## 6. Snapshot of the current state (10,000 simulations, seed 11, 2026-10-25 data)
Bundesliga (61 of 306 fixtures played, about seven matchdays): mean width of the unresolved band over the 18 clubs: title 0.14 percentage points, top four 1.1, relegation (places 17-18) 1.8; the widest single range is 5.5 points. Examples: FC Bayern München title 94.8% to 96.1% and top four 100%; Borussia Dortmund title 2.9% to 3.8%, top four 95.3% to 96.4%; RB Leipzig top four 52.8% to 57.6%; Borussia Mönchengladbach relegation 48.2% to 53.4%. La Liga (89 of 380 fixtures played): title 0.04, top four 0.24, relegation (18-20) 0.52 percentage points; FC Barcelona title 96.3% to 96.6%, Real Madrid 3.0% to 3.3%, Real Betis top four 68.8% to 70.6%. La Liga is tighter because its first tie-break is head-to-head, which is mostly known, while the Bundesliga's first tie-break (overall goal difference) stays open until both clubs' results are fixed. The ranges widen when many clubs are level on points late in the season. Computing them took about 1 to 2 seconds per league for 10,000 simulations on an idle machine (4.6 and 6.9 seconds while two other heavy jobs were running). At the largest allowed count, 50,000 simulations, the points take about 5 seconds and the ranges 22 to 35 seconds measured under that heavy load (about five times the idle 10,000 figure, so roughly 5 to 9 seconds when idle: an estimate, not measured), with a measured peak memory of about 0.5 GB for the Bundesliga; the page shows its spinner meanwhile.

## 7. Limitations disclosed to the user (all shown on the page)
* Lower and upper bounds, not exact probabilities.
* Inherited model limits: static strengths and a modest model; in backtests the 10-90% points intervals were about 75% reliable instead of 80%, so the ranges are probably a little too narrow (the dynamic-strength prototype narrows that gap only partly and is not enabled).
* Sampling error of the simulation (shown per value).
* Deciders that are not match results are never simulated; fair play needs card data we do not hold.
* Bundesliga: direct relegation only (places 17 and 18); the 16th-place play-off is not simulated; head-to-head criteria are not used for three or more clubs.
* La Liga: only the mini-table points are used for three or more clubs; the live federation document has not been checked against its checksum (**pending**, [LALIGA_VERIFICATION.md](LALIGA_VERIFICATION.md)).
* Points deductions and other sanctions are not in the data.
* Experimental: it may be switched off or changed without notice.

## 8. Controls
* Switch off: `config/season_sim.json`, `points_only.position_bounds.enabled = false` (the points-only mode keeps working; the page then says the ranges are switched off).
* Scope: `points_only.position_bounds.scope` (Bundesliga and La Liga). A league also needs a verified rule profile with `bounds_multi_club_prefix`; the Premier League profile has none, and Serie A and Ligue 1 are blocked.
* The final-position simulator is still disabled (`scoreline_method: null`); a request to `POST /api/season/simulate` is still refused.

## 9. Verification (2026-10-26)
| Check | Result |
|---|---|
| Backend, whole suite in one run on an idle machine | **182 passed** (15 min 25 s) |
| Frontend, 5 test files against a live backend on a **private copy** of the database | **65 of 65 passed** with the files run one after another (`vitest run --no-file-parallelism`); production build succeeds |
| An honest note on the frontend run | with the files in parallel, one live-contract test (the gameweek endpoint for the Premier League, about 3.7 seconds per call on this machine today) exceeded vitest's 5-second limit; it passes alone (twice) and sequentially. That endpoint does not touch the season code |
| Browser check on a private copy (desktop pane and 375 px) | ranges, explanation, bars, details, pending warning for La Liga, no horizontal overflow; a La Liga run was started with the page's button and a saved Bundesliga run was opened from the history |
| Frozen models and data (6 sha256 in `data/supervised/hashes_before.json`) | unchanged |
| Protected-file manifest (17 files: frozen models, original CSVs, sync config, prospective-evaluation loggers and logs) | identical to the manifest taken at the end of the previous stage |
| Production database | sha256 equal to the post-import record, `integrity_check` ok, `simulation_runs` 0 |
| Settings | `live_enabled` false, `scoreline_method` null, scoreline status `failed_predeclared_criteria`, ranges enabled for Bundesliga and La Liga |
| Git | nothing staged, no commit; HEAD `970f461` on `feat/club-ml-v2` |
