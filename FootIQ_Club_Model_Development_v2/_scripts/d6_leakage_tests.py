"""Leakage and train/inference parity tests for the v2 feature generator (development data only)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
import v2_features as vf  # noqa

sys.stdout.reconfigure(encoding="utf-8")
meta = json.load(open(os.path.join(WORK, "features_v2_meta.json")))
P2 = meta["elo2_params"]; params = (P2["K"], P2["HA"], P2["season_regression"])
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
Vd = V[V.match_date <= DEV_END]
df = pd.DataFrame(dict(record_id=Vd.record_id, dt=Vd.dt, h=Vd.home_entity_id, a=Vd.away_entity_id, comp=Vd.competition_id, season=Vd.season_corrected, tier=Vd.tier,
                       ctype=Vd.competition_type, regular=Vd.regular_round_robin_stage, rated=Vd.rated, gh=Vd.gh, ga=Vd.ga))
full = pd.read_pickle(os.path.join(WORK, "features_v2_dev.pkl"))
want = set(full.index)
num = [c for c in full.columns if full[c].dtype.kind in "fiu" and c not in ("y",)]
res = []

# Test 1: future-perturbation. Replace every score on/after T by random scores AND drop all matches after T+30d; features for matches dated <= T must be bit-identical.
rng = np.random.default_rng(SEED)
for T in ("2019-12-31", "2021-12-31", "2023-06-30"):
    Tt = pd.Timestamp(T)
    d2 = df[df.dt <= Tt + pd.Timedelta(days=30)].copy()
    m = d2.dt > Tt
    d2.loc[m, "gh"] = rng.integers(0, 6, m.sum()); d2.loc[m, "ga"] = rng.integers(0, 6, m.sum())
    # same-day check: also scramble the scores of matches ON day T itself (their own features may not depend on them)
    onT = d2.dt == Tt
    d2.loc[onT, "gh"] = rng.integers(0, 6, onT.sum()); d2.loc[onT, "ga"] = rng.integers(0, 6, onT.sum())
    ids = set(df[df.dt <= Tt].record_id) & want
    Fp = vf.build(d2, ids, params)
    common = Fp.index.intersection(full.index); num = [c for c in num if c in Fp.columns]
    a, b = Fp.loc[common, num], full.loc[common, num]
    bad = [c for c in num if not np.allclose(a[c].values.astype(float), b[c].values.astype(float), equal_nan=True, rtol=0, atol=1e-9)]
    res.append(dict(test="future scores scrambled + later matches removed", cutoff=T, rows_compared=len(common), differing_columns=";".join(bad), passed=len(bad) == 0))
    print(res[-1], flush=True)

# Test 2: consistency of v2 'elo1' against the v1 contract Elo (same K20/HA60 algorithm) on the development rows
F1 = pd.read_pickle(os.path.join(WORK, "features_v1_dev.pkl")).set_index("record_id")
j = full.join(F1[["home_elo", "away_elo", "elo_diff"]], how="inner")
dmax = float((j.elo1_diff - j.elo_diff).abs().max())
res.append(dict(test="v2 elo1_diff equals v1 contract elo_diff", cutoff="all dev", rows_compared=len(j), differing_columns=f"max abs diff {dmax:.6f}", passed=dmax < 1e-6))
print(res[-1])

# Test 3: no feature is a function of the row's own result (correlation of each numeric feature with goal difference computed on dev rows is reported; identical-to-label check)
gd = (Vd.set_index("record_id").gh - Vd.set_index("record_id").ga).reindex(full.index)
cor = full[num].corrwith(gd).abs().sort_values(ascending=False)
res.append(dict(test="max |corr(feature, own goal difference)| (informational; Elo/form legitimately correlate)", cutoff="all dev", rows_compared=len(full), differing_columns=f"{cor.index[0]}={cor.iloc[0]:.3f}", passed=bool(cor.iloc[0] < 0.5)))
print(res[-1])

# Test 4: inference parity - a fixture with unknown result: features of the last development day computed with the result columns of that day removed (set to NaN-free placeholder 0-0, flagged unrated)
T = df.dt.max()
d3 = df.copy(); mk = d3.dt == T
d3.loc[mk, ["gh", "ga"]] = 0; d3.loc[mk, "rated"] = False
Fi = vf.build(d3, set(df[mk].record_id) & want, params)
c = Fi.index.intersection(full.index); num = [k for k in num if k in Fi.columns]
bad = [k for k in num if not np.allclose(Fi.loc[c, k].values.astype(float), full.loc[c, k].values.astype(float), equal_nan=True, rtol=0, atol=1e-9)]
res.append(dict(test="inference parity: features for a fixture are identical when its own result is placeholder", cutoff=str(T.date()), rows_compared=len(c), differing_columns=";".join(bad), passed=len(bad) == 0))
print(res[-1])
pd.DataFrame(res).to_csv(os.path.join(WORK, "leakage_parity_tests.csv"), index=False)
print("ALL PASSED" if all(r["passed"] for r in res) else "FAILURES")
