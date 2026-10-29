# Position-probability bounds from points only: offline prototype (2026-10-25)

> **Update and correction (2026-10-25, later).** After your approval this prototype was integrated into the experimental points-only mode; the integration, its validation and the current API and interface are in [PHASE3_POSITION_BOUNDS_INTEGRATION.md](PHASE3_POSITION_BOUNDS_INTEGRATION.md). This file stays as the record of the prototype. Two passages of its first version were inaccurate and are corrected below (section 1 and section 7): they described the bounds as replacing a "null with low and high" display *inside the points-only mode*. That display belongs to the disabled final-position engine; the points-only mode had no title, top-four or relegation output at all (see [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)).

**Status of the prototype as first written: research prototype, not wired to the API or the interface.** It ran only on a private copy of the database; the production store was not written. The frozen models were only read. Final-position simulation (`scoreline_method: null`) stays disabled.

Code: `app/seasonsim/pointbounds.py`; report script: `app/seasonsim/m4_bounds_report.py` (output `data/supervised/phase3/m4_bounds_report.json`; the figures of the first prototype run are kept in `m4_bounds_report_prototype_before_prefix.json`).

## 1. The question
Before this work the points-only simulator gave each club's distribution of final **points** and nothing about positions: it draws only win, draw or loss for each remaining match (no scores), so clubs level on points cannot be ordered, because the criteria that separate them (goal difference, goals scored, head-to-head goals) are never drawn. A table, a title chance or a relegation chance therefore needs either invented scores (the scoreline methods, none of which is approved) or a different kind of statement. The prototype asked whether we can state the title, top-four and relegation chances as **rigorous lower and upper bounds from the points-only draws alone**, with no invented score and no coin, and how tight those bounds are.

## 2. Method
For each simulated season (a complete set of win/draw/loss outcomes) and each club, compute the **best and worst final position that any set of scores consistent with those outcomes could produce**, under the league's official tie-break order:
1. A win has goal margin at least +1, a draw exactly 0, a loss at most -1. Goals scored by a team in a match is at least its margin if positive, otherwise at least 0. Completed matches use their real score. This gives an **interval** for each club's goal difference, goals scored and head-to-head quantities (points are exact).
2. Club X is **definitely above** club Y when the tie-break criteria taken in the official order show X ahead for every score assignment (the first criterion that is not identical for both clubs separates their intervals). Clubs level on points whose order cannot be settled by intervals are **unresolved**; they are never ordered by chance.
3. From these relations the best position is 1 plus the number of clubs that are definitely above (counting clubs not definitely below as possibly above gives the worst).
4. For a band (for example positions 1 to 4): **guaranteed** = best >= first place of the band and worst <= last place; **possible** = worst >= first place and best <= last place; **unresolved** = possible minus guaranteed. The pair guaranteed/possible is the **rigorous (conservative) bound**: the true probability under the points-only model is at least the guaranteed share and at most the possible share, because every score assignment consistent with the outcomes is covered, including ones the real world would never produce.
5. Multi-club ties follow the league's own rule: head-to-head for La Liga (mini-table), overall goal difference first for the Bundesliga (head-to-head only later), and a head-to-head criterion for a group larger than two is used only where the rulebook says so (`h2h_scope`).
6. Monte Carlo error: the bounds are estimated from 10,000 simulated seasons and each estimate has a standard error (shown in the report, about 0.001 to 0.005).

## 3. What "rigorous" and "conservative" mean here
* **Rigorous:** for each simulated outcome set, the best and worst positions are mathematically correct (proved by the interval logic and checked by brute force, section 5). No score is invented.
* **Conservative:** the interval allows every score assignment, including very unlikely ones (for example a 10-0 win that reverses a goal-difference tie). So "possible" may be larger than reality and "guaranteed" smaller, never the reverse. The width of the gap is the price of not modelling scores.
* **Not removed by this method:** (a) Monte Carlo error; (b) model error, as the match probabilities come from frozen club v1 with static strengths (in earlier backtests the 80% points intervals covered about 76% of club outcomes; the dynamic-strength prototype narrows that partly, see `PHASE3_DYNAMIC_STRENGTH_RESULTS.md`); (c) rules that are unresolved (fair play, neutral-ground matches), which are reported as unresolved.

## 4. Results (current state of the private copy, 10,000 simulations per league)
Mean probability over clubs that the club's band membership is **unresolved** (the width of the gap between guaranteed and possible):

| League | Band | Mean unresolved, refined bounds | Mean unresolved, naive bounds | Largest for one club |
|---|---|---|---|---|
| Bundesliga | title | 0.14% | 0.14% | 1.2% |
| Bundesliga | top four | 1.07% | 1.07% | 4.8% |
| Bundesliga | relegation (17th-18th) | 1.82% | 1.82% | 5.5% |
| Bundesliga | relegation play-off place (16th) | 3.86% | 3.86% | 10.6% |
| La Liga | title | 0.04% | 0.10% | 0.37% |
| La Liga | top four | 0.24% | 0.69% | 1.8% |
| La Liga | relegation (18th-20th) | 0.52% | 1.61% | 1.5% |

* "Naive" = bounds that use only points; "refined" = the interval logic above including goal-difference, goals-scored and head-to-head intervals.
* Examples (Bundesliga title): FC Bayern München guaranteed 94.8%, possible 96.1% (unresolved 1.2%, standard error 0.2 points); Borussia Dortmund guaranteed 2.9%, possible 3.8%. Bundesliga top four: Dortmund guaranteed 95.3% / possible 96.4%; Leipzig guaranteed 52.8% / possible 57.6%.
* **Why La Liga is tighter than the Bundesliga:** La Liga breaks ties by head-to-head results first, which are known for matches already played, and 16,607 of 25,693 tie groups (65%) were fully decided by the refined logic. In the Bundesliga the first tie-break after points is overall goal difference, which stays unknown until both clubs' remaining results are fixed: none of 23,099 tie groups was fully decided, but the unresolved shares are still small (at most about 4% on average per band) because most ties are between clubs that cannot reach the band anyway.
* **Timing:** each league took about 1 to 2 seconds for 10,000 seasons.
* **Premier League, Serie A, Ligue 1:** not computed (profiles are blocked or outside the approved scope).

## 5. Tests
The first version had 11 tests in `tests/test_pointbounds.py`. The integration extended them (13 in that file) and added `tests/test_pointbounds_exhaustive.py` (exhaustive validation against the real engine, both readings of the rule text, the real 2026-27 state, invariants). See the integration document for the list and the numbers.

## 6. Verdict
**Defensible bounds are possible.** They are mathematically sound, tight enough to be useful (a few percentage points at most for the Bundesliga, about one for La Liga), and honest about what is unresolved. They are the right way to show band probabilities for leagues whose tie-breaks depend on goals, without choosing a scoreline method. They do **not** fix model error, and the gap grows when many matches remain level on points late in the season.

## 7. What happened next
The integration was approved on 2026-10-25 and is described in [PHASE3_POSITION_BOUNDS_INTEGRATION.md](PHASE3_POSITION_BOUNDS_INTEGRATION.md): the ranges are a **new** output added to the experimental points-only mode (`result.position_bounds`), the points distributions are unchanged, and the full final-position simulator stays disabled. One change from the prototype: for three or more clubs level on points only the criteria whose application does not depend on how the rule text is read are used (see the integration document), which can only widen a bound and made 4 of 25,693 simulated La Liga tie groups (0.016%) less decided; the band figures above did not change to four decimals.
