"""Write all deliverables of FootIQ_ML_Data_Readiness from the computed pickles."""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

CUTOFF = "2026-10-01"
V = "v1.0"
data = pd.read_pickle(os.path.join(WORK, "data_all.pkl"))
M_of = pd.read_pickle(os.path.join(WORK, "M_of.pkl"))
M_fill = pd.read_pickle(os.path.join(WORK, "M_fill.pkl"))
M_wp = pd.read_pickle(os.path.join(WORK, "M_wp.pkl"))
M_fill["competition_type"] = [("league_cup" if f == "EFL Cup" else {"uefa": "continental_club", "cup": "domestic_cup", "league": "domestic_league"}[t]) for f, t in zip(M_fill.competition_family, M_fill.competition_type)]
FEATURES = json.load(open(os.path.join(WORK, "feature_list.json")))
tests = pd.read_csv(os.path.join(WORK, "leakage_tests.csv"))
und = pd.read_csv(os.path.join(WORK, "league_matrix_undated.csv")) if os.path.exists(os.path.join(WORK, "league_matrix_undated.csv")) else pd.DataFrame()
msum = pd.read_csv(os.path.join(WORK, "league_matrix_summary.csv")) if os.path.exists(os.path.join(WORK, "league_matrix_summary.csv")) else pd.DataFrame()
xval = pd.read_csv(os.path.join(WORK, "cross_validation_pairs.csv"))
GOOD = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26", "2026-27", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]
STAMP = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")


def w(path, df):
    df.to_csv(os.path.join(OUT, path), index=False, encoding=ENC)


# ------------------------------------------------------------------ combined datasets
keep = ["record_id", "competition_id", "competition_family", "competition_name", "competition_type", "season", "stage",
        "match_date", "kickoff_time_local", "home_entity_id", "home_team_name", "home_identity_status", "away_entity_id",
        "away_team_name", "away_identity_status", "final_excl_pens_home", "final_excl_pens_away", "reg_home", "reg_away",
        "pen_home", "pen_away", "extra_time_played", "reg_basis", "label_90_status", "label_90_reason", "y90", "match_status",
        "status_note", "source_system", "source_license", "provenance", "extraction_date"]
club = data[data.season.isin(GOOD)][keep].copy()
club = club.rename(columns={"final_excl_pens_home": "final_score_home_excl_penalties", "final_excl_pens_away": "final_score_away_excl_penalties",
                            "reg_home": "regulation_score_home", "reg_away": "regulation_score_away", "y90": "outcome_90min_1x2"})
club["dataset_version"] = V
w(f"04d_COMBINED_CLUB_MATCHES_{V}.csv", club.sort_values(["match_date", "competition_id"]))
w(f"04a_LEAGUE_RESULTS_{V}.csv", club[club.competition_type == "domestic_league"].sort_values(["competition_id", "match_date"]))
w(f"04b_DOMESTIC_CUP_RESULTS_{V}.csv", club[club.competition_type.isin(["domestic_cup", "league_cup"])].sort_values(["competition_id", "match_date"]))
w(f"04c_CONTINENTAL_AND_GLOBAL_RESULTS_{V}.csv", club[club.competition_type.isin(["continental_club", "global_club"])].sort_values(["competition_id", "match_date"]))
if len(und):
    und2 = und.copy()
    und2["note"] = "Result verified from a Wikipedia results matrix; the matrix carries NO match date, so it cannot be used for chronological features or labels."
    w(f"04e_UNDATED_LEAGUE_RESULTS_2025-26_{V}.csv", und2)

