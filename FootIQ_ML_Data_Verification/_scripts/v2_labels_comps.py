"""Stage 2 (read-only): 90-minute label audit, competition-season verification, UEFA recoveries, team identity."""
import json
import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
ENC = "utf-8-sig"
RAWS = os.path.join(SUB, "_raw_sources")
sys.path.insert(0, os.path.join(SUB, "_build"))
import build_club_matches as bcm  # noqa: E402  (only its describe() registry is used)

d = pd.read_csv(os.path.join(RDY, "04d_COMBINED_CLUB_MATCHES_v1.0.csv"), low_memory=False, encoding=ENC)
strict = pd.read_csv(os.path.join(RDY, "08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv"), low_memory=False, encoding=ENC, usecols=["record_id", "label_90_status", "label_outcome_90min_1x2", "competition_type", "match_date", "suggested_split"])
ext = pd.read_csv(os.path.join(RDY, "08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv"), low_memory=False, encoding=ENC, usecols=["record_id", "label_90_status", "label_outcome_90min_1x2", "competition_type", "match_date", "suggested_split"])
wp = pd.read_csv(os.path.join(RDY, "_build", "work", "wp_matches.csv"), low_memory=False)
res = {}
issues = []


def issue(sev, ds, ev, impact, fix):
    issues.append(dict(severity=sev, affected_dataset=ds, evidence=ev, impact_on_training=impact, recommended_action=fix))


# ======================================================================= LABELS
L = {}
L["strict_rows"], L["extended_rows"] = len(strict), len(ext)
L["strict_status_values"] = strict.label_90_status.value_counts().to_dict()
L["extended_status_values"] = ext.label_90_status.value_counts().to_dict()
L["strict_subset_of_extended"] = bool(set(strict.record_id) <= set(ext.record_id))
L["extended_minus_strict"] = int(len(set(ext.record_id) - set(strict.record_id)))
L["extra_rows_all_inferred"] = bool(ext[~ext.record_id.isin(strict.record_id)].label_90_status.eq("inferred_no_marker").all())
L["strict_ids_in_04d"] = bool(set(strict.record_id) <= set(d.record_id))

# independent re-derivation of the outcome from the score fields
def cmp(a, b):
    return np.where(a > b, "H", np.where(a < b, "A", "D"))


dd = d.copy()
reg_known = dd.regulation_score_home.notna() & dd.regulation_score_away.notna()
fin_known = dd.final_score_home_excl_penalties.notna()
y_reg = np.where(reg_known, cmp(dd.regulation_score_home, dd.regulation_score_away), "")
y_fin = np.where(fin_known, cmp(dd.final_score_home_excl_penalties, dd.final_score_away_excl_penalties), "")
lab_ok = dd.label_90_status.isin(["confirmed", "inferred_no_marker"])
exp_y = np.where(reg_known, y_reg, y_fin)
L["rows_with_label_status_confirmed_or_inferred"] = int(lab_ok.sum())
L["outcome_mismatch_vs_recomputed"] = int((lab_ok & (dd.outcome_90min_1x2.fillna("") != exp_y)).sum())
L["outcome_present_without_label_status"] = int((~lab_ok & dd.outcome_90min_1x2.fillna("").ne("")).sum())
L["label_status_without_outcome"] = int((lab_ok & dd.outcome_90min_1x2.fillna("").eq("")).sum())

# phase
phase = []
for t, s in zip(dd.competition_type, dd.stage.fillna("")):
    if t == "domestic_league":
        phase.append("knockout" if re.search(r"play-?off", s, re.I) else "league")
    elif t in ("domestic_cup", "league_cup"):
        phase.append("knockout")
    else:
        phase.append("league_phase" if re.search(r"league, matchday|group|matchday|league phase", s, re.I) and not re.search(r"knockout|play-?off|round of|final|quarter|semi", s, re.I) else "knockout")
