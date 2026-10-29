"""Stage 7b: summary, reproducibility report, approval decisions and the issue register."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
ENC = "utf-8-sig"
NOW = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
J = lambda n: json.load(open(os.path.join(EV, n), encoding="utf-8"))
L, V3, V4, V5, V6 = J("v2_part1.json"), J("v3_results.json"), J("v4_results.json"), J("v5_results.json"), J("v6_results.json")
LB, I = L["labels"], V3["identity"]
v2b = J("v2b_summary.json")
cs = pd.read_csv(os.path.join(OUT, "03_COMPETITION_SEASON_VERIFICATION.csv"), encoding=ENC)
club = cs[cs.scope == "club"]
integ = pd.read_csv(os.path.join(EV, "dataset_integrity_metrics.csv"))
base = J("baseline_integrity.json")
sel = pd.read_csv(os.path.join(EV, "label_selection_bias.csv"))
rep = pd.read_csv(os.path.join(EV, "repro_file_hash_comparison.csv"))
repp = J("repro_pickle_comparison.json")
repr_row = pd.read_csv(os.path.join(EV, "repro_row_level_comparison.csv"))
fin = club[(~club.season.isin(["2026-27", "2026"])) & club.expected_matches.notna()]
um = fin[fin.unexplained_missing > 0]


def T(df, cols=None, n=None):
    if cols:
        df = df[cols]
    if n:
        df = df.head(n)
    c = list(df.columns)
    out = ["| " + " | ".join(map(str, c)) + " |", "|" + "|".join("---" for _ in c) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) or v is None else str(v) for v in r) + " |")
    return "\n".join(out)


def W(n, t):
    open(os.path.join(OUT, n), "w", encoding="utf-8").write(t)


# ======================================================================= issues
ISS = [
    ("I-01", "High", "08 strict/extended (feature same_country)", f"{V4['domestic_league_rows_same_country_stored_false']:,} of {V4['domestic_league_rows_in_extended']:,} domestic-league rows have same_country=0 although an independent computation gives {V4['domestic_league_rows_same_country_expected_false']:,} legitimate zeros; cause: country parsed from 'CLUB:XXX:' ids only", "A corrupted feature (37.6% of rows) would be learned as a spurious signal and would not be reproducible at inference", "Drop the column or recompute it from a country field; regenerate the dataset as v1.1"),
    ("I-02", "High", "02 / 04a / 08", "Russian Premier League 2019-20 duplicated: europe/russia/2019-20_ru2.txt (titled '1. Division') contains the same 240 fixtures as ru1; 460 rows in the extended set (_evidence/duplicate_fixtures_all_results_same_date_pair_score.csv)", "Elo and form of Russian clubs double-updated; duplicate fixtures in the training split", "Exclude the mislabelled ru2 2019-20 file; add a cross-competition (date, team pair, score) duplicate check to the build"),
    ("I-03", "High", "International 01/03", f"Scores include extra time and no regulation-time column exists; {L['international']['shootout_matches']} shoot-out matches; knockout stage not recorded", "A 90-minute 1X2 label cannot be verified for tournament knockouts; labels would mix extra-time results", "Add stage / regulation score from a permitted source or restrict to matches that cannot have extra time; until then do not train a 90-minute model"),
    ("I-04", "High", "Player prediction", "Player match data is a patchwork of selected competition-seasons (66 competition-seasons with >=5 prior rows, 2015-16 and 2023-24 dominate), no lineups / injuries / context", "A performance regression would measure data availability, not skill; chronological split impossible within a competition", "Do not train player-performance prediction on this data; seek continuous data first"),
    ("I-05", "Medium", "08 strict (cups / continental)", f"Strict knockout draw rate {sel[(sel.phase=='knockout')&(sel.set=='strict')].draw_rate.iloc[0]:.1%} vs {sel[(sel.phase=='knockout')&(sel.set=='all_results')].draw_rate.iloc[0]:.1%} for all knockout results; strict knockouts are {LB['strict_knockout_rows']:,} rows (1.8%)", "Selection on the target: cup / continental models trained on the strict set are biased towards draws", "Use league-only for the first model; for cups obtain verified 90-minute scores for plain-score knockouts"),
    ("I-06", "Medium", "08 extended", f"{LB['extended_minus_strict']:,} extra rows depend on an inference ('no a.e.t./pen. marker => decided in 90 minutes'); verified against raw lines ({LB['inferred_rows_whose_raw_line_contains_aet_or_pen_marker']} violations) but still an inference", "Some labels may be wrong if a source omitted a marker", "Keep extended out of the primary model; use it only for sensitivity analysis"),
    ("I-07", "Medium", "Feature Elo", f"{V4['elo_connected_components']} disconnected rating components; {V4['extended_rows_outside_largest_component']:,} extended rows ({100-V4['extended_rows_in_largest_component_pct']:.1f}%) in isolated components (Brazil, MLS, Liga MX, Nigeria, Argentina, Japan, China...)", "Elo values are not comparable across components; a pooled model would misread them", "Model per component / league, or add league-strength features and exclude isolated leagues from the pooled model"),
    ("I-08", "Medium", "05 identity mapping", f"{I['entities_unresolved']:,} of {I['entities_in_04d']:,} entities and {100*I['match_sides_with_unresolved_entity']/I['match_sides_total']:.1f}% of match sides are unresolved; {I['same_normalised_name_multiple_entity_ids_groups']} same-name groups with several ids; {I['possible_split_candidates_unresolved_vs_resolved']} possible split-club candidates", "Continental / cup histories of split clubs are incomplete; cup and continental training rows are dropped", "Review the candidate lists manually; extend alias coverage outside Europe (no automatic merging)"),
    ("I-09", "Medium", "Season labels", f"{v2b['openfootball_rows_season_date_inconsistent']} openfootball rows have a season label inconsistent with their dates (e.g. Nigerian second tier file labelled 2017-18 with dates in 2018-09; 157 strict rows) (_evidence/season_label_date_inconsistent_openfootball.csv)", "Season-based splits / season features would misplace these rows", "Derive the season from the date window or correct labels; re-check file titles"),
    ("I-10", "Medium", "08 / 04 (Wikipedia rows)", f"{V6['wikipedia_rows_in_extended']:,} extended rows ({V6['wikipedia_share_of_extended_pct']}%) are CC BY-SA 4.0; no NOTICE file ships with the training CSV; share-alike scope of derived features / models unresolved", "Redistribution of the dataset or a model trained on it may carry share-alike obligations", "Legal review; ship an attribution notice; keep Wikipedia rows flaggable (column source_license) and exclude them from a CC0-only release"),
    ("I-11", "Medium", "Player datasets", "StatsBomb LICENSE.pdf was not machine-readable; README allows research / analysis with credit; ML-training permission is not explicit", "Player clustering / models may exceed the licence if used commercially", "Read the PDF, obtain written clarification; restrict to research use meanwhile"),
    ("I-12", "Medium", "Lower-tier 2025-26 leagues", "Scottish Premiership, Segunda, 2. Bundesliga, 3. Liga, Ligue 2, Turkish, Belgian, Greek, Austrian 2. Liga and English L1/L2/NL stop between 2025-11 and 2026-03 in the dated source; 04e (1,162 undated results) cannot be used chronologically; Belgian 2026-27 has 305 dated fixtures without results", "Forward-holdout contains only early-season matches for these leagues - biased sample; results are unrecoverable from permitted dated sources", "Exclude these league-seasons from evaluation or obtain a dated feed; do not use 04e for chronological features"),
    ("I-13", "Medium", "Player stats (SB)", f"{V5['statsbomb_event_rows_with_zero_events_total']} rows have no pass/shot/tackle; in addition ~0.2% of rows (players with no recorded event) have passes / shots / tackles forced to 0 while goals, xG and other metrics are NaN (see file 09)", "Mixed missing-as-zero conventions bias per-90 features for cameo players", "Set all metrics NaN for players with no event record; keep minutes"),
    ("I-14", "Medium", "Player recent form", f"StatsBomb windows are 'last N observed matches': {100*V5['recent_form_w5_span_gt_60d_share_of_w5_complete']:.1f}% of complete 5-match windows span >60 days; {100*V5['recent_form_share_gap_gt_21_days']:.1f}% of previous-match gaps exceed 21 days", "Windows are not real recent form", "Use span / gap columns as filters; do not present as 'last N matches'"),
    ("I-15", "Medium", "Player identity", f"openfootball players use team-scoped name keys: {V5['openfootball_names_under_multiple_team_keys']} names under several keys, {V5['names_present_in_both_statsbomb_and_openfootball_NOT_merged']} names in both sources; nationality missing for 100% and position for 100% of lineup players", "Transfers unlinkable; no position-specific analysis for openfootball players", "Obtain a licensed player id source; keep sources separate"),
    ("I-16", "Medium", "Kick-off times", "About 40% of extended rows have no kick-off time; same-day ordering cannot be proven (506 entity-days with two or more eligible matches)", "Handled conservatively (date batches), but strict 'known before kick-off' proof is impossible", "Keep date-level cut-off; mark per-kickoff leakage checks UNVERIFIED"),
    ("I-17", "Medium", "Feature neutral_known", "Constant 0; neutral venues (finals) unmarked, home advantage applied", "No information; cup / continental finals mis-modelled", "Drop until neutral-venue data is added"),
    ("I-18", "Medium", "Strict features", "Elo / form state is updated with 'inferred_no_marker' results (7,873 openfootball + others), so strict-set features rest on inferred results", "Not leakage, but the 'verified-only' guarantee does not extend to features", "Document; optionally rebuild state from confirmed labels only for a sensitivity run"),
    ("I-19", "Low", "Competition expectations", f"{len(um)} of {len(fin)} finished competition-seasons with an expected count show an unexplained shortfall (total {int(um.unexplained_missing.sum())} matches; mostly EFL Cup, Coupe de France, lower cups); expectations for lower leagues rely on source-declared schedules (evidence grade B/C) and cannot reveal matches absent from the schedule", "Cup completeness is not independently provable", "Treat cups as descriptive; confirm against an official fixture list"),
    ("I-20", "Low", "UEFA 2019-20", "Expected total 197 is derived from the Wikipedia box count (COVID format with two single-leg round-of-16 ties); structure is consistent (14 R16, 4 QF, 2 SF, 1 F) but not externally confirmed", "Minor", "Keep evidence grade low"),
    ("I-21", "Low", "DFB-Pokal 2025-26", "8 fills replace unscored openfootball rows; 4 of them carry a date one day later than the openfootball placeholder (2025-12-02 vs 2025-12-03)", "One-day date uncertainty for 4 matches", "Prefer the Wikipedia date, flag as disagreement (already marked status_differs in cross_validation_pairs.csv)"),
    ("I-22", "Low", "Strict penalty rows", f"{LB['strict_penalty_rows_where_90min_outcome_is_not_draw']} penalty-decided strict rows have a non-draw 90-minute result (second legs / aggregate ties); not provable from the row", "Probably correct", "Store aggregate / leg information to prove"),
    ("I-23", "Low", "Reproducibility", "02_MISSING_MATCH_INVENTORY.csv row order is not deterministic (set iteration); content identical after sorting", "Cosmetic", "Sort before writing"),
    ("I-24", "Info", "Previous readiness report", "Statement that Conference League 2024-25 would be '36 missing' was an expected-count error already corrected (108-match league phase, total 153); all five headline counts and 1,328 cross-source scores verified", "None", "None"),
    ("I-25", "Info", "Wikipedia fetch", "User-Agent had no contact address (Wikimedia policy) and one 429 was encountered", "Compliance risk only", "Add a contact before further fetching"),
]
iss = pd.DataFrame(ISS, columns=["issue_id", "severity", "affected_dataset", "evidence", "impact_on_training", "recommended_corrective_action"])
iss.to_csv(os.path.join(OUT, "VERIFICATION_ISSUES.csv"), index=False, encoding=ENC)

# ======================================================================= 10 reproducibility
ident = int(rep.identical_bytes.fillna(False).sum())
W("10_REPRODUCIBILITY_REPORT.md", f"""# 10 Reproducibility report (generated {NOW})

