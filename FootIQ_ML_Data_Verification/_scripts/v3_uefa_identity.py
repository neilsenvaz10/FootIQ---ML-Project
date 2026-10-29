"""Stage 3 (read-only): UEFA recovery tests and team identity audit."""
import sys as _s; _s.stdout.reconfigure(encoding="utf-8")
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

import numpy as np
import pandas as pd

P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
ENC = "utf-8-sig"
D = "\u2013"
wp = pd.read_csv(os.path.join(RDY, "_build", "work", "wp_matches.csv"), low_memory=False)
cache = {}
for f in os.listdir(os.path.join(RDY, "raw_external", "wikipedia")):
    j = json.load(open(os.path.join(RDY, "raw_external", "wikipedia", f), encoding="utf-8"))
    if not j.get("missing"):
        cache[j["title"]] = j
R = {}

# ======================================================================= UEFA tests
def uefa_tests(comp, season):
    g = wp[(wp.competition == comp) & (wp.season == season)].copy()
    t = {"competition": comp, "season": season, "rows": len(g)}
    key = g.date.astype(str) + "|" + g.t1_target.fillna(g.t1_display) + "|" + g.t2_target.fillna(g.t2_display)
    t["duplicate_rows_by_date_teams"] = int(key.duplicated().sum())
    t["date_min"], t["date_max"] = g.date.min(), g.date.max()
    t["rows_without_score"] = int(g.s1.isna().sum())
    t["rows_without_date"] = int(g.date.isna().sum())
    t["pens_but_unequal_final_score"] = int(((g.pen1.notna()) & (g.s1 != g.s2)).sum())
    t["goal_lists_consistent_pct"] = round(100 * g.goals_list_consistent.mean(), 1)
    t["stage_counts"] = g.stage_path.str.replace(r" > Matches$", "", regex=True).value_counts().to_dict()
    lp = g[g.stage_path.str.contains("Matchday|Group", case=False, regex=True)]
    if len(lp):
        teams = pd.concat([lp.t1_target.fillna(lp.t1_display), lp.t2_target.fillna(lp.t2_display)])
        per_team = teams.value_counts()
        t["league_phase_teams"] = int(len(per_team))
        t["league_phase_matches_per_team_distribution"] = per_team.value_counts().to_dict()
        home = lp.t1_target.fillna(lp.t1_display).value_counts()
        t["league_phase_home_games_distribution"] = home.value_counts().to_dict()
    # aggregate notes versus computed aggregates
    ko = g[~g.stage_path.str.contains("Matchday|Group", case=False, regex=True)]
    notes = []
    for title in g.page_title.unique():
        w = cache.get(title, {}).get("wikitext", "")
        for m in re.finditer(r"''([^'\n]+?) won (\d+)\s*[\u2013\u2212-]\s*(\d+) on aggregate", w):
            notes.append((m.group(1).strip(), int(m.group(2)), int(m.group(3))))
    t["aggregate_notes_found"] = len(notes)
    ties = defaultdict(lambda: defaultdict(int))
    for r in ko.itertuples():
        a, b = r.t1_display, r.t2_display
        k = tuple(sorted([a, b])) + (r.stage_path.split(" > ")[0],)
        ties[k][a] += int(r.s1)
        ties[k][b] += int(r.s2)
    ok = bad = 0
    bad_list = []
    for who, hi, lo in notes:
        found = False
        for k, v in ties.items():
            vals = sorted(v.values(), reverse=True)
            if len(v) == 2 and vals == sorted([hi, lo], reverse=True):
                found = True
                break
        if found:
            ok += 1
        else:
            bad += 1
            bad_list.append(f"{who} {hi}-{lo}")
    t["aggregate_notes_matching_computed_ties"] = ok
    t["aggregate_notes_not_matching"] = bad
    t["aggregate_mismatch_examples"] = bad_list[:6]
    return t


tests = [uefa_tests(c, s) for c, s in (("UEFA Europa League", "2025-26"), ("UEFA Conference League", "2025-26"),
                                       ("UEFA Europa League", "2018-19"), ("UEFA Europa League", "2019-20"),
                                       ("UEFA Europa League", "2024-25"), ("UEFA Conference League", "2024-25"), ("UEFA Champions League", "2025-26"))]