dd["phase"] = phase
ko = dd[dd.phase == "knockout"]
# strict set: knockout rows with regulation not stated?
sk = dd[dd.record_id.isin(strict.record_id)]
L["strict_knockout_rows"] = int((sk.phase == "knockout").sum())
L["strict_knockout_with_reg_basis"] = sk[sk.phase == "knockout"].reg_basis.value_counts().to_dict()
L["strict_rows_where_regulation_missing_and_not_league_phase"] = int((sk.regulation_score_home.isna() & (sk.phase == "knockout")).sum())
L["strict_rows_extra_time_yes"] = int((sk.extra_time_played == "yes").sum())
L["strict_rows_with_penalties"] = int(sk.pen_home.notna().sum())
# strict rows with penalties: 90-min result must be a draw at the stated regulation score
pk = sk[sk.pen_home.notna()]
L["strict_penalty_rows_where_90min_outcome_is_not_draw"] = int((pk.outcome_90min_1x2 != "D").sum())
L["strict_penalty_rows_where_label_equals_shootout_winner_but_not_draw"] = 0
# ET rows: regulation vs final
et = sk[sk.extra_time_played == "yes"]
L["strict_extra_time_rows_regulation_equals_final"] = int(((et.regulation_score_home == et.final_score_home_excl_penalties) & (et.regulation_score_away == et.final_score_away_excl_penalties)).sum())
L["strict_extra_time_rows_regulation_not_draw"] = int((et.outcome_90min_1x2 != "D").sum())
L["strict_extra_time_rows"] = len(et)
# inferred labels never classified confirmed: raw check (openfootball rows)
ofrows = dd[dd.source_system == "openfootball"].copy()
m = ofrows.provenance.str.extract(r"\s(\S+\.txt):L(\d+)$")
ofrows["raw_file"], ofrows["raw_line"] = m[0], pd.to_numeric(m[1])
cache = {}


def raw_line(f, ln):
    if f not in cache:
        cache[f] = open(os.path.join(RAWS, f), encoding="utf-8").read().splitlines()
    return cache[f][ln - 1]


inf = ofrows[ofrows.label_90_status == "inferred_no_marker"]
bad_inf = 0
bad_examples = []
for r in inf.itertuples():
    t = raw_line(r.raw_file, int(r.raw_line))
    if re.search(r"a\.e\.t\.|pen\.", t):
        bad_inf += 1
        bad_examples.append((r.record_id, t))
L["inferred_openfootball_rows"] = len(inf)
L["inferred_rows_whose_raw_line_contains_aet_or_pen_marker"] = bad_inf
conf_ko = ofrows[(ofrows.label_90_status == "confirmed")]
cko = conf_ko[[p == "knockout" for p in dd.loc[conf_ko.index, "phase"]]]
nb = 0
ex_rows = []
for r in cko.itertuples():
    t = raw_line(r.raw_file, int(r.raw_line))
    has_marker = bool(re.search(r"a\.e\.t\.|pen\.", t))
    two = bool(re.search(r"\(\s*\d+-\d+\s*,\s*\d+-\d+\s*\)", t)) or r.reg_basis != "source_bracket_regulation_score_with_aet_marker"
    if r.reg_basis == "source_bracket_regulation_score_with_aet_marker" and not (has_marker and two):
        # 0-0 a.e.t. (0-0) is derivable; accept it
        if not re.search(r"0-0 a\.e\.t\.", t):
            nb += 1
            ex_rows.append((r.record_id, t))
