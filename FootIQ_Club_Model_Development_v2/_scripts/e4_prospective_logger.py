"""Official/dry-run prospective prediction logger: original v1 LR, matched v1 refit, frozen v2-r1 (plus v1 Elo mapping as a reference).

Guarantees enforced in code:
  * model/artifact hashes verified against the freeze records before any prediction;
  * a fixture is rejected (never logged) if its earliest possible kickoff (match date 00:00 UTC minus 14 h, since local kickoff times/time zones are mostly unknown) is not at least 60 minutes
    after the prediction timestamp, or if the snapshot already holds a result for it -> no backdating, no predictions for completed matches;
  * batches are written once, read-only, hash-chained; dry runs go to a separate DRY_RUN chain and carry counts_for_evaluation=False;
  * OFFICIAL mode refuses to run without the owner's approval file and a matching pre-registration hash.
"""
import hashlib, json, os, pickle, stat, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
import d11_prospective_logger as D  # noqa  (feature generation + v1/v2 scoring helpers)

NEW = os.path.join(OUT, "matched_v1_prospective_r1")
MAD = os.path.join(NEW, "artifacts")
LOGDIR = os.path.join(NEW, "prospective_log")
APPROVAL = os.path.join(NEW, "OFFICIAL_LOGGING_APPROVED.json")           # created by the owner, never by this code
PREREG = os.path.join(NEW, "PREREGISTRATION_r1.json")
EXCL = json.load(open(os.path.join(NEW, "eligibility_exclusions_r1.json")))
MODELS = {"v1_original": "FootIQ_Club_Model_Baseline_v1 multinomial_logreg (frozen 2026-10-20, sha 067426e8)", "v1_matched": "matched-v1-r1 (original v1 recipe refit on the v2-r1 training rows)",
          "v2_frozen": D.MODEL_VERSION_V2, "v1_elo": "v1 Elo ordered-logit mapping (frozen)"}
MIN_LEAD = pd.Timedelta(minutes=60)
STALE_DAYS = 14


def verify_models():
    fr = json.load(open(os.path.join(D.AD, "FROZEN.json")))
    mv = json.load(open(os.path.join(MAD, "MATCHED_V1_FROZEN.json")))
    v1f = json.load(open(os.path.join(V1, "artifacts", "FROZEN.json")))
    out = {}
    for f, h in fr["artifact_sha256"].items():
        out[f"v2/{f}"] = sha(os.path.join(D.AD, f)) == h
    for f, h in mv["artifact_sha256"].items():
        out[f"matched_v1/{f}"] = sha(os.path.join(MAD, f)) == h
    out["v1/multinomial_logreg.pkl"] = sha(os.path.join(V1, "artifacts", "multinomial_logreg.pkl")) == v1f["artifact_sha256"]["multinomial_logreg.pkl"]
    if not all(out.values()):
        raise RuntimeError(f"model integrity failure: {out}")
    return dict(v2=fr["artifact_sha256"]["club_v2_lr_final_candidate.pkl"], matched_v1=mv["artifact_sha256"]["matched_v1_lr_refit.pkl"], v1_original=v1f["artifact_sha256"]["multinomial_logreg.pkl"])


def matched_v1_proba(F1):
    prep = json.load(open(os.path.join(MAD, "matched_v1_preprocessing.json")))
    mdl = pickle.load(open(os.path.join(MAD, "matched_v1_lr_refit.pkl"), "rb"))
    return D.v1_proba(mdl, prep, F1)


def earliest_kickoff_utc(date, time_local):
    return pd.Timestamp(str(date)[:10], tz="UTC") - pd.Timedelta(hours=14)


