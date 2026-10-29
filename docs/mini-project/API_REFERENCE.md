# FootIQ mini-project API reference (v1.3)

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Base URL (local): `http://127.0.0.1:8000`. All endpoints are `GET`, return JSON, need no authentication, and are read-only. Interactive docs: `/docs` (OpenAPI at `/openapi.json`).
Start: `.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000`.

## Conventions

- **Competition keys:** `EPL`, `LALIGA`, `BUNDESLIGA`, `SERIEA`, `LIGUE1` (domestic leagues) and `UCL` (UEFA Champions League). Any other key (including the archived `UEL`, `UECL`, `WC`, `UNL`, `COPA`) answers 404.
- **Team names:** always use the exact strings returned by `/api/competitions/{key}/teams`. Club names are normalised to one spelling per club (the source spells the same club differently across seasons; matching is by club id internally). Old spellings such as `Arsenal` are rejected with 404.
- **Dates:** `YYYY-MM-DD`. Seasons: `2023-24` for the leagues and the Champions League.
- **Probabilities:** floats in 0-1; `home + draw + away = 1` (tested, tolerance 1e-6). For international neutral-ground matches "home" means the first-listed team.
- **Validation badge** (always present on prediction responses): `Validated`, `Partially validated`, or `Not validated (indicative only)`. A frontend must display it next to every probability.
- **Errors** always have `{"detail": "<message>"}`; parameter-validation errors (422) also have `"errors": [{"field", "message"}]`.

| Status | Meaning |
|---|---|
| 200 | OK |
| 404 | Unknown competition, season or team |
| 422 | Bad or missing parameter, bad date, date outside the allowed range, same team twice, team without rating data |
| 500 | Only for a server misconfiguration, e.g. simulator started without `-X utf8` (message says so) |

## Endpoints

### `GET /api/sync/status`
Data freshness per competition, from the results store (503 if `data/footiq.sqlite` has not been built: `python app/store/build.py`).
`{generated_utc, live_enabled, periodic_minutes, approved_sources[], recent_checks[ {run_id, kind, source, started_utc, finished_utc, outcome, requests, detail} ], competitions[ {competition_key, latest_result, awaiting_result, scheduled, last_fixture, oldest_awaiting, approved_sources[], last_successful_sync_utc, state: "fresh" | "stale", state_reasons[]} ], attribution[ {source, text, used_for[]} ], note}`.
`awaiting_result` counts matches whose date has passed but no approved source has a result yet. A competition is `fresh` only if an approved source synced successfully within `stale_after_hours` and nothing is awaiting a result; nothing is ever labelled "live". With `live_enabled: false` (the shipped default) no network request is made and every league reports its cached state.

### Gameweek forecasts (five domestic leagues only)
**`GET /api/gameweeks?key=&season=`**: `{competition_key, season, seasons[], latest_result, today_utc, next_gameweek, gameweeks[ {matchday_no, label, fixtures, first_date, last_date, completed, upcoming, awaiting_result, postponed_or_cancelled, predictable, rescheduled_fixtures, order_issue, saved_forecast_runs} ]}`. `season` defaults to the newest. 422 for a league that is not one of the five, 404 for an unknown season.

**`GET /api/gameweek?key=&matchday=&season=`**: every fixture of one gameweek and the latest SAVED forecast for each. It computes and saves nothing.
`{competition_key, season, matchday_no, label, latest_result, fixtures[ {record_id, date, kickoff_utc, kickoff_local, home, away, status ("scheduled" | "awaiting_result" | "completed" | ...), stored_status, predictable, result {home, away, source} | null, reliability ("full" | "provisional"), flags[], reasons[], stale_days, form {home[], away[]} (last 5, only results before the fixture's date), forecast | null, evaluation | null} ], evaluation {finished_with_forecast, counted, excluded, correct, accuracy, mean_log_loss, caveat}, runs[ {forecast_run_id, created_utc, data_cutoff_date, user_action, fixtures} ]}`.
`status` is the *effective* status: a stored `scheduled` fixture whose date has passed is shown as `awaiting_result` (played, no verified result). Flags: `stale_history`, `missing_results_home|away`, `earlier_fixtures_unplayed_home|away`, `kickoff_time_unknown`, `kickoff_timezone_unknown`, `rescheduled_or_out_of_order`, plus (on saved forecasts) `low_history`, `ratings_not_connected`, `not_certainly_before_kickoff`.
`forecast` = `{forecast_run_id, created_utc, data_cutoff_date, data_cutoff_note, made_before_kickoff ("yes"|"no"|"unknown"), reliability, flags[], models{...}, artifact_sha256{...}, feature_sha256, predictions {primary, secondary, elo_only: {home, draw, away}}}`. `evaluation` (finished fixtures with a saved forecast) = `{actual, predicted, correct, p_actual, log_loss, made_before_kickoff, counted, note}`; only forecasts with `made_before_kickoff == "yes"` are counted in the summary.

