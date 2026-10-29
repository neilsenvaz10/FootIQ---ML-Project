# 11 ML training approval decisions (generated 2026-10-20 22:32)

Statuses are data-readiness decisions only; they say nothing about predictive accuracy. No model was trained.

| Module | Status |
|---|---|
| International 90-minute 1X2 model | **BLOCKED** |
| Club league-only 90-minute 1X2 model | **APPROVED WITH RESTRICTIONS** |
| Club all-competition 90-minute 1X2 model | **BLOCKED** |
| Player descriptive analytics | **APPROVED WITH RESTRICTIONS** |
| Player recent-form analytics | **APPROVED WITH RESTRICTIONS** |
| Player clustering and similarity | **APPROVED WITH RESTRICTIONS** |
| Player-performance prediction | **BLOCKED** |
| Tournament simulation | **NOT VERIFIED** |

## 1. International 90-minute 1X2 - BLOCKED
Why: `01`/`03` hold extra-time-inclusive scores only (688 shoot-outs, no stage, no regulation column); a verified 90-minute label cannot be produced for tournament knockouts. Not approved even for the preserved model's data. Re-open when a regulation-time field (or stage + goal minutes) from a permitted source exists. (All World Cup edition match counts 1930-2026 and 11 continental editions match their formats: 0 count mismatches - the data is complete, but not label-correct.)

## 2. Club league-only 90-minute 1X2 - APPROVED WITH RESTRICTIONS
* **Exact dataset:** `FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv` **filtered to `competition_type == 'domestic_league'`** (121,725 rows; 100% CC0 openfootball, no Wikipedia rows, every label `confirmed` because league matches have no extra time).
* **Period:** 2018-08-01 to 2025-06-29 for fitting / validation / test (train < 2023-07-01, validation 2023-24, test 2024-25). The 2025-26 and early 2026-27 rows are a forward holdout for a single final evaluation.
* **Mandatory corrections before the first fit:** (a) drop `same_country` and `neutral_known` (I-01, I-17); (b) remove the duplicated Russian 2019-20 `ru2` fixtures (I-02); (c) fix or exclude rows whose season label contradicts the date (I-09); (d) restrict the forward holdout to league-seasons with verified complete schedules (all five top leagues, Championship, Austrian Bundesliga) and exclude the 14 lower leagues that stop in 2025-26 (I-12).
* **Restrictions:** Elo values are comparable only inside a connected league component (I-07): model per league group or add a league-strength feature; preprocessing (scaling, imputation, encodings) must be fitted on the training split only; the holdout must not be used for tuning; report calibration (Brier / log loss) and compare to a bookmaker-free baseline (always-home / Elo-only); the strict state uses inferred labels for ratings (I-18).
* **Not covered:** cups, continental competitions, play-offs, extra-time matches.

## 3. Club all-competition 90-minute 1X2 - BLOCKED
Blocking items: cup / continental strict rows are only 4,128 (3.3%) and selected by the target (draw-rate bias, I-05); extended labels are inferred (I-06); 35% of match sides have unresolved identity (I-08); neutral venues unknown (I-17); CC BY-SA rows need legal clearance (I-10). Re-open after verified 90-minute scores and identity review.

## 4. Player descriptive analytics - APPROVED WITH RESTRICTIONS
Permitted data: `05` StatsBomb event-level rows (113,623; 3,961 matches; goals reconcile with scores for 100% of matches) and openfootball appearance rows (minutes ESTIMATED). Keep sources, men and women separate; never merge players by name; label minutes as derived / estimated; credit StatsBomb; research / education use only until the licence PDF is read (I-11).

## 5. Player recent-form analytics - APPROVED WITH RESTRICTIONS
Permitted data: `FootIQ_ML_Data_Verification/player_form_v1/PLAYER_RECENT_FORM_STATSBOMB_v1.0.csv` and `..._OPENFOOTBALL_APPEARANCES_v1.0.csv` for descriptive use. Windows are the last N *observed* matches; filter on `w*_span_days` and gaps before showing them as "form" (I-14).

## 6. Player clustering and similarity - APPROVED WITH RESTRICTIONS
Permitted data: StatsBomb male player-seasons with >= 900 derived minutes, position-specific cohorts (GK 134, DEF 670, MID 543, FWD 421); standardise within competition-season; K-Means and hierarchical suitable, DBSCAN weak; no zero-filling; research use only. Women's data separately (1,204 player-seasons >= 900 min).

## 7. Player-performance prediction - BLOCKED
See file 16: discontinuous coverage, no lineups / injuries, no verified rating target, sparse count targets. An exploratory, clearly labelled baseline may be proposed later but is not approved.

## 8. Tournament simulation - NOT VERIFIED
The v2.3 / v2.13 simulation (preserved) uses team-power inputs and locked results, not the club data audited here. Its inputs (squad values, player-impact heuristic scores flagged R10, tie-break rules R14) were not re-verified in this task. Only the international match results (edition counts) were verified, and those are complete.

## Actions required before approval of the blocked modules
1. Fix / drop `same_country` and `neutral_known`; remove duplicate Russian fixtures; correct season labels; publish dataset v1.1 with new hashes.
2. Provide regulation-time scores for international knockouts (stage + goal minutes) before any international 90-minute model.
3. Resolve identity candidate lists manually and extend alias coverage outside Europe.
4. Legal review of CC BY-SA scope and StatsBomb licence; add NOTICE file.
5. Decide the evaluation protocol (frozen features, holdout used once) and write it down before training.
6. For player prediction: acquire continuous match-level player data with lineups and a verified target definition.