## What was done
1. SHA-256 of {len(pd.read_csv(os.path.join(EV, 'sha256_critical_inputs_outputs.csv')))} critical inputs, outputs, scripts and intermediates recorded in `_evidence/sha256_critical_inputs_outputs.csv`.
2. The Milestone 1 baseline: {base['matching']}/{base['files_listed']} original files unchanged (modified {len(base['modified'])}, missing {len(base['missing'])}). Note: the repository root contains additional untracked directories created by later milestones; they are outside the 522 files.
3. `FootIQ_Dataset_Submission.zip`: all 34 members byte-identical to the directory; the directory's CSVs match the ZIP, so the submission was not modified after zipping.
4. **Isolated rebuild**: the readiness pipeline (`s8_build_dataset.py`, `s9_outputs.py`) was copied to the session scratchpad, its intermediate pickles (`M_of`, `M_fill`, `M_wp`) and Wikipedia-derived tables were copied, and the dataset-building steps were re-run there. Nothing in the project was overwritten.
5. Independent re-implementation of every feature and of the 1X2 label derivation (see files 04 and 06): 0 differences on all 129,829 rows.

## Result of the isolated rebuild
{T(rep, ["file", "bytes_new", "bytes_old", "identical_bytes"])}

* Byte-identical: {ident} of {len(rep)} files, including `04a-04e`, `05`, `08_*_strict.csv`, `08_*_extended.csv`, `07_TEMPORAL_LEAKAGE_TESTS.csv`.
* `02_MISSING_MATCH_INVENTORY.csv` differs in row order only (equal after sorting - set iteration order); the Markdown reports differ by their generation timestamp; the schema JSON differs by its `created` timestamp.
* Row-level comparison of non-identical CSVs: {repr_row.to_dict('records')}.
* Pickle comparison (`data_all.pkl`, key columns: record id, date, Elo, n_prior, labels, eligibility, split): rows {repp['rows_new']:,} vs {repp['rows_old']:,}, equal: **{repp['key_columns_equal']}**.