R["uefa_tests"] = tests
xv = pd.read_csv(os.path.join(RDY, "_build", "work", "cross_validation_pairs.csv"))
xs = xv[xv.competition.isin(["UEFA Europa League", "UEFA Conference League", "UEFA Champions League"])]
R["uefa_cross_validation"] = xs.groupby(["competition", "season"]).kind.value_counts().unstack(fill_value=0).reset_index().to_dict("records")
R["cross_validation_all"] = xv.kind.value_counts().to_dict()
R["cross_validation_date_not_equal"] = int((~xv.date_equal.fillna(True)).sum()) if "date_equal" in xv else None
R["cross_validation_pen_disagree"] = int((~xv.pen_agree.fillna(True)).sum())
R["cross_validation_reg_disagree"] = int((xv.reg_agree == False).sum())
print(json.dumps(R["uefa_cross_validation"], default=str)[:800])
for t in tests:
    print({k: v for k, v in t.items() if k not in ("stage_counts",)})

# ======================================================================= IDENTITY
def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


im = pd.read_csv(os.path.join(RDY, "05_CANONICAL_TEAM_IDENTITY_MAPPING.csv"), low_memory=False, encoding=ENC)
d = pd.read_csv(os.path.join(RDY, "04d_COMBINED_CLUB_MATCHES_v1.0.csv"), low_memory=False, encoding=ENC)
ent = pd.concat([d[["home_entity_id", "home_team_name", "home_identity_status", "competition_type", "competition_id"]].set_axis(["e", "name", "st", "ct", "cid"], axis=1),
                 d[["away_entity_id", "away_team_name", "away_identity_status", "competition_type", "competition_id"]].set_axis(["e", "name", "st", "ct", "cid"], axis=1)])
I = {}
I["mapping_rows"] = len(im)
I["mapping_status"] = im.resolution_status.value_counts().to_dict()
I["mapping_duplicate_keys"] = int(im.duplicated(["source_system", "source_team_key", "country_folder"]).sum())
I["entities_in_04d"] = int(ent.e.nunique())
I["entities_resolved_to_canonical"] = int(ent[ent.e.str.startswith("CLUB:")].e.nunique())
I["entities_unresolved"] = int(ent[~ent.e.str.startswith("CLUB:")].e.nunique())
I["match_sides_with_unresolved_entity"] = int((~ent.e.str.startswith("CLUB:")).sum())
I["match_sides_total"] = len(ent)
I["unresolved_share_by_competition_type"] = ent.assign(un=~ent.e.str.startswith("CLUB:")).groupby("ct").un.mean().round(3).to_dict()
# same name key, different entity ids
ent["country"] = ent.e.map(lambda x: x.split(":")[1] if x.startswith("CLUB:") else (x.split("|")[0] if "|" in x else (x.split(":")[1] if x.startswith("WP:") else "?")))
ent["nk"] = ent.name.map(norm)
grp = ent.groupby(["nk"]).e.nunique()
multi = grp[grp > 1].index
dupgrp = ent[ent.nk.isin(multi)].groupby("nk").agg(entity_ids=("e", lambda s: sorted(set(s))), countries=("country", lambda s: sorted(set(s))), matches=("e", "size")).reset_index()
dupgrp["n_ids"] = dupgrp.entity_ids.map(len)
dupgrp["entity_ids"] = dupgrp.entity_ids.map(lambda v: " | ".join(v))
dupgrp["countries"] = dupgrp.countries.map(lambda v: ";".join(v))
dupgrp.to_csv(os.path.join(EV, "identity_same_name_multiple_ids.csv"), index=False)
I["same_normalised_name_multiple_entity_ids_groups"] = len(dupgrp)
I["matches_touching_those_groups"] = int(dupgrp.matches.sum())
# token-overlap split candidates (report only): unresolved entity vs resolved entity, same country code
GEN = {"fc", "cf", "sc", "ac", "afc", "fk", "sk", "club", "de", "the", "of", "sv", "cd", "ud", "united", "city"}


def toks(s):
    return set(norm(s).split()) - GEN


res_ent = ent[ent.e.str.startswith("CLUB:")].drop_duplicates("e")[["e", "name", "country"]]
unres = ent[~ent.e.str.startswith("CLUB:")].drop_duplicates("e")[["e", "name", "country", "ct"]]
cand = []
byc = res_ent.groupby("country")
cc_map = {"ENG": "ENG", "ESP": "ESP", "GER": "GER", "ITA": "ITA", "FRA": "FRA"}
for u in unres.itertuples():
    cn = u.country if u.country in dict(res_ent.country.value_counts()) else None
    pool = byc.get_group(cn) if cn else res_ent
    tu = toks(u.name)
    if not tu:
        continue
    for r in pool.itertuples():
        tr = toks(r.name)
        if tr and len(tu & tr) / len(tu | tr) >= 0.6:
            cand.append(dict(unresolved_entity=u.e, unresolved_name=u.name, resolved_entity=r.e, resolved_name=r.name, jaccard=round(len(tu & tr) / len(tu | tr), 2)))
