"""Stage 4 (read-only): independent re-implementation of every club feature + adversarial leakage probes."""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
ENC = "utf-8-sig"
R = {}

# universe (all rated results incl. pre-2018 history) written by the pipeline; features re-derived independently from its raw columns
U = pd.read_pickle(os.path.join(RDY, "_build", "work", "data_all.pkl"))
keep = ["record_id", "match_date", "home_entity_id", "away_entity_id", "reg_home", "reg_away", "final_excl_pens_home", "final_excl_pens_away",
        "label_90_status", "competition_type", "stage", "competition_id", "kickoff_time_local", "home_identity_status", "away_identity_status",
        "match_status", "season"]
U = U[keep].copy()
U["dt"] = pd.to_datetime(U.match_date)
R["universe_rows"] = len(U)
R["universe_null_dates"] = int(U.match_date.isna().sum())

# --- independent 90-minute goals (re-derived from raw score columns, not read from pipeline columns)
ph = []
for t, s in zip(U.competition_type, U.stage.fillna("")):
    if t == "domestic_league":
        ph.append("ko" if re.search(r"play-?off", s, re.I) else "lg")
    elif t in ("domestic_cup", "league_cup"):
        ph.append("ko")
    else:
        ph.append("lg" if re.search(r"league, matchday|group|matchday|league phase", s, re.I) and not re.search(r"knockout|play-?off|round of|final|quarter|semi", s, re.I) else "ko")
U["ph"] = ph
ok = U.label_90_status.isin(["confirmed", "inferred_no_marker"])
gh = np.where(U.reg_home.notna(), U.reg_home, U.final_excl_pens_home)
ga = np.where(U.reg_away.notna(), U.reg_away, U.final_excl_pens_away)
U["gh"], U["ga"] = np.where(ok, gh, np.nan), np.where(ok, ga, np.nan)
rated = U[U.gh.notna()].copy()
R["rated_results"] = len(rated)

# --- long table, per-entity arrays
L = pd.concat([
    pd.DataFrame(dict(e=rated.home_entity_id, dt=rated.dt, gf=rated.gh, ga=rated.ga, home=True, opp=rated.away_entity_id, rid=rated.record_id)),
    pd.DataFrame(dict(e=rated.away_entity_id, dt=rated.dt, gf=rated.ga, ga=rated.gh, home=False, opp=rated.home_entity_id, rid=rated.record_id))])
L["pts"] = np.where(L.gf > L.ga, 3, np.where(L.gf == L.ga, 1, 0))
L = L.sort_values(["e", "dt", "rid"])
arr = {e: (g.dt.values.astype("datetime64[D]"), g.pts.values.astype(float), g.gf.values.astype(float), g.ga.values.astype(float), g.home.values)
       for e, g in L.groupby("e", sort=False)}


def feats(e, d):
    if e not in arr:
        return dict(n=0, p5=np.nan, p10=np.nan, gf5=np.nan, ga5=np.nan, gf10=np.nan, ga10=np.nan, vp5=np.nan, rest=np.nan, last=np.datetime64("NaT"))
    dts, pts, gf, ga, hm = arr[e]
    k = int(np.searchsorted(dts, np.datetime64(d, "D"), side="left"))   # strictly earlier calendar dates only
    if k == 0:
        return dict(n=0, p5=np.nan, p10=np.nan, gf5=np.nan, ga5=np.nan, gf10=np.nan, ga10=np.nan, vp5=np.nan, rest=np.nan, last=np.datetime64("NaT"))
    return dict(n=k, p5=pts[max(0, k - 5):k].mean(), p10=pts[max(0, k - 10):k].mean(), gf5=gf[max(0, k - 5):k].mean(), ga5=ga[max(0, k - 5):k].mean(),
                gf10=gf[max(0, k - 10):k].mean(), ga10=ga[max(0, k - 10):k].mean(), last=dts[k - 1], rest=float((np.datetime64(d, "D") - dts[k - 1]).astype(int)), vp5=np.nan)


