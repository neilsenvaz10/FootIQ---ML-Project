# 14 Player historical-form audit (generated 2026-10-20 22:32)

## Built
`player_form_v1/PLAYER_SEASON_STATS_STATSBOMB_v1.0.csv`: 18,481 player-team-competition-season rows with matches observed, starts, derived minutes, totals, per-90 (only when minutes >= 90), pass completion, previous observed season's goals/xG per 90 and minutes. `season_complete_for_player` is deliberately `UNKNOWN`: only matches present in the open data are counted.

## Findings
* Players with two or more observed seasons: 3,406 (of 9,906); consecutive observed seasons are frequently *not* consecutive real seasons (StatsBomb publishes selected seasons), so "trend" columns must be read as "previous observed season".
* Transfers: 2,478 players change team inside the data; the native StatsBomb id keeps identity across clubs and competitions. openfootball keys cannot follow transfers.
* Minutes: season minutes are sums of match-level derived minutes; seasons are incomplete whenever not every match of the team is in the open data. Injuries and unused-substitute games are not recorded.
* Verified vs estimated minutes are separated by source and by file (`minutes_basis` column).
* Career-length trends need >=3 observed seasons; very few players have them (`PLAYER_SEASON_STATS` can be grouped by `source_player_id`).

## Decision: APPROVED WITH RESTRICTIONS for descriptive season tables of StatsBomb competitions; NOT suitable for career-trend modelling.