## Not rebuilt
* Steps that need the network (Wikipedia fetch) were not repeated; the cached pages (103 files, aggregate hash recorded) are the input. Steps `s2-s5` (parse / identity / merge) were not re-executed because they would write into the existing `_build/work` folder; their outputs were verified instead by re-deriving labels, identities and cross-source comparisons independently.
* openfootball parsing (`build_club_matches.py`) was not re-run; instead every training row was traced to its raw `file:line` and re-parsed (0 failures of 128,101).
* Determinism: the builds use fixed sorting (`match_dt, competition_id, record_id`), seeded sampling (2026-10-20 / 7 / 11) and no randomness in features. Only unordered set iteration in the inventory step is non-deterministic (I-23).

## Verdict
Reproducible for the training datasets (byte-identical); inventory order and report timestamps are the only differences.
""")

# ======================================================================= 11 approval
strict_split = V4["split_counts_strict"]
W("11_ML_TRAINING_APPROVAL.md", f"""# 11 ML training approval decisions (generated {NOW})

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
Why: `01`/`03` hold extra-time-inclusive scores only ({L['international']['shootout_matches']} shoot-outs, no stage, no regulation column); a verified 90-minute label cannot be produced for tournament knockouts. Not approved even for the preserved model's data. Re-open when a regulation-time field (or stage + goal minutes) from a permitted source exists. (All World Cup edition match counts 1930-2026 and 11 continental editions match their formats: 0 count mismatches - the data is complete, but not label-correct.)

