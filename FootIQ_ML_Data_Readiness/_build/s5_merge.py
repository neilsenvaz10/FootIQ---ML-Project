"""Merge Wikipedia gap-fills into the openfootball base; cross-validate overlapping seasons."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

U_of = pd.read_pickle(os.path.join(WORK, "U_of.pkl"))
U_wp = pd.read_pickle(os.path.join(WORK, "U_wp.pkl"))
U_of["match_dt"] = pd.to_datetime(U_of.match_date)
U_wp["match_dt"] = pd.to_datetime(U_wp.match_date)
U_of["in_audit_scope"] = U_of.competition_family.notna() & U_of.season.isin(SEASONS)

of_idx = {}
for i, r in U_of[U_of.in_audit_scope].iterrows():
    of_idx.setdefault((r.competition_family, r.season, r.pair_key), []).append(i)

matched_of = {}
wp_match = {}
for i, w in U_wp.iterrows():
    cands = [j for j in of_idx.get((w.competition_family, w.season, w.pair_key), []) if j not in matched_of]
    best, bd = None, 99
    for j in cands:
        if pd.isna(w.match_dt) or pd.isna(U_of.at[j, "match_dt"]):
            continue
        dd = abs((U_of.at[j, "match_dt"] - w.match_dt).days)
        if dd <= 1 and dd < bd:
            best, bd = j, dd
    if best is not None:
        matched_of[best] = i
        wp_match[i] = best

U_wp["matched_of_index"] = U_wp.index.map(lambda i: wp_match.get(i, np.nan))

# ---------------------------------------------------------------- cross-validation on overlapping rows
val = []
for i, w in U_wp[U_wp.matched_of_index.notna()].iterrows():
    o = U_of.loc[int(w.matched_of_index)]
    if o.match_status not in ("completed", "awarded", "abandoned") or w.match_status != "completed":
        val.append(dict(wp_index=i, of_index=int(w.matched_of_index), kind="status_differs", competition=w.competition_family,
                        season=w.season, date_wp=w.match_date, date_of=o.match_date, wp=w.stage, of_status=o.match_status))
        continue
    same_orient = (o.home_entity_id == w.home_entity_id)
    oh, oa = (o.final_excl_pens_home, o.final_excl_pens_away)
    wh, wa = (w.final_excl_pens_home, w.final_excl_pens_away)
    if not same_orient:
        wh, wa = wa, wh
    rec = dict(wp_index=i, of_index=int(w.matched_of_index), competition=w.competition_family, season=w.season,
               date_wp=w.match_date, date_of=o.match_date, home=o.home_team_name, away=o.away_team_name,
               of_final=f"{oh}-{oa}", wp_final=f"{wh}-{wa}", date_equal=(w.match_date == o.match_date))
    if pd.isna(oh) or pd.isna(wh):
        rec["kind"] = "final_score_not_comparable"
    else:
        rec["kind"] = "score_agree" if (oh == wh and oa == wa) else "score_conflict"
    # penalties
    ph, pa = (o.pen_home, o.pen_away)
    wph, wpa = (w.pen_home, w.pen_away)
    if not same_orient:
        wph, wpa = wpa, wph
    rec["pen_agree"] = (pd.isna(ph) and pd.isna(wph)) or (ph == wph and pa == wpa)
    # 90-minute score where both known
    if pd.notna(o.reg_home) and pd.notna(w.reg_home):
        wr = (w.reg_home, w.reg_away) if same_orient else (w.reg_away, w.reg_home)
        rec["reg_both_known"] = True
        rec["reg_agree"] = (o.reg_home, o.reg_away) == wr
    else:
        rec["reg_both_known"] = False
        rec["reg_agree"] = None
    val.append(rec)
val = pd.DataFrame(val)
val.to_csv(os.path.join(WORK, "cross_validation_pairs.csv"), index=False, encoding="utf-8")

# ---------------------------------------------------------------- which WP rows become fills
unmatched = U_wp[U_wp.matched_of_index.isna()].copy()
base_present = U_of[U_of.in_audit_scope].groupby(["competition_family", "season"]).size()
fills = []
for i, w in unmatched.iterrows():
    if w.role == "validate":
        continue  # validation seasons: Wikipedia is never used to add rows
    fills.append(i)
U_fill = U_wp.loc[fills].copy()
# supersede OF unscored rows when a completed WP record exists for the same pair/date window
sup = {}
for i, w in U_wp[U_wp.matched_of_index.notna() & (U_wp.role == "fill")].iterrows():
    o = U_of.loc[int(w.matched_of_index)]
    if o.match_status in ("unscored", "postponed") and w.match_status == "completed":
        sup[int(w.matched_of_index)] = i
U_of["superseded_by_wp_row"] = U_of.index.map(lambda j: sup.get(j, np.nan))
sup_rows = U_wp.loc[list(sup.values())].copy() if sup else U_wp.iloc[0:0].copy()
U_fill = pd.concat([U_fill, sup_rows]).drop_duplicates(subset=["record_id"])
U_fill["fill_reason"] = np.where(U_fill.index.isin(sup_rows.index), "replaces_unscored_openfootball_row",
                                 "competition_season_absent_or_incomplete_in_openfootball")
U_of.to_pickle(os.path.join(WORK, "M_of.pkl"))
U_fill.to_pickle(os.path.join(WORK, "M_fill.pkl"))
U_wp.to_pickle(os.path.join(WORK, "M_wp.pkl"))
print("WP rows", len(U_wp), "matched to OF", int(U_wp.matched_of_index.notna().sum()), "fills", len(U_fill))
if len(val):
    v = val[val.kind.isin(["score_agree", "score_conflict"])]
    print(v.groupby(["competition", "season"]).kind.value_counts().unstack(fill_value=0).to_string())
    print("pen agree:", val.pen_agree.mean(), " reg both known:", int(val.reg_both_known.sum()), "reg agree:", val[val.reg_both_known == True].reg_agree.mean())
print(U_fill.groupby(["competition_family", "season"]).size().to_string())
unm_val = unmatched[unmatched.role == "validate"]
print("validation-season WP rows with no OF counterpart:", len(unm_val))
print(unm_val.groupby(["competition_family", "season"]).size().to_string())
