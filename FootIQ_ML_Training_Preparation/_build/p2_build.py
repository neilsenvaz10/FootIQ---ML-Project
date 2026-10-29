"""P2: build the corrected league-only dataset v1.1 (reads existing files only; writes only inside FootIQ_ML_Training_Preparation)."""
import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
VER = os.path.join(P, "FootIQ_ML_Data_Verification")
OUT = os.path.join(P, "FootIQ_ML_Training_Preparation")
WORK = os.path.join(OUT, "_build", "work")
ENC = "utf-8-sig"
sys.path.insert(0, os.path.join(OUT, "_build"))
sys.path.insert(0, os.path.join(RDY, "_build"))
import feature_contract as fc  # noqa: E402
from labels import label_status, phase_kind  # noqa: E402  (read-only import of the existing label rules)

VERSION = "v1.1"
EXTRACTION = "2026-10-20"
CUTOFF = "2026-10-01"               # results must be dated strictly before this day
TRAIN_START = "2018-08-01"
BOUNDS = dict(train=("2018-08-01", "2023-06-30"), validation=("2023-07-01", "2024-06-30"), test=("2024-07-01", "2025-06-30"),
              forward_holdout=("2025-07-01", "2026-09-30"))


def split_of(d):
    for k, (a, b) in BOUNDS.items():
        if a <= d <= b:
            return k
    return "outside"


M = pd.read_pickle(os.path.join(RDY, "_build", "work", "M_of.pkl")).copy()
cm = pd.read_csv(os.path.join(SUB, "_build", "work", "club_matches_all.csv"), low_memory=False, keep_default_na=False, na_values=[""], usecols=["tier", "competition_country"])
M["tier"] = cm["tier"].values
M["competition_country"] = cm["competition_country"].values
assert len(M) == len(cm)
ex = M.provenance.str.extract(r"(\S+\.txt):L(\d+)$")
M["source_file"], M["source_line"] = ex[0], pd.to_numeric(ex[1])
M["season"] = M.season.astype(str)
M["season_original"] = M.season

# ------------------------------------------------------------------ calendar verification (P1 output)
cal = pd.read_pickle(os.path.join(WORK, "calendar_audit_rows.pkl"))
files = pd.read_csv(os.path.join(WORK, "calendar_audit_files.csv"), parse_dates=["win_start", "win_end"])
M = M.merge(cal[["source_file", "source_line", "reparsed_date", "date_status"]], on=["source_file", "source_line"], how="left")
assert (M.reparsed_date == M.match_date).all()

# ------------------------------------------------------------------ season label verification (labels are NAMES; they are kept unless verified dates contradict them)
def label_range(lbl):
    y = int(str(lbl)[:4])
    return f"{y}-01-01", f"{y + 1}-12-31"          # a season named Y may contain dates from 1 Jan Y to 31 Dec Y+1 (qualifying rounds, calendar-year leagues, COVID delays)


def folder_label(path):
    for part in path.split("/"):
        m = re.match(r"^(\d{4}(?:-\d{2})?)(?:[_.-]|$)", part)
        if m:
            return m.group(1)
    return None


M["folder_label"] = M.source_file.map(folder_label)
lo = M.season_original.map(lambda x: label_range(x)[0])
hi = M.season_original.map(lambda x: label_range(x)[1])
M["label_date_compatible"] = (M.match_date >= lo) & (M.match_date <= hi)
flo = M.folder_label.map(lambda x: label_range(x)[0] if x else "0000")
fhi = M.folder_label.map(lambda x: label_range(x)[1] if x else "9999")
M["folder_label_date_compatible"] = (M.match_date >= flo) & (M.match_date <= fhi)
lab = M.groupby("source_file").agg(competition_id=("competition_id", "first"), label_in_original_submission=("season_original", "first"), folder_label=("folder_label", "first"),
                                   rows=("record_id", "size"), rows_compatible_with_label=("label_date_compatible", "sum"),
                                   rows_compatible_with_folder_label=("folder_label_date_compatible", "sum")).reset_index()