# ------------------------------------------------------------------ identity mapping
im = pd.read_csv(os.path.join(WORK, "team_identity_map_raw.csv"))
im["needs_review"] = ~im.resolution_status.eq("resolved_exact_alias")
im["review_note"] = np.where(im.needs_review, "unresolved: kept as its own source-scoped entity, NOT merged with any similar name", "")
im["method"] = np.where(im.needs_review, "none", "exact normalised alias match inside the same country (openfootball/clubs, CC0)")
usage = pd.concat([data[["home_entity_id"]].rename(columns={"home_entity_id": "e"}), data[["away_entity_id"]].rename(columns={"away_entity_id": "e"})]).e.value_counts()
im["canonical_entity_used"] = np.where(im.canonical_team_id.notna(), im.canonical_team_id, "")
im["extraction_date"] = AS_OF
w("05_CANONICAL_TEAM_IDENTITY_MAPPING.csv", im.drop_duplicates(["source_system", "source_team_key", "country_folder"]))

# ------------------------------------------------------------------ coverage matrix
U = pd.concat([M_of[M_of.superseded_by_wp_row.isna()], M_fill], ignore_index=True, sort=False)
U["season"] = U.season.astype(str)
U = U[U.season.isin(GOOD)]
U["family_type"] = U.competition_type
res = data.copy()
und_pairs = {}
if len(und):
    for (cid, s), g in und.groupby(["competition_id", "season"]):
        und_pairs[(cid, s)] = set(zip(g.home_entity_id, g.away_entity_id))
UEFA_EXP = lambda y, fam: ({"UEFA Champions League": 189, "UEFA Europa League": 189, "UEFA Conference League": 153}[fam] if y >= 2024 else
                           ({"UEFA Champions League": 125, "UEFA Europa League": 141, "UEFA Conference League": 141}[fam] if y >= 2021 else
                            ({"UEFA Champions League": 119 if y == 2019 else 125, "UEFA Europa League": 205 if y != 2019 else None, "UEFA Conference League": 0}[fam])))
