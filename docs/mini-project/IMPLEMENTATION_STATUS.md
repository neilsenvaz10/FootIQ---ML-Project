# What is actually implemented in FootIQ (status ledger, 2026-10-25)

Written after inspecting the running code, not from memory: the API (`app/main.py`, `app/seasonsim/service.py`, `app/seasonsim/pointsonly.py`, `app/seasonsim/eligibility.py`), the interface (`frontend/src/pages/SeasonSimulator.jsx`), the configuration (`config/season_sim.json`, `config/season_rules.json`, `config/sync.json`) and the saved test runs. Nothing here is a plan; planned items are marked as such.

## 1. A correction to my own earlier explanation
In the "What We Did, Problems Faced, and How We Solved Them" section of my previous report (and in the 45-second viva text) I wrote that the points-only simulator "gives the title, top-four and relegation chances". **That was wrong.** Until the change described in section 2, the points-only mode returned **no** title, top-four, relegation, position or ranking at all, by design:

* `app/seasonsim/pointsonly.py` says so in its docstring ("it deliberately does not rank clubs, so there are no title, top-four, relegation or finishing-position probabilities");
* `POST /api/season/points` returned only points figures per club (`expected_points`, `points_p10/p25/median/p75/p90`, `points_min/max`, `distribution`);
* the page said so ("It does not predict league positions, titles, top-four places or relegation");
* the earlier written reports (`PHASE3_POINTS_ONLY_REPORT.md`, `API_REFERENCE.md`) were accurate about this.

What was inaccurate: that chat explanation, and two passages of `PHASE3_POSITION_BOUNDS_PROTOTYPE.md` (section 1 and section 7) which described the bounds as replacing a "null with low/high" display inside the points-only mode. That wording belongs to the **disabled** final-position engine, which is a different mode. Both passages are corrected.

## 2. What exists now, mode by mode

| Capability | Status | API | Interface | Notes |
|---|---|---|---|---|
| **Points-only simulation**: each club's expected final points, 10th to 90th percentile, quartiles, minimum, maximum and the full points distribution | **Implemented, labelled "Experimental"** | `POST /api/season/points` | Season simulator, tab "Points-only (experimental)" | Bundesliga and La Liga only; blocked when data quality is Not eligible; saved only when the user presses the button; frozen club v1 probabilities, static strengths |
| **Position ranges**: for title, top four and relegation, a lower bound (**guaranteed**), an upper bound (**possible**) and the **unresolved** share per club | **Implemented by this change, labelled "Experimental"**; can be switched off in `config/season_sim.json` | `result.position_bounds` in the same response | Section "Where could each club finish?" under the points table | Bundesliga and La Liga only; computed from the same win / draw / loss draws as the points; no score is invented, no tie is settled by chance |
| **Exact** title, top-four, relegation or exact-position **probabilities** | **Not available anywhere** | none | none | Only the final-position simulator could produce them, and it is disabled |
| **Final-position simulator** (invents scores, ranks with tie-break rules) | **Built but disabled**: `scoreline_method: null`; all three scoreline methods failed the predeclared benchmark and none is approved | `POST /api/season/simulate` is refused (422) | Tab "Final positions (disabled)" with its button off | Not changed by this work |
| **Dynamic-strength mode** (strengths update during the simulated season) | **Offline research prototype only**; not in the API or interface; disabled in production | none | none | A labelled forward evaluation on 2026-27 is *designed* in `PHASE3_DYNAMIC_FORWARD_EVALUATION.md`; nothing has been started |
| **World Cup simulator** | Existing, unchanged | `/api/worldcup/*` | Simulations, tab "World Cup" | A different engine |
| **League rule profiles** | Bundesliga **verified**; La Liga **verified, live-document confirmation PENDING** (checksum not yet compared); Premier League verified (outside the approved scope); Serie A and Ligue 1: **2026/27 rule text verified from the primary documents (2026-10-26) but the profiles stay blocked** (engine support, fresh data and scope are missing; Serie A also has one gap in the rule text) | `GET /api/season/status` | Rules notice and the pending warning | See `PHASE3_RULES_STATUS.md` and `LALIGA_VERIFICATION.md` |
| **Validation of scoreline methods** | Original benchmark: **failed** for all three methods (preserved). Protocol v2 (proposal) reviewed and corrected in v3 (proposal); **nothing run on the confirmation data CA or CB** | none | none | `PHASE3_VALIDATION_PROTOCOL_V3.md` |
| **Live data and providers** | Off. `live_enabled` is false; no provider request, account, key or import was made | none | none | football-data.org: documentation checklist only |

Tests that guard these statements: `tests/test_seasonsim_service.py` (points-only has no exact position field; ranges present, labelled and consistent; the final-position simulator is refused), `tests/test_dynamic.py` (dynamic mode is not imported by the service or API and has no setting), `tests/test_benchmark_preserved.py` (Benchmark v1 files unchanged, verdict failed, no scoreline method approved).

## 3. What a user can do today
1. Open **Simulations, Season simulator**; pick the Bundesliga or La Liga; read the coloured data-quality banner.
2. Press **Run points-only simulation** (nothing runs on page load). The page shows, for every club, the points it may finish with (expected value and 10-90% range, distribution on expanding the row), then the new section **"Where could each club finish?"** with, per club, title / top four / relegation as `lower to upper` percentage ranges, bars, a plain-language explanation, per-club details (lower bound, upper bound, unresolved share, sampling error) and the rule limitations of that league.
3. Open a saved run from the history; it shows the same ranges (runs saved before this change show a note that they have none).

## 4. What the ranges are, and are not
* They are **lower and upper bounds** under the model, not probabilities. The real chance under the model lies between them.
* Clubs level on points are separated by goals (or head-to-head results). Goals are not simulated, so such cases are counted as **unresolved** and widen the range. Nothing is decided by a coin.
* They carry all limitations of the simulation behind them: static strengths, probabilities from a modest model, 10-90% points intervals about 75% reliable in backtests instead of 80%.
* They do not include points deductions or sporting sanctions that are not in our data, a relegation play-off (Bundesliga, 16th place) or any decider that is not a match result.

## 5. Not implemented (so nobody assumes otherwise)
Exact league-table prediction; any scoreline method; the full simulator for any league; Premier League, Serie A or Ligue 1 simulations; a dynamic mode in the app; live synchronisation of results; the football-data.org adapter; abandoned/replayed-match data model; monitoring of any kind.

## 6. Viva-ready wording that is accurate today (about 45 seconds)
"FootIQ's season simulator replays the rest of a league season thousands of times, but only as wins, draws and losses from our frozen match model, so it can say how many points each club may finish with. It cannot tell exactly who finishes where, because clubs level on points are separated by goals and I do not invent goals. Instead, for the title, the top four and relegation it gives two numbers: what is guaranteed whatever the unplayed scores turn out to be, and what is still possible. The truth, according to the model, lies in between. I checked those bounds against my own tie-break engine on millions of score combinations, and the page says clearly that they are experimental ranges, not exact probabilities. The full table simulator exists but is switched off because my test for inventing scores failed."
