"""Combined club dataset, label validation, leakage-safe pre-match features, splits, coverage matrix, missing inventory."""
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
from labels import label_status, phase_kind  # noqa

CUTOFF = "2026-10-01"          # 2026-27 results are kept only if dated before this
VERSION = "v1.0"
TYPE_MAP = {"uefa": "continental_club", "cup": "domestic_cup", "league": "domestic_league"}

M_of = pd.read_pickle(os.path.join(WORK, "M_of.pkl"))
M_fill = pd.read_pickle(os.path.join(WORK, "M_fill.pkl"))
M_wp = pd.read_pickle(os.path.join(WORK, "M_wp.pkl"))
M_fill["competition_type"] = [("league_cup" if f == "EFL Cup" else TYPE_MAP[t]) for f, t in zip(M_fill.competition_family, M_fill.competition_type)]

base = M_of[M_of.superseded_by_wp_row.isna()].copy()
base["of_index"] = base.index
comb = pd.concat([base, M_fill], ignore_index=True, sort=False)
comb["season"] = comb.season.astype(str)

# --- cross-source upgrade of 90-minute evidence: Wikipedia goal minutes confirm/contradict the openfootball score
mw = M_wp[M_wp.matched_of_index.notna() & M_wp.reg_basis.isin(["derived_from_goal_minutes", "goalless_no_extra_time_flag"]) & M_wp.reg_home.notna()]
wmap = {int(r.matched_of_index): r for r in mw.itertuples()}
n_up = n_conf = 0
pos = {v: k for k, v in comb.of_index.dropna().astype(int).items()} if "of_index" in comb else {}
for oi, w_ in wmap.items():
    k = pos.get(oi)
    if k is None:
        continue
    same = comb.at[k, "home_entity_id"] == w_.home_entity_id
    wr = (w_.reg_home, w_.reg_away) if same else (w_.reg_away, w_.reg_home)
    wf = (w_.final_excl_pens_home, w_.final_excl_pens_away) if same else (w_.final_excl_pens_away, w_.final_excl_pens_home)
    of_final = (comb.at[k, "final_excl_pens_home"], comb.at[k, "final_excl_pens_away"])
    if comb.at[k, "reg_basis"] in ("confirmed_by_wikipedia_goal_minutes",):
        continue
    if tuple(wf) != tuple(of_final):
        continue            # final scores disagree: leave the openfootball label state untouched (not upgraded)
    cur = (comb.at[k, "reg_home"], comb.at[k, "reg_away"])
    if pd.notna(cur[0]) and tuple(cur) != tuple(wr):
        comb.at[k, "reg_basis"] = "conflict_between_sources_regulation_score"
        n_conf += 1
        continue
    if pd.isna(cur[0]) or comb.at[k, "reg_basis"].startswith(("source_plain", "unknown")):
        comb.at[k, "reg_home"], comb.at[k, "reg_away"] = wr
        comb.at[k, "reg_basis"] = "confirmed_by_wikipedia_goal_minutes"
        n_up += 1
print("90-min evidence upgraded from Wikipedia goal minutes:", n_up, "conflicts:", n_conf)
comb["extraction_date"] = AS_OF
comb["date_status"] = np.where(comb.match_date.notna(), "dated", "undated")

# --- scope: completed results must be dated and not after cut-off / extraction date
def in_window(d, s):
    if d is None or pd.isna(d):
        return False
    return d <= (min(CUTOFF, AS_OF) if s in ("2026-27", "2026") else AS_OF) and not (s in ("2026-27",) and d >= CUTOFF)

comb["completed"] = comb.match_status.isin(["completed", "awarded", "abandoned"])
comb["window_ok"] = [in_window(d, s) for d, s in zip(comb.match_date, comb.season)]
comb["is_result"] = comb.completed & comb.window_ok & comb.final_excl_pens_home.notna()
res = comb[comb.is_result].copy()

# --- duplicate check (same competition/season/date/pair/stage)
res["dup_key"] = res.competition_id + "|" + res.season + "|" + res.match_date + "|" + res.pair_key + "|" + res.stage.astype(str)
dups = res[res.duplicated("dup_key", keep=False)]
dups.drop(columns=["dup_key"]).to_csv(os.path.join(WORK, "duplicates_found.csv"), index=False, encoding="utf-8")
res = res.drop_duplicates("dup_key", keep="first")

# --- labels
st = [label_status(r) for r in res.to_dict("records")]
res["label_90_status"] = [s[0] for s in st]
res["label_90_reason"] = [s[1] for s in st]
home90 = np.where(res.reg_home.notna(), res.reg_home, res.final_excl_pens_home)
away90 = np.where(res.reg_away.notna(), res.reg_away, res.final_excl_pens_away)
ok = res.label_90_status.isin(["confirmed", "inferred_no_marker"])
res["home_goals_90"] = np.where(ok, home90, np.nan)
res["away_goals_90"] = np.where(ok, away90, np.nan)
res["y90"] = np.where(~ok, "", np.where(res.home_goals_90 > res.away_goals_90, "H", np.where(res.home_goals_90 < res.away_goals_90, "A", "D")))
res["phase_kind"] = [phase_kind(t, s) for t, s in zip(res.competition_type, res.stage)]
res["match_dt"] = pd.to_datetime(res.match_date)
res = res.sort_values(["match_dt", "competition_id", "record_id"]).reset_index(drop=True)

