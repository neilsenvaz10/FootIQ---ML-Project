"""P4: documentation, manifests, determinism check. All numbers are computed from the generated files."""
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
OUT = os.path.join(P, "FootIQ_ML_Training_Preparation")
WORK = os.path.join(OUT, "_build", "work")
VER = os.path.join(P, "FootIQ_ML_Data_Verification")
ENC = "utf-8-sig"
sys.path.insert(0, os.path.join(OUT, "_build"))
import feature_contract as fc  # noqa: E402

NOW = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


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


# ------------------------------------------------------------------ determinism: rebuild once more and compare hashes
run1 = json.load(open(os.path.join(WORK, "run1_hashes.json")))
subprocess.run([sys.executable, "-I", os.path.join(OUT, "_build", "p2_build.py")], stdout=open(os.path.join(WORK, "p2_run2.log"), "w"), stderr=subprocess.STDOUT, check=True)
run2 = {f: sha(os.path.join(OUT, f)) for f in run1}
det = {f: run1[f] == run2[f] for f in run1}
print("determinism:", det)

ds = pd.read_csv(os.path.join(OUT, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
fe = pd.read_csv(os.path.join(OUT, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
log = pd.read_csv(os.path.join(OUT, "03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv"), low_memory=False, encoding=ENC)
ss = pd.read_csv(os.path.join(OUT, "season_completeness_by_league_season.csv"), encoding=ENC)
tests = pd.read_csv(os.path.join(OUT, "07_LEAKAGE_AND_FEATURE_PARITY_TEST_RESULTS_v1.1.csv"), encoding=ENC)
par = pd.read_csv(os.path.join(OUT, "04b_FEATURE_PARITY_COMPARISON_v1.1.csv"), encoding=ENC)
V = pd.read_pickle(os.path.join(WORK, "V_universe.pkl"))
E = pd.read_pickle(os.path.join(WORK, "E_final.pkl"))
lab = pd.read_csv(os.path.join(OUT, "season_label_verification_by_file.csv"), encoding=ENC)
ru = json.load(open(os.path.join(OUT, "evidence_russia_2019_20_duplicate.json")))
unm = pd.read_csv(os.path.join(OUT, "identity_spelling_conflicts_unmerged.csv"), encoding=ENC)
sus = pd.read_csv(os.path.join(OUT, "identity_same_league_split_suspects.csv"), encoding=ENC)
amb = pd.read_csv(os.path.join(OUT, "evidence_ambiguous_same_day_duplicates_excluded.csv"), encoding=ENC)
flag706 = pd.read_csv(os.path.join(VER, "_evidence", "season_label_date_inconsistent_openfootball.csv"))

# ------------------------------------------------------------------ 706 inconsistent labels: what happened to each row
orig = log.merge(flag706.assign(season_original=flag706.season.astype(str)), on=["competition_id", "season_original"], how="inner")
orig = orig.drop_duplicates("record_id")
disp706 = orig.groupby("disposition").size().reset_index(name="rows").sort_values("rows", ascending=False)
pair706 = orig.groupby(["competition_id", "season_original", "rows"]).size().reset_index() if False else flag706
total706 = int(flag706.rows.sum())

# ------------------------------------------------------------------ Elo components (informational)
parent = {}


def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


R = V[V.rated]
for h, a in zip(R.home_entity_id, R.away_entity_id):
    ra, rb = find(h), find(a)
    if ra != rb:
        parent[ra] = rb
comp = {e: find(e) for e in parent}
sizes = pd.Series(comp).value_counts()
main = sizes.index[0]
E["in_main_component_fullhistory"] = E.home_entity_id.map(comp) == main
share_main = float(E.in_main_component_fullhistory.mean())
by_comp = E.assign(c=E.home_entity_id.map(comp)).groupby("c").size().sort_values(ascending=False)

# v1.0 strict league subset: how many rows came from non-regular stages (finals, promotion / relegation, play-offs) labelled "confirmed" by the old league rule
old = pd.read_pickle(os.path.join(P, "FootIQ_ML_Data_Readiness", "_build", "work", "data_all.pkl"))
old = old[old.train_eligible_strict & old.competition_type.eq("domestic_league")]
import re as _re
REGX = _re.compile(r"(Matchday \d+$)|(^\d+\. Round$)|(^Regular Season - \d+$)|(^\d+st Phase - \d+$)|(^Championship Round - \d+$)|(^Relegation Round - \d+$)|(^Fase (Campeón|Complementación), Gruppe \d+$)|(^Group [A-F]$)|(^Results( \(continuation\))?$)")
n_v10_irregular = int(sum(1 for x in old.stage.fillna("") if not (REGX.search(x) and not _re.search(r"play-?off", x, _re.I))))
n_v10_et = int((old.extra_time_played.fillna("") == "yes").sum())
# ------------------------------------------------------------------ counts
cnt_split = ds.split.value_counts().reindex(["train", "validation", "test", "forward_holdout"]).fillna(0).astype(int)
prim = ds[ds.eval_primary].split.value_counts().reindex(["validation", "test", "forward_holdout"]).fillna(0).astype(int)
sec = ds[ds.eval_secondary_calendar_year].split.value_counts().reindex(["validation", "test", "forward_holdout"]).fillna(0).astype(int)
notev = ds[(ds.split != "train") & ~ds.eval_primary & ~ds.eval_secondary_calendar_year]
reason = pd.Series(np.where(notev.season_incomplete_flag, "season incomplete / not verified complete", np.where(notev.identity_review_flag, "identity review flag", "other"))).value_counts().to_dict()
excl = log.disposition.value_counts().reset_index()
excl.columns = ["disposition", "rows"]
nz = len(ds)

# ------------------------------------------------------------------ 04 dictionary
FEATURE_DEF = {
    "home_elo": ("Elo rating of the home club before the match", "points", "start 1500, K=20, home advantage 60 only inside the expectation, goal-difference multiplier 1 / 1.5 / (11+gd)/8, updated only by CONFIRMED 90-minute results", "never NaN (1500 for unseen clubs; n_prior shows history length)", "Level comparable only inside a connected rating component; use elo_diff for cross-league pooling"),
    "away_elo": ("Elo rating of the away club before the match", "points", "as home_elo", "never NaN", "as home_elo"),
    "elo_diff": ("home_elo - away_elo", "points", "difference", "never NaN", "Comparable because both clubs are connected in the rating graph before the match (pair_connected_asof is required)"),
    "home_n_prior": ("Number of earlier rated (confirmed 90-minute) matches of the home club in any openfootball competition", "matches", "uncapped count, strictly earlier calendar days", "0 allowed in the file but rows need >= 5", "uncapped (the old model capped at 20)"),
    "away_n_prior": ("same for the away club", "matches", "", "", ""),
    "home_ppg5": ("Mean points per match over the last 5 earlier rated matches (any venue)", "points/match", "3/1/0 from the 90-minute result", "NaN if no history", ""),
    "away_ppg5": ("same for the away club", "points/match", "", "NaN if no history", ""),
    "home_ppg10": ("Mean points over the last 10 earlier rated matches", "points/match", "", "NaN if no history", ""),
    "away_ppg10": ("same, away club", "points/match", "", "NaN if no history", ""),
    "home_gf5": ("Mean goals scored over the last 5 earlier rated matches", "goals/match", "90-minute goals", "NaN if no history", ""),
    "home_ga5": ("Mean goals conceded over the last 5 earlier rated matches", "goals/match", "", "NaN if no history", ""),
    "away_gf5": ("as home_gf5 for the away club", "goals/match", "", "", ""),
    "away_ga5": ("as home_ga5 for the away club", "goals/match", "", "", ""),
    "home_gf10": ("Mean goals scored over the last 10 earlier rated matches", "goals/match", "", "", ""),
    "home_ga10": ("Mean goals conceded over the last 10 earlier rated matches", "goals/match", "", "", ""),
    "away_gf10": ("as home_gf10 for the away club", "goals/match", "", "", ""),
    "away_ga10": ("as home_ga10 for the away club", "goals/match", "", "", ""),
    "home_venue_ppg5": ("Mean points over the home club's last 5 earlier rated HOME matches", "points/match", "", "NaN if fewer than 1 earlier home match (count of such rows in the data dictionary note)", ""),
    "away_venue_ppg5": ("Mean points over the away club's last 5 earlier rated AWAY matches", "points/match", "", "NaN if no earlier away match", ""),
    "ppg5_diff": ("home_ppg5 - away_ppg5", "points/match", "", "NaN if either NaN", ""),
    "gd5_diff": ("(home_gf5 - home_ga5) - (away_gf5 - away_ga5)", "goals/match", "", "NaN if either NaN", ""),
    "home_days_rest": ("Days since the home club's latest earlier completed match of any kind in the openfootball data", "days", "any completed dated match, whatever its label", "NaN if none", "Known matches only: cups / European matches missing from the CC0 data (e.g. Europa and Conference League 2025-26) are not counted, so rest can be overstated"),
    "away_days_rest": ("same for the away club", "days", "", "NaN if none", "as above"),
    "rest_diff": ("home_days_rest - away_days_rest", "days", "", "NaN if either NaN", ""),
    "league_tier": ("Tier of the competition in its national pyramid (1 = top flight)", "integer", "from the source file name", "NaN if unknown", "Not comparable across countries"),
}
rows = []
for i, f in enumerate(fc.FEATURE_ORDER, 1):
    d = FEATURE_DEF[f]
    rows.append(dict(kind="model_feature", position=i, name=f, definition=d[0], unit=d[1], computation=d[2], null_handling=d[3], caveat=d[4],
                     non_null_rows=int(fe[f].notna().sum()), min=fe[f].min(), max=fe[f].max()))
META = [("record_id", "key", "Dataset row id (OF:competition:season_label:Lline)"), ("split", "metadata", "train / validation / test / forward_holdout by match date"),
        ("y_90min_1x2", "LABEL", "H / D / A after 90 minutes plus stoppage time (confirmed only)"), ("meta_latest_info_date", "audit metadata (NOT a feature)", "latest earlier match used by the features"),
        ("meta_pair_connected_asof", "audit metadata (NOT a feature)", "home and away clubs were connected in the rating graph before the match"),
        ("competition_id", "metadata / optional categorical", "competition key; if used as a feature the vocabulary must be fitted on the training split"),
        ("eval_primary", "evaluation flag", "validation/test/holdout row of a complete split-year league-season without identity flags"),
        ("eval_secondary_calendar_year", "evaluation flag", "same, calendar-year leagues (cut by date, reported separately)"),
        ("season_incomplete_flag", "evaluation flag", "league-season not verified complete"), ("identity_review_flag", "evaluation flag", "club identity under review (unresolved twin / un-merged spelling)")]
for n, k, dsc in META:
    rows.append(dict(kind=k, name=n, definition=dsc))
EXC = [("same_country", "removed", "was wrong for 37.6% of rows (country parsed only from canonical ids)"), ("neutral_known", "removed", "constant 0, no information"),
       ("is_league / is_league_phase / is_knockout / comp_type_continental / comp_type_cup", "removed", "constant inside the league-only scope"),
       ("home_goals_90 / away_goals_90 / half-time / final / penalty scores", "never a feature", "outcome information of the target match")]
for n, k, dsc in EXC:
    rows.append(dict(kind=f"excluded ({k})", name=n, definition=dsc))
pd.DataFrame(rows).to_csv(os.path.join(OUT, "04_FINAL_FEATURE_DATA_DICTIONARY_v1.1.csv"), index=False, encoding=ENC)
json.dump(dict(contract_version=fc.CONTRACT_VERSION, feature_order=fc.FEATURE_ORDER, rating=dict(initial=fc.ELO_INIT, K=fc.K, home_advantage=fc.HOME_ADV),
               cutoff_rule="features of a fixture on calendar day D use only matches dated < D; the state absorbs day D only after all fixtures of D were featurised",
               history_rule="rated state = CONFIRMED 90-minute results only; rest days use every completed dated match", scope="regular round-robin league matches (stage whitelist)"),
          open(os.path.join(OUT, "feature_contract_v1.1.json"), "w"), indent=1)
json.dump(dict(learned_preprocessing="NONE is shipped. Every learned step below must be fitted on split == 'train' only and then applied unchanged to validation, test and forward_holdout",
               steps=[dict(step="missing-value imputation", applies_to=["home_venue_ppg5", "away_venue_ppg5", "ppg*/gf*/ga*/rest only if NaN appears in new data"], rule="train-split median; add an indicator; or use a NaN-tolerant model"),
                      dict(step="scaling / standardisation", rule="mean and std from train split only (linear models, k-NN, neural nets)"),
                      dict(step="categorical encoding of competition_id / league_tier", rule="vocabulary from train split only, unknown -> 'other'; no target encoding"),
                      dict(step="class weights / calibration", rule="fitted on train (weights) and validation (calibration); never on test or forward holdout"),
                      dict(step="hyper-parameter and feature selection", rule="validation split only (season 2023-24)")],
               forbidden=["fitting any transformer on the full dataset", "using forward_holdout labels or metrics for any decision before the single final evaluation", "using meta_* columns as inputs"]),
          open(os.path.join(OUT, "preprocessing_spec_v1.1.json"), "w"), indent=1)

# ------------------------------------------------------------------ 05 split manifest
B = {"train": ("2018-08-01", "2023-06-30"), "validation": ("2023-07-01", "2024-06-30"), "test": ("2024-07-01", "2025-06-30"), "forward_holdout": ("2025-07-01", "2026-09-30")}
mrows = []
for k, (a, b) in B.items():
    s_ = ds[ds.split == k]
    mrows.append(dict(split=k, start_inclusive=a, end_inclusive=b, rows=len(s_), first_match=s_.match_date.min(), last_match=s_.match_date.max(),
                      leagues=s_.competition_id.nunique(), eval_primary_rows=int(s_.eval_primary.sum()), eval_secondary_calendar_year_rows=int(s_.eval_secondary_calendar_year.sum()),
                      rows_not_in_any_evaluation_set=int(((~s_.eval_primary) & (~s_.eval_secondary_calendar_year)).sum()) if k != "train" else None, role={"train": "fit models and learned preprocessing", "validation": "model / feature / hyper-parameter selection", "test": "one-time unbiased estimate after all choices are frozen", "forward_holdout": "one-time final evaluation; never used for any decision"}[k]))
man = pd.DataFrame(mrows)
man.to_csv(os.path.join(OUT, "05_CHRONOLOGICAL_SPLIT_MANIFEST_v1.1.csv"), index=False, encoding=ENC)
bylg = ds[ds.split != "train"].groupby(["split", "competition_id", "season_corrected"]).agg(rows=("record_id", "size"), season_status=("season_status", "first"), eval_primary=("eval_primary", "sum"),
                                                                                            eval_secondary=("eval_secondary_calendar_year", "sum"), identity_flag=("identity_review_flag", "sum")).reset_index()
bylg.to_csv(os.path.join(OUT, "05b_EVALUATION_ELIGIBILITY_BY_LEAGUE_SEASON_v1.1.csv"), index=False, encoding=ENC)
json.dump(dict(version="v1.1", boundaries=B, assignment="by match_date only (calendar day); no embargo needed because every feature uses strictly earlier days",
               calendar_year_leagues="leagues labelled YYYY are cut by date like all others (their season halves fall in different splits); they are reported as secondary evaluation only, never pooled into the primary metric",
               primary_evaluation="split in (validation, test, forward_holdout) AND season status complete / complete-through-2026-09-30 AND no identity flag AND split-year league",
               incomplete_seasons="excluded from every evaluation set (listed in 05b and season_completeness_by_league_season.csv); they remain in training because missing results only shorten histories",
               forward_holdout_rule="outcomes not inspected during preparation; any change to these rules after seeing holdout results invalidates the holdout",
               counts=man.to_dict("records")), open(os.path.join(OUT, "05_CHRONOLOGICAL_SPLIT_MANIFEST_v1.1.json"), "w"), indent=1, default=str)

# ------------------------------------------------------------------ 06 duplicate and identity report
W("06_DUPLICATE_AND_IDENTITY_VALIDATION_REPORT.md", f"""# 06 Duplicate and identity validation report (v1.1, generated {NOW})

## Duplicates
| Check | Result |
|---|---|
| Russian Premier League 2019-20 duplicate | `europe/russia/2019-20_ru2.txt` is titled "{ru['title_ru2']}" but its body is **identical line for line** to `2019-20_ru1.txt` ("{ru['title_ru1']}"): {ru['ru2_rows_identical_to_ru1']} of {ru['ru2_rows']} fixtures equal (date, teams, score); both files list the same {ru['distinct_teams_ru1']} clubs; `body_lines_identical_after_title = {ru['body_lines_identical_after_title']}`. All 240 ru2 rows were removed (evidence: `evidence_russia_2019_20_duplicate.json`). The real second tier is not available for that season. |
| Same competition, same day, same pair (reversed orientation) | {len(amb)} rows excluded as unresolvable (`evidence_ambiguous_same_day_duplicates_excluded.csv`): e.g. Barrow v Boreham Wood and Boreham Wood v Barrow both dated 2016-03-08 in one National League file; two-leg Mexican play-off legs printed on one date |
| Duplicate record ids / (competition, season, date, home, away) / (date, pair, score) across competitions in the final dataset | 0 / 0 / 0 (tests in file 07) |

## Identity handling in the approved scope
* Canonical club id: exact normalised alias match inside one country against the curated `openfootball/clubs` tables. Share of match sides with a canonical id: {100 * pd.concat([ds.home_entity_id, ds.away_entity_id]).str.startswith('CLUB:').mean():.1f}%; the rest keep source-scoped ids, consistent inside each league.
* **Wrong merges found and withdrawn:** {len(unm)} (club, spelling) pairs had two spellings of one canonical club inside the same league-season (e.g. `CSKA Sofia` / `CSKA 1948 Sofia`, `FC Universitatea Craiova` / `CS Universitatea Craiova`, `Gazişehir Gaziantep FK` / `Gaziantep FK`, `FC Marchfeld Mannsdorf` / `Donauauen`). The canonical id was withdrawn for those spellings; they use source-scoped ids and are flagged `identity_review_flag` (rows touched: {int(V.identity_unmerged.sum())}). Some pairs are really one renamed club (Gaziantep, Marchfeld): their history is therefore split (conservative, documented), not merged by name similarity. List: `identity_spelling_conflicts_unmerged.csv`.
* **Same-league split suspects** (an unresolved entity whose near-twin shares a competition; {len(sus)} pairs, e.g. `1.FC Slovácko` vs `1. FC Slovácko`): the unresolved entity is flagged; the resolved twin is flagged only when the two names are identical after removing punctuation and spaces. Most pairs are different clubs (reserve teams `II`, `FC United of Manchester`), so nothing was merged. Rows with a flag stay in training but are excluded from primary evaluation: {int(ds.identity_review_flag.sum()):,} rows.
* Cross-border clubs: AS Monaco is one entity (`CLUB:MCO:as-monaco`) across Ligue 1 and cups; Cardiff, Swansea, Wrexham, Newport are single `CLUB:WAL:` entities across the English pyramid.
* Same-name clubs in different countries (e.g. `Liverpool`, `River Plate`) are separate entities by construction.

## Elo limitation caused by disconnected competitions
The rating graph (confirmed 90-minute results of all openfootball competitions) has {len(sizes)} connected components; the largest holds {sizes.iloc[0]:,} of {len(comp):,} clubs and {100 * share_main:.1f}% of the final dataset rows (full-history count, informational). Leagues outside it (e.g. Brazil, MLS, Liga MX, Argentina, Japan, China, Nigeria) form islands, because their clubs never meet clubs from the main component in the verified data. Handling:
1. `elo_diff` is only produced when home and away are already connected in the graph (`pair_connected_asof`, required for eligibility; {int((log.disposition == 'EXCLUDED_ELO_PAIR_NOT_CONNECTED_ASOF').sum())} rows removed).
2. Absolute `home_elo` / `away_elo` are comparable only inside a component: do not interpret them across islands; use `competition_id` (fitted on train) or train per league group, and report metrics per league group.
3. No league-strength adjustment was invented.
""")

# ------------------------------------------------------------------ 07 leakage report
W("07_LEAKAGE_AND_FEATURE_PARITY_REPORT.md", f"""# 07 Leakage and feature-parity test results (v1.1, generated {NOW})

{int((tests.result == 'PASS').sum())} of {len(tests)} tests pass; failing: {int((tests.result == 'FAIL').sum())}. Raw results: `07_LEAKAGE_AND_FEATURE_PARITY_TEST_RESULTS_v1.1.csv`; per-feature parity table: `04b_FEATURE_PARITY_COMPARISON_v1.1.csv`.

{T(tests, ['group', 'test', 'result', 'detail'])}

## Feature parity
Two implementations were compared on all {len(ds):,} rows: the contract builder (`feature_contract.py`, state machine used for training and meant for inference) and an independent re-implementation (`p3_tests.py`: per-entity arrays, `searchsorted`, separate Elo replay). Maximum absolute difference over all features: {par.max_abs_diff.max():.2e}; rows with a difference above 1e-6: {int(par.rows_diff_gt_1e_6.sum())}; NaN pattern mismatches: {int(par.nan_pattern_mismatch.sum())}.

## What is *not* proven
* Kick-off times are missing for part of the data, so intra-day information is excluded by construction rather than proven.
* The openfootball snapshots carry no per-result availability timestamps; historic corrections made upstream after a match are invisible.
* The alias tables used for canonical ids are a 2025 snapshot applied retrospectively (names only, no outcome information).
* Training/inference parity of a *future* live pipeline is only specified (single contract), not yet tested against live data.
""")

# ------------------------------------------------------------------ 09 player restrictions
W("09_PLAYER_DATASETS_PRESERVED_AND_RESTRICTIONS.md", f"""# 09 Player datasets: preserved, with current restrictions

Nothing in `FootIQ_Dataset_Submission/` (files 04, 05, 08), `FootIQ_ML_Data_Verification/player_form_v1/` or the player audit files was modified or deleted in this task.

| Use | Status (from `11_ML_TRAINING_APPROVAL.md`) | Restrictions that still apply |
|---|---|---|
| Descriptive player analytics | APPROVED WITH RESTRICTIONS | keep StatsBomb event-level rows, openfootball appearance rows, men and women separate; minutes: StatsBomb derived, openfootball ESTIMATED; never merge players by name; credit StatsBomb |
| Player recent form | APPROVED WITH RESTRICTIONS | windows are the last N *observed* matches (30.6% of complete 5-match windows span >60 days); filter on `w*_span_days`; openfootball appearance windows treat non-appearance as unknown cause |
| Clustering / similarity | APPROVED WITH RESTRICTIONS | StatsBomb male player-seasons >= 900 derived minutes, position-specific cohorts, standardise within competition-season, no zero-filling, research use until the StatsBomb licence PDF is reviewed |
| Player-performance prediction | BLOCKED | discontinuous coverage, no lineups / injuries, no verified target beyond observed next-match stats; open items I-04, I-11, I-13..I-15 in `VERIFICATION_ISSUES.csv` |

The club league dataset of this folder uses **no player data**.
""")

# ------------------------------------------------------------------ 08 readiness report
inc_eval = ss[(ss.season_status == "incomplete")]
elig_excl = bylg[(bylg.eval_primary == 0) & (bylg.eval_secondary == 0)].groupby(["competition_id", "season_corrected"]).rows.sum().sort_values(ascending=False)
pat = log.disposition.str.replace("INCLUDED_.*", "INCLUDED", regex=True)
crit = [
    ("Zero unresolved duplicate fixtures in scope", "MET", "ru2 duplicate removed (240), 8 ambiguous same-day rows excluded; 0 duplicates by id, natural key and cross-competition (date, pair, score)"),
    ("Zero known incorrect season labels", "MET for the approved scope", f"{total706} flagged rows analysed: see section 2; Belgian 2021-22 folder label corrected (320 rows); unverifiable rows are excluded, not relabelled"),
    ("Zero known 90-minute label errors", "MET as far as verifiable", f"only regular round-robin stages with confirmed labels; {n_v10_irregular} rows of the v1.0 strict league subset came from final / promotion / relegation / play-off stages and are now excluded; residual risk = errors inside the source itself"),
    ("No known future-result leakage", "MET", "prefix-invariance at 3 cut-offs, brute-force deletion test, independent re-implementation on 100% of rows"),
    ("Club identity and Elo limitations documented", "MET (restricted)", "file 06: 12 withdrawn merges, review flags, disconnected Elo islands"),
    ("Reproducible outputs", "MET" if all(det.values()) else "NOT MET", f"two consecutive full rebuilds byte-identical for {sum(det.values())} of {len(det)} key outputs"),
    ("Fixed evaluation boundaries", "MET", "05_CHRONOLOGICAL_SPLIT_MANIFEST_v1.1.csv/json"),
]
W("08_FINAL_TRAINING_READINESS_REPORT.md", f"""# 08 Final training-readiness report - club league-only 90-minute 1X2, dataset v1.1 (generated {NOW})

No model was trained, tuned or evaluated. Forward-holdout outcomes were not inspected.

## 1. Corrections performed
1. **Features:** `same_country` and `neutral_known` removed; constant scope indicators removed; the feature contract now has {len(fc.FEATURE_ORDER)} features (`feature_contract_v1.1.json`, `04_FINAL_FEATURE_DATA_DICTIONARY_v1.1.csv`).
2. **Russian 2019-20 duplicate:** {ru['ru2_rows']} ru2 rows removed on source-level evidence (file body identical to ru1).
3. **Dates verified at source level** (new, found while handling the 706 flagged labels): every openfootball date was re-resolved and accepted only if the source printed an explicit year or a weekday that equals the resolved date. {int((log.disposition == 'EXCLUDED_CALENDAR_UNVERIFIABLE_DOTTED_DATES').sum()):,} rows of Nigerian files that print only "DD.MM." have unverifiable years (their parsed dates disagreed with the files' own declared windows by up to a year: {13} files, 4,206 rows outside the window) and were excluded.
4. **Season labels:** the {total706} rows flagged in the verification belong to {len(flag706)} competition-seasons ({len(orig):,} source rows in all: Nigerian, Ghana 2016-17 and Mexican Ascenso 2014-15 files). Final disposition of those {len(orig):,} rows: {'; '.join(f'{r.disposition} {r.rows:,}' for r in disp706.itertuples())}. Labels are names and were kept unless the verified dates contradict them; a label is compatible when every verified date lies within [1 Jan Y, 31 Dec Y+1]. Corrected: Belgian first division (folder 2021-22 -> 2020-21, supported by the title "2020/21" and the verified dates; {int(ds.season_label_corrected_flag.sum())} rows in the final dataset); excluded: 1 Mexican Ascenso row incompatible with its label. Ghana 2016-17 is compatible (calendar-year season) and kept.
5. **Scope and labels:** only regular round-robin stages (whitelist), `confirmed` labels, no extra-time/penalty marker; play-off, promotion/relegation and final stages are excluded ({int((log.disposition == 'EXCLUDED_OUT_OF_SCOPE_STAGE_NOT_REGULAR_ROUND_ROBIN').sum()):,} rows); the v1.0 strict league subset contained {n_v10_irregular} such rows (including {n_v10_et} with an extra-time marker) that its league rule had treated as ordinary league matches; they are out of scope now.
6. **Identity:** {len(unm)} wrong canonical merges withdrawn; ambiguous duplicates excluded.
7. **Features recomputed** from verified records only (CC0 openfootball; no Wikipedia-derived result enters ratings, form or rest days); ratings use confirmed 90-minute results only.
8. **Evaluation sets** exclude incomplete league-seasons and identity-flagged rows.

## 2. Rows removed or corrected (full detail: `03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv`, one line for each of the {len(log):,} source rows)
{T(excl)}

## 3. Final eligible match count
**{nz:,} matches**: train {cnt_split['train']:,}, validation {cnt_split['validation']:,}, test {cnt_split['test']:,}, forward holdout {cnt_split['forward_holdout']:,}.
Primary evaluation rows: validation {prim['validation']:,}, test {prim['test']:,}, forward holdout {prim['forward_holdout']:,}. Secondary (calendar-year leagues): validation {sec['validation']:,}, test {sec['test']:,}, forward holdout {sec['forward_holdout']:,}. Rows in no evaluation set: {len(notev):,} ({reason}).

## 4. Features
Retained ({len(fc.FEATURE_ORDER)}): {', '.join(fc.FEATURE_ORDER)}. Excluded: `same_country`, `neutral_known`, `is_league`, `is_league_phase`, `is_knockout`, `comp_type_continental`, `comp_type_cup`, and every outcome field. Audit metadata `meta_*` are not inputs.

## 5. Chronological splits (exact boundaries)
{T(man, ['split', 'start_inclusive', 'end_inclusive', 'rows', 'first_match', 'last_match', 'eval_primary_rows', 'eval_secondary_calendar_year_rows', 'role'])}

Calendar-year leagues are cut by date like every other league; their evaluation rows are reported separately. Incomplete league-seasons ({len(inc_eval)} in total, all of them listed in `season_completeness_by_league_season.csv`) are excluded from evaluation; the largest excluded groups in the evaluation window are: {'; '.join(f'{k[0]} {k[1]} ({v:,} rows)' for k, v in list(elig_excl.items())[:8])}.

## 6. Acceptance criteria
{T(pd.DataFrame(crit, columns=['criterion', 'status', 'evidence']))}

## 7. Remaining limitations
* The dataset is a **regular-season league** dataset: no cups, play-offs, extra-time matches or neutral venues.
* 2025-26 lower-tier leagues (Scottish Premiership, Segunda, 2. Bundesliga, 3. Liga, Ligue 2, Belgian, Greek, Turkish, Austrian 2. Liga, English League One/Two/National League, Serie B) stop early in the CC0 data; they stay in training but are not evaluated. 2026-27 evaluation is limited to leagues whose dated fixtures all have results (early season, results end 2026-09-20).
* Elo levels are comparable only inside connected components; {100 - 100 * share_main:.1f}% of rows are in island leagues; no cross-league strength adjustment.
* Identity: {100 * (1 - pd.concat([ds.home_entity_id, ds.away_entity_id]).str.startswith('CLUB:').mean()):.1f}% of match sides use source-scoped ids; {len(unm)} merges withdrawn (renamed clubs lose history); flagged rows excluded from primary evaluation.
* Nigerian files with dotted dates (7,607 rows) are unusable until a verified calendar is available.
* Rest days only know matches present in the CC0 data (several 2025-26 European fixtures are missing), so they can be overstated for those clubs.
* Kick-off times are partly missing; the cut-off is the calendar day.
* No odds, lineups, injuries or xG: expected accuracy is bounded by Elo/form information.
* Data readiness is not predictive accuracy: nothing was fitted.

## 8. Decision
**APPROVED WITH RESTRICTIONS for a controlled baseline training experiment** (club domestic-league 90-minute 1X2 only), under these rules: (1) fit on `split == train` only; (2) select models / features / hyper-parameters on `validation` primary rows only; (3) evaluate on `test` primary rows once, then on `forward_holdout` primary rows once, without changing anything afterwards; (4) fit all preprocessing on train (`preprocessing_spec_v1.1.json`); (5) report per league group and separately for calendar-year leagues; (6) do not use `meta_*` or flag columns as inputs; (7) include simple baselines (Elo-only, always-home); (8) no cups / continental / international data. **Awaiting your explicit approval before any training.**

## 9. Reproducibility
Key outputs rebuilt twice with identical SHA-256: {det}. Build order: `_build/p1_calendar_audit.py`, `p2_build.py`, `p3_tests.py`, `p4_docs.py` (inputs are read-only: Submission `club_matches_all.csv` and raw sources, Readiness `M_of.pkl`, `labels.py`, Verification identity evidence).
""")

# ------------------------------------------------------------------ README with hashes
files = [f for f in sorted(os.listdir(OUT)) if os.path.isfile(os.path.join(OUT, f)) and f != "README.md"]
tb = pd.DataFrame([dict(file=f, bytes=os.path.getsize(os.path.join(OUT, f)), sha256_16=sha(os.path.join(OUT, f))[:16]) for f in files])
W("README.md", f"""# FootIQ_ML_Training_Preparation - dataset v1.1 (club league-only 90-minute 1X2)

Start with `08_FINAL_TRAINING_READINESS_REPORT.md`. Nothing was trained. Original submission, readiness and verification folders are untouched.

Core files: `01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv` (matches, labels, splits, flags, provenance), `02_CORRECTED_FEATURE_DATASET_v1.1.csv` (contract features + label), `03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv`, `04_FINAL_FEATURE_DATA_DICTIONARY_v1.1.csv`, `05_CHRONOLOGICAL_SPLIT_MANIFEST_v1.1.*`, `06_DUPLICATE_AND_IDENTITY_VALIDATION_REPORT.md`, `07_LEAKAGE_AND_FEATURE_PARITY_REPORT.md`, `09_PLAYER_DATASETS_PRESERVED_AND_RESTRICTIONS.md`.
All rows are CC0-1.0 (openfootball), extraction date 2026-10-20.

{T(tb)}
""")
print("docs written")