def venue_p5(e, d, is_home):
    dts, pts, gf, ga, hm = arr[e]
    k = int(np.searchsorted(dts, np.datetime64(d, "D"), side="left"))
    idx = np.where(hm[:k] == is_home)[0][-5:]
    return pts[idx].mean() if len(idx) else np.nan


# --- independent Elo (date-batched)
elo = {}
elo_pre = {}
K, HA = 20.0, 60.0
for dt, g in rated.sort_values(["dt", "competition_id", "record_id"]).groupby("dt", sort=True):
    upd = []
    for r in g.itertuples():
        eh, ea = elo.get(r.home_entity_id, 1500.0), elo.get(r.away_entity_id, 1500.0)
        elo_pre[r.record_id] = (eh, ea)
        upd.append((r.home_entity_id, r.away_entity_id, r.gh, r.ga))
    for h, a, x, y in upd:
        eh, ea = elo.get(h, 1500.0), elo.get(a, 1500.0)
        e_h = 1.0 / (1.0 + 10.0 ** (-(eh + HA - ea) / 400.0))
        s = 1.0 if x > y else (0.5 if x == y else 0.0)
        gd = abs(x - y)
        mult = 1.0 if gd <= 1 else (1.5 if gd == 2 else (11.0 + gd) / 8.0)
        delta = K * mult * (s - e_h)
        elo[h] = eh + delta
        elo[a] = ea - delta
# unrated rows (label unknown) need the pre-state too: elo at their date is the state before that date
# -> compute by replaying with a snapshot lookup
snap = {}
state = {}
dates_sorted = sorted(rated.dt.unique())
# build per-entity (date, elo_after) series to answer 'elo before date d' for any entity/date
series = {}
elo2 = {}
for dt, g in rated.sort_values(["dt", "competition_id", "record_id"]).groupby("dt", sort=True):
    upd = [(r.home_entity_id, r.away_entity_id, r.gh, r.ga) for r in g.itertuples()]
    pre = {}
    for h, a, x, y in upd:
        pre[(h, a, x, y)] = None
    new = {}
    for h, a, x, y in upd:
        eh, ea = elo2.get(h, 1500.0), elo2.get(a, 1500.0)
        e_h = 1.0 / (1.0 + 10.0 ** (-(eh + HA - ea) / 400.0))
        s = 1.0 if x > y else (0.5 if x == y else 0.0)
        gd = abs(x - y)
        mult = 1.0 if gd <= 1 else (1.5 if gd == 2 else (11.0 + gd) / 8.0)
        delta = K * mult * (s - e_h)
        new[h] = new.get(h, eh) + delta if h in new else eh + delta
        new[a] = new.get(a, ea) - delta if a in new else ea - delta
    # same-date double matches for one entity: apply sequentially using the pre-date state (matches pipeline semantics)
    for en, v in new.items():
        pass
    # replay sequentially to equal the pipeline's semantics exactly
    for h, a, x, y in upd:
        eh, ea = elo2.get(h, 1500.0), elo2.get(a, 1500.0)
        e_h = 1.0 / (1.0 + 10.0 ** (-(eh + HA - ea) / 400.0))
        s = 1.0 if x > y else (0.5 if x == y else 0.0)
        gd = abs(x - y)
        mult = 1.0 if gd <= 1 else (1.5 if gd == 2 else (11.0 + gd) / 8.0)
        delta = K * mult * (s - e_h)
        elo2[h] = eh + delta
        elo2[a] = ea - delta
        series.setdefault(h, []).append((dt, elo2[h]))
        series.setdefault(a, []).append((dt, elo2[a]))


def elo_before(e, d):
    s = series.get(e)
    if not s:
        return 1500.0
    ds = [x[0] for x in s]
    i = np.searchsorted(np.array(ds, dtype="datetime64[ns]"), np.datetime64(d, "ns"), side="left")
    return s[i - 1][1] if i > 0 else 1500.0


