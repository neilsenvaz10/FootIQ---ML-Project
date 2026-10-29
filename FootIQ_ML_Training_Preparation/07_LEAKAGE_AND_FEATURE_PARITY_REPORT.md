# 07 Leakage and feature-parity test results (v1.1, generated 2026-10-20 23:14)

45 of 45 tests pass; failing: 0. Raw results: `07_LEAKAGE_AND_FEATURE_PARITY_TEST_RESULTS_v1.1.csv`; per-feature parity table: `04b_FEATURE_PARITY_COMPARISON_v1.1.csv`.

| group | test | result | detail |
|---|---|---|---|
| labels | every row has label_90_status == confirmed | PASS | {'confirmed': 116854} |
| labels | no inferred knockout label (all rows are regular league matches) | PASS | phase/competition_type check |
| labels | no extra-time or penalty marker on any included match | PASS | extra_time_played values {'no': 116854} |
| labels | label equals the sign of the 90-minute score (independent recomputation) | PASS | 116854 rows |
| labels | 90-minute score equals the printed full-time score for league matches | PASS | regulation == final |
| labels | no awarded / abandoned / cancelled match | PASS | {'completed': 116854} |
| labels | goals are non-negative integers <= 15 | PASS | max 13 |
| duplicates | record_id unique | PASS |  |
| duplicates | no duplicate (competition, season, date, home, away) | PASS |  |
| duplicates | no team pair twice on one date in one competition (either orientation) | PASS |  |
| duplicates | no (date, team pair, score) shared by two competitions | PASS |  |
| duplicates | Russian 2019-20 ru2 file absent | PASS |  |
| duplicates | Russian Premier League 2019-20 has exactly its 240 fixtures (16 teams x 15 x 2 = 240) | PASS | 226 eligible rows (<=240, early rows lack history) |
| dates | no null / unparsable date | PASS |  |
| dates | every row has a source-verified date (explicit year or weekday-confirmed) | PASS | {'weekday_verified': 105323, 'explicit_year': 11531} |
| dates | no row from a dotted-date (unverifiable) file | PASS | Nigerian dotted-date files excluded |
| dates | dates inside the training window | PASS | 2018-08-01..2026-09-20 |
| seasons | every date lies inside the season label's calendar range (Jan 1 Y .. Dec 31 Y+1) | PASS |  |
| seasons | known incorrect season labels in scope | PASS | 706 originally flagged rows: Nigerian dotted-date rows excluded (cannot be verified), Ghana 2016-17 verified compatible, 1 Mexican Ascenso row excluded, Belgian folder label corrected (320 rows) |
| seasons | Belgian first division season label corrected from folder 2021-22 to 2020-21 | PASS | see season_label_verification_by_file.csv |
| provenance | provenance, licence and extraction date present on every row | PASS |  |
| provenance | CC0 only (no Wikipedia-derived row) | PASS | {'CC0-1.0': 116854} |
| provenance | raw source line contains both team names and the 90-minute score for every row | PASS | 116854 rows, failures 0 |
| identity | no club appears under two entity ids inside one league-season (name equal after punctuation removal) | PASS | 0 conflicts |
| identity | no entity carries two spellings inside one league-season (wrong-merge guard, e.g. CSKA Sofia / CSKA 1948 Sofia, FC vs CS Universitatea Craiova) | PASS | 0 entities; 12 (entity, spelling) pairs were un-merged |
| identity | share of match sides with canonical (alias-table verified) club id | PASS | 68.8% canonical, rest source-scoped ids (consistent inside each league); flagged for review: 1055 rows |
| identity | cross-border clubs: AS Monaco in Ligue 1, Welsh clubs in English leagues are single entities | PASS | Monaco ids ['CLUB:MCO:as-monaco']; Welsh ids ['CLUB:WAL:aberystwyth-town-fc', 'CLUB:WAL:bala-town-fc', 'CLUB:WAL:barry-town-afc', 'CLUB:WAL:briton-ferry-llansawel-afc', 'CLUB:WAL:caernarfon-town-fc', 'CLUB:WAL:cardiff-city-fc'] |
| features | feature file columns follow the contract order | PASS | 25 features |
| features | removed / forbidden columns absent (same_country, neutral_known, scores, half-time) | PASS | [] |
| features | no constant feature | PASS | [] |
| features | NaN only where history is genuinely absent | PASS | {'home_venue_ppg5': 3, 'away_venue_ppg5': 1} |
| features | meta_latest_info_date strictly earlier than the match date for every row | PASS |  |
| features | home and away were connected in the rating graph before the match | PASS |  |
| parity | independent re-implementation reproduces every stored feature on all rows (contract builder vs independent code) | PASS | 116854 rows, max diff 4.55e-13 |
| parity | diff features equal the differences of their parts | PASS |  |
| leakage | prefix invariance at 2021-07-01: deleting every later match leaves earlier features unchanged | PASS | 33707 rows |
| leakage | prefix invariance at 2023-07-01: deleting every later match leaves earlier features unchanged | PASS | 59356 rows |
| leakage | prefix invariance at 2025-07-01: deleting every later match leaves earlier features unchanged | PASS | 107934 rows |
| leakage | brute force: after deleting all matches on/after the fixture date, n_prior and days_rest are unchanged | PASS | 200 sampled non-train rows x 2 teams, mismatches 0 |
| leakage | no outcome-derived, post-match, standings or future information in the 25 contract features | PASS | features are functions of matches dated before the fixture only (see feature_contract.py) |
| leakage | forward holdout outcomes were not inspected to build or select anything | PASS | p2/p3 compute no label statistics on forward_holdout; eligibility/flags use dates, statuses and prior-match counts only |
| leakage | same-day matches never inform each other | PASS | state is updated after the whole calendar day; confirmed by prefix-invariance and brute-force tests |
| splits | every split lies inside its fixed calendar boundaries and splits do not overlap | PASS | {'train': ('2018-08-01', '2023-06-30', 59356), 'validation': ('2023-07-01', '2024-06-30', 22578), 'test': ('2024-07-01', '2025-06-29', 26000), 'forward_holdout': ('2025-07-02', '2026-09-20', 8920)} |
| splits | no club-season spans the validation/test boundary without chronological separation | PASS | split is by date; calendar-year leagues are cut by date (their halves fall in different splits); they are secondary evaluation only |
| splits | primary evaluation contains only complete (or complete-through-cutoff) split-year league-seasons without identity flags | PASS | 38507 rows |

## Feature parity
Two implementations were compared on all 116,854 rows: the contract builder (`feature_contract.py`, state machine used for training and meant for inference) and an independent re-implementation (`p3_tests.py`: per-entity arrays, `searchsorted`, separate Elo replay). Maximum absolute difference over all features: 4.55e-13; rows with a difference above 1e-6: 0; NaN pattern mismatches: 0.

## What is *not* proven
* Kick-off times are missing for part of the data, so intra-day information is excluded by construction rather than proven.
* The openfootball snapshots carry no per-result availability timestamps; historic corrections made upstream after a match are invisible.
* The alias tables used for canonical ids are a 2025 snapshot applied retrospectively (names only, no outcome information).
* Training/inference parity of a *future* live pipeline is only specified (single contract), not yet tested against live data.