L["confirmed_knockout_openfootball_rows"] = len(cko)
L["confirmed_bracket_rows_failing_raw_check"] = nb
# Wikipedia rows: recompute regulation from stored goal minutes
wpr = dd[dd.source_system == "wikipedia"].copy()
wpr["page_revid"] = wpr.record_id.str.extract(r"WP:(\d+):")[0].astype(float)
wpr["offset"] = wpr.record_id.str.extract(r"WP:\d+:(\d+)")[0].astype(float)
w2 = wp.copy()
w2["key"] = w2.page_revid.astype(float).astype(int).astype(str) + ":" + w2.offset.astype(int).astype(str)
wpr["key"] = wpr.page_revid.astype(int).astype(str) + ":" + wpr.offset.astype(int).astype(str)
wj = wpr.merge(w2[["key", "goals1_min", "goals2_min", "s1", "s2", "aet_flag", "pen1", "reg_basis"]], on="key", how="left", suffixes=("", "_wp"))
bad_w = 0
conf_w = wj[wj.label_90_status == "confirmed"]
for r in conf_w.itertuples():
    if r.reg_basis_wp == "derived_from_goal_minutes":
        g1 = [g for g in json.loads(r.goals1_min) if g[0] <= 90]
        g2 = [g for g in json.loads(r.goals2_min) if g[0] <= 90]
        if (len(g1), len(g2)) != (r.regulation_score_home, r.regulation_score_away):
            bad_w += 1
L["wikipedia_confirmed_rows"] = len(conf_w)
L["wikipedia_confirmed_rows_goal_minute_recompute_mismatch"] = bad_w
# status crosstab
L["status_by_match_status"] = dd.groupby(["match_status", "label_90_status"]).size().reset_index(name="n").to_dict("records")
# breakdown
bd = dd.groupby(["competition_id", "competition_name", "competition_type", "season", "label_90_status"]).size().unstack(fill_value=0).reset_index()
bd.to_csv(os.path.join(EV, "label_breakdown_by_competition_season.csv"), index=False)
# selection bias
sel = []
for ph in ("league", "league_phase", "knockout"):
    a = dd[dd.phase == ph]
    for nm, subset in (("all_results", a), ("strict", a[a.record_id.isin(strict.record_id)]), ("extended", a[a.record_id.isin(ext.record_id)])):
        y = subset.outcome_90min_1x2.fillna("")
        y = y[y != ""]
        sel.append(dict(phase=ph, set=nm, n=len(subset), labelled=len(y), draw_rate=round((y == "D").mean(), 4) if len(y) else None,
                        home_rate=round((y == "H").mean(), 4) if len(y) else None))
selb = pd.DataFrame(sel)
selb.to_csv(os.path.join(EV, "label_selection_bias.csv"), index=False)
kod = dd[(dd.phase == "knockout") & dd.decided_in.eq("x")] if "decided_in" in dd else None
ko_unknown = dd[(dd.phase == "knockout") & (dd.label_90_status == "unknown")]
L["knockout_rows_unknown_label"] = len(ko_unknown)
L["knockout_unknown_with_penalties"] = int(ko_unknown.pen_home.notna().sum())
# reproducible manual sample: ET / penalty / plain knockout
rng = np.random.default_rng(20261020)
samp = []
for nm, sub in (("penalties", ko[ko.pen_home.notna()]), ("extra_time_no_pens", ko[(ko.extra_time_played == "yes") & ko.pen_home.isna()]),
                ("plain_knockout", ko[(ko.extra_time_played == "no")])):
    take = sub.sample(min(12, len(sub)), random_state=20261020)
    for r in take.itertuples():
        raw = ""
        if r.source_system == "openfootball":
            mm = re.search(r"\s(\S+\.txt):L(\d+)$", r.provenance)
            raw = raw_line(mm.group(1), int(mm.group(2))).strip()
        samp.append(dict(group=nm, record_id=r.record_id, competition=r.competition_name, season=r.season, date=r.match_date, home=r.home_team_name,
                         away=r.away_team_name, final_excl_pens=f"{r.final_score_home_excl_penalties}-{r.final_score_away_excl_penalties}",
                         regulation=f"{r.regulation_score_home}-{r.regulation_score_away}", pens=f"{r.pen_home}-{r.pen_away}",
                         label_status=r.label_90_status, outcome90=r.outcome_90min_1x2, raw_source_line=raw, reg_basis=r.reg_basis))
pd.DataFrame(samp).to_csv(os.path.join(EV, "label_manual_sample.csv"), index=False)
res["labels"] = L
print(json.dumps(L, indent=0, default=str)[:3000])