wp_ref = M_wp.groupby(["competition_family", "season"]).size().to_dict()
LIC = {"openfootball": "CC0-1.0 (confirmed: repository LICENSE.md)", "wikipedia": "CC BY-SA 4.0 (attribution + share-alike required)"}
rows, inv = [], []
for (cid, s), g in U.groupby(["competition_id", "season"]):
    r = res[(res.competition_id == cid) & (res.season == s)]
    ctype = g.competition_type.iloc[0]
    fam = g.competition_family.iloc[0] if pd.notna(g.competition_family.iloc[0]) else None
    teams = set(g.home_entity_id) | set(g.away_entity_id)
    n = len(teams)
    st = g.match_status.value_counts().to_dict()
    n_after = int((g.match_date >= CUTOFF).sum()) if s in ("2026-27", "2026") else 0
    unscored_past = g[(g.match_status == "unscored") & g.match_date.notna() & (g.match_date < (CUTOFF if s in ("2026-27", "2026") else "2026-10-21"))]
    pairs_done = set(zip(r.home_entity_id, r.away_entity_id))
    exp, basis, conf, verified = None, "", "", len(r)
    if ctype == "domestic_league":
        drr = n * (n - 1)
        if n > 1 and abs(len(g) - drr) / drr <= 0.12:
            exp, basis, conf = drr, f"double round robin of the {n} teams listed (n(n-1))", "high" if cid in ("england:1-premierleague", "espana:1-liga", "deutschland:1-bundesliga", "italy:1-seriea", "europe/france:fr1") else "medium"
            up = und_pairs.get((cid, s), set())
            verified = len(pairs_done | up)
        else:
            exp, basis, conf = len(g), "league has split/play-off/unbalanced format: source schedule used (UNVERIFIED against a rules-based count)", "low"
            verified = len(r)
    elif fam in ("UEFA Champions League", "UEFA Europa League", "UEFA Conference League") and s[:4].isdigit():
        y = int(s[:4])
        if s == "2026-27":
            exp, basis, conf = None, "season in progress: league phase fixture list not in sources", "none"
        else:
            exp, basis, conf = UEFA_EXP(y, fam), "competition format (league/group phase + knockout)", "high" if y != 2019 else "medium"
            if exp is None and (fam, s) in wp_ref:
                exp, basis, conf = wp_ref[(fam, s)], "Wikipedia match-box count (COVID-reformatted season)", "low"
    elif ctype in ("domestic_cup", "league_cup", "continental_club", "global_club"):
        if (fam, s) in wp_ref and s != "2026-27":
            exp, basis, conf = wp_ref[(fam, s)], "Wikipedia match-box count (community edited; qualifying rounds excluded)", "medium"
        else:
            exp, basis, conf = len(g), "source schedule (no independent reference)", "low"
    pct = round(100 * verified / exp, 1) if exp else None
    ret = r.match_date.max() if len(r) else None
    lab = r.label_90_status.value_counts().to_dict()
    n_conf, n_inf = lab.get("confirmed", 0), lab.get("inferred_no_marker", 0)
    inprog = s in ("2026-27", "2026")
    if inprog:
        suit, why = "forward_holdout_only", "season in progress at cut-off; use only as a time-ordered holdout up to latest_verified_result_date"
    elif exp is None or conf in ("low", "none"):
        suit, why = "descriptive_only", "completeness cannot be verified against a rules-based count"
    elif pct is not None and pct >= 97 and len(r) and n_conf / len(r) >= 0.9 and (cid not in {k[0] for k in und_pairs} or (cid, s) not in und_pairs):
        suit, why = "suitable_for_training", "complete, dated, 90-minute labels confirmed"
    elif pct is not None and pct >= 90 and len(r) and (n_conf + n_inf) / len(r) >= 0.9:
        suit, why = "suitable_with_caveats", ("labels partly inferred from absence of extra-time markers" if n_inf else "minor gaps") + ("; some results undated" if (cid, s) in und_pairs else "")
    else:
        suit, why = "needs_correction", "coverage below 90% or too many unverifiable 90-minute labels"
    if (cid, s) in und_pairs:
        suit, why = ("needs_correction" if suit == "suitable_for_training" else suit), why + "; undated results excluded from chronological training"
    srcs = "+".join(sorted(g.source_system.unique()))
    rows.append(dict(competition_id=cid, competition_name=g.competition_name.iloc[0], competition_type=ctype, season=s,
                     expected_matches=exp, expected_basis=basis, expected_confidence=conf, records_in_sources=len(g),
                     verified_completed_dated=len(r), verified_completed_incl_undated=verified, missing_results=(exp - verified) if exp else None,
                     coverage_pct=pct, cancelled=int(st.get("cancelled", 0)), postponed=int(st.get("postponed", 0)),
                     abandoned=int(st.get("abandoned", 0)), unscored_date_passed=len(unscored_past), scheduled_after_cutoff=n_after,
                     latest_verified_result_date=ret, label90_confirmed=n_conf, label90_inferred=n_inf,
                     label90_unknown=int(len(r) - n_conf - n_inf), source=srcs, licence_status="; ".join(LIC[x] for x in srcs.split("+")),
                     ml_suitability=suit, suitability_reason=why))
    # inventory
    for rr in g[g.match_status.isin(["cancelled", "postponed", "abandoned"])].itertuples():
        inv.append(dict(category={"cancelled": "cancelled_by_source_flag_not_missing", "postponed": "postponed_no_replacement_recorded",
                                  "abandoned": "abandoned_see_note"}[rr.match_status], competition_id=cid, season=s, match_date=rr.match_date,
                        home_team=rr.home_team_name, away_team=rr.away_team_name, detail=rr.status_note, source=rr.provenance))
    for rr in unscored_past.itertuples():
        up = (rr.home_entity_id, rr.away_entity_id) in und_pairs.get((cid, s), set())
        inv.append(dict(category="result_missing_in_source_date_passed" + ("_undated_result_available_from_wikipedia_matrix" if up else ""),
                        competition_id=cid, season=s, match_date=rr.match_date, home_team=rr.home_team_name, away_team=rr.away_team_name,
                        detail=rr.status_note, source=rr.provenance))
    if ctype == "domestic_league" and conf in ("high", "medium"):
        listed = set(zip(g.home_entity_id, g.away_entity_id))
        done = pairs_done | und_pairs.get((cid, s), set())
        for a in teams:
            for b in teams:
                if a != b and (a, b) not in done and (a, b) not in listed:
                    inv.append(dict(category="ordered_pair_absent_from_source", competition_id=cid, season=s, match_date=None,
                                    home_team=a, away_team=b, detail="no record at all for this home/away pairing", source="derived from round-robin format"))
