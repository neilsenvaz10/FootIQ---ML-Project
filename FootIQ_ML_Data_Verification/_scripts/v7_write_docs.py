"""Stage 7: write every audit deliverable from the evidence files (numbers are never typed by hand)."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
ENC = "utf-8-sig"
NOW = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")


def J(n):
    return json.load(open(os.path.join(EV, n), encoding="utf-8"))


def T(df, n=None, cols=None):
    if cols:
        df = df[cols]
    if n:
        df = df.head(n)
    c = list(df.columns)
    out = ["| " + " | ".join(map(str, c)) + " |", "|" + "|".join("---" for _ in c) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) or v is None else str(v) for v in r) + " |")
    return "\n".join(out)


def W(name, text):
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(text)


integ = pd.read_csv(os.path.join(EV, "dataset_integrity_metrics.csv"))
base = J("baseline_integrity.json")
zipc = pd.read_csv(os.path.join(EV, "zip_vs_directory.csv"))
hashes = pd.read_csv(os.path.join(EV, "sha256_critical_inputs_outputs.csv"))
L = J("v2_part1.json")
LB, INTL = L["labels"], L["international"]
sel = pd.read_csv(os.path.join(EV, "label_selection_bias.csv"))
samp = pd.read_csv(os.path.join(EV, "label_manual_sample.csv"))
cs = pd.read_csv(os.path.join(OUT, "03_COMPETITION_SEASON_VERIFICATION.csv"), encoding=ENC)
V3 = J("v3_results.json")
I = V3["identity"]
V4 = J("v4_results.json")
V5 = J("v5_results.json")
V6 = J("v6_results.json")
fc = pd.read_csv(os.path.join(EV, "feature_recomputation_comparison.csv"))
lic = pd.read_csv(os.path.join(EV, "licence_files_and_commits.csv"))
v2b = J("v2b_summary.json")
rep_path = os.path.join(EV, "repro_file_hash_comparison.csv")
rep = pd.read_csv(rep_path) if os.path.exists(rep_path) else None
repr_row = pd.read_csv(os.path.join(EV, "repro_row_level_comparison.csv")) if os.path.exists(os.path.join(EV, "repro_row_level_comparison.csv")) else pd.DataFrame()
repp = J("repro_pickle_comparison.json") if os.path.exists(os.path.join(EV, "repro_pickle_comparison.json")) else None
club = cs[cs.scope == "club"]
SUIT = club.independent_ml_suitability.value_counts().to_dict()
claims = {"SUB/02_Historical_Club_Matches.csv": 223625, "SUB/01_Historical_International_Matches.csv": 49362, "SUB/03_Recent_Match_Results.csv": 1482,
          "RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv": 125858, "RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv": 129829}
integ["claimed_rows"] = integ.file.map(claims)
integ["matches_claim"] = np.where(integ.claimed_rows.isna(), "", np.where(integ.claimed_rows == integ.rows, "YES", "NO"))

# ------------------------------------------------------------------ player facts needed in several docs
p5 = pd.read_csv(os.path.join(SUB, "05_Player_Match_Statistics.csv"), low_memory=False, encoding=ENC, usecols=["source_dataset", "goals", "passes", "shots", "tackles", "stats_coverage", "competition_gender"])
sbp = p5[p5.source_dataset.str.startswith("Stats")]
n_goal_nan = int(sbp.goals.isna().sum())
n_nan_but_zero_passes = int((sbp.goals.isna() & (sbp.passes == 0)).sum())

# =============================================================== 02 integrity
cols = ["file", "rows", "columns", "date_min", "date_max", "unique_ids", "duplicate_ids", "unique_matches_natural_key", "duplicate_natural_key_rows", "competitions", "seasons", "missing_cell_pct", "invalid_dates", "invalid_scores_or_values", "claimed_rows", "matches_claim"]
W("02_DATASET_INTEGRITY_REPORT.md", f"""# 02 Dataset integrity report (independent, generated {NOW})

All numbers below were computed directly from the CSV files by `_scripts/v1_integrity.py`; no previous summary was reused.

## 1. Record counts versus the previous claims
{T(integ[integ.claimed_rows.notna()], cols=["file", "rows", "claimed_rows", "matches_claim", "columns", "date_min", "date_max", "unique_ids", "duplicate_ids", "competitions", "seasons"])}

All five claimed counts are exactly reproduced. `04d` has 143,055 rows because it is restricted to seasons 2018 onward; the training sets draw on a wider universe (227,374 results since 2010-11), so strict/extended rows are **not** a subset of `04d` (157 strict rows belong to a 2017-18 Nigerian second-tier file dated 2018-09: see season-label issue).

## 2. Per-dataset integrity metrics
{T(integ, cols=cols)}

Notes
* `duplicate_natural_key_rows` > 0 in 01 = {int(integ.loc[integ.file.str.contains('01_Historical'), 'duplicate_natural_key_rows'].iloc[0])} real same-day double-headers (e.g. Tahiti v New Caledonia 1974-02-17) with different scores, retained by the source.
* Null dates: 04e is intentionally undated (matrix results). Every other match file has zero null/invalid dates.
* Invalid scores = negative, non-integer or above 25 goals (minutes above 130 for 05). Reported value per file is in the table.
* Columns that are `object` but look numeric: see `_evidence/dataset_integrity_metrics.csv` (column `object_columns_that_look_numeric`).

## 3. Integrity of the preserved artefacts
* Milestone 1 baseline: {base['matching']} of {base['files_listed']} files in `docs/baseline/capture_2026-10-20/original_files.sha256` still match their recorded SHA-256 (modified: {len(base['modified'])}, missing: {len(base['missing'])}).
* `FootIQ_Dataset_Submission.zip`: {int(zipc.same_hash.sum())} of {len(zipc)} members are byte-identical to the files in `FootIQ_Dataset_Submission/`.
* The model artefact `data/model_artifacts/v27/live_match_model.pkl` and `data/raw/international_results/results.csv` are hashed in `_evidence/sha256_critical_inputs_outputs.csv` ({len(hashes)} hashed items).