lab = lab.merge(files[["source_file", "title", "win_start", "win_end", "win_span_days"]], on="source_file", how="left")
lab["label_verdict"] = np.where(lab.rows_compatible_with_label == lab.rows, np.where(lab.folder_label != lab.label_in_original_submission,
                                "CORRECTED_FOLDER_LABEL_CONTRADICTED_BY_TITLE_AND_DATES", "verified_compatible"), "ROWS_INCOMPATIBLE_WITH_LABEL")
lab.to_csv(os.path.join(OUT, "season_label_verification_by_file.csv"), index=False, encoding=ENC)
M = M.merge(lab[["source_file", "label_verdict", "win_start", "win_end"]], on="source_file", how="left")
M["label_evidence"] = M.apply(lambda r: f"title/folder: {r.folder_label}->{r.season_original}; declared window {str(r.win_start)[:10]}..{str(r.win_end)[:10]}" if r.label_verdict.startswith("CORRECTED") else "", axis=1)

# ------------------------------------------------------------------ Russian 2019-20 duplicate: source-level evidence
def parse_lines(fn):
    out = set()
    sub = M[M.source_file == fn]
    for r in sub.itertuples():
        out.add((r.match_date, r.home_team_name, r.away_team_name, r.final_excl_pens_home, r.final_excl_pens_away))
    return out


ru1 = parse_lines("europe/russia/2019-20_ru1.txt")
ru2 = parse_lines("europe/russia/2019-20_ru2.txt")
ev = dict(ru1_rows=len(ru1), ru2_rows=len(ru2), ru2_rows_identical_to_ru1=len(ru2 & ru1))
t1 = open(os.path.join(SUB, "_raw_sources", "europe/russia/2019-20_ru1.txt"), encoding="utf-8").read().splitlines()
t2 = open(os.path.join(SUB, "_raw_sources", "europe/russia/2019-20_ru2.txt"), encoding="utf-8").read().splitlines()
ev["title_ru1"], ev["title_ru2"] = t1[0], t2[0]
ev["body_lines_identical_after_title"] = t1[1:] == t2[1:]
ev["distinct_teams_ru1"] = len({x[1] for x in ru1} | {x[2] for x in ru1})
ev["distinct_teams_ru2"] = len({x[1] for x in ru2} | {x[2] for x in ru2})
other_ru2 = [f for f in M.source_file.unique() if "russia" in f and f.endswith("_ru2.txt")]
ev["other_ru2_files"] = other_ru2
json.dump(ev, open(os.path.join(OUT, "evidence_russia_2019_20_duplicate.json"), "w"), indent=1)
print(ev)

# ------------------------------------------------------------------ disposition of every source row
M["is_result_row"] = M.match_status.isin(["completed", "awarded", "abandoned"]) & M.final_excl_pens_home.notna()
M["reason"] = ""


def mark(mask, code):
    m = mask & (M.reason == "")
    M.loc[m, "reason"] = code


mark(M.source_file.eq("europe/russia/2019-20_ru2.txt") & (ev["ru2_rows_identical_to_ru1"] == ev["ru2_rows"]), "REMOVED_DUPLICATE_RU2_2019_20_IDENTICAL_TO_RU1")
mark(M.date_status.isin(["no_weekday_no_year_UNVERIFIED", "weekday_mismatch", "unresolvable", "no_date_line"]), "EXCLUDED_CALENDAR_UNVERIFIABLE_DOTTED_DATES")
mark(~M.label_date_compatible, "EXCLUDED_SEASON_LABEL_INCOMPATIBLE_WITH_VERIFIED_DATE")
mark(~M.is_result_row, "NOT_A_COMPLETED_RESULT")
mark(M.match_date.isna() | (M.match_date >= CUTOFF), "NOT_BEFORE_2026_10_01")
M["season_corrected"] = M.season_original
M["season_was_corrected"] = M.label_verdict.str.startswith("CORRECTED")

