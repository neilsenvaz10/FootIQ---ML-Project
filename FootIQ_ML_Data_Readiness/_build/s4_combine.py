"""Combine the original openfootball club matches with Wikipedia gap-fills; resolve club identities; write
universe.csv (all usable matches, unified schema) and the team identity map."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
import identity as I  # noqa

CUP_COUNTRY = {"FA Cup": "england", "EFL Cup": "england", "Copa del Rey": "spain", "Coppa Italia": "italy",
               "Coupe de France": "france", "DFB-Pokal": "germany"}
FAM_BY_COMP = {k: v[0] for k, v in FAMILY.items()}

index, canon = I.load_clubs()

# ------------------------------------------------------------------ openfootball (original submission)
of = pd.read_csv(os.path.join(SUBWORK, "club_matches_all.csv"), low_memory=False, keep_default_na=False, na_values=[""])
for c in ["home_goals_regulation", "away_goals_regulation", "home_goals_after_extra_time", "away_goals_after_extra_time",
          "home_penalties", "away_penalties", "home_goals_halftime", "away_goals_halftime"]:
    of[c] = pd.to_numeric(of[c], errors="coerce")


def of_folder(ns, code):
    if isinstance(code, str) and code:
        return I.CODE2FOLDER.get(code)
    if ns.startswith("europe/"):
        return ns.split("/")[1]
    return I.NS2FOLDER.get(ns)


of["ns"] = of.competition_id.str.split(":").str[0]
tm = []
for side in ("home", "away"):
    x = of[[f"{side}_team_id", f"{side}_team", f"{side}_team_country_code", "ns"]].copy()
    x.columns = ["tid", "name", "code", "ns"]
    tm.append(x)
tm = pd.concat(tm)
tm["folder"] = [of_folder(n, c) for n, c in zip(tm.ns, tm.code)]
tm = tm.drop_duplicates(["tid", "folder"])
ident = {}
rows_map = []
for r in tm.itertuples():
    cid, st = I.resolve(index, r.folder, r.name)
    ident[(r.tid, r.folder)] = (cid, st)
    rows_map.append(dict(source_system="openfootball", source_team_key=r.tid, source_team_name=r.name,
                         country_folder=r.folder, country_code=I.FOLDER2CODE.get(r.folder, ""),
                         canonical_team_id=cid, resolution_status=st,
                         canonical_name=canon[cid]["canonical_name"] if cid else "",
                         evidence=canon[cid]["source_file"] + f":L{canon[cid]['source_line']}" if cid else ""))

# ------------------------------------------------------------------ Wikipedia
wp = pd.read_csv(os.path.join(WORK, "wp_matches.csv"), low_memory=False)
wp["family"] = wp.competition
wp["cup_folder"] = wp.competition.map(CUP_COUNTRY)


def wp_target_map(df):
    m = {}
    for t, d, c in zip(df.t1_target.tolist() + df.t2_target.tolist(), df.t1_display.tolist() + df.t2_display.tolist(),
                       df.t1_code.tolist() + df.t2_code.tolist()):
        if isinstance(t, str):
            m.setdefault((d, c), t)
    return m


tmap = wp_target_map(wp)
wp_ident = {}
for side in ("t1", "t2"):
    for disp, tgt, code, cupf in zip(wp[f"{side}_display"], wp[f"{side}_target"], wp[f"{side}_code"], wp.cup_folder):
        if not isinstance(tgt, str):
            tgt = tmap.get((disp, code))
        folder = I.CODE2FOLDER.get(code) if isinstance(code, str) else cupf
        key = (code if isinstance(code, str) else cupf, tgt or disp)
        if key in wp_ident:
            continue
        cands = []
        for nm in (tgt, disp):
            if isinstance(nm, str):
                cands.append(I.resolve(index, folder, nm))
        ok = {c[0] for c in cands if c[0]}
        if len(ok) == 1:
            cid, st = next(iter(ok)), "resolved_exact_alias"
        elif len(ok) > 1:
            cid, st = None, "ambiguous_multiple_clubs"
        else:
            cid, st = None, (cands[0][1] if cands else "no_alias_match")
        wp_ident[key] = (cid, st, tgt, disp, folder)
        rows_map.append(dict(source_system="wikipedia", source_team_key=f"WP:{key[0]}:{key[1]}", source_team_name=tgt or disp,
                             country_folder=folder, country_code=I.FOLDER2CODE.get(folder, ""), canonical_team_id=cid,
                             resolution_status=st, canonical_name=canon[cid]["canonical_name"] if cid else "",
                             evidence=canon[cid]["source_file"] + f":L{canon[cid]['source_line']}" if cid else ""))


def wp_entity(disp, tgt, code, cupf):
    if not isinstance(tgt, str):
        tgt = tmap.get((disp, code))
    key = (code if isinstance(code, str) else cupf, tgt or disp)
    cid, st, _, _, _ = wp_ident[key]
    return (cid or f"WP:{key[0]}:{key[1]}"), st, (tgt or disp)


# ------------------------------------------------------------------ unified schema
def of_unified():
    df = pd.DataFrame(index=of.index)
    df["record_id"] = "OF:" + of.match_id
    df["source_system"] = "openfootball"
    df["source_license"] = "CC0-1.0"
    df["competition_id"] = of.competition_id
    df["competition_family"] = of.competition_id.map(FAM_BY_COMP)
    df["competition_name"] = of.competition_name
    df["competition_type"] = of.competition_type
    df["season"] = of.season.astype(str)
    df["stage"] = of.stage.fillna("")
    df["match_date"] = of.match_date
    df["kickoff_time_local"] = of.kickoff_time_local.fillna("")
    for side in ("home", "away"):
        folders = [of_folder(n, c) for n, c in zip(of.ns, of[f"{side}_team_country_code"])]
        res = [ident.get((t, f), (None, "no_alias_match")) for t, f in zip(of[f"{side}_team_id"], folders)]
        df[f"{side}_entity_id"] = [r[0] or t for r, t in zip(res, of[f"{side}_team_id"])]
        df[f"{side}_identity_status"] = [r[1] for r in res]
        df[f"{side}_team_name"] = of[f"{side}_team"]
    # unified score semantics
    aet_h, aet_a = of.home_goals_after_extra_time, of.away_goals_after_extra_time
    df["reg_home"] = of.home_goals_regulation
    df["reg_away"] = of.away_goals_regulation
    df["final_excl_pens_home"] = aet_h.where(aet_h.notna(), of.home_goals_regulation)
    df["final_excl_pens_away"] = aet_a.where(aet_a.notna(), of.away_goals_regulation)
    df["pen_home"] = of.home_penalties
    df["pen_away"] = of.away_penalties
    df["extra_time_played"] = of.extra_time_played.fillna("")
    basis = []
    for d, e, p, rh in zip(of.decided_in, of.extra_time_played, of.penalties_played, of.home_goals_regulation):
        if pd.isna(rh):
            basis.append("unknown_regulation_score_not_stated")
        elif d == "regulation":
            basis.append("source_plain_score_no_extra_time_marker")
        elif d == "extra_time":
            basis.append("source_bracket_regulation_score_with_aet_marker")
        elif d == "penalties" and e == "yes":
            basis.append("source_bracket_regulation_score_with_aet_marker")
        else:
            basis.append("unknown_penalties_without_extra_time_statement")
    df["reg_basis"] = basis
    df["match_status"] = of.match_status
    df["status_note"] = of.status_note.fillna("")
    df["provenance"] = ("openfootball " + of.source_repo + "@" + of.source_repo_commit.fillna("").str[:12] + " " +
                        of.source_file + ":L" + of.source_line.astype(str))
    df["goals_listed_consistent"] = ""
    return df


def wp_unified():
    df = pd.DataFrame(index=wp.index)
    df["record_id"] = ["WP:" + str(r) + ":" + str(o) for r, o in zip(wp.page_revid, wp.offset)]
    df["source_system"] = "wikipedia"
    df["source_license"] = "CC BY-SA 4.0"
    fam_to_cid = {v[0]: k for k, v in FAMILY.items()}
    df["competition_id"] = wp.competition.map(fam_to_cid)
    df["competition_family"] = wp.competition
    df["competition_name"] = wp.competition
    df["competition_type"] = [FAMILY[c][1] for c in df.competition_id]
    df["season"] = wp.season
    df["stage"] = wp.stage_path.fillna("")
    df["match_date"] = wp.date
    df["kickoff_time_local"] = wp.time_raw.fillna("").str.slice(0, 5)
    ids = []
    for side in ("t1", "t2"):
        e = [wp_entity(d, t, c, f) for d, t, c, f in zip(wp[f"{side}_display"], wp[f"{side}_target"], wp[f"{side}_code"], wp.cup_folder)]
        ids.append(e)
    df["home_entity_id"] = [e[0] for e in ids[0]]
    df["home_identity_status"] = [e[1] for e in ids[0]]
    df["home_team_name"] = [e[2] for e in ids[0]]
    df["away_entity_id"] = [e[0] for e in ids[1]]
    df["away_identity_status"] = [e[1] for e in ids[1]]
    df["away_team_name"] = [e[2] for e in ids[1]]
    df["reg_home"], df["reg_away"] = wp.reg1, wp.reg2
    df["final_excl_pens_home"], df["final_excl_pens_away"] = wp.s1, wp.s2
    df["pen_home"], df["pen_away"] = wp.pen1, wp.pen2
    df["extra_time_played"] = wp.et_played
    df["reg_basis"] = wp.reg_basis
    played = wp.s1.notna() & wp.date.notna() & (wp.date <= AS_OF)
    df["match_status"] = np.where(played, "completed", "unscored")
    df["status_note"] = wp.score_raw.where(~played, "").fillna("")
    df["provenance"] = ("wikipedia rev " + wp.page_revid.astype(str) + " (" + wp.page_revision_timestamp.str[:10] + ") " +
                        wp.page_url + " retrieved " + wp.retrieved)
    df["goals_listed_consistent"] = wp.goals_list_consistent
    return df


U_of, U_wp = of_unified(), wp_unified()
U_of["role"] = "base"
U_wp["role"] = wp.role.values
U_wp["wp_row"] = wp.index
for d_ in (U_of, U_wp):
    d_["pair_key"] = [("|".join(sorted([a, b]))) for a, b in zip(d_.home_entity_id, d_.away_entity_id)]

pd.DataFrame(rows_map).to_csv(os.path.join(WORK, "team_identity_map_raw.csv"), index=False, encoding="utf-8")
U_of.to_pickle(os.path.join(WORK, "U_of.pkl"))
U_wp.to_pickle(os.path.join(WORK, "U_wp.pkl"))
print("OF rows", len(U_of), "WP rows", len(U_wp))
print("WP identity:", pd.concat([U_wp.home_identity_status, U_wp.away_identity_status]).value_counts().to_dict())
print(U_wp.groupby(["competition_family", "season"]).apply(lambda g: pd.Series(dict(
    n=len(g), resolved=float((g.home_identity_status.eq('resolved_exact_alias') & g.away_identity_status.eq('resolved_exact_alias')).mean())))).to_string())