**`POST /api/gameweek/predict`** body `{key, season, matchday, user_action}`. `user_action` must be exactly `"predict_gameweek_button"`; anything else returns 422 and saves nothing. Forecasts every unplayed fixture of the gameweek with the frozen club models and saves one run (3 model variants per fixture, with the exact feature snapshot, its sha256, the data cut-off and the artifact hashes). Returns `{forecast_run_id, created_utc, data_cutoff_date, models, artifact_sha256, saved_fixtures, skipped[], note, forecasts[ {record_id, date, home, away, reliability, flags[], reasons[], made_before_kickoff, feature_path, predictions} ]}`. 422 when nothing in the gameweek is unplayed. Each call creates a new run; nothing is overwritten. May take about 30 s when fixtures dated before the newest stored result need the day-by-day replay. Saved runs are application history, not the official prospective evaluation.

CORS now also allows `POST` (still only for the configured origins).

### `GET /api/featured-fixture[?comp=&upcoming=&results=]` (Home dashboard; five domestic leagues)
The Home page's one request: the featured upcoming fixture, the fixtures after it, the latest verified results, the data freshness of each league and the eligibility of every fixture. It reads the results store with a fixed number of bounded, indexed statements. **It computes no forecast, saves nothing, loads no model and never calls the gameweek view.** 503 if the store has not been built.

Parameters: `comp` optional, one of `EPL`, `LALIGA`, `BUNDESLIGA`, `SERIEA`, `LIGUE1` (anything else is 422); `upcoming` 1 to 12 (default 8), the number of fixtures listed after the featured one; `results` 0 to 12 (default 8). Anything outside the range is 422.

```
{generated_utc, today_utc, scope {competitions[], rule},
 featured {record_id, competition_key, competition, season, matchday_no, matchday_label, date,
           kickoff {state: "utc" | "local_without_time_zone" | "unknown", utc, local, time_precision},
           home {name, entity, resolved}, away {name, entity, resolved}, status: "scheduled", source,
           eligibility {eligible, predictable, reliability: "full" | "provisional", flags[], reasons[], stale_days},
           has_saved_forecast, forecast | null} | null,
 empty_state null | {code: "no_upcoming_fixture" | "no_eligible_fixture", message},
 upcoming [ the fields of `featured` without `forecast`, and with `eligibility` reduced to {eligible, predictable, reliability, flags} ],
 recent_results [ {record_id, competition_key, competition, season, matchday_no, date, home, away, home_goals, away_goals, status: "completed" | "awarded", source} ],
 leagues [ {competition_key, name, season, upcoming_found, started_today, next_fixture_date, latest_result, state} ],
 freshness {live_enabled, periodic_minutes, note, attribution[], competitions {KEY: {state, state_reasons[], latest_result, last_successful_sync_utc, approved_sources[], awaiting_result, scheduled}}},
 notes[]}
```
* **Which fixtures.** The newest season of each league; status `scheduled`; dated today (UTC) or later. A fixture dated today whose stored UTC kickoff has already passed is not upcoming (the gameweek page shows it as awaiting a result). Order: date, stored UTC kickoff, league order (`EPL`, `LALIGA`, `BUNDESLIGA`, `SERIEA`, `LIGUE1`), record id. `featured` is the first fixture whose two clubs are both matched to a club identity; `upcoming` continues after it and never contains it. With none, `featured` is `null` and `empty_state` says why.
* **Nothing is invented.** Names, dates, matchdays, sources and scores are the stored values. `kickoff.state` says what the store holds: `utc` (a time from a source that states UTC), `local_without_time_zone` (a time as published, zone not stated; shown as local, never converted) or `unknown` (no time). `forecast` is the latest forecast that was already saved for the featured fixture, the same object the gameweek page returns, otherwise `null`; this endpoint never creates one. `matchday_label` can be `null`.
* **Eligibility** uses the same rules as the gameweek page (`reliability`, `flags` as listed above, `reasons` and `stale_days` for the featured fixture only). `freshness` follows the `/api/sync/status` rules for the five leagues.
* **Cost.** 5 newest-season lookups, 5 upcoming, 5 results, at most 5 season reads (only for leagues with a shown fixture), 1 saved-forecast lookup and the freshness statements (about 35 small ones): the count does not depend on how many fixtures exist. Every query is anchored on the `(competition_key, season)` index; `tests/test_featured.py` asserts the query plans (no scan, never `idx_matches_status_date`, which spans the whole store).
* **Featured choice (P4.3).** The earliest eligible fixture, unless its league's data is stale and a league with fresh data has an eligible fixture at most 3 days later: that one is featured. The skipped fixture stays in `upcoming`, and every chip and `freshness` entry belongs to the chosen fixture's own league, so a stale fixture is never shown without its warning. Fixtures carry `timing` and `kickoff.zone_verified` as in `/api/matches`.
* **Caching.** The payload is cached in the process for 60 seconds per `(comp, upcoming, results, UTC date)`, and dropped as soon as the store file changes or a synchronisation stored new results. Headers: `Cache-Control: private, max-age=60`, `ETag`, `X-FootIQ-Cache: hit | miss`. A request with `If-None-Match` equal to the current ETag gets `304` and no body.
* Measured response times are in the table below; why `/api/gameweek` is not used for this: [phase4/P4_2_PERFORMANCE_INVESTIGATION.md](phase4/P4_2_PERFORMANCE_INVESTIGATION.md).

