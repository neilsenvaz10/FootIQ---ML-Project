"""Gameweek forecasts with the EXISTING frozen club models, saved only when the user presses "Predict gameweek".

Time safety (strict, by construction)
  * Every fixture is featurised from results dated STRICTLY BEFORE the fixture's date. Results on the fixture's own day are excluded, so it does not matter whether the
    kickoff time is known (an unknown kickoff can never leak a same-day result).
  * If a fixture is dated after every result in the store, the cached state is used (fast). If any fixture is dated on or before the newest result in the store
    (late, postponed or back-dated fixtures), the project's own day-by-day replay is used for those fixtures so that no later result of ANY competition reaches them.
  * Only fixtures whose kickoff has certainly not passed are forecast (kickoff.made_before_kickoff == "yes", Phase 4.8B); finished matches and fixtures awaiting a verified result
    are never "predicted in hindsight". A forecast saved earlier is never recalculated or overwritten.
Separation
  * Saved rows live in forecast_runs / forecasts of the application store. They are NOT the official prospective evaluation: nothing is written to any research folder,
    no ledger or protocol file is touched, and the model artifacts are only read.
"""
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd

import config as C
import gameweeks as gw
import kickoff as KO
import predict
from store import db as store_db

NOTE = "Application forecast history: saved because the user pressed Predict gameweek. Not part of the official prospective evaluation."
ARTIFACTS = {
    "club_v1": C.ROOT / "FootIQ_Club_Model_Baseline_v1" / "artifacts" / "multinomial_logreg.pkl",
    "club_v2_r1": C.ROOT / "FootIQ_Club_Model_Development_v2" / "final_refit_v2_r1" / "artifacts" / "club_v2_lr_final_candidate.pkl",
}
EXPLICIT_ACTION = "predict_gameweek_button"


class ForecastError(ValueError):
    pass


@lru_cache(maxsize=1)
def artifact_hashes() -> dict:
    return {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in ARTIFACTS.items()}


def model_ids() -> dict:
    lg, _, _ = predict._club_runtime()
    return {"club_v1": lg.MODEL_VERSION_V1, "club_v2_r1": lg.MODEL_VERSION_V2, "elo_baseline": "Elo ordered-logit mapping (part of the club v1 artifacts)"}


made_before_kickoff = KO.made_before_kickoff           # the rule lives in kickoff.py so the page, the forecast and the manual prediction share it


def _batch_features(df: pd.DataFrame, latest: pd.Timestamp):
    """Features and probabilities for fixture rows (fixture_id, dt, h, a, comp, season, tier). Returns list of scored dicts in df order and the path used per fixture."""
    scored: dict[str, dict] = {}
    path: dict[str, str] = {}
    late = df[df.dt <= latest]
    early = df[df.dt > latest]
    for r in early.itertuples():
        F2, F1 = predict.club_features_fast(r.h, r.a, r.comp, r.season, r.dt, r.tier)
        scored[r.fixture_id] = predict.club_score(F2, F1)[0]
        path[r.fixture_id] = "cached_state_before_all_results"
    if len(late):
        F2, F1 = predict.club_features_exact(late[["fixture_id", "dt", "h", "a", "comp", "season", "tier"]])
        for i, r in enumerate(late.itertuples()):
            scored[r.fixture_id] = predict.club_score(F2.iloc[[i]], F1.iloc[[i]])[0]
            path[r.fixture_id] = "day_by_day_replay"
    return scored, path


