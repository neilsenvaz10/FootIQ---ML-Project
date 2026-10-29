# 08 Final training-readiness report - club league-only 90-minute 1X2, dataset v1.1 (generated 2026-10-20 23:14)

No model was trained, tuned or evaluated. Forward-holdout outcomes were not inspected.

## 1. Corrections performed
1. **Features:** `same_country` and `neutral_known` removed; constant scope indicators removed; the feature contract now has 25 features (`feature_contract_v1.1.json`, `04_FINAL_FEATURE_DATA_DICTIONARY_v1.1.csv`).
2. **Russian 2019-20 duplicate:** 240 ru2 rows removed on source-level evidence (file body identical to ru1).
3. **Dates verified at source level** (new, found while handling the 706 flagged labels): every openfootball date was re-resolved and accepted only if the source printed an explicit year or a weekday that equals the resolved date. 7,607 rows of Nigerian files that print only "DD.MM." have unverifiable years (their parsed dates disagreed with the files' own declared windows by up to a year: 13 files, 4,206 rows outside the window) and were excluded.
4. **Season labels:** the 706 rows flagged in the verification belong to 13 competition-seasons (4,537 source rows in all: Nigerian, Ghana 2016-17 and Mexican Ascenso 2014-15 files). Final disposition of those 4,537 rows: EXCLUDED_CALENDAR_UNVERIFIABLE_DOTTED_DATES 4,089; USED_ONLY_FOR_RATING_STATE_BEFORE_2018_08_01 421; EXCLUDED_OUT_OF_SCOPE_STAGE_NOT_REGULAR_ROUND_ROBIN 24; EXCLUDED_LABEL_NOT_CONFIRMED_UNKNOWN 1; EXCLUDED_NOT_A_COMPLETED_RESULT 1; EXCLUDED_SEASON_LABEL_INCOMPATIBLE_WITH_VERIFIED_DATE 1. Labels are names and were kept unless the verified dates contradict them; a label is compatible when every verified date lies within [1 Jan Y, 31 Dec Y+1]. Corrected: Belgian first division (folder 2021-22 -> 2020-21, supported by the title "2020/21" and the verified dates; 320 rows in the final dataset); excluded: 1 Mexican Ascenso row incompatible with its label. Ghana 2016-17 is compatible (calendar-year season) and kept.
5. **Scope and labels:** only regular round-robin stages (whitelist), `confirmed` labels, no extra-time/penalty marker; play-off, promotion/relegation and final stages are excluded (2,700 rows); the v1.0 strict league subset contained 272 such rows (including 65 with an extra-time marker) that its league rule had treated as ordinary league matches; they are out of scope now.
6. **Identity:** 12 wrong canonical merges withdrawn; ambiguous duplicates excluded.
7. **Features recomputed** from verified records only (CC0 openfootball; no Wikipedia-derived result enters ratings, form or rest days); ratings use confirmed 90-minute results only.
8. **Evaluation sets** exclude incomplete league-seasons and identity-flagged rows.

## 2. Rows removed or corrected (full detail: `03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv`, one line for each of the 236,702 source rows)
| disposition | rows |
|---|---|
| USED_ONLY_FOR_RATING_STATE_BEFORE_2018_08_01 | 76700 |
| INCLUDED_TRAIN | 59356 |
| INCLUDED_TEST | 26000 |
| INCLUDED_VALIDATION | 22578 |
| EXCLUDED_OUT_OF_SCOPE_NOT_DOMESTIC_LEAGUE | 14703 |
| EXCLUDED_NOT_A_COMPLETED_RESULT | 12293 |
| INCLUDED_FORWARD_HOLDOUT | 8920 |
| EXCLUDED_CALENDAR_UNVERIFIABLE_DOTTED_DATES | 7607 |
| EXCLUDED_INSUFFICIENT_HISTORY_LT5_PRIOR_RATED_MATCHES | 5414 |
| EXCLUDED_OUT_OF_SCOPE_STAGE_NOT_REGULAR_ROUND_ROBIN | 2700 |
| REMOVED_DUPLICATE_RU2_2019_20_IDENTICAL_TO_RU1 | 240 |
| EXCLUDED_LABEL_NOT_CONFIRMED_UNKNOWN | 173 |
| EXCLUDED_AMBIGUOUS_SAME_DAY_DUPLICATE_FIXTURE | 8 |
| EXCLUDED_ELO_PAIR_NOT_CONNECTED_ASOF | 6 |
| EXCLUDED_LABEL_NOT_CONFIRMED_NOT_COMPLETED | 3 |
| EXCLUDED_SEASON_LABEL_INCOMPATIBLE_WITH_VERIFIED_DATE | 1 |

## 3. Final eligible match count
**116,854 matches**: train 59,356, validation 22,578, test 26,000, forward holdout 8,920.
Primary evaluation rows: validation 17,092, test 15,645, forward holdout 5,770. Secondary (calendar-year leagues): validation 5,015, test 3,449, forward holdout 570. Rows in no evaluation set: 9,957 ({'season incomplete / not verified complete': 9574, 'identity review flag': 383}).

## 4. Features
Retained (25): home_elo, away_elo, elo_diff, home_n_prior, away_n_prior, home_ppg5, away_ppg5, home_ppg10, away_ppg10, home_gf5, home_ga5, away_gf5, away_ga5, home_gf10, home_ga10, away_gf10, away_ga10, home_venue_ppg5, away_venue_ppg5, ppg5_diff, gd5_diff, home_days_rest, away_days_rest, rest_diff, league_tier. Excluded: `same_country`, `neutral_known`, `is_league`, `is_league_phase`, `is_knockout`, `comp_type_continental`, `comp_type_cup`, and every outcome field. Audit metadata `meta_*` are not inputs.

## 5. Chronological splits (exact boundaries)
| split | start_inclusive | end_inclusive | rows | first_match | last_match | eval_primary_rows | eval_secondary_calendar_year_rows | role |
|---|---|---|---|---|---|---|---|---|
| train | 2018-08-01 | 2023-06-30 | 59356 | 2018-08-01 | 2023-06-30 | 0 | 0 | fit models and learned preprocessing |
| validation | 2023-07-01 | 2024-06-30 | 22578 | 2023-07-01 | 2024-06-30 | 17092 | 5015 | model / feature / hyper-parameter selection |
| test | 2024-07-01 | 2025-06-30 | 26000 | 2024-07-01 | 2025-06-29 | 15645 | 3449 | one-time unbiased estimate after all choices are frozen |
| forward_holdout | 2025-07-01 | 2026-09-30 | 8920 | 2025-07-02 | 2026-09-20 | 5770 | 570 | one-time final evaluation; never used for any decision |

Calendar-year leagues are cut by date like every other league; their evaluation rows are reported separately. Incomplete league-seasons (75 in total, all of them listed in `season_completeness_by_league_season.csv`) are excluded from evaluation; the largest excluded groups in the evaluation window are: espana:2-liga2 2024-25 (453 rows); europe/netherlands:nl2 2024-25 (370 rows); italy:2-serieb 2024-25 (366 rows); england:3-league1 2025-26 (356 rows); europe/turkey:tr1 2024-25 (328 rows); italy:2-serieb 2025-26 (309 rows); england:5-nationalleague 2025-26 (288 rows); italy:3-seriec_b 2024-25 (285 rows).

## 6. Acceptance criteria
| criterion | status | evidence |
|---|---|---|
| Zero unresolved duplicate fixtures in scope | MET | ru2 duplicate removed (240), 8 ambiguous same-day rows excluded; 0 duplicates by id, natural key and cross-competition (date, pair, score) |
| Zero known incorrect season labels | MET for the approved scope | 706 flagged rows analysed: see section 2; Belgian 2021-22 folder label corrected (320 rows); unverifiable rows are excluded, not relabelled |
| Zero known 90-minute label errors | MET as far as verifiable | only regular round-robin stages with confirmed labels; 272 rows of the v1.0 strict league subset came from final / promotion / relegation / play-off stages and are now excluded; residual risk = errors inside the source itself |
| No known future-result leakage | MET | prefix-invariance at 3 cut-offs, brute-force deletion test, independent re-implementation on 100% of rows |
| Club identity and Elo limitations documented | MET (restricted) | file 06: 12 withdrawn merges, review flags, disconnected Elo islands |
| Reproducible outputs | MET | two consecutive full rebuilds byte-identical for 4 of 4 key outputs |
| Fixed evaluation boundaries | MET | 05_CHRONOLOGICAL_SPLIT_MANIFEST_v1.1.csv/json |

## 7. Remaining limitations
* The dataset is a **regular-season league** dataset: no cups, play-offs, extra-time matches or neutral venues.
* 2025-26 lower-tier leagues (Scottish Premiership, Segunda, 2. Bundesliga, 3. Liga, Ligue 2, Belgian, Greek, Turkish, Austrian 2. Liga, English League One/Two/National League, Serie B) stop early in the CC0 data; they stay in training but are not evaluated. 2026-27 evaluation is limited to leagues whose dated fixtures all have results (early season, results end 2026-09-20).
* Elo levels are comparable only inside connected components; 28.5% of rows are in island leagues; no cross-league strength adjustment.
* Identity: 31.2% of match sides use source-scoped ids; 12 merges withdrawn (renamed clubs lose history); flagged rows excluded from primary evaluation.
* Nigerian files with dotted dates (7,607 rows) are unusable until a verified calendar is available.
* Rest days only know matches present in the CC0 data (several 2025-26 European fixtures are missing), so they can be overstated for those clubs.
* Kick-off times are partly missing; the cut-off is the calendar day.
* No odds, lineups, injuries or xG: expected accuracy is bounded by Elo/form information.
* Data readiness is not predictive accuracy: nothing was fitted.

## 8. Decision
**APPROVED WITH RESTRICTIONS for a controlled baseline training experiment** (club domestic-league 90-minute 1X2 only), under these rules: (1) fit on `split == train` only; (2) select models / features / hyper-parameters on `validation` primary rows only; (3) evaluate on `test` primary rows once, then on `forward_holdout` primary rows once, without changing anything afterwards; (4) fit all preprocessing on train (`preprocessing_spec_v1.1.json`); (5) report per league group and separately for calendar-year leagues; (6) do not use `meta_*` or flag columns as inputs; (7) include simple baselines (Elo-only, always-home); (8) no cups / continental / international data. **Awaiting your explicit approval before any training.**

## 9. Reproducibility
Key outputs rebuilt twice with identical SHA-256: {'01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv': True, '02_CORRECTED_FEATURE_DATASET_v1.1.csv': True, '03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv': True, 'season_completeness_by_league_season.csv': True}. Build order: `_build/p1_calendar_audit.py`, `p2_build.py`, `p3_tests.py`, `p4_docs.py` (inputs are read-only: Submission `club_matches_all.csv` and raw sources, Readiness `M_of.pkl`, `labels.py`, Verification identity evidence).
