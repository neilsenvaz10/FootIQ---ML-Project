# 15 Player clustering readiness (generated 2026-10-20 22:32; no clustering was run)

## Cohort sizes (StatsBomb, male competitions, derived minutes per player-competition-season)
| position_group | player_seasons | >=450min | >=900min | >=1350min | distinct_competitions |
|---|---|---|---|---|---|
| GK | 982 | 212 | 134 | 110 | 17 |
| DEF | 4891 | 972 | 670 | 513 | 17 |
| MID | 4491 | 789 | 543 | 422 | 17 |
| FWD | 3840 | 627 | 421 | 292 | 17 |
| UNKNOWN | 0 | 0 | 0 | 0 | 0 |
Female player-seasons >= 900 minutes: 1,204 (cluster separately). Total male player-seasons >= 900 min: 1,768.

## Feature quality among players with >= 900 minutes
* Zero share of per-90 features: {'goals_p90': 0.352, 'assists_p90': 0.364, 'shots_p90': 0.08, 'key_passes_p90': 0.064, 'tackles_p90': 0.072, 'interceptions_p90': 0.074, 'clearances_p90': 0.042}; NaN share: {'goals_p90': 0.0, 'xg_p90': 0.0, 'pass_completion': 0.0}.
* Available per-90 inputs: goals, assists, shots, shots on target, xG, key passes, passes, pass completion, tackles, interceptions, clearances, blocks, pressures, dribbles, fouls, carries. Goalkeeper statistics exist only as saves / goals conceded (not post-shot xG). No xA, no tracking.

## Method-specific readiness
| Method | Readiness | Comment |
|---|---|---|
| K-Means | APPROVED WITH RESTRICTIONS | Position-specific cohorts (GK, DEF, MID, FWD) with >= 900 minutes; z-score within cohort; log1p counts; drop collinear columns; k chosen on validation stability, not on labels. Cohorts of 134 (GK) to 670 (DEF) are small. |
| Hierarchical | APPROVED WITH RESTRICTIONS | Same cohorts; sizes are workable. |
| DBSCAN | Weak | Density depends on competition mix and scaling; ~420-670 points per cohort and 15+ dimensions give unstable epsilon; use after PCA only. |
| Position-aware similarity | APPROVED WITH RESTRICTIONS | Position = first listed position only. |
| PCA visualisation | APPROVED | descriptive only. |

## Recommendations
* Minimum playing time: 900 minutes (>= 450 only for sensitivity); per-90 only when minutes >= 90.
* Competition context: standardise within competition-season or include competition as a stratifier; cross-league comparison is not valid.
* Missing data: do not zero-fill; drop players with NaN in selected features; goalkeepers cluster only on keeper metrics.
* Never cluster openfootball lineup players (no event metrics, estimated minutes).
* Licence: StatsBomb terms are research/education only until the PDF is reviewed.

## Decision: APPROVED WITH RESTRICTIONS (StatsBomb male player-seasons; research use).