cd = pd.DataFrame(cand).drop_duplicates()
cd.to_csv(os.path.join(EV, "identity_possible_split_candidates_NOT_MERGED.csv"), index=False)
I["possible_split_candidates_unresolved_vs_resolved"] = len(cd)
# possible wrong merges: canonical with very different source names
res = im[im.resolution_status == "resolved_exact_alias"]
chk = res.groupby("canonical_team_id").source_team_name.agg(lambda s: sorted(set(s)))
wm = []
for cid, names in chk.items():
    if len(names) > 1:
        tk = [toks(n) for n in names]
        mn = min((len(a & b) / len(a | b) if (a | b) else 1) for i, a in enumerate(tk) for b in tk[i + 1:])
        if mn < 0.34:
            wm.append(dict(canonical=cid, source_names=" | ".join(names), min_token_jaccard=round(mn, 2)))
pd.DataFrame(wm).to_csv(os.path.join(EV, "identity_possible_wrong_merges_review.csv"), index=False)
I["canonical_ids_with_dissimilar_source_names_for_review"] = len(wm)
# reserve teams
I["canonical_reserve_teams_used"] = int(res.canonical_name.str.contains(r"\b(B|II|U2[0-3]|Jong|Reserves?)\b", regex=True).sum())
# Monaco / Welsh
focus = ["AS Monaco", "Monaco", "Cardiff City", "Swansea City", "Wrexham", "Newport County", "Merthyr", "Barry Town", "The New Saints", "Bala Town"]
mrows = []
for f in focus:
    x = d[(d.home_team_name.str.contains(f, case=False, na=False)) | (d.away_team_name.str.contains(f, case=False, na=False))]
    if len(x):
        ids = pd.concat([x[x.home_team_name.str.contains(f, case=False, na=False)].home_entity_id, x[x.away_team_name.str.contains(f, case=False, na=False)].away_entity_id])
        names = pd.concat([x[x.home_team_name.str.contains(f, case=False, na=False)].home_team_name, x[x.away_team_name.str.contains(f, case=False, na=False)].away_team_name])
        mrows.append(dict(search=f, entity_ids=" | ".join(sorted(set(ids))), names=" | ".join(sorted(set(names))), competitions=" | ".join(sorted(set(x.competition_id))[:8]), matches=len(x),
                          seasons=f"{x.season.min()}..{x.season.max()}"))
pd.DataFrame(mrows).to_csv(os.path.join(EV, "identity_cross_border_focus.csv"), index=False)
I["cross_border_focus"] = mrows
print(json.dumps({k: v for k, v in I.items() if k != "cross_border_focus"}, indent=0, default=str)[:2500])
for r in mrows:
    print(r)
# national teams: former names
fn = pd.read_csv(os.path.join(SUB, "_raw_sources", "martj42_refresh", "former_names.csv"))
i1 = pd.read_csv(os.path.join(SUB, "01_Historical_International_Matches.csv"), low_memory=False, encoding=ENC, usecols=["match_date", "home_team", "away_team"])
names = pd.concat([i1[["match_date", "home_team"]].rename(columns={"home_team": "t"}), i1[["match_date", "away_team"]].rename(columns={"away_team": "t"})])
fr = []
for r in fn.itertuples():
    cur = names[names.t == r.current]
    fo = names[names.t == r.former]
    fr.append(dict(current=r.current, former=r.former, start=r.start_date, end=r.end_date, rows_under_current_name=len(cur), rows_under_former_name=len(fo),
                   current_rows_before_start=int((cur.match_date < r.start_date).sum()), former_rows_after_end=int((fo.match_date > r.end_date).sum())))
frd = pd.DataFrame(fr)
frd.to_csv(os.path.join(EV, "national_team_former_names_check.csv"), index=False)
I["national_teams_with_rows_under_both_current_and_former"] = int(((frd.rows_under_current_name > 0) & (frd.rows_under_former_name > 0)).sum())
I["national_team_name_ids_in_01"] = int(names.t.nunique())
R["identity"] = I
json.dump(R, open(os.path.join(EV, "v3_results.json"), "w"), indent=1, default=str)
