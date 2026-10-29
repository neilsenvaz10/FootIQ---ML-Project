# 09 Player data audit (generated 2026-10-20 22:32)

## Counts
* Players (04): 25,288 rows, 25,288 unique ids: {'source_native_id_StatsBomb': 9906, 'derived_squad_scoped_key': 9583, 'derived_team_scoped_name_key': 5799}.
* Player-match rows (05): 180,172 ({'StatsBomb Open Data': 113623, 'openfootball match files (CC0)': 66549}); duplicate (match, player, team): **0**.
* Memberships (08): lineup-based 24,694 (n_matches mismatches vs 05: **0**), squad lists 9,583 (all undated), team types {'club': 27202, 'national': 7075}.
* Competitions/seasons: 107 competition-season blocks (`12_PLAYER_STATISTICS_COVERAGE.csv`): StatsBomb 80 blocks (3,961 matches), openfootball 27 blocks (2025-26 top-5 + Austria, Club World Cup 2000-2025).
* Gender: StatsBomb rows {'male': 74937, 'female': 38686}; matches {'male': 2651, 'female': 1310}. openfootball rows are **unlabelled** ({"unlabelled in source (men's competition assumed from competition name)": 66549}).

## Identity
* StatsBomb ids are native; 6 normalised names carry more than one id (`_evidence/player_identity_same_name_multiple_statsbomb_ids.csv`) - could be homonyms or duplicates; not merged.
* openfootball lineup and squad keys are `team-scoped name keys`: 584 names appear under several team keys (transfers or homonyms - undecidable); 873 names occur in both sources and were not merged. Nationality missing for 100% and position for 100% of openfootball lineup players.
* Transfers: 2,478 of 9,906 StatsBomb players appear for 2+ teams; same player with two teams on one date: **0**. 155 player-competition-seasons list two teams (mid-season transfer or club + loan; not verifiable).
* No career history exists outside the matches present: club histories are **not** reconstructed.

## Statistics: verified vs estimated vs missing
* StatsBomb minutes: derived from lineup position intervals (union of overlapping intervals; range checked <= 130); missing 0.0%; goal totals per match reconcile with the official score for **3,961 of 3,961** matches (own goals credited to the opponent) - an independent validation of the event aggregation.
* openfootball minutes: **ESTIMATED** (substitution / red-card minutes within a 90-minute frame; extra time and stoppage ignored); only appearances, estimated minutes, goals, own goals, penalty goals and cards exist.
* No xA / expected assists anywhere; xG exists only for StatsBomb. Metric availability per source: `_evidence/player_metric_availability.csv`.
* **Missing-as-zero defect:** 190 StatsBomb rows (players with no recorded event) have `goals`, `shots_on_target`, `xg`, ... as NaN but `passes`, `shots` and `tackles` forced to 0 (190 rows with passes = 0 and NaN goals). Inconsistent treatment of missing data.
* 812 appearance rows have no pass/shot/tackle at all (short cameos or data gaps).
* Positions: StatsBomb first position only (not the full role history); position groups {'MID': 38416, 'DEF': 37713, 'FWD': 29489, 'GK': 8005}.

## Suitability (summary; details in files 13-16)
A. Descriptive player analytics: APPROVED WITH RESTRICTIONS. B. Clustering / similarity: APPROVED WITH RESTRICTIONS (StatsBomb male player-seasons only). C. Future performance regression: BLOCKED.