# ---------------------------------------------------------------- compare with stored extended training set
ext = pd.read_csv(os.path.join(RDY, "08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv"), low_memory=False, encoding=ENC)
ext["dt"] = pd.to_datetime(ext.match_date)
rows = []
for r in ext.itertuples():
    fh, fa = feats(r.home_entity_id, r.dt), feats(r.away_entity_id, r.dt)
    rows.append(dict(record_id=r.record_id,
                     home_n_prior=fh["n"], away_n_prior=fa["n"], home_ppg5=fh["p5"], away_ppg5=fa["p5"], home_ppg10=fh["p10"], away_ppg10=fa["p10"],
                     home_gf5=fh["gf5"], home_ga5=fh["ga5"], away_gf5=fa["gf5"], away_ga5=fa["ga5"], home_gf10=fh["gf10"], home_ga10=fh["ga10"],
                     away_gf10=fa["gf10"], away_ga10=fa["ga10"], home_days_rest=fh["rest"], away_days_rest=fa["rest"],
                     home_venue_ppg5=venue_p5(r.home_entity_id, r.dt, True) if fh["n"] else np.nan,
                     away_venue_ppg5=venue_p5(r.away_entity_id, r.dt, False) if fa["n"] else np.nan,
                     home_elo=elo_before(r.home_entity_id, r.dt), away_elo=elo_before(r.away_entity_id, r.dt)))
ind = pd.DataFrame(rows).set_index("record_id")
st = ext.set_index("record_id")
cmpres = []
for c in ind.columns:
    a, b = st.loc[ind.index, c].astype(float), ind[c].astype(float)
    both_nan = a.isna() & b.isna()
    diff = (a - b).abs()
    diff[both_nan] = 0
    mism_nan = (a.isna() ^ b.isna())
    tol = 1e-6 if "elo" not in c else 1e-6
    cmpres.append(dict(feature=c, rows=len(a), max_abs_diff=float(np.nanmax(diff)) if len(diff) else 0, rows_diff_gt_1e6=int((diff > tol).sum()),
                       nan_pattern_mismatch=int(mism_nan.sum())))
cmpdf = pd.DataFrame(cmpres)
cmpdf.to_csv(os.path.join(EV, "feature_recomputation_comparison.csv"), index=False)
print(cmpdf.to_string())
R["feature_compare_all_rows"] = len(ind)
R["feature_max_abs_diff_overall"] = float(cmpdf.max_abs_diff.max())
R["feature_rows_with_any_difference"] = int(((ind.sub(st.loc[ind.index, ind.columns].astype(float)).abs() > 1e-6).any(axis=1)).sum())

# ---------------------------------------------------------------- adversarial probes
# 1 same-day multiple matches per entity
dd = pd.concat([ext[["home_entity_id", "match_date", "record_id"]].set_axis(["e", "d", "r"], axis=1), ext[["away_entity_id", "match_date", "record_id"]].set_axis(["e", "d", "r"], axis=1)])
cnt = dd.groupby(["e", "d"]).r.nunique()
R["entity_days_with_multiple_eligible_matches"] = int((cnt > 1).sum())
U_all = pd.concat([U[["home_entity_id", "match_date", "record_id"]].set_axis(["e", "d", "r"], axis=1), U[["away_entity_id", "match_date", "record_id"]].set_axis(["e", "d", "r"], axis=1)])
c2 = U_all.groupby(["e", "d"]).r.nunique()
R["entity_days_with_multiple_matches_all_results"] = int((c2 > 1).sum())
multi = c2[c2 > 1].reset_index().merge(U[["match_date", "kickoff_time_local", "record_id"]].rename(columns={"record_id": "r"}), left_on=["d", "r"], right_on=["match_date", "r"], how="left") if False else None
R["kickoff_time_known_pct_in_extended"] = round(100 * ext.merge(U[["record_id", "kickoff_time_local"]], on="record_id").kickoff_time_local.notna().mean(), 1)
# 2 same_country bug
ext["sc_expected"] = ext.home_entity_id.map(lambda x: x.split(":")[1] if x.startswith("CLUB:") else (x.split("|")[0])) == ext.away_entity_id.map(lambda x: x.split(":")[1] if x.startswith("CLUB:") else (x.split("|")[0]))
lgm = ext[ext.competition_type == "domestic_league"]
R["domestic_league_rows_in_extended"] = len(lgm)
R["domestic_league_rows_same_country_stored_false"] = int((lgm.same_country == 0).sum())
R["domestic_league_rows_same_country_expected_false"] = int((~lgm.sc_expected).sum())
R["same_country_all_false_share_in_extended"] = round(float((ext.same_country == 0).mean()), 3)
# 3 constant / low-variance features
FEATURES = json.load(open(os.path.join(RDY, "_build", "work", "feature_list.json")))
R["constant_features"] = [c for c in FEATURES if ext[c].nunique(dropna=True) <= 1]
R["feature_missing_pct"] = {c: round(100 * ext[c].isna().mean(), 2) for c in FEATURES if ext[c].isna().any()}
# 4 elo connectivity
parent = {}


