# Training-label validation report (v1.0, generated 2026-10-20 21:34)

Target: **90-minute 1X2** (home win / draw / away win after regulation time). A label is used only when the 90-minute score is verifiable.

## Rules
* `confirmed` - league or league/group-phase match (extra time does not exist in the format), or the source states the regulation score next to an extra-time/penalty marker, or the regulation score is derived from goal minutes that add up to the final score (Wikipedia).
* `inferred_no_marker` - knockout match with no extra-time/penalty marker: decided in 90 minutes only by the absence of a marker. **Excluded from the strict training set.**
* `unknown` - extra time or penalties without a stated regulation score, awarded results, or anything ambiguous. **Never used.** Full-time scores are never reused as 90-minute scores when extra-time semantics are ambiguous.
* `not_completed` - cancelled/postponed/unscored.

## Counts (all club results 2018-19 to 2026-27, before 2026-10-01)
| competition_type | confirmed | inferred_no_marker | not_completed | unknown |
|---|---|---|---|---|
| continental_club | 4334 | 5312 | 0 | 138 |
| domestic_cup | 3077 | 3480 | 0 | 329 |
| domestic_league | 208127 | 1346 | 3 | 226 |
| global_club | 82 | 132 | 0 | 10 |
| league_cup | 259 | 417 | 0 | 102 |

Total results: 227,374. Confirmed: 215,879; inferred: 10,687; unknown: 805.

## Cross-source agreement (Wikipedia vs openfootball on overlapping matches)
* Matched matches with comparable final scores: 1,328; scores agree: 1,328; conflicts: 0.
* Penalty-shootout agreement: 1.000. 90-minute scores known in both sources: 1276, agreeing: 1.000.
* Wikipedia rows that matched no openfootball row in validation seasons were NOT added; they mostly involve clubs whose identity could not be verified.

## Other checks
* Duplicates removed on (competition, season, date, team pair, stage): see `_build/work/duplicates_found.csv`.
* Dates: all training rows are dated; undated matrix results are excluded.
* Penalty winners are recorded separately and never used as 90-minute outcomes.
