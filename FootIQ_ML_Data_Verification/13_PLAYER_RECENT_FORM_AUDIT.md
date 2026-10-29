# 13 Player recent-form audit (generated 2026-10-20 22:32)

## What was built (new files, originals untouched)
`player_form_v1/PLAYER_RECENT_FORM_STATSBOMB_v1.0.csv` (113,623 rows, 9,906 players): for each appearance, windows of the last 3 / 5 / 10 **observed earlier** matches (strictly earlier calendar dates) with mean minutes, start rate, per-90 goals, assists, shots, shots on target, xG, key passes, passes, pass completion, tackles, interceptions, clearances, blocks, pressures, yellow-card rate, plus window length and span. Current-match values are stored only in `TARGET_*` columns.
`player_form_v1/PLAYER_RECENT_FORM_OPENFOOTBALL_APPEARANCES_v1.0.csv` (66,549 rows): appearances, appearance rate, estimated minutes, goals and starts over the team's previous 3 / 5 / 10 matches (2025-26 top-5 leagues, Austria, Club World Cup).

## Feasibility
| Question | Answer |
|---|---|
| Last 3 / 5 / 10 matches (StatsBomb) | rows with >=3 / >=5 / >=10 prior observed matches: 89,780 / 79,617 / 60,015 |
| Are the windows real "last N matches"? | **No, only last N observed matches.** StatsBomb covers selected competition-seasons; median gap to the previous observed match 7 days, but 16.8% of gaps exceed 21 days and 30.6% of complete 5-match windows span more than 60 days |
| Rolling minutes, goals, assists, shots, passes, defensive actions, xG | available (StatsBomb) |
| Rolling xA | **not available** |
| Per-90 | available; computed as window sum / window minutes x 90 (NaN when minutes = 0) |
| Participation trend | appearance rate only from openfootball (team-match denominators); unused substitutes / squad omissions / injuries are indistinguishable |
| Strictly earlier matches only | brute-force recomputation of 500 random rows: mismatches **0**; same-day matches excluded by design |
| Minutes verified vs estimated | StatsBomb derived (not independently verified); openfootball estimated - kept in separate files |

## Leakage and missing-data findings
* Features contain no information from the target match; `TARGET_*` columns must be dropped from X.
* Women's and men's rows are mixed in the StatsBomb file (`gender`); filter before use.
* Injuries and transfers cannot be seen: a long gap is not distinguishable from a missed match.
* NaN is kept where a window has no minutes or no events.

## Decision: APPROVED WITH RESTRICTIONS (descriptive recent-form analytics only; flag `w*_span_days`; do not call the windows "last N matches").
