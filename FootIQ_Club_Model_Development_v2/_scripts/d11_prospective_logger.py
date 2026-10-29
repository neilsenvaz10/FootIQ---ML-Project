"""Prospective prediction logger for the frozen v2-r1 candidate and the frozen v1 reference (original v1 artifacts).
Inference-mode feature generation shares V2State / the v1 contract code with training; fixtures never update the state.

usage (library):  make_predictions(fixtures_df, results_snapshot_df, cutoff_ts)  /  append_batch(records, log_dir)
CLI dry run:      python d11_prospective_logger.py --dry-run     (writes only to final_refit_v2_r1/prospective_log/DRY_RUN, never counted)
"""
import hashlib
import json
import os
import pickle
import stat
import sys
import time

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
from v2_models import add_derived, Prep  # noqa  (Prep needed to unpickle the artifact)
import v2_features as vf  # noqa
sys.path.insert(0, os.path.join(PREP, "_build"))
import feature_contract as fc  # noqa

FD = os.path.join(OUT, "final_refit_v2_r1")
AD = os.path.join(FD, "artifacts")
V1A = os.path.join(V1, "artifacts")
MODEL_VERSION_V2 = "club_v2_lr_final_candidate v2-r1"
MODEL_VERSION_V1 = "club_v1 multinomial_logreg (frozen 2026-10-20)"


def load_models():
    v2 = pickle.load(open(os.path.join(AD, "club_v2_lr_final_candidate.pkl"), "rb"))
    v1 = pickle.load(open(os.path.join(V1A, "multinomial_logreg.pkl"), "rb"))
    v1prep = json.load(open(os.path.join(V1A, "preprocessing_train_fitted.json")))
    v1elo = json.load(open(os.path.join(V1A, "baseline_parameters.json")))["elo_ordered_logit"]
    return v2, v1, v1prep, v1elo


def v1_proba(v1, prep, frame):
    FEAT = prep["feature_order"]
    x = frame[FEAT].copy()
    ind = np.column_stack([x[c].isna().astype(float).values for c in prep["indicator_columns"]])
    x = x.fillna(pd.Series(prep["median_train"]))
    z = ((x - pd.Series(prep["mean_train"])) / pd.Series(prep["std_train"])).values
    return v1.predict_proba(np.hstack([z, ind]))


def v1_elo_proba(p, d):
    z = p["scale_per_100_elo"] * np.asarray(d) / 100.0
    pA = expit(p["threshold_away_draw"] - z); pAD = expit(p["threshold_draw_home"] - z)
    return np.column_stack([1 - pAD, pAD - pA, pA])


def universe_frame(V):
    return pd.DataFrame(dict(record_id=V.record_id, dt=V.dt, h=V.home_entity_id, a=V.away_entity_id, comp=V.competition_id, season=V.season_corrected, tier=V.tier,
                             ctype=V.competition_type, regular=V.regular_round_robin_stage, rated=V.rated, gh=V.gh, ga=V.ga))


def features_for(V, fx):
    """V: results snapshot (only completed matches dated strictly before the fixtures are used by construction of the state machine).
    fx: DataFrame fixture_id, dt, h, a, comp, season, tier. Returns (v2 feature frame, v1 feature frame) indexed by fixture_id."""
    base = universe_frame(V)
    f = pd.DataFrame(dict(record_id=fx.fixture_id.values, dt=fx.dt.values, h=fx.h.values, a=fx.a.values, comp=fx.comp.values, season=fx.season.values, tier=fx.tier.values, ctype="domestic_league",
                          regular=True, rated=False, gh=np.nan, ga=np.nan, is_fixture=True))
    base = base[base.dt < fx.dt.max() + pd.Timedelta(days=1)].copy(); base["is_fixture"] = False
    allr = pd.concat([base, f], ignore_index=True)
    meta = json.load(open(os.path.join(WORK, "features_v2_meta.json")))["elo2_params"]
    F2 = vf.build(allr, set(f.record_id), (meta["K"], meta["HA"], meta["season_regression"]))
    fr = allr.rename(columns={"h": "home", "a": "away"})[["record_id", "dt", "home", "away", "tier", "rated", "gh", "ga"]].copy()
    fr["completed"] = ~allr.is_fixture.values
    fr["want_features"] = allr.is_fixture.values
    F1 = fc.build_features(fr).set_index("record_id")
    return add_derived(F2), F1