def predict(fixtures, results_universe, past_no_result, snapshot_id, snapshot_sha, mode, now=None):
    """fixtures: DataFrame(fixture_id, dt, h, a, comp, season, tier, home_name, away_name, kickoff, kickoff_known). Returns (records, rejects)."""
    hashes = verify_models()
    if mode == "official":
        if not os.path.exists(APPROVAL) or not os.path.exists(PREREG):
            raise PermissionError("official logging needs the owner's approval file and the pre-registration file")
        ap = json.load(open(APPROVAL))
        if ap.get("model_hashes") != hashes:
            raise PermissionError("approval file does not match the frozen model hashes")
    now = now or pd.Timestamp.now(tz="UTC")
    done = set(zip(results_universe.competition_id, results_universe.match_date.astype(str), results_universe.home_entity_id, results_universe.away_entity_id))
    keep, rej = [], []
    for r in fixtures.itertuples():
        reason = None
        if earliest_kickoff_utc(r.dt, r.kickoff) - now < MIN_LEAD:
            reason = "kickoff_not_at_least_60min_after_prediction_timestamp_(backdating_or_too_late)"
        elif (r.comp, str(pd.Timestamp(r.dt).date()), r.h, r.a) in done:
            reason = "result_already_in_snapshot"
        (rej if reason else keep).append((r, reason))
    rejects = pd.DataFrame([dict(fixture_id=r.fixture_id, reason=why, match_date=str(r.dt)[:10]) for r, why in rej], columns=["fixture_id", "reason", "match_date"])
    if not keep:
        return [], rejects
    fx = fixtures[fixtures.fixture_id.isin([r.fixture_id for r, _ in keep])].reset_index(drop=True)
    F2, F1 = D.features_for(results_universe, fx)
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    v2, v1, v1prep, v1elo = D.load_models()
    P2 = v2["model"].predict_proba(v2["prep"].transform(F2, True)); P1 = D.v1_proba(v1, v1prep, F1); PM = matched_v1_proba(F1); PE = D.v1_elo_proba(v1elo, F1.elo_diff.values)
    last_comp = results_universe.groupby("competition_id").match_date.max()
    bad_ent = {(e["competition_id"], e["entity_id"]) for e in EXCL["entities"]}
    unresolved_clubs = set()
    for r in past_no_result.itertuples():
        unresolved_clubs.add((r.comp, r.h)); unresolved_clubs.add((r.comp, r.a))
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    recs = []
    for i, r in enumerate(fx.itertuples()):
        reasons = []
        nh, na = int(F2.home_n_prior.iloc[i]), int(F2.away_n_prior.iloc[i])
        if not (nh >= 5 and na >= 5 and bool(F1.pair_connected_asof.iloc[i])): reasons.append("history_lt5_or_elo_disconnected")
        if (r.comp, r.h) in bad_ent or (r.comp, r.a) in bad_ent: reasons.append("identity_collision_unresolved")
        if (r.comp, r.h) in unresolved_clubs or (r.comp, r.a) in unresolved_clubs: reasons.append("club_has_unresolved_past_fixture")
        lc = last_comp.get(r.comp)
        gap = (pd.Timestamp(r.dt) - pd.Timestamp(lc)).days if lc is not None else None
        if gap is None or gap > STALE_DAYS: reasons.append(f"stale_competition_results(gap_days={gap})")
        flags = [] if r.kickoff_known else ["kickoff_time_unknown"]
        if r.comp == "world/africa:zw1": flags.append("zw1_history_date_anomaly_flag")
        recs.append(dict(fixture_id=r.fixture_id, competition_id=r.comp, season=r.season, home_team=r.home_name, away_team=r.away_name, home_entity_id=r.h, away_entity_id=r.a,
                         scheduled_kickoff=r.kickoff, kickoff_time_known=bool(r.kickoff_known), earliest_possible_kickoff_utc=str(earliest_kickoff_utc(r.dt, r.kickoff)),
                         prediction_timestamp_utc=ts, feature_availability_cutoff=f"results in snapshot {snapshot_id} (latest completed result in competition: {lc})", input_snapshot_id=snapshot_id, input_snapshot_sha256=snapshot_sha,
                         models={k: MODELS[k] for k in MODELS}, model_hashes=hashes,
                         probs=dict(v2_frozen=dict(H=float(P2[i, 0]), D=float(P2[i, 1]), A=float(P2[i, 2])), v1_original=dict(H=float(P1[i, 0]), D=float(P1[i, 1]), A=float(P1[i, 2])),
                                    v1_matched=dict(H=float(PM[i, 0]), D=float(PM[i, 1]), A=float(PM[i, 2])), v1_elo=dict(H=float(PE[i, 0]), D=float(PE[i, 1]), A=float(PE[i, 2]))),
                         home_n_prior=nh, away_n_prior=na, eligibility_reasons=reasons, primary_eligible=len(reasons) == 0, coverage_flags=flags,
                         counts_for_evaluation=(mode == "official"), mode=mode,
                         v2_feature_sha256=hashlib.sha256(np.ascontiguousarray(F2[v2["features"]].values.astype(float)[i]).tobytes()).hexdigest()))
    return recs, rejects


def append_batch(recs, mode, name=None):
    d = os.path.join(LOGDIR, "OFFICIAL" if mode == "official" else "DRY_RUN")
    name = name or f"{mode}_batch_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return D.append_batch(recs, d, name), d


def verify_chain(d):
    return D.verify_chain(d)
