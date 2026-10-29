# 06 Feature-engineering audit (generated 2026-10-20 22:32)

## Method
The club features of `08_*_extended.csv` were re-implemented from scratch (`_scripts/v4_features.py`, different algorithm: per-entity arrays + `searchsorted` on calendar dates, independent Elo replay) and compared with the stored values for **all 129,829 rows**, not a sample.

## Exact differences
| feature | rows | max_abs_diff | rows_diff_gt_1e6 | nan_pattern_mismatch |
|---|---|---|---|---|
| home_n_prior | 129829 | 0.0 | 0 | 0 |
| away_n_prior | 129829 | 0.0 | 0 | 0 |
| home_ppg5 | 129829 | 0.0 | 0 | 0 |
| away_ppg5 | 129829 | 0.0 | 0 | 0 |
| home_ppg10 | 129829 | 4.440892098500626e-16 | 0 | 0 |
| away_ppg10 | 129829 | 4.440892098500626e-16 | 0 | 0 |
| home_gf5 | 129829 | 0.0 | 0 | 0 |
| home_ga5 | 129829 | 0.0 | 0 | 0 |
| away_gf5 | 129829 | 0.0 | 0 | 0 |
| away_ga5 | 129829 | 0.0 | 0 | 0 |
| home_gf10 | 129829 | 4.440892098500626e-16 | 0 | 0 |
| home_ga10 | 129829 | 8.881784197001252e-16 | 0 | 0 |
| away_gf10 | 129829 | 8.881784197001252e-16 | 0 | 0 |
| away_ga10 | 129829 | 8.881784197001252e-16 | 0 | 0 |
| home_days_rest | 129829 | 0.0 | 0 | 0 |
| away_days_rest | 129829 | 0.0 | 0 | 0 |
| home_venue_ppg5 | 129829 | 4.440892098500626e-16 | 0 | 0 |
| away_venue_ppg5 | 129829 | 4.440892098500626e-16 | 0 | 0 |
| home_elo | 129829 | 4.547473508864641e-13 | 0 | 0 |
| away_elo | 129829 | 4.547473508864641e-13 | 0 | 0 |
Maximum absolute difference over all features: **4.55e-13** (floating point); rows with any difference > 1e-6: **0**. Elo, n_prior, points/goal windows, venue form and rest days are reproduced exactly, including NaN patterns.

## Definitions as verified
* Rated result = completed, dated match with a `confirmed` or `inferred_no_marker` 90-minute label (226,566 of 227,374 universe results). Results with `unknown` labels never update state.
* A team's history uses **strictly earlier calendar dates** (`date < match date`); same-day matches never see each other.
* `*_n_prior` is uncapped; windows are the last 5 / 10 rated matches of the team in **any** competition; `venue_ppg5` uses the last 5 home (or away) matches; `days_rest` = days since the last rated match (NaN if none).
* Elo: start 1500, K=20, home advantage 60 inside the expectation only, goal-difference multiplier 1 / 1.5 / (11+gd)/8, global across competitions.
* Competition features: `is_league`, `is_league_phase`, `is_knockout`, `comp_type_continental`, `comp_type_cup`.

## Defects found
1. **`same_country` is wrong** for unresolved clubs: it parses the country from `CLUB:XXX:` ids and yields NaN for ids such as `ENG|Name`, so the comparison is False. In the extended set it is 0 for 37.6% of rows, including **45,005 of 122,507 domestic-league rows** (an independent computation gives 4,815 legitimate zeros). The feature must be fixed or dropped before training.
2. **`neutral_known` is constant 0** (['neutral_known']) - no information; neutral venues (cup/continental finals) are unmarked, so home advantage is applied to neutral finals.
3. **Duplicate fixtures** inflate state: Russian Premier League 2019-20 appears twice (`ru1` and a mislabelled `ru2` file): 460 extended rows, 240 matches (`_evidence/duplicate_fixtures_all_results_same_date_pair_score.csv`). Elo and form of those clubs are double-updated.
4. **Elo is not globally comparable**: 64 disconnected components; 38,234 extended rows (29.4%) sit in isolated components (Brazil, MLS, Liga MX, Nigeria, Argentina, Japan, China...). Elo differences are meaningful inside a component only.
5. **Inferred labels feed the state** of the strict set (ratings are updated with `inferred_no_marker` results). Not leakage, but strict-set features depend on inferred results.
6. Missing history: venue form NaN for {'home_venue_ppg5': 0.0, 'away_venue_ppg5': 0.01}; all other features complete because rows need >=5 prior rated matches.
7. **Same-day ordering:** 506 entity-days in the extended set have two or more matches (kick-off times are missing for ~40% of rows). The conservative date-batch rule makes the order irrelevant, so no ambiguity enters the features; the second match of a double day simply does not know the first.
8. **Undated lower-tier results** (`04e`, 1,162 rows) are not in the training or universe files (no null dates in 08/04d; the build script never reads `league_matrix_undated.csv`).
9. Cross-competition history **is** shared (a club's league and cup results update one state) - verified by the brute-force recomputation across all competitions.

## Proposed single feature contract for future club training and inference
Order, name, definition and null rule (the same function must produce training and live rows from the same match table; no `latest.csv` snapshots):

| position | feature |
|---|---|
| 1 | home_elo |
| 2 | away_elo |
| 3 | elo_diff |
| 4 | home_n_prior |
| 5 | away_n_prior |
| 6 | home_ppg5 |
| 7 | away_ppg5 |
| 8 | home_ppg10 |
| 9 | away_ppg10 |
| 10 | home_gf5 |
| 11 | home_ga5 |
| 12 | away_gf5 |
| 13 | away_ga5 |
| 14 | home_gf10 |
| 15 | home_ga10 |
| 16 | away_gf10 |
| 17 | away_ga10 |
| 18 | home_venue_ppg5 |
| 19 | away_venue_ppg5 |
| 20 | ppg5_diff |
| 21 | gd5_diff |
| 22 | home_days_rest |
| 23 | away_days_rest |
| 24 | rest_diff |
| 25 | is_league |
| 26 | is_league_phase |
| 27 | is_knockout |
| 28 | comp_type_continental |
| 29 | comp_type_cup |
| 30 | same_country |
| 31 | neutral_known |

* Cut-off: all inputs have `date < fixture date` (calendar day); a live fixture uses results completed by the previous day.
* Units: goals and points per match; `days_rest` in days; Elo points.
* Null handling: NaN for unknown history (never 0 / 1.0 / 999); tree models can use NaN, linear models need an explicit imputation fitted on the training split only; always include `*_n_prior`.
* Competition encoding: fixed vocabulary stored with the model, fitted on the training split.
* Neutral venue: required boolean from the fixture feed (not guessed). Rating constants K, HA and the start value are part of the contract.
* Fix before use: drop or correct `same_country`; remove `neutral_known` until neutral venues are sourced.