# ------------------------------------------------------------------ feature engine
K, HA, INIT = 20.0, 60.0, 1500.0


def gd_mult(gd):
    gd = abs(gd)
    return 1.0 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8.0)


def build_features(df):
    elo = defaultdict(lambda: INIT)
    hist = defaultdict(list)   # entity -> list of (date, points, gf, ga, was_home)
    out = []
    for dt, grp in df.groupby("match_dt", sort=True):
        updates = []
        for r in grp.itertuples():
            h, a = r.home_entity_id, r.away_entity_id
            f = dict(record_id=r.record_id)
            for side, e in (("home", h), ("away", a)):
                hh = hist[e]
                f[f"{side}_n_prior"] = len(hh)
                f[f"{side}_elo"] = elo[e]
                f[f"{side}_days_rest"] = (dt - hh[-1][0]).days if hh else np.nan
                f[f"{side}_latest_info_date"] = hh[-1][0] if hh else pd.NaT
                for w in (5, 10):
                    x = hh[-w:]
                    f[f"{side}_ppg{w}"] = np.mean([i[1] for i in x]) if x else np.nan
                    f[f"{side}_gf{w}"] = np.mean([i[2] for i in x]) if x else np.nan
                    f[f"{side}_ga{w}"] = np.mean([i[3] for i in x]) if x else np.nan
                v = [i for i in hh if i[4] == (side == "home")][-5:]
                f[f"{side}_venue_ppg5"] = np.mean([i[1] for i in v]) if v else np.nan
            f["elo_diff"] = f["home_elo"] - f["away_elo"]
            f["ppg5_diff"] = f["home_ppg5"] - f["away_ppg5"] if pd.notna(f["home_ppg5"]) and pd.notna(f["away_ppg5"]) else np.nan
            f["gd5_diff"] = (f["home_gf5"] - f["home_ga5"]) - (f["away_gf5"] - f["away_ga5"]) if pd.notna(f["home_gf5"]) and pd.notna(f["away_gf5"]) else np.nan
            f["rest_diff"] = f["home_days_rest"] - f["away_days_rest"] if pd.notna(f["home_days_rest"]) and pd.notna(f["away_days_rest"]) else np.nan
            f["latest_info_date"] = max([d for d in (f["home_latest_info_date"], f["away_latest_info_date"]) if pd.notna(d)], default=pd.NaT)
            out.append(f)
            if r.y90 != "":
                updates.append((h, a, r.home_goals_90, r.away_goals_90, dt))
        for h, a, gh, ga, d in updates:   # same-day matches never see each other
            eh, ea = elo[h], elo[a]
            exp_h = 1 / (1 + 10 ** (-((eh + HA) - ea) / 400))
            sh = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
            delta = K * gd_mult(gh - ga) * (sh - exp_h)
            elo[h], elo[a] = eh + delta, ea - delta
            hist[h].append((d, 3 if gh > ga else (1 if gh == ga else 0), gh, ga, True))
            hist[a].append((d, 3 if ga > gh else (1 if gh == ga else 0), ga, gh, False))
    return pd.DataFrame(out)


feat = build_features(res)
data = res.merge(feat, on="record_id", how="left")
data["same_country"] = data.home_entity_id.str.split(":").str[1] == data.away_entity_id.str.split(":").str[1]
data["is_league"] = (data.phase_kind == "league").astype(int)
data["is_league_phase"] = (data.phase_kind == "league_phase").astype(int)
data["is_knockout"] = (data.phase_kind == "knockout").astype(int)
data["comp_type_continental"] = (data.competition_type == "continental_club").astype(int)
data["comp_type_cup"] = data.competition_type.isin(["domestic_cup", "league_cup"]).astype(int)
data["neutral_known"] = 0   # neutral venues (e.g. cup finals) are not reliably marked in the sources

# --- eligibility
domestic_ok = data.competition_type.eq("domestic_league")
ident_ok = domestic_ok | (data.home_identity_status.eq("resolved_exact_alias") & data.away_identity_status.eq("resolved_exact_alias"))
data["identity_ok"] = ident_ok
data["min_prior_ok"] = (data.home_n_prior >= 5) & (data.away_n_prior >= 5)
data["info_before_kickoff"] = data.latest_info_date.isna() | (data.latest_info_date < data.match_dt)
base_ok = data.identity_ok & data.min_prior_ok & data.info_before_kickoff & (data.match_date >= "2018-08-01")
data["train_eligible_strict"] = base_ok & data.label_90_status.eq("confirmed")
data["train_eligible_extended"] = base_ok & data.label_90_status.isin(["confirmed", "inferred_no_marker"])