## 2. Club league-only 90-minute 1X2 - APPROVED WITH RESTRICTIONS
* **Exact dataset:** `FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv` **filtered to `competition_type == 'domestic_league'`** ({int((pd.read_csv(os.path.join(P, 'FootIQ_ML_Data_Readiness', '08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv'), usecols=['competition_type'], low_memory=False, encoding=ENC).competition_type == 'domestic_league').sum()):,} rows; 100% CC0 openfootball, no Wikipedia rows, every label `confirmed` because league matches have no extra time).
* **Period:** 2018-08-01 to 2025-06-29 for fitting / validation / test (train < 2023-07-01, validation 2023-24, test 2024-25). The 2025-26 and early 2026-27 rows are a forward holdout for a single final evaluation.
* **Mandatory corrections before the first fit:** (a) drop `same_country` and `neutral_known` (I-01, I-17); (b) remove the duplicated Russian 2019-20 `ru2` fixtures (I-02); (c) fix or exclude rows whose season label contradicts the date (I-09); (d) restrict the forward holdout to league-seasons with verified complete schedules (all five top leagues, Championship, Austrian Bundesliga) and exclude the 14 lower leagues that stop in 2025-26 (I-12).
* **Restrictions:** Elo values are comparable only inside a connected league component (I-07): model per league group or add a league-strength feature; preprocessing (scaling, imputation, encodings) must be fitted on the training split only; the holdout must not be used for tuning; report calibration (Brier / log loss) and compare to a bookmaker-free baseline (always-home / Elo-only); the strict state uses inferred labels for ratings (I-18).
* **Not covered:** cups, continental competitions, play-offs, extra-time matches.