# ------------------------------------------------------------------ results universe (verified, deduplicated)
V = M[M.reason == ""].copy()
V["pair_key"] = [("|".join(sorted([a, b]))) for a, b in zip(V.home_entity_id, V.away_entity_id)]
V["score_key"] = V.final_excl_pens_home.astype(int).astype(str) + "-" + V.final_excl_pens_away.astype(int).astype(str)
cross = V[V.duplicated(["match_date", "pair_key", "score_key"], keep=False)]
dup_report = cross.groupby(["match_date", "pair_key", "score_key"]).competition_id.agg(lambda s: "|".join(sorted(set(s)))).value_counts().to_dict()
print("remaining cross-competition duplicate (date,pair,score) groups:", len(cross) // 2 if len(cross) else 0, dup_report)
same_comp = V[V.duplicated(["competition_id", "season_corrected", "match_date", "pair_key", "stage"], keep=False)]
print("same-competition same-day duplicates (excluded, both rows):", len(same_comp))
same_comp[["record_id", "competition_id", "season_corrected", "match_date", "home_team_name", "away_team_name", "stage", "provenance"]].to_csv(os.path.join(OUT, "evidence_ambiguous_same_day_duplicates_excluded.csv"), index=False, encoding=ENC)
M.loc[M.record_id.isin(same_comp.record_id), "reason"] = "EXCLUDED_AMBIGUOUS_SAME_DAY_DUPLICATE_FIXTURE"
V = V[~V.record_id.isin(same_comp.record_id)].copy()

# ---- identity safety: one canonical club must not carry two spellings inside one league-season (e.g. CSKA Sofia / CSKA 1948 Sofia)
long = pd.concat([V[["competition_id", "season_corrected", "home_entity_id", "home_team_name"]].set_axis(["c", "s", "e", "n"], axis=1),
                  V[["competition_id", "season_corrected", "away_entity_id", "away_team_name"]].set_axis(["c", "s", "e", "n"], axis=1)]).drop_duplicates()
long = long[long.e.str.startswith("CLUB:")]
cnt = long.groupby(["c", "s", "e"]).n.nunique()
bad = cnt[cnt > 1].reset_index()[["c", "s", "e"]]
conf = long.merge(bad, on=["c", "s", "e"])[["e", "n"]].drop_duplicates()
conf_set = set(zip(conf.e, conf.n))
conf.assign(action="canonical id withdrawn for this spelling; spelling keeps a source-scoped id (flagged for review, NOT merged)").to_csv(
    os.path.join(OUT, "identity_spelling_conflicts_unmerged.csv"), index=False, encoding=ENC)
for side in ("home", "away"):
    ids = V[f"{side}_entity_id"].tolist()
    nms = V[f"{side}_team_name"].tolist()
    V[f"{side}_entity_id"] = [f"SRCSCOPED|{e}|{n}" if (e, n) in conf_set else e for e, n in zip(ids, nms)]
V["identity_unmerged"] = V.home_entity_id.str.startswith("SRCSCOPED|") | V.away_entity_id.str.startswith("SRCSCOPED|")
print("spelling conflicts withdrawn:", len(conf_set), "rows touched:", int(V.identity_unmerged.sum()))
V["pair_key"] = [("|".join(sorted([a, b]))) for a, b in zip(V.home_entity_id, V.away_entity_id)]
REG = re.compile(r"(Matchday \d+$)|(^\d+\. Round$)|(^Regular Season - \d+$)|(^\d+st Phase - \d+$)|(^Championship Round - \d+$)|(^Relegation Round - \d+$)|(^Fase (Campeón|Complementación), Gruppe \d+$)|(^Group [A-F]$)|(^Results( \(continuation\))?$)")
V["regular_round_robin_stage"] = V.stage.fillna("").map(lambda x: bool(REG.search(x)) and not re.search(r"play-?off", x, re.I))
recs = V.to_dict("records")
for r in recs:
    if r["competition_type"] == "domestic_league" and not r["regular_round_robin_stage"]:
        r["competition_type"] = "domestic_cup"          # treat as a knockout / play-off stage: 90-minute label only if the source states it
st = [label_status(r) for r in recs]
V["label_90_status"] = [s[0] for s in st]
V["label_90_reason"] = [s[1] for s in st]
V["gh"] = np.where(V.reg_home.notna(), V.reg_home, V.final_excl_pens_home)
V["ga"] = np.where(V.reg_away.notna(), V.reg_away, V.final_excl_pens_away)
V["rated"] = V.label_90_status.eq("confirmed")          # only CONFIRMED 90-minute results update Elo / form
V["dt"] = pd.to_datetime(V.match_date)
V["phase"] = np.where((V.competition_type == "domestic_league") & V.regular_round_robin_stage, "league", "knockout_or_other")
V["in_scope"] = V.competition_type.eq("domestic_league") & V.phase.eq("league") & V.label_90_status.eq("confirmed") & V.extra_time_played.eq("no") & V.pen_home.isna() & (V.match_date >= TRAIN_START)
print("universe results:", len(V), " in scope before eligibility:", int(V.in_scope.sum()))

# ------------------------------------------------------------------ features (single contract implementation)
fr = V.rename(columns={"home_entity_id": "home", "away_entity_id": "away"})[["record_id", "dt", "home", "away", "tier", "rated", "gh", "ga", "in_scope"]].copy()
fr["completed"] = True
fr["want_features"] = fr.in_scope
feat = fc.build_features(fr)
D = V[V.in_scope].merge(feat, on="record_id", how="left")
D["enough_history"] = (D.home_n_prior >= 5) & (D.away_n_prior >= 5)
D["eligible_final"] = D.enough_history & D.pair_connected_asof

# ------------------------------------------------------------------ season completeness (corrected seasons, all source records of verified files)
R = M[~M.reason.isin(["REMOVED_DUPLICATE_RU2_2019_20_IDENTICAL_TO_RU1", "EXCLUDED_CALENDAR_UNVERIFIABLE_DOTTED_DATES", "EXCLUDED_SEASON_LABEL_INCOMPATIBLE_WITH_VERIFIED_DATE"])]
R = R[R.competition_type.eq("domestic_league")]
rows = []
for (cid, s), g in R.groupby(["competition_id", "season_corrected"]):
    teams = set(g.home_entity_id) | set(g.away_entity_id)
    n = len(teams)
    res = g[g.is_result_row & (g.match_date < CUTOFF)]
    upast = g[g.match_status.isin(["unscored", "postponed"]) & g.match_date.notna() & (g.match_date < CUTOFF)]
    canc = g[g.match_status.eq("cancelled")]
    inprog = (g.match_date.max() >= CUTOFF) or s in ("2026-27", "2026")
    drr = n * (n - 1)
    pairs_done = set(zip(res.home_entity_id, res.away_entity_id))
    pairs_canc = set(zip(canc.home_entity_id, canc.away_entity_id))
    drr_like = n > 1 and abs(len(g) - drr) / drr <= 0.12
    cov = (len(pairs_done | pairs_canc) / drr) if (drr_like and n > 1) else None
    if len(res) == 0:
        status, why = "no_results", "no completed results"
    elif len(upast) > 0:
        status, why = "incomplete", f"{len(upast)} dated fixtures before 2026-10-01 without a result"
    elif cov is not None and cov < 0.99 and not inprog:
        status, why = "incomplete", f"only {cov:.3f} of the {drr} home/away pairings have a result or a cancellation"
    elif inprog:
        status, why = "in_progress_complete_through_cutoff", "every dated fixture before 2026-10-01 has a result"
    else:
        status, why = "complete", "no dated fixture without result; pairing coverage ok" if cov is not None else "no dated fixture without result (non-round-robin format: format completeness not rule-verifiable)"
    rows.append(dict(competition_id=cid, season_corrected=s, teams=n, source_records=len(g), results=len(res), unscored_or_postponed_dated_before_cutoff=len(upast),
                     cancelled=len(canc), pairing_coverage=None if cov is None else round(cov, 4), latest_result=res.match_date.max(), season_status=status, season_status_reason=why))
SS = pd.DataFrame(rows)
SS.to_csv(os.path.join(OUT, "season_completeness_by_league_season.csv"), index=False, encoding=ENC)
D = D.merge(SS[["competition_id", "season_corrected", "season_status"]], on=["competition_id", "season_corrected"], how="left")

# ------------------------------------------------------------------ identity review flag (same-league split suspects, NOT merged)
cand = pd.read_csv(os.path.join(VER, "_evidence", "identity_possible_split_candidates_NOT_MERGED.csv"))
ent_comps = pd.concat([V[["home_entity_id", "competition_id"]].set_axis(["e", "c"], axis=1), V[["away_entity_id", "competition_id"]].set_axis(["e", "c"], axis=1)]).groupby("e").c.agg(set).to_dict()
import unicodedata
def compact(x):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(x).split("|")[-1].split(":")[-1]).encode("ascii", "ignore").decode().lower())
names = dict(zip(pd.concat([V.home_entity_id, V.away_entity_id]), pd.concat([V.home_team_name, V.away_team_name])))
susp = set()
sus_rows = []
for r in cand.itertuples():
    a, b = ent_comps.get(r.unresolved_entity, set()), ent_comps.get(r.resolved_entity, set())
    if a & b:
        equal_compact = compact(names.get(r.unresolved_entity, "")) == compact(names.get(r.resolved_entity, "")) and compact(names.get(r.unresolved_entity, "")) != ""
        susp.add(r.unresolved_entity)                       # the unresolved entity always carries a partial history
        if equal_compact:
            susp.add(r.resolved_entity)                     # identical after punctuation/space removal: same club written twice
        sus_rows.append(dict(entity_unresolved=r.unresolved_entity, entity_resolved=r.resolved_entity, shared_competitions="|".join(sorted(a & b)),
                             names_equal_after_removing_punctuation=equal_compact, flagged="unresolved entity" + (" + resolved twin" if equal_compact else "")))
