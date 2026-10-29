# 07 Temporal leakage audit - adversarial (generated 2026-10-20 22:32)

The previous six tests were **not** re-run as the evidence; the checks below use independent code (`v4_features.py`) and independent data reads.

| Leakage route | Verdict | Evidence |
|---|---|---|
| Future match results in features | PASS | Independent recomputation using only earlier dates reproduces all 129,829 rows (max diff 4.5e-13); prefix-invariance test in the pipeline passes. |
| Final-season standings / season totals | PASS | No season-aggregate or table-position feature exists in the declared feature list. |
| Current team ratings applied retrospectively | PASS | Elo is replayed chronologically; no 'latest' rating table is read by the club pipeline. |
| Post-match statistics (half-time, shots, cards) | PASS | Half-time, final, 90-minute goals and penalties are excluded from the 31 declared features. |
| Future player transfers | PASS (not applicable) | Player data is not used in club features. |
| Team identity resolution | UNVERIFIED | Alias tables are a 2025-01-03 snapshot (`openfootball/clubs`) applied to all seasons; whether an alias existed at the time of a match is not recorded. No outcome information is involved, but the mapping is retrospective. |
| Feature normalisation | PASS (not applicable) | The dataset ships raw values; no scaling was applied. Future scaling must be fitted on the training split only. |
| Target encoding | PASS (not applicable) | No target-derived columns. |
| Imputation | PASS | Missing values are NaN; no imputation was applied. (SB player stats: see player audit for 0-fills.) |
| Duplicate fixtures across splits | FAIL | 460 rows share (date, team pair): Russian 2019-20 duplicated by a mislabelled file; both copies are in the training split here, but any duplicate straddling a split boundary would leak. |
| Same-day ordering | PASS with caveat | Date-batched updates; 506 entity-days with 2+ matches; kick-off times unknown for ~40% of rows, so intra-day ordering cannot be proven and is not used. |
| Calibration / hyperparameter selection | NOT VERIFIED | No model has been trained; the split labels exist but no procedure restricting selection to train/validation can be audited yet. |
| Historical data corrections | UNVERIFIED | Wikipedia pages were retrieved on 2026-10-20 and can contain later edits; openfootball is a snapshot. Availability timestamps per result do not exist. |
| Full-dataset preprocessing | PASS | Elo constants were fixed a priori; eligibility uses only prior-match counts; the splits are chronological; the forward holdout is a label, not yet used for fitting. |
| Forward holdout excluded from fitting/selection | NOT VERIFIED | Holdout = 2025-07-01 onward (10,211 strict rows). Nothing has been fitted; the guarantee depends on how training is run. |
| Selection on the outcome | FAIL | Strict knockout rows are dominated by matches level after 90 minutes (draw rate 30.7% vs 19.6% for all knockout results); plain-score knockouts are excluded as inferred. This is selection on the target; irrelevant for league-only, biasing for cups. |
| Label provenance across time | UNVERIFIED | Wikipedia-derived labels (goal minutes) were obtained after the fact; fine for training labels, but their availability time is not recorded. |

## Chronological boundaries (strict set)
Train < 2023-07-01 (64,220); validation 2023-07-01..2024-06-30 (23,799); test 2024-07-01..2025-06-29 (27,628); forward holdout 2025-07-01..2026-09-20 (10,211). Boundaries are strictly ordered and non-overlapping. The holdout contains 2025-26 and early 2026-27 matches, including 830 Wikipedia-derived rows with a different data-generating process, and partial seasons for 14 lower leagues (early-season matches only).

## Where exact availability timestamps are missing
Per-match result timestamps (when a result became known), kick-off times (~40% missing) and the retrieval time of each openfootball line are not available; every check that would need them is marked UNVERIFIED rather than PASS.
