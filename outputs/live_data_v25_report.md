# Live Data Backbone v2.5

V2.5 turns the live-data pilot into reusable model-ready tables. The prediction formula is still the v2.3/v2.4 engine; the upgrade is data structure, repeatability, and auditability.

## Run Summary

- Tracked fixtures: 8.
- Provider fixture matches found: 1/8.
- Weather rows available: 8/8.
- Fixtures with confirmed lineup context: 0/8.
- Final fixtures ready for scoring: 0.
- Average data-quality score: 47.4/100.

## API Budget

- Requests counted today: 8 / 100.
- Reserve kept untouched: 15.
- Remaining before local stop: 77.

## Model-Ready Tables

| Table | Rows | Purpose |
|---|---:|---|
| v25_fixtures_live | 8 | Canonical fixture scope. |
| v25_team_strength_live | 15 | One current strength row per team. |
| v25_provider_status_live | 8 | API-Football fixture/status/result layer. |
| v25_confirmed_lineups_live | 0 | Confirmed starters plus player-impact matching. |
| v25_player_availability_live | 16 | Availability contract; injuries still neutral/pending. |
| v25_weather_context_live | 8 | Match-hour temperature/rain/wind context. |
| v25_odds_snapshot_live | 8 | Odds contract; live odds not enabled yet. |
| v25_match_predictions_live | 8 | Final v2.5 match calls. |
| v25_postmatch_results_live | 8 | Scoring table for final results. |
| v25_data_quality_live | 8 | Missing-input and quality audit. |

## Current Calls

| Match | Status | Live score | Verdict | Confidence | Pick | Data quality |
|---|---|---|---|---|---|---:|
| Portugal vs Chile | not found |  | No strong edge | Pass | team1_win | 43 |
| Germany vs USA | not found |  | No strong edge | Pass | team1_win | 43 |
| Bolivia vs Scotland | not found |  | Draw lean | Low-medium | draw | 43 |
| Brazil vs Egypt | not found |  | Brazil avoid defeat | Medium-low | team1_win | 43 |
| Argentina vs Honduras | not found |  | Argentina win lean | Medium | team1_win | 43 |
| Morocco vs Norway | not found |  | Draw risk / no strong edge | Pass | draw | 43 |
| Colombia vs Jordan | not found |  | Colombia win lean | Medium | team1_win | 43 |
| Argentina vs Iceland | NS |  | Argentina win lean | Medium | team1_win | 78 |

## What v2.5 Still Does Not Solve

- Injury/suspension data is tabled but not fully ingested yet.
- Odds movement is tabled but not connected to a live odds feed yet.
- Data refresh is manual; v2.6 should add scheduled refresh logic and stronger prediction updates.