## 3. Club all-competition 90-minute 1X2 - BLOCKED
Blocking items: cup / continental strict rows are only {V4['strict_rows_by_competition_type'].get('continental_club', 0) + V4['strict_rows_by_competition_type'].get('domestic_cup', 0) + V4['strict_rows_by_competition_type'].get('league_cup', 0):,} ({100 - V4['strict_rows_domestic_league_pct']:.1f}%) and selected by the target (draw-rate bias, I-05); extended labels are inferred (I-06); {100*I['match_sides_with_unresolved_entity']/I['match_sides_total']:.0f}% of match sides have unresolved identity (I-08); neutral venues unknown (I-17); CC BY-SA rows need legal clearance (I-10). Re-open after verified 90-minute scores and identity review.

## 4. Player descriptive analytics - APPROVED WITH RESTRICTIONS
Permitted data: `05` StatsBomb event-level rows ({V5['statsbomb_rows_event_level']:,}; 3,961 matches; goals reconcile with scores for 100% of matches) and openfootball appearance rows (minutes ESTIMATED). Keep sources, men and women separate; never merge players by name; label minutes as derived / estimated; credit StatsBomb; research / education use only until the licence PDF is read (I-11).

## 5. Player recent-form analytics - APPROVED WITH RESTRICTIONS
Permitted data: `FootIQ_ML_Data_Verification/player_form_v1/PLAYER_RECENT_FORM_STATSBOMB_v1.0.csv` and `..._OPENFOOTBALL_APPEARANCES_v1.0.csv` for descriptive use. Windows are the last N *observed* matches; filter on `w*_span_days` and gaps before showing them as "form" (I-14).

## 6. Player clustering and similarity - APPROVED WITH RESTRICTIONS
Permitted data: StatsBomb male player-seasons with >= 900 derived minutes, position-specific cohorts (GK {V5['clustering_cohorts_male'][0]['>=900min']}, DEF {V5['clustering_cohorts_male'][1]['>=900min']}, MID {V5['clustering_cohorts_male'][2]['>=900min']}, FWD {V5['clustering_cohorts_male'][3]['>=900min']}); standardise within competition-season; K-Means and hierarchical suitable, DBSCAN weak; no zero-filling; research use only. Women's data separately ({V5['clustering_female_player_seasons_ge900']:,} player-seasons >= 900 min).

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
""")

# ======================================================================= 01 summary
u = pd.DataFrame(V3["uefa_tests"])
u["stages_ok"] = u.apply(lambda r: "yes", axis=1)
uefa_tbl = pd.DataFrame([dict(competition=t["competition"], season=t["season"], matches=t["rows"], duplicates=t["duplicate_rows_by_date_teams"], date_range=f"{t['date_min']}..{t['date_max']}",
                              league_phase_teams=t.get("league_phase_teams"), matches_per_team=t.get("league_phase_matches_per_team_distribution"),
                              aggregate_notes_checked=t["aggregate_notes_found"], aggregate_notes_matching=t["aggregate_notes_matching_computed_ties"],
                              goal_lists_consistent_pct=t["goal_lists_consistent_pct"]) for t in V3["uefa_tests"]])
suit = club.independent_ml_suitability.value_counts().to_dict()
W("01_VERIFICATION_SUMMARY.md", f"""# 01 Verification summary - FootIQ datasets (independent audit, generated {NOW})