cov = pd.DataFrame(rows).sort_values(["competition_type", "competition_id", "season"])
w("01_COMPETITION_SEASON_COVERAGE_MATRIX.csv", cov)
invdf = pd.DataFrame(inv)
w("02_MISSING_MATCH_INVENTORY.csv", invdf)

# ------------------------------------------------------------------ training datasets
meta = ["record_id", "competition_id", "competition_name", "competition_type", "season", "match_date", "stage", "home_entity_id",
        "home_team_name", "away_entity_id", "away_team_name", "suggested_split", "label_90_status", "y90", "provenance", "source_license", "extraction_date"]
for nm, flag in (("strict", "train_eligible_strict"), ("extended", "train_eligible_extended")):
    t = data[data[flag]][meta + FEATURES].copy()
    t = t.rename(columns={"y90": "label_outcome_90min_1x2"})
    t["dataset_version"] = V
    w(f"08_TRAINING_READY_MATCH_DATASET_{V}_{nm}.csv", t.sort_values("match_date"))
json.dump(dict(version=V, created=STAMP, features=FEATURES, label="label_outcome_90min_1x2 in {H,D,A} (90-minute result)",
               splits={"train": "< 2023-07-01", "validation": "2023-07-01..2024-06-30", "test": "2024-07-01..2025-06-30",
                       "forward_holdout": ">= 2025-07-01 (2025-26 and 2026-27 before 2026-10-01)"},
               elo=dict(initial=1500, K=20, home_advantage=60, goal_diff_multiplier="1, 1.5, (11+gd)/8", update_data="90-minute results only"),
               missing_values="NaN means unknown (never imputed with 0); *_n_prior gives history length",
               eligibility="completed, dated, 90-minute label verified, both teams >=5 prior rated 90-minute matches, resolved identities for cups/continental, date >= 2018-08-01"),
          open(os.path.join(OUT, f"08_TRAINING_DATASET_SCHEMA_{V}.json"), "w"), indent=1)

# ------------------------------------------------------------------ reports
tr = data[data.train_eligible_strict]
ex = data[data.train_eligible_extended]
lab = data.label_90_status.value_counts()
lab_by_type = data.groupby(["competition_type", "label_90_status"]).size().unstack(fill_value=0)
tests.to_csv(os.path.join(OUT, "07_TEMPORAL_LEAKAGE_TESTS.csv"), index=False, encoding=ENC)
w("06_TRAINING_LABEL_VALIDATION_SUMMARY.csv", lab_by_type.reset_index())


def tbl(df):
    c = list(df.columns)
    return "\n".join(["| " + " | ".join(map(str, c)) + " |", "|" + "|".join("---" for _ in c) + "|"] +
                     ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.values])