### `GET /api/matches[?comp=&season=&matchday=&status=&team=&limit=&cursor=&order=]` (Matches hub; five domestic leagues and the Champions League)
Fixtures and results, filtered and paginated. Reads the store only: **no forecast, no model, never the gameweek view.** 422 for a bad parameter or cursor, 404 for a season the selection does not have, 503 without a store.

Parameters: `comp` one of the five leagues or `UCL` (default all six); `team` a club identifier from `facets.teams` (needs `comp`; restricts rows and counts to that club's matches); `season` such as `2026-27` (default: the newest season of each league); `matchday` 1 to 60; `status` `upcoming` (default), `awaiting_result`, `completed`, `other` (postponed, cancelled, abandoned) or `all`; `limit` 1 to 50 (default 25); `cursor` the `page.next_cursor` of the previous answer (opaque); `order` `asc` or `desc` (default: ascending for `upcoming` or when a matchday is chosen, descending otherwise).

```
{generated_utc, today_utc, scope {competitions[], seasons {KEY: season}, matchday, status, order, limit, team},
 counts {upcoming, awaiting_result, completed, other, all},          // for the league / season / matchday selection, whatever the status
 items [ {record_id, competition_key, competition, season, matchday_no, matchday_label, date,
          kickoff {state: "utc" | "local_without_time_zone" | "unknown", utc, local, time_precision, zone_verified},
          home {name, entity, resolved}, away {...}, status, stored_status, result {home_goals, away_goals, source} | null, result_missing, source,
          timing {phase, ambiguous, note}, eligibility {eligible, predictable, reliability, flags} | null, saved_forecast_runs, validation_badge} ],
 page {limit, returned, has_more, next_cursor}, facets {seasons[], matchdays[], teams[ {entity, name} ] (one league-season only, else [])}, freshness {...as in /api/featured-fixture}, notes[]}
```
* **Champions League (Phase 4.20).** `UCL` rows are listed like the leagues, with three differences: their `matchday_no` is read from the stage label (`Matches > Matchday 3` is matchday 3, so the filter and facet work although the store holds no number); `eligibility` is `null` (the eligibility rules belong to the gameweek page, which is domestic-only; there is no gameweek for the Champions League); and `validation_badge` is `Not validated (indicative only)`, which a client must show next to any prediction link. Its `freshness` entry has no approved source (`historical_only` in `/api/data-freshness`): it changes only through approved imports (`app/store/uefa_import.py`).
* **Statuses** are effective ones, from the stored status, the stored date and kickoff, and the server's UTC clock: `upcoming` = stored scheduled, dated today or later and not known to have kicked off; `awaiting_result` = no verified result although the date has passed, or today's **stored UTC** kickoff has passed; `completed` = a verified final result is stored (`completed` or `awarded`). There is no live status. A fixture dated today whose kickoff is a local time without a time zone (or has no time) stays `upcoming`: the page cannot know whether it has started.
* **Kickoffs are never converted.** `zone_verified` is true only for `state: "utc"`; for a local time `utc` is `null`. `timing.phase` is one of `future_date`, `today_before_kickoff`, `today_time_zone_unconfirmed`, `today_time_unknown`, `kickoff_passed`, `date_passed`, `result_stored`, `not_played`; `ambiguous` is true when whether the match has started or finished cannot be known, and `note` says why. A finished match without a stored score has `result: null` and `result_missing: true`, never 0-0.
* **Bounded.** One season of one league is about 400 rows and every statement is anchored on the `(competition_key, season)` index (a unary plus on `status` keeps the planner off the store-wide status index); paging is by keyset, so a deep page costs what the first one does; a fixed set of statements per request (tests assert the count, the plans and the bound). `eligibility` is for matches not yet played and follows the gameweek page's rules; `saved_forecast_runs` counts the runs saved for the match's gameweek.
* Cached 60 s per parameter set with `ETag`, `Cache-Control: private, max-age=60` and `X-FootIQ-Cache`, like `/api/featured-fixture`.

### `GET /api/health`
`{status: "ok", club_prediction_ready: bool, data_rows: int}`. Poll `club_prediction_ready` after start-up (see timings).

### `GET /api/meta`
Attribution (`attribution[] {source, licence, requirement?}`), `data_through {club_results, note}`, `models`, `integrity` (sha256 check of the frozen club artifacts: `club_v1.ok`, `club_v2_r1.ok`; the international v2.7 pickle has no recorded hash, so `ok` is `null` and its hash is shown), `limitations[]`, `validation_badges{key: badge}`. Use it for the footer / about page. Slow first call is not an issue (about 0.1 s).

### `GET /api/models/performance`
Evaluation results read from the repository's own report files (nothing recomputed): `club_v1` {role, status, evaluation[ {period, n, models[ {model, label, n, accuracy, log_loss, brier, macro_f1} ]} ] (test season, forward holdout), per_league[ {key, competition, test{n, accuracy, log_loss, always_home_log_loss}, forward_holdout{...}} ] for the five leagues, notes}, `club_v2_r1` {status, development{period, n, accuracy, log_loss_v2, log_loss_v1_lr, log_loss_v1_elo, delta_vs_v1_lr}, notes}, `international_v27` {split{train_matches, calibration_matches, test_matches, test_period}, models[ {model, label, log_loss, brier, accuracy, ece, public_coverage, public_pick_accuracy} ], gate{...}, notes}, `worldcup` {results[ {scope, correct, scored, accuracy_pct, ci_low_pct, ci_high_pct} ], notes}, `uefa_club` {status, note}, `caveats[]`, `sources[]`. 503 if an evaluation file is missing. These results were inspected during development; they are historical evidence, not new independent validation.

### `GET /api/competitions`
Array of `{key, name, group, badge, basis, rows, seasons, first_date, last_date, sources, licences}` for the six supported competitions. `group` is `Domestic league` or `Continental club`. `rows` equals the number of matches in `data/miniproject/matches.csv`.

### `GET /api/competitions/{key}/seasons`
`["2026-27", "2025-26", ...]`, newest first. 404 for unknown key.

### `GET /api/competitions/{key}/teams[?season=]`
Sorted array of team names. Without `season`: every team that ever appears in that competition in the dataset, including clubs that have since left. With `season` (a value from `/seasons`): only teams with at least one match in that season; use the newest season for "current" participants. 404 for an unknown key or season.

### `GET /api/competitions/{key}/coverage`
Per season: `{competition_key, season, rows_in_dataset, expected_matches, coverage_pct, note}`. `note` is `incomplete or in progress` when fewer matches than expected exist, or `no expected-count reference available` (then `expected_matches`/`coverage_pct` are `""`; always the case for international competitions).

### `GET /api/competitions/{key}/dashboard?season=`
```
{competition, badge, season,
 summary {matches, goals_per_match, home_win_rate, draw_rate, away_win_rate (null if no outcome known), outcome_basis, first_date, last_date},
 standings [{pos, team, played, won, drawn, lost, gf, ga, gd, points}] | null,
 results   [{date, stage, home, away, home_goals, away_goals, shootout_winner}]  // newest 30
}
```
Each standings row also has `form`: the last five results (`"W"`, `"D"`, `"L"`, oldest first).
`standings` is only present for the five domestic leagues (computed from the dataset, 3-1-0 points; `null` for cups and internationals). 404 for unknown season. `season` is required (422 otherwise).

### `GET /api/team?key=&team=[&opponent=]`
```
{form {team, played, points, last [{date, opponent, venue: "H"|"A", gf, ga, result: "W"|"D"|"L"}]},   // last 10 in that competition, oldest first
 head_to_head {a, b, meetings, a_wins, b_wins, draws, last [{date, season, home, away, home_goals, away_goals}]}}  // only if opponent given; last 10, newest first
```
Scores are the recorded scores of that competition (knockouts include extra time). 404 unknown team/opponent; 422 if `opponent == team`.

### `GET /api/predict?key=&home=&away=[&date=][&venue=]`
`date` optional. `venue` is accepted and ignored: every supported competition is a club competition.
**Club (leagues, UEFA club):**
```
{competition_key, competition, validation_badge, validation_basis, home, away, date, data_through,
 primary   {model, home, draw, away},    // club v1 (frozen)
 secondary {model, home, draw, away},    // club v2-r1 (frozen candidate; development-validated only)
 elo_only  {model, home, draw, away},
 history   {home_prior_matches, away_prior_matches},
 inputs    {home: {elo, ppg5, goals_for_5, goals_against_5, gd5, days_rest, prior_matches}, away: {...}},  // the model's own inputs (club v1 features); null if unknown
 notes [str]}
```
Date rule: the date must be **after** `data_through` (default = the next day). A date more than 180 days after `data_through` gets a low-confidence note.

### `GET /api/data-freshness` (Phase 4.17-4.18)
One record per supported competition: `{key, name, group, latest_result, days_since_latest_result, data_status ("startup_updated" | "historical_only"), data_status_label, update_note, last_successful_refresh_utc, sync_mode, has_warnings, warnings [{level, text}]}`. `startup_updated` only for Bundesliga and La Liga (refreshed once when FootIQ starts); everything else, including the Champions League, is `historical_only`. Nothing is ever labelled live.

### `GET /api/competitions/{key}/league-phase?season=` (Phase 4.17-4.18)
The 36-team Champions League league-phase table (seasons from 2024-25) with the tie-breakers of UEFA Regulations 2026/27 Article 18 that the data can evaluate; provisional while the phase is running. 422 for other competitions or earlier seasons.

### Removed in Phase 4.18
`/api/worldcup/bracket` and `/api/worldcup/simulate` (the World Cup left the supported scope; `app/worldcup_sim.py` and `app/bracket.py` stay in the repository, unused).

## Typical response times (this machine, one process)

| Call | Time |
|---|---|
| Static endpoints (`competitions`, `dashboard`, `team`, `meta`) | 10-20 ms |
| `GET /api/featured-fixture` (Home): uncached / from its cache / `304` | about 50 ms / 25 ms / 15 ms over HTTP with a new connection per request (13 kB body); the cached and `304` figures are the cost of the connection |
| `GET /api/gameweek` (one gameweek of 10 fixtures; for comparison) | 2.8 s on an idle machine, 5 to 12 s under CPU load: 20 store-wide index walks, see [phase4/P4_2_PERFORMANCE_INVESTIGATION.md](phase4/P4_2_PERFORMANCE_INVESTIGATION.md) |
| First club prediction if requested immediately after start | about 20 s (history replay; waits for the background warm-up) |
| Club prediction after warm-up (`/api/health` -> `club_prediction_ready: true`) | 30-40 ms |

## CORS

Allowed origins default to the usual dev servers: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`. Only `GET`, no credentials. Override with the environment variable `FOOTIQ_CORS_ORIGINS` (comma-separated exact origins); `*` is refused at start-up. Any other origin gets no CORS headers.

---

## Season simulator (Phase 3)

All errors keep the uniform `{"detail": "..."}` shape. Nothing here is live data; simulations are saved only by an explicit `POST`.

| Method and path | Purpose |
|---|---|
| `GET /api/season/status?key=&season=` | Eligibility (`ready` / `provisional` / `not_eligible`) with reasons, counts, freshness, the league's rule profile (status, sources, bands), the scoreline gate, `can_simulate` and `blockers`. Computes and saves nothing. `season` defaults to the newest. |
| `POST /api/season/simulate` | Body `{key, season, user_action: "simulate_season_button", simulations?, seed?, include_experimental?}`. Refused with 422 (nothing saved) if the action is wrong, the simulation count is outside the configured range, the data are not eligible, the rule profile is blocked, the league is outside the approved scope, or no scoreline method has been approved (`config/season_sim.json`, currently `null`, so every league is blocked). Otherwise runs, saves one row in `simulation_runs` and returns `{run_id, assumptions, result}`. |
| `GET /api/season/runs?key=&season=` | Saved runs (id, time, simulations, seed, model, data cut-off), newest first. |
| `GET /api/season/run?id=` | One saved run (404 if missing). |

`result.summary.teams[]`: `expected_points`, `points_p10/p90`, `expected_rank`, `rank_p10/p90`, `expected_goal_difference`, `p_title`, `p_top4`, `p_relegation`, `p_relegation_playoff`, `position_probabilities[]`. `result.summary.tie_resolution` reports how often a final decider was needed. `assumptions` carries the model ids and artifact hashes, scoreline method and its validation status, rule-profile sources, data cut-off, source freshness, eligibility snapshot, the input fingerprint, the limitations list, seed and timestamp.

### Experimental points-only simulation (approved 2026-10-25)

| Method and path | Purpose |
|---|---|
| `POST /api/season/points` | Body `{key, season, user_action: "simulate_points_button", simulations?, seed?}`. Simulates win / draw / loss only from the frozen club v1 probabilities (3 / 1 / 0 points) and saves one row in `simulation_runs` (`assumptions.mode = "points_only"`, label "Experimental \u2014 Points-only simulation"). Refused with 422 (nothing saved) if the action is wrong, the count is outside the configured range, the data are Not eligible, or the league is outside the approved scope (Bundesliga and La Liga). It needs no scoreline method; it returns **no exact** title, top-four, relegation or position probability and no table. For the Bundesliga and La Liga it also returns **position ranges** (lower and upper bounds) in `result.position_bounds` (below). |

`GET /api/season/status` also returns `points_only: {label, can_run, blockers, limitations}`. `GET /api/season/runs` adds `mode` (`points_only` or `final_positions`).
`result.summary.teams[]` (points-only): `current_points`, `remaining_fixtures`, `expected_points`, `points_sd`, `points_p10/p25/median/p75/p90`, `points_min/max`, `distribution {first_points, probabilities[]}`. No club row carries a position field.

**Position ranges (`result.position_bounds`, experimental, added 2026-10-25; also in `GET /api/season/run` and saved with the run).** Lower and upper bounds, not exact probabilities; computed from the same win / draw / loss draws as the points, with no invented score and no tie settled by chance.

| Field | Meaning |
|---|---|
| `status` | `available`, or `unavailable` with `reason` (switched off in `config/season_sim.json`, outside the scope, league rules blocked, no verified bounds settings, or an internal consistency check failed); when unavailable there are no numbers |
| `label`, `kind` | "Experimental — position ranges (lower and upper bounds, not exact probabilities)", `lower_and_upper_bounds` |
| `meaning`, `method` | plain-language definitions of `guaranteed`, `possible`, `unresolved`, and how they are computed |
| `bands[]` | `{id: title \| top4 \| relegation, label, positions [first, last], places}`; relegation means direct relegation (Bundesliga 17-18, La Liga 18-20) |
| `clubs[]` | same order as the points table: `{entity_id, name, title \| top4 \| relegation: {guaranteed, possible, unresolved, se_guaranteed, se_possible}}` |
| `guaranteed` (lower bound) | share of simulated seasons in which the club is in the band whatever the unplayed scores turn out to be |
| `possible` (upper bound) | share of simulated seasons in which the club could be in the band for some scores |
| `unresolved` | `possible - guaranteed`: what the points and the verified rules cannot settle |
| `checks` | `lower_never_above_upper`, `all_values_between_0_and_100_percent`, `places_sums_consistent`, `places_sums` (sum of lower bounds <= places <= sum of upper bounds) |
| `ties` | `tie_groups`, `tie_groups_fully_decided`, `simulations` |
| `rules` | `profile_id`, `status`, `sources[]`, `live_confirmation` (La Liga: PENDING until the checksum is verified), `criteria_used {two_clubs, three_or_more_clubs}`, `deciders_never_simulated`, `interpretation_notes` |
| `limitations[]`, `monte_carlo` | the limitations shown on the page; simulations, seed, `standard_error_max` |

Values are fractions in [0, 1]; `guaranteed <= possible` always. `GET /api/season/status` adds `points_only.position_bounds {available, blockers, bands}`. See [PHASE3_POSITION_BOUNDS_INTEGRATION.md](PHASE3_POSITION_BOUNDS_INTEGRATION.md).

Final-position simulations (`POST /api/season/simulate`) stay disabled. When a tie cannot be resolved by a supported rule it is left unresolved: the affected band probability is `null` and only `*_low` / `*_high` bounds are given.