pd.DataFrame(sus_rows).to_csv(os.path.join(OUT, "identity_same_league_split_suspects.csv"), index=False, encoding=ENC)
D["identity_review_flag"] = D.home_entity_id.isin(susp) | D.away_entity_id.isin(susp) | D.identity_unmerged

# ------------------------------------------------------------------ splits and evaluation flags
D["split"] = D.match_date.map(split_of)
D["calendar_type"] = np.where(D.season_corrected.str.contains("-"), "split_year (Aug-May style)", "calendar_year")
st_ok = D.season_status.isin(["complete", "in_progress_complete_through_cutoff"])
non_train = D.split != "train"
D["eval_primary"] = non_train & st_ok & ~D.identity_review_flag & D.calendar_type.str.startswith("split") & D.eligible_final
D["eval_secondary_calendar_year"] = non_train & st_ok & ~D.identity_review_flag & D.calendar_type.eq("calendar_year") & D.eligible_final
D["season_incomplete_flag"] = ~st_ok
D["home_goals_90"], D["away_goals_90"] = D.gh, D.ga
D["y_90min_1x2"] = np.where(D.gh > D.ga, "H", np.where(D.gh < D.ga, "A", "D"))

# ------------------------------------------------------------------ row-level disposition log
disp = M[["record_id", "source_file", "source_line", "competition_id", "competition_type", "season_original", "season_corrected", "match_date", "home_team_name", "away_team_name", "match_status", "reason"]].copy()
disp["season_label_status"] = M.label_verdict
disp["season_label_evidence"] = M.label_evidence
disp["date_status"] = M.date_status
info = V.set_index("record_id")
dd = D.set_index("record_id")
M_corr = dict(zip(M.record_id, M.season_was_corrected))
final = []
corr = []
for r in disp.itertuples():
    if r.reason:
        final.append("EXCLUDED_" + r.reason if not r.reason.startswith(("EXCLUDED", "REMOVED")) else r.reason)
        corr.append("")
        continue
    v = info.loc[r.record_id]
    if r.record_id in dd.index:
        d_ = dd.loc[r.record_id]
        if not d_.enough_history:
            final.append("EXCLUDED_INSUFFICIENT_HISTORY_LT5_PRIOR_RATED_MATCHES")
        elif not d_.pair_connected_asof:
            final.append("EXCLUDED_ELO_PAIR_NOT_CONNECTED_ASOF")
        else:
            final.append("INCLUDED_" + d_.split.upper())
        corr.append("SEASON_LABEL_CORRECTED" if M_corr.get(r.record_id, False) else "")
    else:
        if v.competition_type != "domestic_league":
            final.append("EXCLUDED_OUT_OF_SCOPE_NOT_DOMESTIC_LEAGUE")
        elif v.phase != "league":
            final.append("EXCLUDED_OUT_OF_SCOPE_STAGE_NOT_REGULAR_ROUND_ROBIN")
        elif v.extra_time_played != "no" or pd.notna(v.pen_home):
            final.append("EXCLUDED_ET_OR_PENALTY_MARKER_IN_REGULAR_ROUND")
        elif v.label_90_status != "confirmed":
            final.append("EXCLUDED_LABEL_NOT_CONFIRMED_" + v.label_90_status.upper())
        elif v.match_date < TRAIN_START:
            final.append("USED_ONLY_FOR_RATING_STATE_BEFORE_2018_08_01")
        else:
            final.append("EXCLUDED_OTHER")
        corr.append("SEASON_LABEL_CORRECTED" if M_corr.get(r.record_id, False) else "")