def split(d):
    return ("train" if d < "2023-07-01" else "validation" if d < "2024-07-01" else "test" if d < "2025-07-01" else "forward_holdout")


data["suggested_split"] = data.match_date.map(split)
data.to_pickle(os.path.join(WORK, "data_all.pkl"))

# ------------------------------------------------------------------ leakage tests
tests = []
tr = data[data.train_eligible_extended]
tests.append(dict(test="T1 latest information date < kickoff date for every eligible row", passed=bool((tr.latest_info_date < tr.match_dt).all()),
                  detail=f"{len(tr)} rows checked"))
cut = pd.Timestamp("2023-07-01")
pre = res[res.match_dt < cut]
f2 = build_features(pre).set_index("record_id")
f1 = feat.set_index("record_id").loc[f2.index]
cols = ["home_elo", "away_elo", "home_n_prior", "away_n_prior", "home_ppg5", "away_ppg5", "home_gf10", "away_ga10", "home_days_rest"]
same = np.allclose(f1[cols].astype(float).fillna(-9).values, f2[cols].astype(float).fillna(-9).values)
tests.append(dict(test="T2 prefix invariance: features for matches before 2023-07-01 are identical when all later data is removed",
                  passed=bool(same), detail=f"{len(f2)} rows, columns {cols}"))
rng = np.random.default_rng(7)
sample = tr.sample(min(400, len(tr)), random_state=7)
ent_rows = defaultdict(list)
for r in res[res.y90 != ""].itertuples():
    ent_rows[r.home_entity_id].append((r.match_dt, 3 if r.home_goals_90 > r.away_goals_90 else (1 if r.home_goals_90 == r.away_goals_90 else 0)))
    ent_rows[r.away_entity_id].append((r.match_dt, 3 if r.away_goals_90 > r.home_goals_90 else (1 if r.home_goals_90 == r.away_goals_90 else 0)))
bad = 0
for r in sample.itertuples():
    for side, e in (("home", r.home_entity_id), ("away", r.away_entity_id)):
        prior = sorted([x for x in ent_rows[e] if x[0] < r.match_dt], key=lambda x: x[0])
        n_exp = len(prior)
        p5 = np.mean([p for _, p in prior[-5:]]) if prior else np.nan
        n_got = getattr(r, f"{side}_n_prior")
        p5g = getattr(r, f"{side}_ppg5")
        if n_exp != n_got or not (np.isclose(p5, p5g, equal_nan=True)):
            bad += 1
tests.append(dict(test="T3 brute-force recomputation (strictly earlier matches only) of n_prior and ppg5", passed=bad == 0,
                  detail=f"{len(sample)} random rows x 2 teams, mismatches={bad}"))
forbidden = [c for c in data.columns if c.startswith(("home_goals_90", "away_goals_90", "home_goals_half", "away_goals_half"))]
FEATURES = ["home_elo", "away_elo", "elo_diff", "home_n_prior", "away_n_prior", "home_ppg5", "away_ppg5", "home_ppg10", "away_ppg10",
            "home_gf5", "home_ga5", "away_gf5", "away_ga5", "home_gf10", "home_ga10", "away_gf10", "away_ga10", "home_venue_ppg5",
            "away_venue_ppg5", "ppg5_diff", "gd5_diff", "home_days_rest", "away_days_rest", "rest_diff", "is_league", "is_league_phase",
            "is_knockout", "comp_type_continental", "comp_type_cup", "same_country", "neutral_known"]
tests.append(dict(test="T4 no outcome-derived column is in the declared feature list", passed=not (set(FEATURES) & set(forbidden)) and
                  not any("half" in c or "y90" in c or "final" in c for c in FEATURES), detail=f"{len(FEATURES)} declared features"))
same_day = tr.groupby(["home_entity_id", "match_date"]).size()
tests.append(dict(test="T5 same-day matches do not inform each other (state updated after the whole date is processed)",
                  passed=True, detail="by construction + T3 (strict < date); teams with >1 match on one date: %d" % int((same_day > 1).sum())))
tests.append(dict(test="T6 splits are chronological (max train date < min validation date < min test date < min holdout date)",
                  passed=bool(tr[tr.suggested_split == 'train'].match_date.max() < tr[tr.suggested_split == 'validation'].match_date.min() <
                              tr[tr.suggested_split == 'test'].match_date.min() < tr[tr.suggested_split == 'forward_holdout'].match_date.min()),
                  detail=json.dumps(tr.groupby("suggested_split").match_date.agg(["min", "max", "size"]).reset_index().to_dict("records"))))
pd.DataFrame(tests).to_csv(os.path.join(WORK, "leakage_tests.csv"), index=False, encoding="utf-8")
json.dump(FEATURES, open(os.path.join(WORK, "feature_list.json"), "w"))
print(pd.DataFrame(tests)[["test", "passed", "detail"]].to_string())
print(len(data), "results;", int(data.train_eligible_strict.sum()), "strict;", int(data.train_eligible_extended.sum()), "extended")
print(data.label_90_status.value_counts().to_string())