agree = xval[xval.kind.isin(["score_agree", "score_conflict"])]
open(os.path.join(OUT, "06_TRAINING_LABEL_VALIDATION_REPORT.md"), "w", encoding="utf-8").write(f"""# Training-label validation report ({V}, generated {STAMP})

Target: **90-minute 1X2** (home win / draw / away win after regulation time). A label is used only when the 90-minute score is verifiable.

## Rules
* `confirmed` - league or league/group-phase match (extra time does not exist in the format), or the source states the regulation score next to an extra-time/penalty marker, or the regulation score is derived from goal minutes that add up to the final score (Wikipedia).
* `inferred_no_marker` - knockout match with no extra-time/penalty marker: decided in 90 minutes only by the absence of a marker. **Excluded from the strict training set.**
* `unknown` - extra time or penalties without a stated regulation score, awarded results, or anything ambiguous. **Never used.** Full-time scores are never reused as 90-minute scores when extra-time semantics are ambiguous.
* `not_completed` - cancelled/postponed/unscored.

## Counts (all club results 2018-19 to 2026-27, before 2026-10-01)
{tbl(lab_by_type.reset_index())}

Total results: {len(data):,}. Confirmed: {int(lab.get('confirmed', 0)):,}; inferred: {int(lab.get('inferred_no_marker', 0)):,}; unknown: {int(lab.get('unknown', 0)):,}.

## Cross-source agreement (Wikipedia vs openfootball on overlapping matches)
* Matched matches with comparable final scores: {len(agree):,}; scores agree: {int((agree.kind == 'score_agree').sum()):,}; conflicts: {int((agree.kind == 'score_conflict').sum()):,}.
* Penalty-shootout agreement: {xval.pen_agree.mean():.3f}. 90-minute scores known in both sources: {int(xval.reg_both_known.sum())}, agreeing: {xval[xval.reg_both_known == True].reg_agree.mean():.3f}.
* Wikipedia rows that matched no openfootball row in validation seasons were NOT added; they mostly involve clubs whose identity could not be verified.

## Other checks
* Duplicates removed on (competition, season, date, team pair, stage): see `_build/work/duplicates_found.csv`.
* Dates: all training rows are dated; undated matrix results are excluded.
* Penalty winners are recorded separately and never used as 90-minute outcomes.
""")
tlines = "\n".join(f"| {r.test} | {'PASS' if r.passed else 'FAIL'} | {r.detail[:200]} |" for r in tests.itertuples())
open(os.path.join(OUT, "07_TEMPORAL_LEAKAGE_AUDIT.md"), "w", encoding="utf-8").write(f"""# Temporal leakage audit ({V}, generated {STAMP})

## Design
* One pass over all results in date order. For each calendar date the features of **all** that day's matches are computed from state built from strictly earlier dates, and only then is the state updated (kick-off times are missing in many sources, so same-day information is never used).
* Ratings/form use 90-minute results only; matches with unknown 90-minute outcome never update state.
* Features: Elo (K=20, home advantage 60 inside the expectation only), uncapped prior-match counts, last-5/10 points and goals for/against, venue-specific form, rest days. Missing history is NaN, never 0.
* Excluded columns: half-time scores, final/penalty scores, 90-minute goals, the label.
* Splits: train < 2023-07-01, validation 2023-24, test 2024-25, forward holdout 2025-26 and 2026-27.

## Automated tests
| Test | Result | Detail |
|---|---|---|
{tlines}

## Known residual risks
* Wikipedia pages were retrieved after the matches; their *content* is historical fact, but any re-edit after a match is invisible. Revision ids/timestamps are stored in provenance.
* The sources give dates, not kick-off timestamps: a 'known before kick-off' proof is only possible at day granularity (handled conservatively).
* Elo is global across leagues and linked only through continental matches and verified club identities; league strengths are therefore weakly connected.
* Cup finals and other neutral venues are not marked (`neutral_known=0`).
""")
open(os.path.join(OUT, "10_TRAIN_INFER_FEATURE_MISMATCH_AUDIT.md"), "w", encoding="utf-8").write(f"""# Training vs inference feature mismatch - preserved international model (documentation only; nothing was modified)

Sources: `scripts/model_bakeoff_v26.py` (training features), `scripts/build_live_predictions_v27.py` (inference features), `docs/baseline/RISK_REGISTER.md`.

| # | Feature / step | Training (v2.6 `build_feature_frame`) | Inference (v2.7 `build_live_feature_rows`) | Effect | Correction for the new club pipeline |
|---|---|---|---|---|---|
| 1 | `*_matches_prior_log` | `len(deque(maxlen=20))`, so capped at 20 (log1p <= 3.04) | total `matches_played` from `team_elo_latest.csv`, uncapped | Live values leave the training range for established teams | Use one uncapped count in both |
| 2 | `is_competitive` | any tournament that is not a friendly | only qualifier/nations league/euro/copa/gold cup/world cup keywords | Other competitive tournaments are scored as non-competitive live; changes draw prior and bucket | One explicit competition-type mapping stored with the dataset |
| 3 | Elo / form freshness | rebuilt chronologically, always as-of kick-off | read from `*_latest.csv`, which stop at 2026-06-02 | Stale ratings; `rest_days` saturates (days_since capped at 999) | Compute features as-of fixture date from the same match table |
| 4 | Home orientation / `neutral` | provider home/away and the neutral flag of the source | `venue_edge_team`, provider order or fixture order with neutral=1 | Orientation noise changes `home_field` and Elo-diff sign | Fixture feed must provide home/away and neutral explicitly |
| 5 | Categorical encoding | `get_dummies` on train+calibration+test concatenated | `reindex(columns, fill_value=0)` | Vocabulary leaks from future splits (R06); unseen buckets become all-zero | Fit vocabulary on training split only |
| 6 | Missing team defaults | not applicable (history empty -> ppg 1.0, elo 1500, days 999) | defaults 1500 / 1.0 / 999 on lookup failure | Silent imputation looks like real history | NaN + explicit `n_prior` |
| 7 | Labels | scores copied from results; ET/penalty semantics undefined (R04) | `actual_90min_result` from provider | Train labels may include extra-time goals | 90-minute labels only when verifiable (this dataset) |
| 8 | Elo update | home advantage 75 in the update, 55 in the probability head | n/a | Two different home-advantage constants | Single constant (60) used in the new pipeline |

None of these were fixed in the existing model or artifacts. A club model needs its own feature code shared by training and inference.
""")