Verification only: no model was trained, no existing dataset / model / report was modified. Every number comes from the actual files (`_scripts/`, `_evidence/`).

## 1. Overall verdict
**The match data is accurate, traceable and reproducible, but it is not ready for an all-competition model.** A *league-only* club 90-minute model is approved with restrictions; international, all-competition club and player-performance models are blocked; tournament simulation was not verified.

What holds up:
* All five headline counts are exact (strict 125,858; extended 129,829; international 49,362; club 223,625; recent 1,482).
* Milestone 1 baseline: {base['matching']}/{base['files_listed']} files unchanged; the submission ZIP equals the directory; the isolated rebuild reproduces the training CSVs byte for byte.
* Every one of the 129,829 feature rows was re-derived independently with zero differences; the 90-minute label of all 142,309 labelled results was re-derived with zero mismatches; 128,101 openfootball rows were traced to their raw source line and 1,571 Wikipedia rows to a cached revision with zero failures.
* Wikipedia and openfootball agree on all 1,328 overlapping comparable final scores (0 conflicts, 0 penalty disagreements, 0 regulation-score disagreements).

What does not:
* Feature defect (`same_country` wrong for 37.6% of rows), duplicate Russian fixtures, constant `neutral_known`, disconnected Elo components, unresolved identities for 34.6% of match sides, selection bias in the strict knockout rows, unusable undated lower-tier results, unresolved CC BY-SA scope, unread StatsBomb licence, discontinuous player data. See `VERIFICATION_ISSUES.csv` ({len(iss)} issues: {iss.severity.value_counts().to_dict()}).

## 2. Verified counts
{T(integ[integ.file.isin(['SUB/01_Historical_International_Matches.csv','SUB/02_Historical_Club_Matches.csv','SUB/03_Recent_Match_Results.csv','RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv','RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv'])], ['file','rows','columns','date_min','date_max','unique_ids','duplicate_ids','competitions','seasons','missing_cell_pct'])}

## 3. Competition-season completeness (file `03_COMPETITION_SEASON_VERIFICATION.csv`)
{len(club)} club competition-seasons and {len(cs)-len(club)} international rows were independently checked. Independent suitability: {suit}. Of {len(fin)} finished club competition-seasons that have an expected count, {len(fin)-len(um)} show no unexplained shortfall; {len(um)} show a total shortfall of {int(um.unexplained_missing.sum())} matches (mostly EFL Cup, Coupe de France 2024-25, lower cups; see I-19). The five major leagues, the Championship, the Champions League, Europa League (2018-19 to 2025-26) and Conference League (2021-22 to 2025-26) have no unexplained shortfall except the known cancellations (Ligue 1 2019-20: 101 cancelled; Europa League 2021-22: 2 cancelled). International: World Cup 1930-2026 (23 editions) and 11 continental editions match the expected edition counts exactly.
2025-26 lower-tier leagues are incomplete in the dated sources (Scottish Premiership 63/198, Segunda 131/462, 2. Bundesliga 99/306, 3. Liga 130/380, Ligue 2 116/306, Turkish 99/306, Belgian 121/240, Greek 62/182, Austrian 2. Liga 96/240, Serie B 309/380). For 2026-27 only matches dated before 2026-10-01 were assessed; results end 2026-09-20 and Belgium has 305 dated fixtures without results.

## 4. Recovered UEFA competitions (Wikipedia, cross-checked)
{T(uefa_tbl)}

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
""")
print("summary docs written; issues:", len(iss))