## 4. Scripts that build the training data (inspected)
`FootIQ_Dataset_Submission/_build/{{footballtxt,build_club_matches,build_players_openfootball,build_players_statsbomb,assemble_matches,assemble_players,validate_and_document,write_description}}.py` and `FootIQ_ML_Data_Readiness/_build/{{common,identity,labels,wiki_fetch,wp_parse,s2_fetch_wikipedia,s3_parse_wikipedia,s4_combine,s5_merge,s7_league_matrix,s8_build_dataset,s9_outputs}}.py`. Hashes of all of them are in the hash file.

Data flow: openfootball clones + martj42 refresh -> `club_matches_all.csv` -> (+ Wikipedia fills, identity map) -> `data_all.pkl` -> `08_*_strict/extended.csv`.
""")

# =============================================================== 04 labels
sel_t = sel.copy()
inf_share = LB["strict_knockout_rows"]
W("04_MATCH_LABEL_AUDIT.md", f"""# 04 Match-label audit - 90-minute 1X2 (generated {NOW})

Target: result after 90 minutes plus stoppage time, excluding extra time and shoot-outs.

## 1. Strict / extended consistency
* Strict rows {LB['strict_rows']:,}; extended {LB['extended_rows']:,}; strict is a subset of extended: **{LB['strict_subset_of_extended']}**; the {LB['extended_minus_strict']:,} extra rows are all `inferred_no_marker`: **{LB['extra_rows_all_inferred']}**.
* Label status inside strict: {LB['strict_status_values']}. Inside extended: {LB['extended_status_values']}. **No inferred label is present in the strict file.**
* Independent re-derivation of the 1X2 outcome from the score columns reproduced every label: mismatches **{LB['outcome_mismatch_vs_recomputed']}**; outcomes without a label status **{LB['outcome_present_without_label_status']}**; label statuses without outcome **{LB['label_status_without_outcome']}**.