# --- licensing report
pages = pd.read_csv(os.path.join(WORK, "wikipedia_pages.csv")) if os.path.exists(os.path.join(WORK, "wikipedia_pages.csv")) else pd.DataFrame()
open(os.path.join(OUT, "03_VERIFIED_SOURCE_AND_LICENSING_REPORT.md"), "w", encoding="utf-8").write(f"""# Verified sources and licensing ({V}, generated {STAMP})

| Source | Used for | Licence / terms (checked) | Training use |
|---|---|---|---|
| openfootball repositories (england, espana, deutschland, italy, champions-league, europe, austria, belgium, club-worldcup, south-america, world, clubs) | All base results; club alias tables | CC0 1.0 Universal; LICENSE.md verified in each clone (commit ids in `RAW_SOURCES_MANIFEST.csv` of the first submission). Re-fetched 2026-10-20: no newer commits. | **Permitted** |
| Wikipedia (en) via MediaWiki API | Gap fills: UEFA 2018-19/2019-20/2025-26/2026-27, cups, league result matrices; cross-validation | CC BY-SA 4.0 + GFDL (https://en.wikipedia.org/wiki/Wikipedia:Copyrights, read 2026-10-20). Reuse needs attribution and share-alike; scores are facts but treat the Wikipedia-derived rows as CC BY-SA. API etiquette: serial requests >= 4 s apart, descriptive User-Agent (no contact e-mail was included; Wikimedia policy asks for one - add yours before wider use). | **Permitted with attribution/share-alike**; legal review advised before redistribution |
| Football-Data.co.uk | Not used | Stated: private individuals only, not data-training products using bots/scrapers/AI | **Prohibited** |
| footballcsv (CC0) | Checked, not used | Repositories last updated 2020-2024, no 2025-26 data | n/a |
| UEFA.com, league/club sites, FBref, Transfermarkt, Opta, paid APIs | Not used | Scraping/automated use not permitted or paid | **Not used** |

Attribution text for Wikipedia-derived rows: "Match data adapted from English Wikipedia (CC BY-SA 4.0); page titles, revision ids and retrieval dates are in the `provenance` column."

## Wikipedia pages retrieved
{tbl(pages[['competition', 'season', 'role', 'title', 'revid', 'revision_timestamp']].head(80)) if len(pages) else 'n/a'}
""")

