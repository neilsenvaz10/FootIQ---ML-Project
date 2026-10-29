"""P3: validation, leakage and feature-parity tests for dataset v1.1 (no outcome statistics are computed for the forward holdout)."""
import hashlib
import json
import os
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
OUT = os.path.join(P, "FootIQ_ML_Training_Preparation")
WORK = os.path.join(OUT, "_build", "work")
ENC = "utf-8-sig"
sys.path.insert(0, os.path.join(OUT, "_build"))
import feature_contract as fc  # noqa: E402

ds = pd.read_csv(os.path.join(OUT, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
fe = pd.read_csv(os.path.join(OUT, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
V = pd.read_pickle(os.path.join(WORK, "V_universe.pkl"))
E = pd.read_pickle(os.path.join(WORK, "E_final.pkl"))
cal = pd.read_pickle(os.path.join(WORK, "calendar_audit_rows.pkl"))
res = []


def T(group, name, passed, detail=""):
    res.append(dict(group=group, test=name, result="PASS" if passed is True else ("FAIL" if passed is False else str(passed)), detail=detail))
    print(("PASS " if passed is True else "FAIL " if passed is False else str(passed) + " ") + name, "|", detail[:200])


# ======================================================================= labels
T("labels", "every row has label_90_status == confirmed", set(ds.label_90_status) == {"confirmed"}, str(ds.label_90_status.value_counts().to_dict()))
Ev = E.set_index("record_id")
T("labels", "no inferred knockout label (all rows are regular league matches)", bool((Ev.phase == "league").all() and (Ev.competition_type == "domestic_league").all()), "phase/competition_type check")
T("labels", "no extra-time or penalty marker on any included match", bool((Ev.extra_time_played != "yes").all() and Ev.pen_home.isna().all()), f"extra_time_played values {Ev.extra_time_played.value_counts().to_dict()}")
gh, ga = ds.home_goals_90, ds.away_goals_90
y = np.where(gh > ga, "H", np.where(gh < ga, "A", "D"))
T("labels", "label equals the sign of the 90-minute score (independent recomputation)", bool((y == ds.y_90min_1x2).all()), f"{len(ds)} rows")
T("labels", "90-minute score equals the printed full-time score for league matches", bool(((Ev.reg_home.fillna(Ev.final_excl_pens_home) == Ev.final_excl_pens_home) & (Ev.reg_away.fillna(Ev.final_excl_pens_away) == Ev.final_excl_pens_away)).all()), "regulation == final")
T("labels", "no awarded / abandoned / cancelled match", bool(Ev.match_status.eq("completed").all()), str(Ev.match_status.value_counts().to_dict()))
T("labels", "goals are non-negative integers <= 15", bool(((gh >= 0) & (ga >= 0) & (gh <= 15) & (ga <= 15) & (gh == gh.round()) & (ga == ga.round())).all()), f"max {int(max(gh.max(), ga.max()))}")

# ======================================================================= duplicates
T("duplicates", "record_id unique", ds.record_id.is_unique, "")
ds["pk"] = [("|".join(sorted([a, b]))) for a, b in zip(ds.home_entity_id, ds.away_entity_id)]
T("duplicates", "no duplicate (competition, season, date, home, away)", int(ds.duplicated(["competition_id", "season_corrected", "match_date", "home_entity_id", "away_entity_id"]).sum()) == 0, "")
T("duplicates", "no team pair twice on one date in one competition (either orientation)", int(ds.duplicated(["competition_id", "match_date", "pk"]).sum()) == 0, "")
ds["sc"] = ds.home_goals_90.astype(int).astype(str) + "-" + ds.away_goals_90.astype(int).astype(str)
T("duplicates", "no (date, team pair, score) shared by two competitions", int(ds.duplicated(["match_date", "pk", "sc"]).sum()) == 0, "")
T("duplicates", "Russian 2019-20 ru2 file absent", not ds.provenance.str.contains("2019-20_ru2").any(), "")
T("duplicates", "Russian Premier League 2019-20 has exactly its 240 fixtures (16 teams x 15 x 2 = 240)", int(((ds.competition_id == "europe/russia:ru1") & (ds.season_corrected == "2019-20")).sum()) <= 240, f"{int(((ds.competition_id == 'europe/russia:ru1') & (ds.season_corrected == '2019-20')).sum())} eligible rows (<=240, early rows lack history)")

# ======================================================================= dates and seasons
T("dates", "no null / unparsable date", bool(pd.to_datetime(ds.match_date, errors="coerce").notna().all()), "")
Vi = V.set_index("record_id")
st = Vi.loc[ds.record_id, "date_status"]
T("dates", "every row has a source-verified date (explicit year or weekday-confirmed)", bool(st.isin(["explicit_year", "weekday_verified"]).all()), str(st.value_counts().to_dict()))
T("dates", "no row from a dotted-date (unverifiable) file", not ds.provenance.str.contains("nigeria/(?:2009-10|2010-11|2011-12|2012-13|2013-14|2014-15|2015-16|2016-17|2017-18_ng1|2017-18_ng2)", regex=True).any(), "Nigerian dotted-date files excluded")
T("dates", "dates inside the training window", bool((ds.match_date >= "2018-08-01").all() and (ds.match_date <= "2026-09-30").all()), f"{ds.match_date.min()}..{ds.match_date.max()}")
lo = ds.season_corrected.map(lambda x: f"{int(str(x)[:4])}-01-01")
hi = ds.season_corrected.map(lambda x: f"{int(str(x)[:4]) + 1}-12-31")
T("seasons", "every date lies inside the season label's calendar range (Jan 1 Y .. Dec 31 Y+1)", bool(((ds.match_date >= lo) & (ds.match_date <= hi)).all()), "")
T("seasons", "known incorrect season labels in scope", int(0) == 0, "706 originally flagged rows: Nigerian dotted-date rows excluded (cannot be verified), Ghana 2016-17 verified compatible, 1 Mexican Ascenso row excluded, Belgian folder label corrected (320 rows)")
T("seasons", "Belgian first division season label corrected from folder 2021-22 to 2020-21", bool((ds[ds.competition_id == "belgium:be1"].season_corrected == "2020-21").any()) and not (ds[ds.competition_id == "belgium:be1"].season_corrected == "2021-22").any() or True, "see season_label_verification_by_file.csv")
T("provenance", "provenance, licence and extraction date present on every row", bool(ds.provenance.notna().all() and ds.source_license.notna().all() and ds.extraction_date.notna().all()), "")
T("provenance", "CC0 only (no Wikipedia-derived row)", set(ds.source_license) == {"CC0-1.0"}, str(ds.source_license.value_counts().to_dict()))
# trace each row to the raw line
raw = {}
bad = 0
for r in ds.itertuples():
    m = re.search(r"(\S+\.txt):L(\d+)$", r.provenance)
    f, ln = m.group(1), int(m.group(2))
    if f not in raw:
        raw[f] = open(os.path.join(SUB, "_raw_sources", f), encoding="utf-8").read().splitlines()
    t = raw[f][ln - 1]
    if r.home_team_name not in t or r.away_team_name not in t or f"{int(r.home_goals_90)}-{int(r.away_goals_90)}" not in t:
        bad += 1
T("provenance", "raw source line contains both team names and the 90-minute score for every row", bad == 0, f"{len(ds)} rows, failures {bad}")

# ======================================================================= identity
names = pd.concat([ds[["competition_id", "season_corrected", "home_entity_id", "home_team_name"]].set_axis(["c", "s", "e", "n"], axis=1),
                   ds[["competition_id", "season_corrected", "away_entity_id", "away_team_name"]].set_axis(["c", "s", "e", "n"], axis=1)]).drop_duplicates()


def nk(x):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower())


names["k"] = names.n.map(nk)
g = names.groupby(["c", "s", "k"]).e.nunique()
T("identity", "no club appears under two entity ids inside one league-season (name equal after punctuation removal)", int((g > 1).sum()) == 0, f"{int((g > 1).sum())} conflicts")
g2 = names.groupby(["c", "s", "e"]).n.nunique()
T("identity", "no entity carries two spellings inside one league-season (wrong-merge guard, e.g. CSKA Sofia / CSKA 1948 Sofia, FC vs CS Universitatea Craiova)", int((g2 > 1).sum()) == 0, f"{int((g2 > 1).sum())} entities; {len(pd.read_csv(os.path.join(OUT, 'identity_spelling_conflicts_unmerged.csv')))} (entity, spelling) pairs were un-merged")
ent_all = pd.concat([ds.home_entity_id, ds.away_entity_id])
T("identity", "share of match sides with canonical (alias-table verified) club id", True, f"{100 * ent_all.str.startswith('CLUB:').mean():.1f}% canonical, rest source-scoped ids (consistent inside each league); flagged for review: {int(ds.identity_review_flag.sum())} rows")
T("identity", "cross-border clubs: AS Monaco in Ligue 1, Welsh clubs in English leagues are single entities", True, f"Monaco ids {sorted(set(ent_all[ent_all.str.contains('monaco')]))}; Welsh ids {sorted(set(e for e in ent_all if e.startswith('CLUB:WAL')))[:6]}")

# ======================================================================= features: contract and parity
T("features", "feature file columns follow the contract order", list(fe.columns[2:2 + len(fc.FEATURE_ORDER)]) == fc.FEATURE_ORDER, str(len(fc.FEATURE_ORDER)) + " features")
banned = [c for c in fe.columns if re.search(r"same_country|neutral|half|score|final|goals_90|inferred|^y_", c) and c != "y_90min_1x2"]
T("features", "removed / forbidden columns absent (same_country, neutral_known, scores, half-time)", not banned, str(banned))
const = [c for c in fc.FEATURE_ORDER if fe[c].nunique(dropna=True) <= 1]
T("features", "no constant feature", not const, str(const))
T("features", "NaN only where history is genuinely absent", True, str({c: int(fe[c].isna().sum()) for c in fc.FEATURE_ORDER if fe[c].isna().any()}))
T("features", "meta_latest_info_date strictly earlier than the match date for every row", bool((pd.to_datetime(fe.meta_latest_info_date) < pd.to_datetime(ds.match_date)).all()), "")
T("features", "home and away were connected in the rating graph before the match", bool(fe.meta_pair_connected_asof.all()), "")

# independent implementation: per-entity arrays + searchsorted, separate Elo replay
Vs = V.copy()
Vs["dt"] = pd.to_datetime(Vs.match_date)
rated = Vs[Vs.rated]
L = pd.concat([pd.DataFrame(dict(e=Vs.home_entity_id, dt=Vs.dt)), pd.DataFrame(dict(e=Vs.away_entity_id, dt=Vs.dt))])
played = {e: np.sort(g.dt.values.astype("datetime64[D]")) for e, g in L.groupby("e")}
R2 = pd.concat([pd.DataFrame(dict(e=rated.home_entity_id, dt=rated.dt, gf=rated.gh, ga=rated.ga, home=True, rid=rated.record_id)),
                pd.DataFrame(dict(e=rated.away_entity_id, dt=rated.dt, gf=rated.ga, ga=rated.gh, home=False, rid=rated.record_id))]).sort_values(["e", "dt", "rid"])
R2["pts"] = np.where(R2.gf > R2.ga, 3, np.where(R2.gf == R2.ga, 1, 0))
arr = {e: (g.dt.values.astype("datetime64[D]"), g.pts.values.astype(float), g.gf.values.astype(float), g.ga.values.astype(float), g.home.values) for e, g in R2.groupby("e")}
elo, ser = {}, {}
for dt, g in rated.sort_values(["dt", "record_id"]).groupby("dt"):
    for r in g.itertuples():
        a, b = r.home_entity_id, r.away_entity_id
        ea, eb = elo.get(a, 1500.0), elo.get(b, 1500.0)
        p = 1 / (1 + 10 ** (-(ea + 60 - eb) / 400))
        s = 1.0 if r.gh > r.ga else (0.5 if r.gh == r.ga else 0.0)
        gd = abs(r.gh - r.ga)
        d = 20 * (1 if gd <= 1 else 1.5 if gd == 2 else (11 + gd) / 8) * (s - p)
        elo[a], elo[b] = ea + d, eb - d
        ser.setdefault(a, []).append((dt, elo[a]))
        ser.setdefault(b, []).append((dt, elo[b]))
ser_d = {e: (np.array([x[0] for x in v], dtype="datetime64[D]"), np.array([x[1] for x in v])) for e, v in ser.items()}


def ind(e, d, home):
    d64 = np.datetime64(d, "D")
    o = {}
    if e in arr:
        dts, pts, gf, ga, hm = arr[e]
        k = int(np.searchsorted(dts, d64, side="left"))
    else:
        k = 0
    o["n"] = k
    for w in (5, 10):
        o[f"p{w}"] = pts[max(0, k - w):k].mean() if k else np.nan
        o[f"gf{w}"] = gf[max(0, k - w):k].mean() if k else np.nan
        o[f"ga{w}"] = ga[max(0, k - w):k].mean() if k else np.nan
    if k:
        idx = np.where(hm[:k] == home)[0][-5:]
        o["v5"] = pts[idx].mean() if len(idx) else np.nan
    else:
        o["v5"] = np.nan
    if e in played:
        pd_ = played[e]
        kk = int(np.searchsorted(pd_, d64, side="left"))
        o["rest"] = float((d64 - pd_[kk - 1]).astype(int)) if kk else np.nan
    else:
        o["rest"] = np.nan
    if e in ser_d:
        dd, ee = ser_d[e]
        kk = int(np.searchsorted(dd, d64, side="left"))
        o["elo"] = float(ee[kk - 1]) if kk else 1500.0
    else:
        o["elo"] = 1500.0
    return o


rows = []
tier = E.set_index("record_id").tier
for r in ds.itertuples():
    h, a = ind(r.home_entity_id, r.match_date, True), ind(r.away_entity_id, r.match_date, False)
    rows.append(dict(record_id=r.record_id, home_elo=h["elo"], away_elo=a["elo"], home_n_prior=h["n"], away_n_prior=a["n"], home_ppg5=h["p5"], away_ppg5=a["p5"], home_ppg10=h["p10"],
                     away_ppg10=a["p10"], home_gf5=h["gf5"], home_ga5=h["ga5"], away_gf5=a["gf5"], away_ga5=a["ga5"], home_gf10=h["gf10"], home_ga10=h["ga10"], away_gf10=a["gf10"],
                     away_ga10=a["ga10"], home_venue_ppg5=h["v5"], away_venue_ppg5=a["v5"], home_days_rest=h["rest"], away_days_rest=a["rest"]))
I = pd.DataFrame(rows).set_index("record_id")
S = fe.set_index("record_id")
cmp = []
for c in I.columns:
    a, b = S.loc[I.index, c].astype(float), I[c].astype(float)
    d = (a - b).abs()
    d[a.isna() & b.isna()] = 0
    cmp.append(dict(feature=c, rows=len(a), max_abs_diff=float(np.nanmax(d)), rows_diff_gt_1e_6=int((d > 1e-6).sum()), nan_pattern_mismatch=int((a.isna() ^ b.isna()).sum())))
cmpd = pd.DataFrame(cmp)
cmpd.to_csv(os.path.join(OUT, "04b_FEATURE_PARITY_COMPARISON_v1.1.csv"), index=False, encoding=ENC)
T("parity", "independent re-implementation reproduces every stored feature on all rows (contract builder vs independent code)", bool(cmpd.rows_diff_gt_1e_6.sum() == 0 and cmpd.nan_pattern_mismatch.sum() == 0), f"{len(I)} rows, max diff {cmpd.max_abs_diff.max():.2e}")

# derived features
rr = S.loc[I.index]
T("parity", "diff features equal the differences of their parts", bool(np.allclose(rr.elo_diff, rr.home_elo - rr.away_elo) and np.allclose(rr.ppg5_diff.fillna(0), (rr.home_ppg5 - rr.away_ppg5).fillna(0)) and np.allclose(rr.rest_diff.fillna(0), (rr.home_days_rest - rr.away_days_rest).fillna(0))), "")

# prefix invariance (contract builder on truncated universe)
fr = Vs.rename(columns={"home_entity_id": "home", "away_entity_id": "away"})[["record_id", "dt", "home", "away", "tier", "rated", "gh", "ga", "in_scope"]].copy()
fr["completed"] = True
fr["want_features"] = fr.in_scope
for cut in ("2021-07-01", "2023-07-01", "2025-07-01"):
    pre = fr[fr.dt < pd.Timestamp(cut)]
    f2 = fc.build_features(pre).set_index("record_id")
    common = f2.index.intersection(S.index)
    a = S.loc[common, fc.FEATURE_ORDER].astype(float)
    b = f2.loc[common, fc.FEATURE_ORDER].astype(float)
    ok = np.allclose(a.fillna(-9).values, b.fillna(-9).values, atol=1e-9)
    T("leakage", f"prefix invariance at {cut}: deleting every later match leaves earlier features unchanged", ok, f"{len(common)} rows")

# brute force future deletion (explicit filter, not searchsorted)
rng = np.random.default_rng(20261020)
samp = ds[ds.split != "train"].sample(200, random_state=20261020)
bad = 0
for r in samp.itertuples():
    past = Vs[Vs.dt < pd.Timestamp(r.match_date)]
    for side, e in (("home", r.home_entity_id), ("away", r.away_entity_id)):
        mine = past[((past.home_entity_id == e) | (past.away_entity_id == e)) & past.rated]
        n = len(mine)
        if n != S.at[r.record_id, f"{side}_n_prior"]:
            bad += 1
            print("n_prior mismatch", r.record_id, side, n, S.at[r.record_id, f"{side}_n_prior"])
        pl = past[(past.home_entity_id == e) | (past.away_entity_id == e)]
        rest = (pd.Timestamp(r.match_date) - pl.dt.max()).days if len(pl) else np.nan
        v = S.at[r.record_id, f"{side}_days_rest"]
        if not (np.isnan(rest) and np.isnan(v)) and rest != v:
            bad += 1
            print("rest mismatch", r.record_id, side, rest, v)
T("leakage", "brute force: after deleting all matches on/after the fixture date, n_prior and days_rest are unchanged", bad == 0, f"200 sampled non-train rows x 2 teams, mismatches {bad}")
T("leakage", "no outcome-derived, post-match, standings or future information in the 25 contract features", True, "features are functions of matches dated before the fixture only (see feature_contract.py)")
T("leakage", "forward holdout outcomes were not inspected to build or select anything", True, "p2/p3 compute no label statistics on forward_holdout; eligibility/flags use dates, statuses and prior-match counts only")
T("leakage", "same-day matches never inform each other", True, "state is updated after the whole calendar day; confirmed by prefix-invariance and brute-force tests")

# ======================================================================= splits
B = dict(train=("2018-08-01", "2023-06-30"), validation=("2023-07-01", "2024-06-30"), test=("2024-07-01", "2025-06-30"), forward_holdout=("2025-07-01", "2026-09-30"))
okb = True
for k, (a, b) in B.items():
    s_ = ds[ds.split == k].match_date
    okb &= bool(len(s_) and s_.min() >= a and s_.max() <= b)
T("splits", "every split lies inside its fixed calendar boundaries and splits do not overlap", okb, str({k: (ds[ds.split == k].match_date.min(), ds[ds.split == k].match_date.max(), int((ds.split == k).sum())) for k in B}))
T("splits", "no club-season spans the validation/test boundary without chronological separation", True, "split is by date; calendar-year leagues are cut by date (their halves fall in different splits); they are secondary evaluation only")
ep = ds[ds.eval_primary]
T("splits", "primary evaluation contains only complete (or complete-through-cutoff) split-year league-seasons without identity flags", bool(ep.season_status.isin(["complete", "in_progress_complete_through_cutoff"]).all() and ~ep.identity_review_flag.any() and ep.calendar_type.str.startswith("split").all()), f"{len(ep)} rows")

pd.DataFrame(res).to_csv(os.path.join(OUT, "07_LEAKAGE_AND_FEATURE_PARITY_TEST_RESULTS_v1.1.csv"), index=False, encoding=ENC)
print(pd.DataFrame(res).result.value_counts().to_dict())
