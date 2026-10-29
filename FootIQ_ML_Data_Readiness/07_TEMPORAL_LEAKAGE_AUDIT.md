# Temporal leakage audit (v1.0, generated 2026-10-20 21:34)

## Design
* One pass over all results in date order. For each calendar date the features of **all** that day's matches are computed from state built from strictly earlier dates, and only then is the state updated (kick-off times are missing in many sources, so same-day information is never used).
* Ratings/form use 90-minute results only; matches with unknown 90-minute outcome never update state.
* Features: Elo (K=20, home advantage 60 inside the expectation only), uncapped prior-match counts, last-5/10 points and goals for/against, venue-specific form, rest days. Missing history is NaN, never 0.
* Excluded columns: half-time scores, final/penalty scores, 90-minute goals, the label.
* Splits: train < 2023-07-01, validation 2023-24, test 2024-25, forward holdout 2025-26 and 2026-27.

## Automated tests
| Test | Result | Detail |
|---|---|---|
| T1 latest information date < kickoff date for every eligible row | PASS | 129829 rows checked |
| T2 prefix invariance: features for matches before 2023-07-01 are identical when all later data is removed | PASS | 157700 rows, columns ['home_elo', 'away_elo', 'home_n_prior', 'away_n_prior', 'home_ppg5', 'away_ppg5', 'home_gf10', 'away_ga10', 'home_days_rest'] |
| T3 brute-force recomputation (strictly earlier matches only) of n_prior and ppg5 | PASS | 400 random rows x 2 teams, mismatches=0 |
| T4 no outcome-derived column is in the declared feature list | PASS | 31 declared features |
| T5 same-day matches do not inform each other (state updated after the whole date is processed) | PASS | by construction + T3 (strict < date); teams with >1 match on one date: 237 |
| T6 splits are chronological (max train date < min validation date < min test date < min holdout date) | PASS | [{"suggested_split": "forward_holdout", "min": "2025-07-01", "max": "2026-09-20", "size": 10592}, {"suggested_split": "test", "min": "2024-07-01", "max": "2025-06-29", "size": 28376}, {"suggested_spli |

## Known residual risks
* Wikipedia pages were retrieved after the matches; their *content* is historical fact, but any re-edit after a match is invisible. Revision ids/timestamps are stored in provenance.
* The sources give dates, not kick-off timestamps: a 'known before kick-off' proof is only possible at day granularity (handled conservatively).
* Elo is global across leagues and linked only through continental matches and verified club identities; league strengths are therefore weakly connected.
* Cup finals and other neutral venues are not marked (`neutral_known=0`).