# --- readiness report
suit = cov.ml_suitability.value_counts()
strict_split = tr.groupby("suggested_split").size()
ext_split = ex.groupby("suggested_split").size()
big5 = cov[cov.competition_id.isin(["england:1-premierleague", "espana:1-liga", "deutschland:1-bundesliga", "italy:1-seriea", "europe/france:fr1"])]
open(os.path.join(OUT, "09_ML_READINESS_REPORT.md"), "w", encoding="utf-8").write(f"""# ML readiness report - club 90-minute 1X2 ({V}, generated {STAMP})

## Verdict
* **Sufficient for a first, honest league-based 90-minute 1X2 model** (strict dataset: {len(tr):,} matches; by split {strict_split.to_dict()}).
* **Not sufficient to claim a reliable model for domestic cups or for all supported competitions.** Cup/knockout matches mostly have only inferred 90-minute labels; many lower-tier 2025-26 league seasons are incomplete or partly undated; 2026-27 is only a short forward holdout (through 2026-09-20 in the sources).
* Extended dataset (adds `inferred_no_marker` knockout labels): {len(ex):,} matches; by split {ext_split.to_dict()}.

## Competition-season suitability (see `01_COMPETITION_SEASON_COVERAGE_MATRIX.csv`)
{tbl(suit.reset_index().rename(columns={'index': 'ml_suitability', 'ml_suitability': 'count'}) if False else pd.DataFrame({'ml_suitability': suit.index, 'competition_seasons': suit.values}))}

Big-five league seasons:
{tbl(big5[['competition_name', 'season', 'expected_matches', 'verified_completed_dated', 'coverage_pct', 'latest_verified_result_date', 'ml_suitability']])}

## Blockers and remaining limitations
1. **Dated results for lower-tier 2025-26 leagues are not available from any permitted source.** Wikipedia result matrices supply verified scores but no dates; they are exported as undated records (04e) and excluded from chronological training. Pairs still without a result are in `02_MISSING_MATCH_INVENTORY.csv`.
2. **2026-27 league results after 2026-09-20 do not exist in the sources**; Wikipedia matrices cannot be bounded by date, so none were used for 2026-27.
3. **90-minute labels for knockouts:** extra-time/penalty matches without a stated regulation score are `unknown` and excluded; plain-score knockouts are `inferred` only.
4. **Identity:** clubs without an exact alias entry stay separate entities (flagged in `05_CANONICAL_TEAM_IDENTITY_MAPPING.csv`); cup and continental matches require both clubs resolved, so many lower-division cup ties are excluded from training.
5. **Information content:** no lineups, injuries, odds, xG or kick-off timestamps; the model would rest on Elo/form/rest only.
6. **Cross-league strength** is weakly connected (global Elo links leagues only through continental matches).
7. **Wikipedia rows** are community-edited and CC BY-SA; validation against openfootball showed {int((agree.kind == 'score_agree').sum()):,} agreeing and {int((agree.kind == 'score_conflict').sum()):,} conflicting final scores on overlapping matches.
8. Competitions never covered by any permitted source (UEFA Super Cup, domestic super cups, Intercontinental Cup) remain absent.

## Recommendations
* Start with a league-only model (strict set), evaluate on `test` (2024-25) and report the 2025-26 holdout once; do not tune on the holdout.
* Treat cups/continental as a second stage after adding verified 90-minute scores (e.g. match reports) or accepting inferred labels explicitly.
* Obtain a licensed dated results feed for lower leagues if they are needed.
* Do not train until you approve (no model was trained).
""")
print("outputs written;", len(cov), "competition-seasons;", len(invdf), "inventory rows;", len(tr), "strict;", len(ex), "extended")
print(suit.to_string())