def predict_gameweek(key: str, season: str, matchday_no: int, user_action: str, now: Optional[datetime] = None, today: Optional[date] = None, db_path=None) -> dict:
    if user_action != EXPLICIT_ACTION:
        raise ForecastError("forecasts are saved only when the user explicitly presses Predict gameweek")
    gw.check_league(key)
    now = now or datetime.now(timezone.utc)
    today = today or now.date()
    conn = store_db.connect(db_path)
    try:
        data = gw.gameweek_fixtures(conn, key, season, matchday_no, today, now)
        eligible = [f for f in data["fixtures"] if f["predictable"]]
        if not eligible:
            raise ForecastError(f"Matchday {matchday_no} has no fixture that can still be forecast before kickoff (all are completed, past kickoff and awaiting a verified result, postponed or cancelled)")
        lg, V, tiers = predict._club_runtime()
        comp_id = C.BY_KEY[key]["source_id"]
        tier = tiers.get(comp_id, np.nan)
        model_entity = {r["record_id"]: (r["model_home_entity"] or r["home_entity_id"], r["model_away_entity"] or r["away_entity_id"])
                        for r in conn.execute(f"SELECT record_id, model_home_entity, model_away_entity, home_entity_id, away_entity_id FROM matches WHERE record_id IN ({','.join('?' * len(eligible))})", [f['record_id'] for f in eligible])}
        df = pd.DataFrame([dict(fixture_id=f["record_id"], dt=pd.Timestamp(f["date"]), h=model_entity[f["record_id"]][0], a=model_entity[f["record_id"]][1], comp=comp_id, season=season, tier=tier) for f in eligible])
        latest = V.dt.max()
        scored, path = _batch_features(df, latest)
        ids, hashes = model_ids(), artifact_hashes()
        cutoff = str(latest.date())
        results = []
        with conn:                                                   # one transaction: a failure saves nothing
            run_id = conn.execute("INSERT INTO forecast_runs(created_utc, competition_key, season, matchday_label, model_id, model_artifact_sha256, data_cutoff_date, data_cutoff_note, user_action, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                  (now.strftime("%Y-%m-%dT%H:%M:%SZ"), key, season, f"Matchday {matchday_no}", json.dumps(ids), json.dumps(hashes), cutoff,
                                   f"latest result in the model history (all competitions) {cutoff}; latest result in this competition {data['latest_result']}", user_action, NOTE)).lastrowid
            for f in eligible:
                s = scored[f["record_id"]]
                mb = f["kickoff_state"]                              # the page answer for this fixture under the shared rule (league zones, floor, disputes)
                rel = f["reliability"]
                reasons = list(f["reasons"])
                flags = list(f["flags"])
                if s["n_h"] < 5 or s["n_a"] < 5:
                    rel = "provisional"
                    flags.append("low_history")
                    reasons.append("Fewer than 5 earlier rated matches for at least one team.")
                if not s["connected"]:
                    rel = "provisional"
                    flags.append("ratings_not_connected")
                    reasons.append("The two teams are not connected in the rating graph at this date; their ratings are less comparable.")
                if mb != "yes":
                    flags.append("not_certainly_before_kickoff")
                    reasons.append("This forecast was saved when it cannot be shown to be before kickoff.")
                snap_v1, snap_v2 = json.dumps(s["v1_features"], sort_keys=True), json.dumps(s["v2_features"], sort_keys=True)
                snap_hash_v1 = hashlib.sha256(snap_v1.encode()).hexdigest()
                for variant, p, snap, h in (("club_v1", s["p1"], snap_v1, snap_hash_v1), ("club_v2_r1", s["p2"], snap_v2, hashlib.sha256(snap_v2.encode()).hexdigest()), ("elo_baseline", s["pe"], snap_v1, snap_hash_v1)):
                    conn.execute("INSERT INTO forecasts(forecast_run_id, record_id, p_home, p_draw, p_away, model_variant, feature_snapshot_json, feature_sha256, made_before_kickoff, reliability, flags_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                 (run_id, f["record_id"], float(p[0]), float(p[1]), float(p[2]), variant, snap, h, mb, rel, json.dumps(flags)))
                results.append(dict(record_id=f["record_id"], date=f["date"], home=f["home"], away=f["away"], reliability=rel, flags=flags, reasons=reasons, made_before_kickoff=mb, feature_path=path[f["record_id"]],
                                    predictions=dict(primary=dict(home=float(s["p1"][0]), draw=float(s["p1"][1]), away=float(s["p1"][2])), secondary=dict(home=float(s["p2"][0]), draw=float(s["p2"][1]), away=float(s["p2"][2])),
                                                     elo_only=dict(home=float(s["pe"][0]), draw=float(s["pe"][1]), away=float(s["pe"][2])))))
        return dict(forecast_run_id=run_id, created_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), competition_key=key, season=season, matchday_no=matchday_no, data_cutoff_date=cutoff, models=ids, artifact_sha256=hashes,
                    saved_fixtures=len(results), skipped=[dict(record_id=f["record_id"], home=f["home"], away=f["away"], status=f["status"]) for f in data["fixtures"] if not f["predictable"]],
                    note=NOTE, forecasts=results)
    finally:
        conn.close()