def make_predictions(fx, V, availability_cutoff, input_version, prediction_ts):
    v2, v1, v1prep, v1elo = load_models()
    F2, F1 = features_for(V, fx)
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    P2 = v2["model"].predict_proba(v2["prep"].transform(F2, True))
    P1 = v1_proba(v1, v1prep, F1)
    PE = v1_elo_proba(v1elo, F1.elo_diff.values)
    out = []
    for i, r in enumerate(fx.itertuples()):
        n_h, n_a = int(F2.home_n_prior.iloc[i]), int(F2.away_n_prior.iloc[i])
        v11_ok = bool(n_h >= 5 and n_a >= 5 and F1.pair_connected_asof.iloc[i])
        out.append(dict(fixture_id=r.fixture_id, competition_id=r.comp, season=r.season, home_team=r.home_name, away_team=r.away_name, home_entity_id=r.h, away_entity_id=r.a,
                        scheduled_kickoff=r.kickoff, kickoff_time_known=bool(r.kickoff_known), prediction_timestamp=prediction_ts, feature_availability_cutoff=availability_cutoff,
                        latest_result_date_in_input=str(V.match_date.max()), input_data_version=input_version,
                        model_version=MODEL_VERSION_V2, p_home=float(P2[i, 0]), p_draw=float(P2[i, 1]), p_away=float(P2[i, 2]),
                        reference_v1_model_version=MODEL_VERSION_V1, v1_p_home=float(P1[i, 0]), v1_p_draw=float(P1[i, 1]), v1_p_away=float(P1[i, 2]),
                        v1_elo_p_home=float(PE[i, 0]), v1_elo_p_draw=float(PE[i, 1]), v1_elo_p_away=float(PE[i, 2]),
                        home_n_prior=n_h, away_n_prior=n_a, eligible_dataset_v1_1_rule=v11_ok,
                        eligibility_status="eligible" if v11_ok else "logged_not_in_primary_set (history<5 or Elo-disconnected)",
                        v2_feature_sha256=hashlib.sha256(np.ascontiguousarray(F2[v2["features"]].values.astype(float)[i]).tobytes()).hexdigest()))
    return out


def append_batch(records, log_dir, batch_name):
    """Writes an immutable (read-only) JSONL batch whose records are hash-chained to the previous batch; a chain index is kept in CHAIN.jsonl."""
    os.makedirs(log_dir, exist_ok=True)
    chain = os.path.join(log_dir, "CHAIN.jsonl")
    prev = "GENESIS"
    if os.path.exists(chain):
        last = [json.loads(x) for x in open(chain, encoding="utf-8") if x.strip()][-1]
        prev = last["batch_sha256"]
    path = os.path.join(log_dir, f"{batch_name}.jsonl")
    assert not os.path.exists(path), "batch exists"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in records:
            r = dict(r, prev_batch_sha256=prev)
            fh.write(json.dumps(r, sort_keys=True, default=str) + "\n")
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    with open(chain, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(dict(batch=batch_name, batch_sha256=h, prev_batch_sha256=prev, n_records=len(records), written_at=time.strftime("%Y-%m-%d %H:%M:%S %z"))) + "\n")
    os.chmod(path, stat.S_IREAD)
    return path, h


def verify_chain(log_dir):
    prev, ok = "GENESIS", True
    for line in open(os.path.join(log_dir, "CHAIN.jsonl"), encoding="utf-8"):
        c = json.loads(line)
        ok &= c["prev_batch_sha256"] == prev and hashlib.sha256(open(os.path.join(log_dir, c["batch"] + ".jsonl"), "rb").read()).hexdigest() == c["batch_sha256"]
        prev = c["batch_sha256"]
    return ok


def dry_run():
    V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
    u = pd.read_csv(os.path.join(P, "FootIQ_Dataset_Submission", "09_Upcoming_Fixtures.csv"), low_memory=False)
    u = u[(u.competition_type == "domestic_league") & (u.fixture_status == "upcoming") & (u.match_date >= "2026-10-22") & (u.match_date <= "2026-11-05")].copy()
    ent = pd.concat([V[["competition_id", "home_team_name", "home_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1), V[["competition_id", "away_team_name", "away_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1)]).drop_duplicates(["competition_id", "n"], keep="last")
    u = u.merge(ent.rename(columns={"n": "home_team", "e": "h"}), on=["competition_id", "home_team"], how="left").merge(ent.rename(columns={"n": "away_team", "e": "a"}), on=["competition_id", "away_team"], how="left")
    tier = V.groupby("competition_id").tier.first()
    unresolved = int(u.h.isna().sum() + u.a.isna().sum())
    u = u.dropna(subset=["h", "a"])
    fx = pd.DataFrame(dict(fixture_id=u.match_id.values, dt=pd.to_datetime(u.match_date).values, h=u.h.values, a=u.a.values, comp=u.competition_id.values, season=u.season.values,
                           tier=u.competition_id.map(tier).values, home_name=u.home_team.values, away_name=u.away_team.values,
                           kickoff=(u.match_date + " " + u.kickoff_time_local.fillna("00:00")).values, kickoff_known=u.kickoff_time_local.notna().values))
    ts = time.strftime("%Y-%m-%d %H:%M:%S %z")
    recs = make_predictions(fx, V, "results in the 2026-10-20 snapshot (latest result dated " + str(V.match_date.max()) + ")", "dataset_v1.1_2026-10-20+fixtures_2026-10-15", ts)
    for r in recs:
        r["DRY_RUN_NOT_COUNTED"] = True
    d = os.path.join(FD, "prospective_log", "DRY_RUN")
    if os.path.exists(os.path.join(d, "CHAIN.jsonl")):
        for f in os.listdir(d):
            os.chmod(os.path.join(d, f), stat.S_IWRITE); os.remove(os.path.join(d, f))
    path, h = append_batch(recs, d, "dry_run_batch_001")
    pdq = pd.DataFrame(recs)
    print("fixtures", len(fx), "unresolved team names dropped", unresolved, "predictions", len(recs), "chain ok", verify_chain(d))
    print(pdq[["p_home", "p_draw", "p_away"]].describe().round(3).to_string())
    print("eligible per v1.1 rule:", int(pdq.eligible_dataset_v1_1_rule.sum()), "sum-to-1 ok:", bool(np.allclose(pdq[["p_home", "p_draw", "p_away"]].sum(1), 1)))
    print(path, h)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--dry-run" in sys.argv:
        dry_run()
