# 01 Verification summary - FootIQ datasets (independent audit, generated 2026-10-20 22:32)

Verification only: no model was trained, no existing dataset / model / report was modified. Every number comes from the actual files (`_scripts/`, `_evidence/`).

## 1. Overall verdict
**The match data is accurate, traceable and reproducible, but it is not ready for an all-competition model.** A *league-only* club 90-minute model is approved with restrictions; international, all-competition club and player-performance models are blocked; tournament simulation was not verified.

What holds up:
* All five headline counts are exact (strict 125,858; extended 129,829; international 49,362; club 223,625; recent 1,482).
* Milestone 1 baseline: 522/522 files unchanged; the submission ZIP equals the directory; the isolated rebuild reproduces the training CSVs byte for byte.
* Every one of the 129,829 feature rows was re-derived independently with zero differences; the 90-minute label of all 142,309 labelled results was re-derived with zero mismatches; 128,101 openfootball rows were traced to their raw source line and 1,571 Wikipedia rows to a cached revision with zero failures.
* Wikipedia and openfootball agree on all 1,328 overlapping comparable final scores (0 conflicts, 0 penalty disagreements, 0 regulation-score disagreements).

What does not:
* Feature defect (`same_country` wrong for 37.6% of rows), duplicate Russian fixtures, constant `neutral_known`, disconnected Elo components, unresolved identities for 34.6% of match sides, selection bias in the strict knockout rows, unusable undated lower-tier results, unresolved CC BY-SA scope, unread StatsBomb licence, discontinuous player data. See `VERIFICATION_ISSUES.csv` (25 issues: {'Medium': 14, 'Low': 5, 'High': 4, 'Info': 2}).

## 2. Verified counts
| file | rows | columns | date_min | date_max | unique_ids | duplicate_ids | competitions | seasons | missing_cell_pct |
|---|---|---|---|---|---|---|---|---|---|
| SUB/01_Historical_International_Matches.csv | 49362 | 25 | 1872-11-30 | 2026-06-02 | 49362.0 | 0.0 | 222.0 |  | 7.92 |
| SUB/02_Historical_Club_Matches.csv | 223625 | 39 | 1888-09-08 | 2026-05-31 | 223625.0 | 0.0 | 160.0 | 62.0 | 22.58 |
| SUB/03_Recent_Match_Results.csv | 1482 | 32 | 2026-06-03 | 2026-10-06 | 1482.0 | 0.0 | 33.0 | 3.0 | 25.54 |
| RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv | 125858 | 49 | 2018-08-01 | 2026-09-20 | 125858.0 | 0.0 | 143.0 | 19.0 | 0.0 |
| RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv | 129829 | 49 | 2018-08-01 | 2026-09-20 | 129829.0 | 0.0 | 144.0 | 19.0 | 0.0 |

## 3. Competition-season completeness (file `03_COMPETITION_SEASON_VERIFICATION.csv`)
612 club competition-seasons and 41 international rows were independently checked. Independent suitability: {'SUITABLE_WITH_RESTRICTIONS': 386, 'SUITABLE': 121, 'DESCRIPTIVE_ONLY_OR_NEEDS_CORRECTION': 82, 'FORWARD_HOLDOUT_ONLY': 23}. Of 589 finished club competition-seasons that have an expected count, 548 show no unexplained shortfall; 41 show a total shortfall of 143 matches (mostly EFL Cup, Coupe de France 2024-25, lower cups; see I-19). The five major leagues, the Championship, the Champions League, Europa League (2018-19 to 2025-26) and Conference League (2021-22 to 2025-26) have no unexplained shortfall except the known cancellations (Ligue 1 2019-20: 101 cancelled; Europa League 2021-22: 2 cancelled). International: World Cup 1930-2026 (23 editions) and 11 continental editions match the expected edition counts exactly.
2025-26 lower-tier leagues are incomplete in the dated sources (Scottish Premiership 63/198, Segunda 131/462, 2. Bundesliga 99/306, 3. Liga 130/380, Ligue 2 116/306, Turkish 99/306, Belgian 121/240, Greek 62/182, Austrian 2. Liga 96/240, Serie B 309/380). For 2026-27 only matches dated before 2026-10-01 were assessed; results end 2026-09-20 and Belgium has 305 dated fixtures without results.