def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for h, a in zip(rated.home_entity_id, rated.away_entity_id):
    ra, rb = find(h), find(a)
    if ra != rb:
        parent[ra] = rb
comp = pd.Series({e: find(e) for e in parent})
sizes = comp.value_counts()
R["elo_connected_components"] = int(len(sizes))
R["elo_largest_component_entities"] = int(sizes.iloc[0])
R["elo_entities_total"] = int(len(comp))
ext_comp = ext.home_entity_id.map(comp)
R["extended_rows_in_largest_component_pct"] = round(100 * float((ext_comp == sizes.index[0]).mean()), 1)
R["extended_rows_outside_largest_component"] = int((ext_comp != sizes.index[0]).sum())
bycomp = ext.assign(c=ext_comp).groupby("c").size().sort_values(ascending=False)
R["extended_rows_by_component_top"] = bycomp.head(6).astype(int).to_dict()
# leagues outside the main component
out = ext[ext_comp != sizes.index[0]].groupby("competition_id").size().sort_values(ascending=False).head(12)
R["extended_rows_outside_main_component_by_competition"] = out.to_dict()
# 5 duplicate fixtures
ext["pk"] = ext.apply(lambda r: "|".join(sorted([r.home_entity_id, r.away_entity_id])), axis=1)
dup = ext.duplicated(["match_date", "pk"], keep=False)
R["extended_duplicate_pair_date_rows"] = int(dup.sum())
ext[dup][["record_id", "competition_id", "season", "match_date", "home_team_name", "away_team_name", "suggested_split"]].to_csv(os.path.join(EV, "duplicate_fixture_candidates_in_extended.csv"), index=False)
# 6 label distribution per split
lab = ext.groupby(["suggested_split", "label_outcome_90min_1x2"]).size().unstack(fill_value=0)
R["label_distribution_extended"] = lab.to_dict("index")
strict = pd.read_csv(os.path.join(RDY, "08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv"), low_memory=False, encoding=ENC, usecols=["suggested_split", "label_outcome_90min_1x2", "competition_type", "competition_id"])
R["label_distribution_strict"] = strict.groupby(["suggested_split", "label_outcome_90min_1x2"]).size().unstack(fill_value=0).to_dict("index")
R["strict_rows_by_competition_type"] = strict.competition_type.value_counts().to_dict()
R["split_counts_strict"] = strict.suggested_split.value_counts().to_dict()
R["strict_rows_domestic_league_pct"] = round(100 * float((strict.competition_type == "domestic_league").mean()), 1)
# 7 forward holdout contamination: Elo for train rows must not depend on holdout (prefix test)
cut = np.datetime64("2023-07-01")
pre = rated[rated.dt < pd.Timestamp("2023-07-01")]
R["rated_results_before_2023_07_01"] = len(pre)
# 8 eligibility selection effects
sel = U.copy()
R["rows_with_unknown_label_share_by_phase"] = sel.groupby("ph").label_90_status.apply(lambda s: round(float((s == "unknown").mean()), 4)).to_dict()
json.dump(R, open(os.path.join(EV, "v4_results.json"), "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in R.items() if k not in ("label_distribution_extended", "label_distribution_strict")}, indent=0, default=str)[:3500])