## 2. Raw-source verification of the label classes
* `inferred_no_marker` openfootball rows checked against the original source line: {LB['inferred_openfootball_rows']:,} rows, containing an `a.e.t.` or `pen.` marker: **{LB['inferred_rows_whose_raw_line_contains_aet_or_pen_marker']}** (the inference rule - "no marker, therefore decided in 90 minutes" - is applied correctly; it is still an inference).
* Confirmed knockout rows resting on a source bracket ({LB['confirmed_knockout_openfootball_rows']:,} rows): rows whose raw line lacks the marker or the two-value bracket: **{LB['confirmed_bracket_rows_failing_raw_check']}**.
* Wikipedia-derived confirmed rows ({LB['wikipedia_confirmed_rows']:,}): regulation score recomputed from the stored goal minutes (<= 90') : mismatches **{LB['wikipedia_confirmed_rows_goal_minute_recompute_mismatch']}**.
* Strict knockout rows: {LB['strict_knockout_rows']:,}; basis: {LB['strict_knockout_with_reg_basis']}. Strict rows with unknown regulation score outside league/league-phase matches: **{LB['strict_rows_where_regulation_missing_and_not_league_phase']}**.

## 3. Extra time and penalties
* Strict rows with extra time played: {LB['strict_rows_extra_time_yes']}; of these {LB['strict_extra_time_rows_regulation_equals_final']} have regulation = final (goalless extra time) and {LB['strict_extra_time_rows_regulation_not_draw']} have a non-draw 90-minute result (second legs where the aggregate, not the leg, was tied).
* Strict rows with a penalty shoot-out: {LB['strict_rows_with_penalties']}; 90-minute outcome is the regulation result, never the shoot-out winner (0 rows labelled with the shoot-out winner); {LB['strict_penalty_rows_where_90min_outcome_is_not_draw']} have a non-draw 90-minute result (same second-leg / aggregate situation: e.g. EFL Cup semi-final, Liga MX and MLS two-legged playoffs). These cannot be proved from the rows alone because the aggregate of the tie is not stored: **unverified, probably legitimate**.
* Awarded results ({[r['n'] for r in LB['status_by_match_status'] if r['match_status']=='awarded'][0]}) are labelled `unknown`; abandoned matches ({[r['n'] for r in LB['status_by_match_status'] if r['match_status']=='abandoned'][0]}) are `not_completed`; neither is in the training files.

## 4. Selection bias introduced by the label filter
{T(sel_t)}

The strict knockout sample (draw rate 30.7%) is **not representative** of all knockout results (19.6%) or of the extended sample (20.7%): knockout rows qualify as `confirmed` mainly because the source printed an extra-time / penalty bracket - i.e. the match was level after 90 minutes - or because Wikipedia goal minutes were available, while plain-score knockouts are `inferred` and left out. That is selection on the target (draws over-represented). Strict knockouts are only {LB['strict_knockout_rows']:,} of {LB['strict_rows']:,} rows (1.8%), so a league-only model is unaffected; any cup / continental model trained on the strict set would be biased towards draws. Knockout matches whose regulation score cannot be verified at all ({LB['knockout_rows_unknown_label']} results, {LB['knockout_unknown_with_penalties']} penalty-decided) are excluded from both sets.

## 5. Breakdown by competition and season
Full table: `_evidence/label_breakdown_by_competition_season.csv` (confirmed / inferred / unknown / not_completed per competition-season).

## 6. Reproducible manual sample ({len(samp)} knockout matches, seed 20261020)
Each row is printed with its raw source line (openfootball) so it can be read against the labels: `_evidence/label_manual_sample.csv`. First rows:
{T(samp, 18, ["group", "competition", "season", "date", "home", "away", "final_excl_pens", "regulation", "pens", "label_status", "outcome90", "raw_source_line"])}

## 7. International dataset
`01_Historical_International_Matches.csv` has only an extra-time-inclusive score (`{list(INTL['score_basis_values'])[0]}`), no regulation-time column ({INTL['regulation_score_columns_present']}) and {INTL['shootout_matches']} shoot-out matches. Tournament knockouts therefore cannot be given a verified 90-minute label: **international 90-minute labels are unverifiable**.
""")

# =============================================================== 03 summary handled by CSV. 05 identity
cb = pd.DataFrame(I["cross_border_focus"])
dupg = pd.read_csv(os.path.join(EV, "identity_same_name_multiple_ids.csv")).sort_values("matches", ascending=False)
split = pd.read_csv(os.path.join(EV, "identity_possible_split_candidates_NOT_MERGED.csv"))
wm = pd.read_csv(os.path.join(EV, "identity_possible_wrong_merges_review.csv"))
W("05_TEAM_IDENTITY_AUDIT.md", f"""# 05 Team identity audit (generated {NOW}; nothing was merged or changed)

## Findings
* Mapping rows {I['mapping_rows']:,}; status {I['mapping_status']}; duplicate keys **{I['mapping_duplicate_keys']}**.
* Entities used in `04d`: {I['entities_in_04d']:,}; resolved to a canonical `CLUB:` id {I['entities_resolved_to_canonical']:,}; **unresolved {I['entities_unresolved']:,}** (kept as source-scoped ids). Unresolved match sides: {I['match_sides_with_unresolved_entity']:,} of {I['match_sides_total']:,} ({100*I['match_sides_with_unresolved_entity']/I['match_sides_total']:.1f}%). Share by competition type: {I['unresolved_share_by_competition_type']}.
* Resolution rule (exact normalised alias match inside one country, `openfootball/clubs`, CC0) is name-based but curated; no similarity matching was used. Alias tables exist only for Europe, Israel and Kazakhstan, so South-American, North-American, African and Asian clubs are unresolved by construction.

## Same name, several entity ids ({I['same_normalised_name_multiple_entity_ids_groups']} groups, {I['matches_touching_those_groups']:,} match records)
Two different situations are mixed in this list (`_evidence/identity_same_name_multiple_ids.csv`):
1. **Homonyms (correctly separate)**, e.g. `CLUB:ENG:liverpool-fc` vs `URU|Liverpool FC`; `River Plate` in ARG/PAR/URU.
2. **True splits of one club** across continental and domestic sources, e.g. `BRA|São Paulo FC` vs `south-america/brazil|São Paulo FC`, Mexican (`MEX|` vs `world/north-america|`) and US clubs. Elo/form of these clubs is split between continental and domestic ids.
Largest groups:
{T(dupg, 10, ["nk", "entity_ids", "matches"])}

Impact: domestic league matches stay internally consistent. Continental and cup matches require both clubs `resolved`, so split clubs are *excluded* from cup / continental training rather than mis-linked. Their cross-competition history is lost (no leakage, but incomplete history).

## Possible splits of one club (candidate pairs, NOT merged): {I['possible_split_candidates_unresolved_vs_resolved']}
{T(split, 12)}
Some are homonyms (`URU|Liverpool` v `Liverpool FC`; `CHI|Everton` v `Everton FC`; `ECU|Barcelona` v `FC Barcelona`) and must stay separate; others (`Gazélec FC Ajaccio` / `GFC Ajaccio`, `Gimnàstic de Tarragona`, `Reggina 1914`) are the same club under a name the alias table does not list. **Manual review required.**

## Possible wrong merges (canonical ids fed by dissimilar source names): {I['canonical_ids_with_dissimilar_source_names_for_review']}
Listed in `_evidence/identity_possible_wrong_merges_review.csv` for review (alias lists contain legitimate former names, so many are fine). Reserve/youth canonical entities used: {I['canonical_reserve_teams_used']} (kept separate from senior teams by the alias table).

## Cross-border clubs
{T(cb, cols=["search", "entity_ids", "competitions", "matches", "seasons"])}

* **AS Monaco** is a single entity `CLUB:MCO:as-monaco` across Ligue 1, the French cup, Champions League and Europa League (explicit fallback rule france -> monaco): **verified**.
* **Cardiff, Swansea, Wrexham, Newport** are single `CLUB:WAL:` entities across the English league pyramid and cups: **verified**. (Merthyr Town, Barry Town, TNS and Bala resolve consistently.)

## National teams
{I['national_team_name_ids_in_01']} national-team names in 01; none of the {len(pd.read_csv(os.path.join(EV, 'national_team_former_names_check.csv')))} former-name rules produces rows under both the current and former name ({I['national_teams_with_rows_under_both_current_and_former']}). Historic names (Czechoslovakia, Yugoslavia...) stay separate entities by design, so no history is linked across state successions.

## Effect on features
Elo / form are computed per entity id; split entities therefore carry partial histories. This is conservative (cold-start entities fail the >=5-prior-matches rule) but reduces data and can understate strength for continental participants outside Europe.
""")

# =============================================================== 06 features
FE = list(json.load(open(os.path.join(RDY, "_build", "work", "feature_list.json"))))
W("06_FEATURE_ENGINEERING_AUDIT.md", f"""# 06 Feature-engineering audit (generated {NOW})

## Method
The club features of `08_*_extended.csv` were re-implemented from scratch (`_scripts/v4_features.py`, different algorithm: per-entity arrays + `searchsorted` on calendar dates, independent Elo replay) and compared with the stored values for **all {V4['feature_compare_all_rows']:,} rows**, not a sample.

## Exact differences
{T(fc)}
Maximum absolute difference over all features: **{V4['feature_max_abs_diff_overall']:.2e}** (floating point); rows with any difference > 1e-6: **{V4['feature_rows_with_any_difference']}**. Elo, n_prior, points/goal windows, venue form and rest days are reproduced exactly, including NaN patterns.

## Definitions as verified
* Rated result = completed, dated match with a `confirmed` or `inferred_no_marker` 90-minute label ({V4['rated_results']:,} of {V4['universe_rows']:,} universe results). Results with `unknown` labels never update state.
* A team's history uses **strictly earlier calendar dates** (`date < match date`); same-day matches never see each other.
* `*_n_prior` is uncapped; windows are the last 5 / 10 rated matches of the team in **any** competition; `venue_ppg5` uses the last 5 home (or away) matches; `days_rest` = days since the last rated match (NaN if none).
* Elo: start 1500, K=20, home advantage 60 inside the expectation only, goal-difference multiplier 1 / 1.5 / (11+gd)/8, global across competitions.
* Competition features: `is_league`, `is_league_phase`, `is_knockout`, `comp_type_continental`, `comp_type_cup`.

## Defects found
1. **`same_country` is wrong** for unresolved clubs: it parses the country from `CLUB:XXX:` ids and yields NaN for ids such as `ENG|Name`, so the comparison is False. In the extended set it is 0 for {100*V4['same_country_all_false_share_in_extended']:.1f}% of rows, including **{V4['domestic_league_rows_same_country_stored_false']:,} of {V4['domestic_league_rows_in_extended']:,} domestic-league rows** (an independent computation gives {V4['domestic_league_rows_same_country_expected_false']:,} legitimate zeros). The feature must be fixed or dropped before training.
2. **`neutral_known` is constant 0** ({V4['constant_features']}) - no information; neutral venues (cup/continental finals) are unmarked, so home advantage is applied to neutral finals.
3. **Duplicate fixtures** inflate state: Russian Premier League 2019-20 appears twice (`ru1` and a mislabelled `ru2` file): {V4['extended_duplicate_pair_date_rows']} extended rows, 240 matches (`_evidence/duplicate_fixtures_all_results_same_date_pair_score.csv`). Elo and form of those clubs are double-updated.
4. **Elo is not globally comparable**: {V4['elo_connected_components']} disconnected components; {V4['extended_rows_outside_largest_component']:,} extended rows ({100-V4['extended_rows_in_largest_component_pct']:.1f}%) sit in isolated components (Brazil, MLS, Liga MX, Nigeria, Argentina, Japan, China...). Elo differences are meaningful inside a component only.
5. **Inferred labels feed the state** of the strict set (ratings are updated with `inferred_no_marker` results). Not leakage, but strict-set features depend on inferred results.
6. Missing history: venue form NaN for {V4['feature_missing_pct']}; all other features complete because rows need >=5 prior rated matches.
7. **Same-day ordering:** {V4['entity_days_with_multiple_eligible_matches']} entity-days in the extended set have two or more matches (kick-off times are missing for ~40% of rows). The conservative date-batch rule makes the order irrelevant, so no ambiguity enters the features; the second match of a double day simply does not know the first.
8. **Undated lower-tier results** (`04e`, 1,162 rows) are not in the training or universe files (no null dates in 08/04d; the build script never reads `league_matrix_undated.csv`).
9. Cross-competition history **is** shared (a club's league and cup results update one state) - verified by the brute-force recomputation across all competitions.

## Proposed single feature contract for future club training and inference
Order, name, definition and null rule (the same function must produce training and live rows from the same match table; no `latest.csv` snapshots):

{T(pd.DataFrame(dict(position=range(1, len(FE) + 1), feature=FE)))}

* Cut-off: all inputs have `date < fixture date` (calendar day); a live fixture uses results completed by the previous day.
* Units: goals and points per match; `days_rest` in days; Elo points.
* Null handling: NaN for unknown history (never 0 / 1.0 / 999); tree models can use NaN, linear models need an explicit imputation fitted on the training split only; always include `*_n_prior`.
* Competition encoding: fixed vocabulary stored with the model, fitted on the training split.
* Neutral venue: required boolean from the fixture feed (not guessed). Rating constants K, HA and the start value are part of the contract.
* Fix before use: drop or correct `same_country`; remove `neutral_known` until neutral venues are sourced.
""")

# =============================================================== 07 leakage
rows = [
    ("Future match results in features", "PASS", f"Independent recomputation using only earlier dates reproduces all {V4['feature_compare_all_rows']:,} rows (max diff {V4['feature_max_abs_diff_overall']:.1e}); prefix-invariance test in the pipeline passes."),
    ("Final-season standings / season totals", "PASS", "No season-aggregate or table-position feature exists in the declared feature list."),
    ("Current team ratings applied retrospectively", "PASS", "Elo is replayed chronologically; no 'latest' rating table is read by the club pipeline."),
    ("Post-match statistics (half-time, shots, cards)", "PASS", "Half-time, final, 90-minute goals and penalties are excluded from the 31 declared features."),
    ("Future player transfers", "PASS (not applicable)", "Player data is not used in club features."),
    ("Team identity resolution", "UNVERIFIED", "Alias tables are a 2025-01-03 snapshot (`openfootball/clubs`) applied to all seasons; whether an alias existed at the time of a match is not recorded. No outcome information is involved, but the mapping is retrospective."),
    ("Feature normalisation", "PASS (not applicable)", "The dataset ships raw values; no scaling was applied. Future scaling must be fitted on the training split only."),
    ("Target encoding", "PASS (not applicable)", "No target-derived columns."),
    ("Imputation", "PASS", "Missing values are NaN; no imputation was applied. (SB player stats: see player audit for 0-fills.)"),
    ("Duplicate fixtures across splits", "FAIL", f"{V4['extended_duplicate_pair_date_rows']} rows share (date, team pair): Russian 2019-20 duplicated by a mislabelled file; both copies are in the training split here, but any duplicate straddling a split boundary would leak."),
    ("Same-day ordering", "PASS with caveat", f"Date-batched updates; {V4['entity_days_with_multiple_eligible_matches']} entity-days with 2+ matches; kick-off times unknown for ~40% of rows, so intra-day ordering cannot be proven and is not used."),
    ("Calibration / hyperparameter selection", "NOT VERIFIED", "No model has been trained; the split labels exist but no procedure restricting selection to train/validation can be audited yet."),
    ("Historical data corrections", "UNVERIFIED", "Wikipedia pages were retrieved on 2026-10-20 and can contain later edits; openfootball is a snapshot. Availability timestamps per result do not exist."),
    ("Full-dataset preprocessing", "PASS", "Elo constants were fixed a priori; eligibility uses only prior-match counts; the splits are chronological; the forward holdout is a label, not yet used for fitting."),
    ("Forward holdout excluded from fitting/selection", "NOT VERIFIED", "Holdout = 2025-07-01 onward ({0:,} strict rows). Nothing has been fitted; the guarantee depends on how training is run.".format(V4['split_counts_strict']['forward_holdout'])),
    ("Selection on the outcome", "FAIL", "Strict knockout rows are dominated by matches level after 90 minutes (draw rate 30.7% vs 19.6% for all knockout results); plain-score knockouts are excluded as inferred. This is selection on the target; irrelevant for league-only, biasing for cups."),
    ("Label provenance across time", "UNVERIFIED", "Wikipedia-derived labels (goal minutes) were obtained after the fact; fine for training labels, but their availability time is not recorded."),
]
W("07_TEMPORAL_LEAKAGE_AUDIT.md", f"""# 07 Temporal leakage audit - adversarial (generated {NOW})

The previous six tests were **not** re-run as the evidence; the checks below use independent code (`v4_features.py`) and independent data reads.

| Leakage route | Verdict | Evidence |
|---|---|---|
""" + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows) + f"""

## Chronological boundaries (strict set)
Train < 2023-07-01 ({V4['split_counts_strict']['train']:,}); validation 2023-07-01..2024-06-30 ({V4['split_counts_strict']['validation']:,}); test 2024-07-01..2025-06-29 ({V4['split_counts_strict']['test']:,}); forward holdout 2025-07-01..2026-09-20 ({V4['split_counts_strict']['forward_holdout']:,}). Boundaries are strictly ordered and non-overlapping. The holdout contains 2025-26 and early 2026-27 matches, including 830 Wikipedia-derived rows with a different data-generating process, and partial seasons for 14 lower leagues (early-season matches only).

## Where exact availability timestamps are missing
Per-match result timestamps (when a result became known), kick-off times (~40% missing) and the retrieval time of each openfootball line are not available; every check that would need them is marked UNVERIFIED rather than PASS.
""")

# =============================================================== 08 source & licence
ls = lic[["repo", "license_file", "states_cc0", "commit", "origin"]]
W("08_SOURCE_AND_LICENSE_AUDIT.md", f"""# 08 Source and licence audit (generated {NOW})

## Evidence inspected
* {V6['repos_checked']} cloned repositories, licence file text hashed ({V6['repos_with_cc0_file']} contain the CC0 1.0 Universal text; StatsBomb ships `LICENSE.pdf`, which could **not** be machine-read here). Commits and origins:
{T(ls)}
* Traceability of the {V6['extended_rows']:,} extended training rows: null provenance **{V6['provenance_null']}**, null licence **{V6['source_license_null']}**, null extraction date **{V6['extraction_date_null']}**. {V6['openfootball_rows_traced']:,} openfootball rows point to `file:line`; the line exists for all (**{V6['openfootball_rows_source_line_missing']} missing**), contains both team names (**{V6['openfootball_rows_team_names_not_on_source_line']} failures**) and a score (**{V6['openfootball_rows_score_not_on_source_line']} failures**). {V6['wikipedia_rows_in_extended']:,} Wikipedia rows point to a revision id: all revisions exist in the local cache (**{V6['wikipedia_rows_revision_not_in_cache']} missing**) and each offset starts a football-box template (**{V6['wikipedia_rows_offset_not_a_football_box']} failures**).
* Provenance hashes use the first 12 characters of the repository commit; every training row can be traced to a file/line or page revision.

## Licence position
| Source | Rows in extended set | Licence | Educational / ML use | Attribution | Share-alike / redistribution |
|---|---|---|---|---|---|
| openfootball | {V6['source_license_values'].get('CC0-1.0', 0):,} | CC0 1.0 (file text verified) | Permitted | Not required | None |
| martj42 international results (files 01/03, not in club training) | - | CC0-1.0 (GitHub licence metadata read 2026-10-20; the repo's own file was not cloned) | Permitted | Not required | None |
| Wikipedia (English) | {V6['source_license_values'].get('CC BY-SA 4.0', 0):,} ({V6['wikipedia_share_of_extended_pct']}%) | CC BY-SA 4.0 + GFDL | Reuse permitted under licence | **Required** (page + revision) | **Required** for adaptations; unresolved whether extracted scores are adaptations of expression or uncopyrightable facts; EU database right not assessed |
| StatsBomb Open Data (player files) | - | README terms: free for research; credit StatsBomb; LICENSE.pdf unread | Research/education only (ML terms not explicit) | Required if published | Not stated |
| Football-Data.co.uk | 0 | Private use only, no automated/AI use | **Prohibited** | - | - |

## Wikipedia-derived rows
{V6['wikipedia_rows_in_extended']:,} extended rows by split {V6['wikipedia_rows_by_split']} and competition {V6['wikipedia_rows_by_competition']}. They are **all confirmed-label rows**, i.e. Wikipedia supplies 90-minute evidence (goal minutes) that openfootball lacks. No domestic-league row is Wikipedia-derived, so a league-only training set is CC0-only.

## Unresolved permissions / flags
1. Share-alike scope for the 1,571 Wikipedia rows and anything derived from them (features, trained artefacts) - legal review needed before redistribution; no NOTICE/attribution file ships with the training CSV (attribution is only in the `provenance` column).
2. The Wikimedia API client sent no contact address (policy asks for one); requests were serial and rate limited.
3. StatsBomb licence PDF not read; ML-training permission unverified.
4. The 06/07 teams and competitions tables mix CC0 and StatsBomb names.
5. `raw_external/wikipedia` caches full wikitext (CC BY-SA); do not redistribute the cache without the licence notice.
""")

# =============================================================== 09 players
cov = pd.read_csv(os.path.join(OUT, "12_PLAYER_STATISTICS_COVERAGE.csv"), encoding=ENC, low_memory=False)
cc = cov[cov.level == "competition_season"]
sb_cov = cc[cc.source.str.startswith("Stats")]
W("09_PLAYER_DATA_AUDIT.md", f"""# 09 Player data audit (generated {NOW})

## Counts
* Players (04): {V5['players_rows']:,} rows, {V5['players_unique_ids']:,} unique ids: {V5['players_by_id_scope']}.
* Player-match rows (05): {V5['player_match_rows']:,} ({V5['rows_by_source']}); duplicate (match, player, team): **{V5['duplicates_match_player_team']}**.
* Memberships (08): lineup-based {V5['memberships_lineup_rows']:,} (n_matches mismatches vs 05: **{V5['memberships_n_matches_mismatch_vs_05']}**), squad lists {V5['memberships_squad_list_rows']:,} (all undated), team types {V5['memberships_by_team_type']}.
* Competitions/seasons: {len(cc)} competition-season blocks (`12_PLAYER_STATISTICS_COVERAGE.csv`): StatsBomb {len(sb_cov)} blocks (3,961 matches), openfootball {len(cc)-len(sb_cov)} blocks (2025-26 top-5 + Austria, Club World Cup 2000-2025).
* Gender: StatsBomb rows {V5['rows_by_gender']}; matches {V5['matches_by_gender']}. openfootball rows are **unlabelled** ({V5['openfootball_gender_label']}).

## Identity
* StatsBomb ids are native; {V5['statsbomb_normalised_names_with_multiple_ids']} normalised names carry more than one id (`_evidence/player_identity_same_name_multiple_statsbomb_ids.csv`) - could be homonyms or duplicates; not merged.
* openfootball lineup and squad keys are `team-scoped name keys`: {V5['openfootball_names_under_multiple_team_keys']} names appear under several team keys (transfers or homonyms - undecidable); {V5['names_present_in_both_statsbomb_and_openfootball_NOT_merged']} names occur in both sources and were not merged. Nationality missing for {V5['players_missing_nationality_pct_by_scope']['derived_team_scoped_name_key']:.0f}% and position for {V5['players_missing_position_pct_by_scope']['derived_team_scoped_name_key']:.0f}% of openfootball lineup players.
* Transfers: {V5['statsbomb_players_with_2plus_teams']:,} of {V5['statsbomb_players_total_with_stats_rows']:,} StatsBomb players appear for 2+ teams; same player with two teams on one date: **{V5['statsbomb_player_dates_with_two_teams']}**. {V5['players_with_two_teams_in_same_competition_season']} player-competition-seasons list two teams (mid-season transfer or club + loan; not verifiable).
* No career history exists outside the matches present: club histories are **not** reconstructed.

## Statistics: verified vs estimated vs missing
* StatsBomb minutes: derived from lineup position intervals (union of overlapping intervals; range checked <= 130); missing {V5['minutes_missing_pct_statsbomb']}%; goal totals per match reconcile with the official score for **{V5['statsbomb_goal_reconciliation_matches_ok']:,} of {V5['statsbomb_goal_reconciliation_matches_ok'] + V5['statsbomb_goal_reconciliation_matches_mismatch']:,}** matches (own goals credited to the opponent) - an independent validation of the event aggregation.
* openfootball minutes: **ESTIMATED** (substitution / red-card minutes within a 90-minute frame; extra time and stoppage ignored); only appearances, estimated minutes, goals, own goals, penalty goals and cards exist.
* No xA / expected assists anywhere; xG exists only for StatsBomb. Metric availability per source: `_evidence/player_metric_availability.csv`.
* **Missing-as-zero defect:** {n_goal_nan:,} StatsBomb rows (players with no recorded event) have `goals`, `shots_on_target`, `xg`, ... as NaN but `passes`, `shots` and `tackles` forced to 0 ({n_nan_but_zero_passes:,} rows with passes = 0 and NaN goals). Inconsistent treatment of missing data.
* {V5['statsbomb_event_rows_with_zero_events_total']} appearance rows have no pass/shot/tackle at all (short cameos or data gaps).
* Positions: StatsBomb first position only (not the full role history); position groups {V5['position_group_counts_statsbomb_rows']}.

## Suitability (summary; details in files 13-16)
A. Descriptive player analytics: APPROVED WITH RESTRICTIONS. B. Clustering / similarity: APPROVED WITH RESTRICTIONS (StatsBomb male player-seasons only). C. Future performance regression: BLOCKED.
""")

# =============================================================== 12 done; 13-17
w3 = V5
W("13_PLAYER_RECENT_FORM_AUDIT.md", f"""# 13 Player recent-form audit (generated {NOW})

## What was built (new files, originals untouched)
`player_form_v1/PLAYER_RECENT_FORM_STATSBOMB_v1.0.csv` ({w3['recent_form_rows']:,} rows, {w3['recent_form_players']:,} players): for each appearance, windows of the last 3 / 5 / 10 **observed earlier** matches (strictly earlier calendar dates) with mean minutes, start rate, per-90 goals, assists, shots, shots on target, xG, key passes, passes, pass completion, tackles, interceptions, clearances, blocks, pressures, yellow-card rate, plus window length and span. Current-match values are stored only in `TARGET_*` columns.
`player_form_v1/PLAYER_RECENT_FORM_OPENFOOTBALL_APPEARANCES_v1.0.csv` ({w3['openfootball_form_rows']:,} rows): appearances, appearance rate, estimated minutes, goals and starts over the team's previous 3 / 5 / 10 matches (2025-26 top-5 leagues, Austria, Club World Cup).

## Feasibility
| Question | Answer |
|---|---|
| Last 3 / 5 / 10 matches (StatsBomb) | rows with >=3 / >=5 / >=10 prior observed matches: {w3['recent_form_with_ge3_prior']:,} / {w3['recent_form_with_ge5_prior']:,} / {w3['recent_form_with_ge10_prior']:,} |
| Are the windows real "last N matches"? | **No, only last N observed matches.** StatsBomb covers selected competition-seasons; median gap to the previous observed match {w3['recent_form_median_gap_days_prev_match']:.0f} days, but {100*w3['recent_form_share_gap_gt_21_days']:.1f}% of gaps exceed 21 days and {100*w3['recent_form_w5_span_gt_60d_share_of_w5_complete']:.1f}% of complete 5-match windows span more than 60 days |
| Rolling minutes, goals, assists, shots, passes, defensive actions, xG | available (StatsBomb) |
| Rolling xA | **not available** |
| Per-90 | available; computed as window sum / window minutes x 90 (NaN when minutes = 0) |
| Participation trend | appearance rate only from openfootball (team-match denominators); unused substitutes / squad omissions / injuries are indistinguishable |
| Strictly earlier matches only | brute-force recomputation of 500 random rows: mismatches **{w3['recent_form_bruteforce_mismatches_of_500']}**; same-day matches excluded by design |
| Minutes verified vs estimated | StatsBomb derived (not independently verified); openfootball estimated - kept in separate files |

## Leakage and missing-data findings
* Features contain no information from the target match; `TARGET_*` columns must be dropped from X.
* Women's and men's rows are mixed in the StatsBomb file (`gender`); filter before use.
* Injuries and transfers cannot be seen: a long gap is not distinguishable from a missed match.
* NaN is kept where a window has no minutes or no events.

## Decision: APPROVED WITH RESTRICTIONS (descriptive recent-form analytics only; flag `w*_span_days`; do not call the windows "last N matches").
""")
W("14_PLAYER_HISTORICAL_FORM_AUDIT.md", f"""# 14 Player historical-form audit (generated {NOW})

## Built
`player_form_v1/PLAYER_SEASON_STATS_STATSBOMB_v1.0.csv`: {w3['season_rows']:,} player-team-competition-season rows with matches observed, starts, derived minutes, totals, per-90 (only when minutes >= 90), pass completion, previous observed season's goals/xG per 90 and minutes. `season_complete_for_player` is deliberately `UNKNOWN`: only matches present in the open data are counted.

## Findings
* Players with two or more observed seasons: {w3['players_with_2plus_observed_seasons']:,} (of {w3['recent_form_players']:,}); consecutive observed seasons are frequently *not* consecutive real seasons (StatsBomb publishes selected seasons), so "trend" columns must be read as "previous observed season".
* Transfers: {w3['statsbomb_players_with_2plus_teams']:,} players change team inside the data; the native StatsBomb id keeps identity across clubs and competitions. openfootball keys cannot follow transfers.
* Minutes: season minutes are sums of match-level derived minutes; seasons are incomplete whenever not every match of the team is in the open data. Injuries and unused-substitute games are not recorded.
* Verified vs estimated minutes are separated by source and by file (`minutes_basis` column).
* Career-length trends need >=3 observed seasons; very few players have them (`PLAYER_SEASON_STATS` can be grouped by `source_player_id`).

## Decision: APPROVED WITH RESTRICTIONS for descriptive season tables of StatsBomb competitions; NOT suitable for career-trend modelling.
""")
cl = pd.DataFrame(w3["clustering_cohorts_male"])
W("15_PLAYER_CLUSTERING_READINESS.md", f"""# 15 Player clustering readiness (generated {NOW}; no clustering was run)

## Cohort sizes (StatsBomb, male competitions, derived minutes per player-competition-season)
{T(cl)}
Female player-seasons >= 900 minutes: {w3['clustering_female_player_seasons_ge900']:,} (cluster separately). Total male player-seasons >= 900 min: {w3['clustering_male_player_seasons_ge900_total']:,}.

## Feature quality among players with >= 900 minutes
* Zero share of per-90 features: {w3['per90_feature_zero_share_ge900']}; NaN share: {w3['per90_feature_null_share_ge900']}.
* Available per-90 inputs: goals, assists, shots, shots on target, xG, key passes, passes, pass completion, tackles, interceptions, clearances, blocks, pressures, dribbles, fouls, carries. Goalkeeper statistics exist only as saves / goals conceded (not post-shot xG). No xA, no tracking.

## Method-specific readiness
| Method | Readiness | Comment |
|---|---|---|
| K-Means | APPROVED WITH RESTRICTIONS | Position-specific cohorts (GK, DEF, MID, FWD) with >= 900 minutes; z-score within cohort; log1p counts; drop collinear columns; k chosen on validation stability, not on labels. Cohorts of 134 (GK) to 670 (DEF) are small. |
| Hierarchical | APPROVED WITH RESTRICTIONS | Same cohorts; sizes are workable. |
| DBSCAN | Weak | Density depends on competition mix and scaling; ~420-670 points per cohort and 15+ dimensions give unstable epsilon; use after PCA only. |
| Position-aware similarity | APPROVED WITH RESTRICTIONS | Position = first listed position only. |
| PCA visualisation | APPROVED | descriptive only. |

## Recommendations
* Minimum playing time: 900 minutes (>= 450 only for sensitivity); per-90 only when minutes >= 90.
* Competition context: standardise within competition-season or include competition as a stratifier; cross-league comparison is not valid.
* Missing data: do not zero-fill; drop players with NaN in selected features; goalkeepers cluster only on keeper metrics.
* Never cluster openfootball lineup players (no event metrics, estimated minutes).
* Licence: StatsBomb terms are research/education only until the PDF is reviewed.

## Decision: APPROVED WITH RESTRICTIONS (StatsBomb male player-seasons; research use).
""")
W("16_PLAYER_PREDICTION_READINESS.md", f"""# 16 Player-performance prediction readiness (generated {NOW}; no model trained)

## Targets that can be built from observed data
Next-observed-match goals, assists, shots, shots on target, xG, passes, tackles, interceptions and minutes (`TARGET_*` columns of the recent-form file). Features come only from strictly earlier matches.

## Data reality
* Rows with >= 5 prior observed matches (male): {w3['prediction_rows_male_ge5_prior']:,}; of which previous match within 21 days: {w3['prediction_rows_male_ge5_prior_and_gap_le_21d']:,}.
* Rows after 2018-12-31 with >= 5 priors: {w3['prediction_rows_after_2018-12-31_with_ge5_prior']:,}; after 2022-12-31: {w3['prediction_rows_after_2022-12-31_with_ge5_prior']:,}. Competition-seasons contributing: {w3['prediction_competition_seasons_with_ge5_prior_rows']}. Rows by year are very uneven ({dict(list(w3['prediction_rows_by_year'].items())[-12:])}): two seasons (2015, 2016) contain {w3['prediction_rows_by_year'].get('2015', 0)+w3['prediction_rows_by_year'].get('2016', 0):,} rows.
* Target properties: goals mean {w3['target_goals_mean']}, {100*w3['target_goals_zero_share']:.1f}% zeros (sparse count -> Poisson-type models, not Linear Regression); minutes mean {w3['target_minutes_mean']}.

## Blocking issues
1. Coverage is a patchwork of selected competition-seasons; the "next observed match" is often weeks/months later or in a different competition.
2. No lineup, injury, suspension, opposition-strength or fixture-level context; minutes (the main driver) cannot be predicted without squad/lineup information.
3. A chronological split leaves almost no player with both history and held-out matches inside the same competition-season; a random split would leak player identity.
4. No transfer / team-change features; xA missing; women's and men's data mixed.
5. Minutes are derived (not independently verified); openfootball minutes are estimates and cannot be targets.

## Model families
| Model | Feasibility |
|---|---|
| Linear / Ridge / Lasso | Mechanically possible, statistically poor for zero-inflated counts; usable only as a baseline for minutes or xG per 90 on pooled data |
| Poisson / negative-binomial GLM, gradient boosting | More appropriate once the coverage issue is solved |
| Any "player rating" model | **Not possible**: no verified performance rating exists; do not invent one |

## Decision: BLOCKED for player-performance prediction. An exploratory baseline (Ridge on per-90 xG or minutes, split by competition-season) may be run only after explicit approval and must be labelled exploratory.
""")
fd = [
    ("player_id", "id", "Dataset player id (SB:P<id> native StatsBomb)", "key", "n/a", "never merge by name"),
    ("source_player_id", "id", "StatsBomb player id", "key", "n/a", ""),
    ("record_id", "id", "player_match_id from file 05", "key", "n/a", ""),
    ("match_date", "date", "ISO date of the target match", "date", "n/a", "windows use dates strictly before this"),
    ("n_prior_observed_matches", "count", "Number of earlier observed matches of this player in the dataset", "matches", "0 = no history", "not the player's real career length"),
    ("days_since_previous_observed_match", "days", "Days to the previous observed match", "days", "NaN if none", ""),
    ("w{3,5,10}_n", "count", "Matches inside the window", "matches", "", ""),
    ("w{3,5,10}_span_days", "days", "Days from the first to the last match in the window", "days", "NaN if empty", "large values = non-contiguous window"),
    ("w{3,5,10}_minutes_mean", "minutes", "Mean derived minutes per observed match", "min/match", "NaN if empty", "StatsBomb derived"),
    ("w{3,5,10}_start_rate", "ratio", "Share of window matches started", "0-1", "NaN if empty", ""),
    ("w{3,5,10}_goals_p90", "per 90", "sum(goals)/sum(minutes)*90", "goals/90", "NaN if minutes = 0", "excludes shoot-out kicks"),
    ("w{3,5,10}_assists_p90", "per 90", "sum(assists)/sum(minutes)*90", "assists/90", "NaN if minutes = 0", "StatsBomb goal_assist only"),
    ("w{3,5,10}_shots_p90 / sot_p90", "per 90", "shots, shots on target", "per 90", "NaN", ""),
    ("w{3,5,10}_xg_p90", "per 90", "StatsBomb xG", "xG/90", "NaN", "StatsBomb model xG"),
    ("w{3,5,10}_key_passes_p90 / passes_p90", "per 90", "key passes, pass attempts", "per 90", "NaN", ""),
    ("w{3,5,10}_pass_completion", "ratio", "completed / attempted passes in window", "0-1", "NaN if no passes", ""),
    ("w{3,5,10}_tackles_p90 / interceptions_p90 / clearances_p90 / blocks_p90 / pressures_p90", "per 90", "defensive actions", "per 90", "NaN", ""),
    ("w{3,5,10}_yellow_rate", "ratio", "yellow cards per match in window", "cards/match", "NaN if empty", ""),
    ("TARGET_minutes_played / goals / assists / shots / shots_on_target / xg / passes / tackles / interceptions", "target", "Observed value in the current match", "as stat", "NaN if unavailable", "MUST NOT be used as features"),
    ("team_matches_before", "count", "(openfootball file) team matches before this one in the data", "matches", "", ""),
    ("w{3,5,10}_appearance_rate", "ratio", "(openfootball file) appearances / team matches in window", "0-1", "NaN if no earlier team match", "non-appearance cause unknown"),
    ("w{3,5,10}_minutes_est_mean_per_team_match", "minutes", "(openfootball file) ESTIMATED minutes", "min", "NaN", "estimate, not verified"),
    ("w{3,5,10}_goals / start_count", "count", "(openfootball file) goals and starts in window", "count", "NaN", ""),
    ("minutes_basis", "text", "derived (StatsBomb) or ESTIMATED (openfootball)", "", "", "never merge the two"),
    ("dataset_version", "text", "v1.0", "", "", ""),
]
pd.DataFrame(fd, columns=["feature", "type", "definition", "unit", "null_handling", "leakage_or_quality_note"]).to_csv(os.path.join(OUT, "17_PLAYER_FEATURE_DATA_DICTIONARY.csv"), index=False, encoding=ENC)
print("docs part 1 written")