## 4. Recovered UEFA competitions (Wikipedia, cross-checked)
| competition | season | matches | duplicates | date_range | league_phase_teams | matches_per_team | aggregate_notes_checked | aggregate_notes_matching | goal_lists_consistent_pct |
|---|---|---|---|---|---|---|---|---|---|
| UEFA Europa League | 2025-26 | 189 | 0 | 2025-09-24..2026-05-20 | 36 | {'8': 36} | 20 | 20 | 95.8 |
| UEFA Conference League | 2025-26 | 153 | 0 | 2025-10-02..2026-05-27 | 36 | {'6': 36} | 22 | 22 | 92.8 |
| UEFA Europa League | 2018-19 | 205 | 0 | 2018-09-20..2019-05-29 | 48 | {'6': 48} | 27 | 27 | 92.2 |
| UEFA Europa League | 2019-20 | 197 | 0 | 2019-09-19..2020-08-21 | 48 | {'6': 48} | 20 | 20 | 96.4 |
| UEFA Europa League | 2024-25 | 189 | 0 | 2024-09-25..2025-05-21 | 36 | {'8': 36} | 20 | 20 | 95.8 |
| UEFA Conference League | 2024-25 | 153 | 0 | 2024-10-02..2025-05-28 | 36 | {'6': 36} | 20 | 20 | 96.7 |
| UEFA Champions League | 2025-26 | 189 | 0 | 2025-09-16..2026-05-30 | 36 | {'8': 36} | 22 | 22 | 94.7 |

Format checks: league phase of 36 teams, each playing 8 (Europa League) or 6 (Conference League) matches with 4 / 3 at home; knockout stages 16 + 16 + 8 + 4 + 1 (2024-25 and 2025-26); 2018-19: 12 groups x 12 + 32 + 16 + 8 + 4 + 1 = 205; 2019-20: 197 = 144 + 32 + 14 + 4 + 2 + 1 (two round-of-16 ties single-leg after COVID). Every "won X-Y on aggregate" note on the pages (20-27 per competition, 156 in total) equals the aggregate computed from the parsed legs: 0 mismatches. Openfootball overlaps exist only for 2024-25 (and Champions League 2025-26): all comparable scores agree. For 2025-26 Europa / Conference League and 2018-20 Europa League there is **no second dated source**, so those results rest on one community-edited page set plus internal consistency (not on official UEFA records, which are not permitted to be scraped).

## 5. Labels - see `04_MATCH_LABEL_AUDIT.md`
Strict contains only `confirmed` labels; inferred labels exist only in the extended set; 0 raw-line violations. Remaining ambiguity: selection bias in strict knockouts (I-05) and unproven second-leg cases (I-22).

## 6. Features and leakage - see files 06 and 07
No future information enters features (independent recomputation identical). Failing / unverified items: duplicate fixtures, selection on target, identity mapping retrospective, availability timestamps, calibration protocol, holdout discipline.

## 7. Sources and licences - see file 08
openfootball CC0 (file text verified in 16 repos); Wikipedia CC BY-SA 4.0 (1.21% of extended rows, no domestic-league rows); StatsBomb licence PDF unread; Football-Data.co.uk excluded.

## 8. Players - see files 09, 12-17
25,288 player records, 180,172 player-match rows (113,623 StatsBomb event-level, 66,549 openfootball appearance-only), no duplicates, StatsBomb goals reconcile with scores for all 3,961 matches. New versioned form datasets were built from existing verified statistics in `player_form_v1/`.

## 9. Decisions - see `11_ML_TRAINING_APPROVAL.md`
International 90-min: BLOCKED. Club league-only: APPROVED WITH RESTRICTIONS. Club all-competition: BLOCKED. Player descriptive / recent form / clustering: APPROVED WITH RESTRICTIONS. Player-performance prediction: BLOCKED. Tournament simulation: NOT VERIFIED.
