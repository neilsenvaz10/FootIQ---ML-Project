# 02 Club identity defect investigation

Scripts: `_scripts/e1_integrity_and_identity.py`. Tables: `02a`–`02d`, `02_identity_audit_summary.json`, `eligibility_exclusions_r1.json`. Nothing in the frozen v2 model, its training data, or dataset v1.1 was changed.

## 1. Police FC and Vision FC (cross-country club-ID collisions) — CONFIRMED
* **Cause (source-backed):** the dataset build assigns team ids as `<region>|<name>` for the `world/` repository (`world/africa|Police FC`); the openfootball files themselves sit in country folders. Different clubs with the same name therefore receive one id. Scanning all 02_Historical_Club_Matches rows with `world/` ids against their source-file country folder finds exactly two such ids across the whole source (all other multi-competition `world/` ids stay inside one country, e.g. Mexico/Israel promotions):

| Id | Country folder / competition | Source rows |
|---|---|---|
| world/africa\|Police FC | rwanda / rw1 | 154 |
| world/africa\|Police FC | uganda / ug1 | 60 |
| world/africa\|Vision FC | ghana / gh1 | 34 |
| world/africa\|Vision FC | rwanda / rw1 | 30 |

* **Affects the frozen v2 / matched-v1 training data?** Yes, in a small way: **257 training rows (0.22%)** involve the two merged ids (train 53, validation 30, test 114, forward holdout 60). Two real clubs share one Elo/form history from the first overlap onwards; in 2024-09 they appear on the same date in different leagues, which is how it showed in the same-day Elo check.
* **Affects future predictions?** Only fixtures involving these two clubs. The current upcoming-fixtures file (3,167 fixtures compared) contains none of them, and the sensitivity run (frozen v2 features recomputed with the proposed corrections, `02b_...csv`) changes every other fixture's probabilities by at most 2.1e-5. The affected clubs will matter when the Rwanda/Uganda/Ghana 2026-27 fixtures are published.
* **Decision:** `eligibility_exclusions_r1.json` lists the four (entity, competition) pairs. The logger flags any fixture with such a club `identity_collision_unresolved` (logged for transparency, excluded from the primary population) until the proposal below is approved and implemented.
* **Correction proposal (not applied):** namespace world ids by country folder — `world/africa/rwanda|Police FC`, `world/africa/uganda|Police FC`, `world/africa/ghana|Vision FC`, `world/africa/rwanda|Vision FC` (table `02c_identity_correction_proposal.csv`) — in a new dataset version (v1.2). Because it changes training rows, it requires a new model version (v2-r2 and a matched v1 refit) and cannot be applied to the frozen candidates.

## 2. Zimbabwe 2021-22 duplicate-date records — CONFIRMED SOURCE ANOMALY
* **Source evidence** (openfootball `world@42df8203`, `africa/zimbabwe/2021-22_zw1.txt`, header: `Date Fri Jul 2 2021 - Sun Jun 26 2022 (359d)`, 306 matches, cited upstream RSSSF `zimb2021.html`): Matchdays 1-18 carry dates 2021-11-05 .. 2022-06-26, Matchdays 19-34 carry dates 2021-07-02 .. 2021-11-13, each date line has weekday and year (`Fri Nov 5 2021`). The matchday numbering is not chronological, and both blocks cover 5-13 Nov 2021: **five clubs are listed twice on the same date** (Harare City 5 Nov, FC Platinum, Highlanders, Ngezi Platinum Stars and ZPC Kariba 6 Nov). Parser and date-repair are not the cause (the dates are explicit in the file). Which block is mis-dated cannot be decided from the files; the RSSSF page gives round order but no dates.
* **Affects training?** Yes: **259 training rows** (all in the original train split, season 2021-22; 47 of the 306 source rows are not in dataset v1.1 for reasons of its eligibility pipeline, not re-derived here). The effect is a small amount of out-of-order history for 18 clubs, and the lost-update Elo defect reported earlier was triggered here.
* **Affects future predictions?** Only through those 18 Zimbabwean clubs' old rating history; zw1 plays a calendar-year season (no zw1 fixtures in the current upcoming file). The sensitivity run with the whole zw1 2021-22 season removed from the state changes predictions of all other upcoming fixtures by at most 2.1e-5, and no zw1 fixture is currently scheduled.
* **Decision:** zw1 fixtures are logged with the flag `zw1_history_date_anomaly_flag` and reported as a separate stratum; they are not excluded unless the anomaly is shown to matter.
* **Correction proposal (not applied):** quarantine the zw1 2021-22 season (list in `02d_zw1_2021_22_quarantine_candidates.csv`, 259 training rows) until a second approved source confirms the dates; if confirmed, correct the dates, otherwise keep it excluded (dataset v1.2).

## Summary
| Defect | In frozen training data | Affects prospective inference | Handling |
|---|---|---|---|
| Police FC / Vision FC id collision | 257 rows (0.22%) | Only fixtures of those clubs | Fixtures ineligible until fixed |
| zw1 2021-22 duplicate dates | 259 rows (0.22%) | Negligible (old history, no current fixtures) | Flagged stratum |
