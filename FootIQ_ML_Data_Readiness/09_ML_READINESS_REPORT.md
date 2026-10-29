# ML readiness report - club 90-minute 1X2 (v1.0, generated 2026-10-20 21:34)

## Verdict
* **Sufficient for a first, honest league-based 90-minute 1X2 model** (strict dataset: 125,858 matches; by split {'forward_holdout': 10211, 'test': 27628, 'train': 64220, 'validation': 23799}).
* **Not sufficient to claim a reliable model for domestic cups or for all supported competitions.** Cup/knockout matches mostly have only inferred 90-minute labels; many lower-tier 2025-26 league seasons are incomplete or partly undated; 2026-27 is only a short forward holdout (through 2026-09-20 in the sources).
* Extended dataset (adds `inferred_no_marker` knockout labels): 129,829 matches; by split {'forward_holdout': 10592, 'test': 28376, 'train': 66485, 'validation': 24376}.

## Competition-season suitability (see `01_COMPETITION_SEASON_COVERAGE_MATRIX.csv`)
| ml_suitability | competition_seasons |
|---|---|
| suitable_for_training | 269 |
| descriptive_only | 235 |
| needs_correction | 50 |
| suitable_with_caveats | 35 |
| forward_holdout_only | 25 |

Big-five league seasons:
| competition_name | season | expected_matches | verified_completed_dated | coverage_pct | latest_verified_result_date | ml_suitability |
|---|---|---|---|---|---|---|
| German Bundesliga | 2018-19 | 306.0 | 306 | 100.0 | 2019-05-18 | suitable_for_training |
| German Bundesliga | 2019-20 | 306.0 | 306 | 100.0 | 2020-06-27 | suitable_for_training |
| German Bundesliga | 2020-21 | 306.0 | 306 | 100.0 | 2021-05-22 | suitable_for_training |
| German Bundesliga | 2021-22 | 306.0 | 306 | 100.0 | 2022-05-14 | suitable_for_training |
| German Bundesliga | 2022-23 | 306.0 | 306 | 100.0 | 2023-05-27 | suitable_for_training |
| German Bundesliga | 2023-24 | 306.0 | 306 | 100.0 | 2024-05-18 | suitable_for_training |
| German Bundesliga | 2024-25 | 306.0 | 306 | 100.0 | 2025-05-17 | suitable_for_training |
| German Bundesliga | 2025-26 | 306.0 | 306 | 100.0 | 2026-05-16 | suitable_for_training |
| German Bundesliga | 2026-27 | 306.0 | 36 | 11.8 | 2026-09-20 | forward_holdout_only |
| English Premier League | 2018-19 | 380.0 | 380 | 100.0 | 2019-05-12 | suitable_for_training |
| English Premier League | 2019-20 | 380.0 | 380 | 100.0 | 2020-07-26 | suitable_for_training |
| English Premier League | 2020-21 | 380.0 | 380 | 100.0 | 2021-05-23 | suitable_for_training |
| English Premier League | 2021-22 | 380.0 | 380 | 100.0 | 2022-05-22 | suitable_for_training |
| English Premier League | 2022-23 | 380.0 | 380 | 100.0 | 2023-05-28 | suitable_for_training |
| English Premier League | 2023-24 | 380.0 | 380 | 100.0 | 2024-05-19 | suitable_for_training |
| English Premier League | 2024-25 | 380.0 | 380 | 100.0 | 2025-05-25 | suitable_for_training |
| English Premier League | 2025-26 | 380.0 | 380 | 100.0 | 2026-05-24 | suitable_for_training |
| English Premier League | 2026-27 | 380.0 | 50 | 13.2 | 2026-09-20 | forward_holdout_only |
| Spanish La Liga | 2018-19 | 380.0 | 380 | 100.0 | 2019-05-19 | suitable_for_training |
| Spanish La Liga | 2019-20 | 380.0 | 380 | 100.0 | 2020-07-19 | suitable_for_training |
| Spanish La Liga | 2020-21 | 380.0 | 380 | 100.0 | 2021-05-23 | suitable_for_training |
| Spanish La Liga | 2021-22 | 380.0 | 380 | 100.0 | 2022-05-22 | suitable_for_training |
| Spanish La Liga | 2022-23 | 380.0 | 380 | 100.0 | 2023-06-04 | suitable_for_training |
| Spanish La Liga | 2023-24 | 380.0 | 380 | 100.0 | 2024-05-26 | suitable_for_training |
| Spanish La Liga | 2024-25 | 380.0 | 380 | 100.0 | 2025-05-25 | suitable_for_training |
| Spanish La Liga | 2025-26 | 380.0 | 380 | 100.0 | 2026-05-24 | suitable_for_training |
| Spanish La Liga | 2026-27 | 380.0 | 69 | 18.2 | 2026-09-20 | forward_holdout_only |
| French Ligue 1 | 2018-19 | 380.0 | 380 | 100.0 | 2019-05-24 | suitable_for_training |
| French Ligue 1 | 2019-20 | 380.0 | 279 | 73.4 | 2020-03-08 | needs_correction |
| French Ligue 1 | 2020-21 | 380.0 | 380 | 100.0 | 2021-05-23 | suitable_for_training |
| French Ligue 1 | 2021-22 | 380.0 | 380 | 100.0 | 2022-05-21 | suitable_for_training |
| French Ligue 1 | 2022-23 | 380.0 | 380 | 100.0 | 2023-06-03 | suitable_for_training |
| French Ligue 1 | 2023-24 | 306.0 | 306 | 100.0 | 2024-05-19 | suitable_for_training |
| French Ligue 1 | 2024-25 | 306.0 | 306 | 100.0 | 2025-05-17 | suitable_for_training |
| France | Ligue 1 | 2025-26 | 306.0 | 306 | 100.0 | 2026-05-17 | suitable_for_training |
| French Ligue 1 | 2026-27 | 306.0 | 45 | 14.7 | 2026-09-20 | forward_holdout_only |
| Italian Serie A | 2018-19 | 380.0 | 380 | 100.0 | 2019-05-26 | suitable_for_training |
| Italian Serie A | 2019-20 | 380.0 | 380 | 100.0 | 2020-08-02 | suitable_for_training |
| Italian Serie A | 2020-21 | 380.0 | 380 | 100.0 | 2021-05-23 | suitable_for_training |
| Italian Serie A | 2021-22 | 380.0 | 380 | 100.0 | 2022-05-22 | suitable_for_training |
| Italian Serie A | 2022-23 | 380.0 | 380 | 100.0 | 2023-06-04 | suitable_for_training |
| Italian Serie A | 2023-24 | 380.0 | 380 | 100.0 | 2024-06-02 | suitable_for_training |
| Italian Serie A | 2024-25 | 380.0 | 380 | 100.0 | 2025-05-25 | suitable_for_training |
| Italian Serie A | 2025-26 | 380.0 | 380 | 100.0 | 2026-05-24 | suitable_for_training |
| Italian Serie A | 2026-27 | 380.0 | 50 | 13.2 | 2026-09-20 | forward_holdout_only |