# ======================================================================= INTERNATIONAL
i1 = pd.read_csv(os.path.join(SUB, "01_Historical_International_Matches.csv"), low_memory=False, encoding=ENC)
i3 = pd.read_csv(os.path.join(SUB, "03_Recent_Match_Results.csv"), low_memory=False, encoding=ENC)
i3 = i3[i3.record_scope == "international"]
IN = {}
IN["shootout_matches"] = int(i1.decided_by_penalty_shootout.sum())
IN["rows_total"] = len(i1)
IN["score_basis_values"] = i1.score_basis.value_counts().to_dict()
IN["regulation_score_columns_present"] = [c for c in i1.columns if "regulation" in c]
# World Cup editions
wcexp = {1930: 18, 1934: 17, 1938: 18, 1950: 22, 1954: 26, 1958: 35, 1962: 32, 1966: 32, 1970: 32, 1974: 38, 1978: 38, 1982: 52, 1986: 52, 1990: 52,
         1994: 52, 1998: 64, 2002: 64, 2006: 64, 2010: 64, 2014: 64, 2018: 64, 2022: 64, 2026: 104}
iall = pd.concat([i1.rename(columns={"tournament": "tournament"}), i3.rename(columns={"competition_name": "tournament"})], ignore_index=True, sort=False)
iall["year"] = iall.match_date.str[:4].astype(int)
iall["matchkey"] = iall.match_date + "|" + iall.home_team + "|" + iall.away_team
wc = iall[iall.tournament == "FIFA World Cup"]
wcrows = []
for y, e in wcexp.items():
    n = len(wc[wc.year == y])
    wcrows.append(dict(competition_id="INTL:fifa-world-cup", competition_name="FIFA World Cup", season=str(y), expected_matches=e, expected_evidence="FIFA tournament formats (matches played per edition)",
                       verified_scores=n, dup=int(wc[wc.year == y].duplicated("matchkey").sum()), latest=wc[wc.year == y].match_date.max()))
CONT = {("UEFA Euro", 2016): 51, ("UEFA Euro", 2020): 51, ("UEFA Euro", 2024): 51, ("Copa América", 2019): 26, ("Copa América", 2021): 28, ("Copa América", 2024): 32,
        ("African Cup of Nations", 2019): 52, ("African Cup of Nations", 2021): 52, ("African Cup of Nations", 2023): 52, ("AFC Asian Cup", 2019): 51, ("AFC Asian Cup", 2023): 51}
for (t, y), e in CONT.items():
    sub = iall[(iall.tournament == t) & (iall.year == y)]
    wcrows.append(dict(competition_id="INTL:" + t.lower().replace(" ", "-"), competition_name=t, season=str(y), expected_matches=e,
                       expected_evidence="tournament format (matches played)", verified_scores=len(sub), dup=int(sub.duplicated("matchkey").sum()), latest=sub.match_date.max()))
pd.DataFrame(wcrows).to_csv(os.path.join(EV, "international_edition_checks.csv"), index=False)
IN["edition_mismatches"] = [r for r in wcrows if r["expected_matches"] != r["verified_scores"]]
IN["friendly_rows"] = int((i1.competition_category == "friendly").sum())
IN["rows_by_category"] = i1.competition_category.value_counts().to_dict()
res["international"] = IN
cat = i1.groupby("competition_category").agg(n=("match_id", "size"), shootouts=("decided_by_penalty_shootout", "sum")).reset_index()
cat.to_csv(os.path.join(EV, "international_category_counts.csv"), index=False)
print(IN["edition_mismatches"][:25])
if bad_inf:
    issue("High", "08 extended / 04d", f"{bad_inf} 'inferred' openfootball rows contain an a.e.t./pen. marker in the raw line", "mis-labelled 90-minute outcomes", "reclassify as unknown")
json.dump(res, open(os.path.join(EV, "v2_part1.json"), "w"), indent=1, default=str)
json.dump(issues, open(os.path.join(EV, "v2_issues_part1.json"), "w"), indent=1, default=str)