disp["disposition"] = final
disp["correction"] = corr
disp = disp.drop(columns=["reason"])
disp["dataset_version"] = VERSION
disp.to_csv(os.path.join(OUT, "03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv"), index=False, encoding=ENC)
print(disp.disposition.value_counts().to_string())

# ------------------------------------------------------------------ write deliverables 1 and 2
E = D[D.eligible_final].sort_values(["match_date", "competition_id", "record_id"]).reset_index(drop=True)
ds_cols = ["record_id", "competition_id", "competition_name", "competition_country", "tier", "season_original", "season_corrected", "calendar_type", "match_date", "kickoff_time_local",
           "home_entity_id", "home_team_name", "home_identity_status", "away_entity_id", "away_team_name", "away_identity_status", "home_goals_90", "away_goals_90", "y_90min_1x2",
           "label_90_status", "reg_basis", "split", "season_status", "eval_primary", "eval_secondary_calendar_year", "season_incomplete_flag", "identity_review_flag",
           "source_license", "provenance"]
ds = E[ds_cols].copy()
ds["season_label_corrected_flag"] = E.season_was_corrected.values
ds["extraction_date"] = EXTRACTION
ds["dataset_version"] = VERSION
ds.to_csv(os.path.join(OUT, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), index=False, encoding=ENC)
fe = E[["record_id", "split"] + fc.FEATURE_ORDER + ["y_90min_1x2", "latest_info_date", "pair_connected_asof"]].rename(columns={"latest_info_date": "meta_latest_info_date", "pair_connected_asof": "meta_pair_connected_asof"})
fe["dataset_version"] = VERSION
fe.to_csv(os.path.join(OUT, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), index=False, encoding=ENC)
V.to_pickle(os.path.join(WORK, "V_universe.pkl"))
E.to_pickle(os.path.join(WORK, "E_final.pkl"))
print("final eligible:", len(E), E.split.value_counts().to_dict(), "primary eval:", int(E.eval_primary.sum()), "secondary:", int(E.eval_secondary_calendar_year.sum()))
summ = dict(universe_results=len(V), in_scope=int(V.in_scope.sum()), final=len(E), by_split=E.split.value_counts().to_dict(),
            eval_primary=E[E.eval_primary].split.value_counts().to_dict(), eval_secondary=E[E.eval_secondary_calendar_year].split.value_counts().to_dict(),
            season_labels_corrected_rows_in_final=int(ds.season_label_corrected_flag.sum()))
json.dump(summ, open(os.path.join(WORK, "build_summary.json"), "w"), indent=1, default=str)
print(summ)