## Blockers and remaining limitations
1. **Dated results for lower-tier 2025-26 leagues are not available from any permitted source.** Wikipedia result matrices supply verified scores but no dates; they are exported as undated records (04e) and excluded from chronological training. Pairs still without a result are in `02_MISSING_MATCH_INVENTORY.csv`.
2. **2026-27 league results after 2026-09-20 do not exist in the sources**; Wikipedia matrices cannot be bounded by date, so none were used for 2026-27.
3. **90-minute labels for knockouts:** extra-time/penalty matches without a stated regulation score are `unknown` and excluded; plain-score knockouts are `inferred` only.
4. **Identity:** clubs without an exact alias entry stay separate entities (flagged in `05_CANONICAL_TEAM_IDENTITY_MAPPING.csv`); cup and continental matches require both clubs resolved, so many lower-division cup ties are excluded from training.
5. **Information content:** no lineups, injuries, odds, xG or kick-off timestamps; the model would rest on Elo/form/rest only.
6. **Cross-league strength** is weakly connected (global Elo links leagues only through continental matches).
7. **Wikipedia rows** are community-edited and CC BY-SA; validation against openfootball showed 1,328 agreeing and 0 conflicting final scores on overlapping matches.
8. Competitions never covered by any permitted source (UEFA Super Cup, domestic super cups, Intercontinental Cup) remain absent.

## Recommendations
* Start with a league-only model (strict set), evaluate on `test` (2024-25) and report the 2025-26 holdout once; do not tune on the holdout.
* Treat cups/continental as a second stage after adding verified 90-minute scores (e.g. match reports) or accepting inferred labels explicitly.
* Obtain a licensed dated results feed for lower leagues if they are needed.
* Do not train until you approve (no model was trained).
