"""Match-outcome prediction using the EXISTING frozen models. Nothing is trained or modified here.

Club competitions  -> club v1 (primary) and club v2-r1 (shown separately), both via the feature code the project already uses
                      for inference (FootIQ_Club_Model_Development_v2/_scripts/d11_prospective_logger.py -> make_predictions).
International       -> ARCHIVED (Phase 4.18): the v2.7 ensemble artifact and predict_intl() are kept, unused. The supported scope is the five domestic
                      leagues and the Champions League, all club competitions; predict() refuses every other competition.

Every result carries the competition's validation badge from config.py.
"""
import os
import re
import sys
import threading
from datetime import datetime, timezone
from functools import lru_cache

import numpy as np
import pandas as pd

import config as C
import analytics
import kickoff as KO

DEV = C.ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"
PREP_BUILD = C.ROOT / "FootIQ_ML_Training_Preparation" / "_build"
SCRIPTS = C.ROOT / "scripts"
V_UNIVERSE = PREP_BUILD / "work" / "V_universe.pkl"
V27_ARTIFACT = C.ROOT / "data" / "model_artifacts" / "v27" / "live_match_model.pkl"


class PredictionError(ValueError):
    """Raised for user-facing problems (unknown team, bad date, missing data)."""


HORIZON_NOTE_DAYS = 180


def _parse_date(date: str) -> pd.Timestamp:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
        raise PredictionError("date must be formatted YYYY-MM-DD")
    try:
        return pd.Timestamp(date)
    except ValueError as exc:
        raise PredictionError("date is not a valid calendar date") from exc


def _horizon_note(dt: pd.Timestamp, data_end: pd.Timestamp) -> list[str]:
    days = (dt - data_end).days
    if days > HORIZON_NOTE_DAYS:
        return [f"The prediction date is {days} days after the data ends ({data_end.date()}). Team ratings and form cannot reflect anything in between, so treat this as low-confidence."]
    return []


def _base(key: str) -> dict:
    comp = C.BY_KEY[key]
    return dict(competition_key=key, competition=comp["name"], validation_badge=comp["badge"], validation_basis=comp["basis"])


# ------------------------------------------------------------------------------------------------ club
@lru_cache(maxsize=1)
def _club_runtime():
    if not analytics.use_store() and not V_UNIVERSE.exists():
        raise PredictionError(f"club history file missing: {V_UNIVERSE.relative_to(C.ROOT)} (needed for feature construction)")
    for p in (str(DEV), str(PREP_BUILD)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import d11_prospective_logger as lg  # noqa: E402  (existing project code; importing it writes nothing)

    if analytics.use_store():                      # results store (baseline + synced results); identical to the frozen pickle for the baseline (tested)
        from store import db as store_db
        from store import views as store_views

        conn = store_db.connect(readonly=True)
        try:
            V = store_views.model_universe(conn)
        finally:
            conn.close()
    else:
        V = pd.read_pickle(V_UNIVERSE)
    tier = V.groupby("competition_id").tier.first()
    return lg, V, tier


@lru_cache(maxsize=1)
def _club_state():
    """Replay all history ONCE with the project's own state machines (same loop as v2_features.build / feature_contract.build_features),
    then answer any number of fixtures from the final state. Parity with make_predictions is checked in tests/test_miniproject.py."""
    import json

    lg, V, tier = _club_runtime()
    import v2_features as vf
    import feature_contract as fc

    meta = json.load(open(os.path.join(lg.WORK, "features_v2_meta.json")))["elo2_params"]
    st2, st1 = vf.V2State((meta["K"], meta["HA"], meta["season_regression"])), fc.ClubState()
    base = lg.universe_frame(V)
    for dt, g in base.sort_values(["dt", "record_id"], kind="mergesort").groupby("dt", sort=True):
        rows = list(g.itertuples())
        st2.apply_day(dt.toordinal(), [dict(h=r.h, a=r.a, comp=r.comp, season=r.season, ctype=r.ctype, regular=r.regular, rated=r.rated, gh=r.gh, ga=r.ga) for r in rows])
        st1.apply_day(dt, [dict(home=r.h, away=r.a, completed=True, rated=r.rated, gh=r.gh, ga=r.ga) for r in rows])
    return st2, st1, vf, fc


_BUILD_LOCK = threading.Lock()   # lru_cache does not stop two threads building the 30 s state at once


def club_features_fast(h, a, comp_id, season, dt, tier):
    """Features for ONE fixture from the cached state. Valid only when `dt` is later than every result in the store (the state contains no result on or after `dt`)."""
    lg, V, tiers = _club_runtime()
    with _BUILD_LOCK:
        st2, st1, vf, fc = _club_state()
    from v2_models import add_derived

    f2 = st2.features(h, a, comp_id, season, dt.toordinal(), tier)
    F = pd.DataFrame([f2])
    pH, pD, pA = vf.poisson_probs(F.lambda_home.fillna(1.4).values, F.lambda_away.fillna(1.1).values)
    nanrow = (F.lambda_home.isna() | F.lambda_away.isna()).values
    F["poisson_pH"], F["poisson_pD"], F["poisson_pA"] = np.where(nanrow, np.nan, pH), np.where(nanrow, np.nan, pD), np.where(nanrow, np.nan, pA)
    F["exp_goal_diff"] = F.lambda_home - F.lambda_away
    return add_derived(F), pd.DataFrame([st1.features(h, a, dt, tier)])


def club_features_exact(fixtures: pd.DataFrame):
    """Features for fixtures of ANY date, each from the state of the day before it: the project's own replay (`features_for`), which applies a day's results only AFTER
    the fixtures of that day are featurised. Slow (about 25 s, one replay for the whole batch). `fixtures`: fixture_id, dt, h, a, comp, season, tier."""
    lg, V, _ = _club_runtime()
    fx = fixtures.assign(home_name="x", away_name="x", kickoff="x", kickoff_known=False)
    F2, F1 = lg.features_for(V, fx)
    return F2.loc[fixtures.fixture_id], F1.loc[fixtures.fixture_id]


def club_score(F2: pd.DataFrame, F1: pd.DataFrame) -> list[dict]:
    """Frozen-model probabilities for feature rows (v1 primary, v2-r1 candidate, Elo-only baseline). No training, no state change."""
    lg, V, _ = _club_runtime()
    v2m, v1m, v1prep, v1elo = _club_models()
    p2 = v2m["model"].predict_proba(v2m["prep"].transform(F2, True))
    p1 = lg.v1_proba(v1m, v1prep, F1)
    pe = lg.v1_elo_proba(v1elo, F1.elo_diff.values)
    out = []
    for i in range(len(F1)):
        out.append(dict(p2=p2[i], p1=p1[i], pe=pe[i], n_h=int(F2.home_n_prior.iloc[i]), n_a=int(F2.away_n_prior.iloc[i]), connected=bool(F1.pair_connected_asof.iloc[i]),
                        f1=F1.iloc[i].to_dict(), v1_features={k: (None if pd.isna(F1.iloc[i][k]) else float(F1.iloc[i][k])) for k in v1prep["feature_order"]},
                        v2_features={k: (None if pd.isna(F2.iloc[i][k]) else float(F2.iloc[i][k])) for k in v2m["features"]}))
    return out


def _club_probs(h, a, comp_id, season, dt, tier):
    F2, F1 = club_features_fast(h, a, comp_id, season, dt, tier)
    r = club_score(F2, F1)[0]
    return r["p2"], r["p1"], r["pe"], r["n_h"], r["n_a"], r["connected"], r["f1"]


def reset_club_state() -> None:
    """Forget the cached history so the next prediction replays the (updated) store. Model weights are never touched."""
    _club_runtime.cache_clear()
    _club_state.cache_clear()


def warm_up():
    """Optional: build the cached club state at server start (about 30 s) so the first request is fast."""
    with _BUILD_LOCK:
        _club_state()
        _club_models()


@lru_cache(maxsize=1)
def _club_models():
    return _club_runtime()[0].load_models()


def club_ready() -> bool:
    """True once the club history state is built (first club prediction is then fast)."""
    return _club_state.cache_info().currsize == 1


def club_data_end() -> str:
    _, V, _ = _club_runtime()
    return str(V.match_date.max())[:10]


def _entity(key: str, team: str) -> str:
    d = analytics.matches()
    d = d[d.competition_key == key]
    for col_name, col_id in (("home", "home_entity_id"), ("away", "away_entity_id")):
        hit = d.loc[d[col_name] == team, col_id]
        if len(hit):
            return hit.iloc[-1]
    raise PredictionError(f"'{team}' has no matches in {C.BY_KEY[key]['name']} in the dataset")


def _stored_fixture(key: str, h: str, a: str, day: str):
    """The unplayed stored fixture of this exact pairing on this day, if any (read-only). None when the pairing is only a hypothetical matchup."""
    from store import db as store_db

    if not analytics.use_store() or not store_db.exists():
        return None
    conn = store_db.connect(readonly=True)
    try:
        row = conn.execute("SELECT record_id, match_date, kickoff_utc, status FROM matches WHERE competition_key=? AND match_date=? AND status IN ('scheduled','awaiting_result') "
                           "AND ((model_home_entity=? AND model_away_entity=?) OR (home_entity_id=? AND away_entity_id=?)) LIMIT 1", (key, day, h, a, h, a)).fetchone()
        if row is None:
            return None
        import disputes
        return dict(row, alt_dates=tuple(disputes.by_record(conn).get(row["record_id"], ())))
    finally:
        conn.close()


def predict_club(key: str, home: str, away: str, date: str | None = None, now=None) -> dict:
    if home == away:
        raise PredictionError("home and away team must differ")
    comp = C.BY_KEY[key]
    lg, V, tier = _club_runtime()
    h, a = _entity(key, home), _entity(key, away)
    last = V.dt.max()
    dt = _parse_date(date) if date else last + pd.Timedelta(days=1)
    if dt <= last:
        raise PredictionError(f"date must be after the last result in the data ({last.date()}); features only use earlier matches")
    now = now or datetime.now(timezone.utc)
    fx = _stored_fixture(key, h, a, str(dt.date()))
    if fx is not None:                                                    # Phase 4.8B: a real fixture whose kickoff has passed gets no new pre-match prediction
        state = KO.made_before_kickoff(now, fx["match_date"], fx["kickoff_utc"], key, fx["alt_dates"])
        if state != "yes":
            raise PredictionError(KO.BLOCKED_MESSAGE[state])
    season = analytics.seasons(key)[0]
    p2, p1, pe, n_h, n_a, connected, f1 = _club_probs(h, a, comp["source_id"], season, dt, tier.get(comp["source_id"], np.nan))
    rec = dict(v1_p_home=p1[0], v1_p_draw=p1[1], v1_p_away=p1[2], p_home=p2[0], p_draw=p2[1], p_away=p2[2], v1_elo_p_home=pe[0], v1_elo_p_draw=pe[1],
               v1_elo_p_away=pe[2], home_n_prior=n_h, away_n_prior=n_a, eligible_dataset_v1_1_rule=bool(n_h >= 5 and n_a >= 5 and connected))
    notes = _horizon_note(dt, last)
    if fx is None and dt.date() < now.date():
        notes.append("This date is already in the past and no stored fixture matches it: a hypothetical matchup, not a forecast of a scheduled match.")
    if rec["home_n_prior"] < 5 or rec["away_n_prior"] < 5:
        notes.append("Fewer than 5 earlier rated matches for at least one team: low-history prediction.")
    if not rec["eligible_dataset_v1_1_rule"] and not notes:
        notes.append("The two teams are not connected in the rating graph at this date; treat ratings as less comparable.")
    if comp["badge"] == C.NOT_VALIDATED:
        notes.append("This competition is NOT validated: the club models were evaluated on domestic leagues only. Probabilities are indicative.")
    def side(p):  # the v1 model inputs for one team (what the model "saw"); NaN -> None
        g = lambda k: None if pd.isna(f1[f"{p}_{k}"]) else float(f1[f"{p}_{k}"])  # noqa: E731
        gf, ga = g("gf5"), g("ga5")
        return dict(elo=g("elo"), ppg5=g("ppg5"), goals_for_5=gf, goals_against_5=ga, gd5=None if gf is None or ga is None else gf - ga, days_rest=g("days_rest"), prior_matches=int(f1[f"{p}_n_prior"]))

    trio = lambda m, *k: dict(model=m, **{n: float(rec[x]) for n, x in zip(("home", "draw", "away"), k)})  # noqa: E731
    return dict(**_base(key), home=home, away=away, date=str(dt.date()), data_through=str(last.date()),
                primary=trio("Club v1 (frozen multinomial logistic regression)", "v1_p_home", "v1_p_draw", "v1_p_away"),
                secondary=trio("Club v2-r1 (frozen candidate; development-validated only, no unbiased evaluation)", "p_home", "p_draw", "p_away"),
                elo_only=trio("Elo-only mapping (v1 baseline)", "v1_elo_p_home", "v1_elo_p_draw", "v1_elo_p_away"),
                history=dict(home_prior_matches=rec["home_n_prior"], away_prior_matches=rec["away_n_prior"]), inputs=dict(home=side("home"), away=side("away")), notes=notes)


# ------------------------------------------------------------------------------------------------ international
@lru_cache(maxsize=1)
def _intl_runtime():
    import pickle

    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_live_predictions_v27 as v27  # noqa: E402
    import build_worldcup_model_v2 as v2  # noqa: E402
    import model_bakeoff_v26 as v26  # noqa: E402

    with open(V27_ARTIFACT, "rb") as fh:
        artifact = pickle.load(fh)
    elo = v27.load_lookup(v27.PROCESSED / "team_elo_latest.csv", "team", normalize_key=True)
    form = v27.load_lookup(v27.PROCESSED / "team_recent_form_latest.csv", "team", normalize_key=True)
    asof = max(r.get("last_match_date", "") for r in elo.values())
    return v27, v2, v26, artifact, elo, form, asof


def predict_intl(key: str, home: str, away: str, date: str | None = None, venue: str | None = None) -> dict:
    """venue: 'neutral' or 'home' (the first team has home advantage). Default: neutral, except Nations League (home/away legs)."""
    if home == away:
        raise PredictionError("teams must differ")
    comp = C.BY_KEY[key]
    v27, v2, v26, artifact, elo, form, asof = _intl_runtime()
    venue = venue or ("home" if key == "UNL" else "neutral")
    h, a = v2.normalize_team(home), v2.normalize_team(away)
    for t, raw in ((h, home), (a, away)):
        if t not in elo or t not in form:
            raise PredictionError(f"no rating/form data for '{raw}' in the international tables")
    data_end = pd.Timestamp(asof)
    dt = _parse_date(date) if date else data_end
    if dt < data_end:
        raise PredictionError(f"date must be on or after the date the team ratings end ({data_end.date()}); an earlier date would use ratings that already contain later results")
    fixture_date = dt.to_pydatetime()
    neutral, home_field = (1, 0) if venue == "neutral" else (0, 1)
    is_comp, is_wc, bucket = v27.tournament_flags(comp["name"])
    safe = v27.safe_float

    def side(t):
        f, e = form[t], elo[t]
        return dict(elo=safe(e.get("elo_rating"), 1500.0), ppg5=safe(f.get("ppg_last_5"), 1.0), ppg10=safe(f.get("ppg_last_10"), 1.0),
                    gd5=v27.avg_total(f, "goal_diff_last_5", "matches_last_5", 0.0), gd10=v27.avg_total(f, "goal_diff_last_10", "matches_last_10", 0.0),
                    ec5=v27.avg_total(f, "elo_change_last_5", "matches_last_5", 0.0), ec10=v27.avg_total(f, "elo_change_last_10", "matches_last_10", 0.0),
                    opp5=safe(f.get("avg_opponent_elo_last_5"), 1500.0), days=v27.days_since(fixture_date, f.get("last_match_date") or e.get("last_match_date")),
                    n=safe(e.get("matches_played"), 0.0))
    H, A = side(h), side(a)
    import math

    row = {
        "fixture_key": "Q1", "team1": home, "team2": away, "home_team": h, "away_team": a, "tournament_bucket": bucket, "neutral": neutral,
        "home_field": home_field, "is_competitive": is_comp, "is_world_cup": is_wc,
        "home_elo_pre": H["elo"], "away_elo_pre": A["elo"], "elo_diff": H["elo"] - A["elo"], "abs_elo_diff": abs(H["elo"] - A["elo"]),
        "elo_avg": (H["elo"] + A["elo"]) / 2.0, "home_recent_ppg5": H["ppg5"], "away_recent_ppg5": A["ppg5"], "recent_ppg5_diff": H["ppg5"] - A["ppg5"],
        "recent_gd5_diff": H["gd5"] - A["gd5"], "recent_elochg5_diff": H["ec5"] - A["ec5"], "recent_oppelo5_diff": H["opp5"] - A["opp5"],
        "recent_ppg10_diff": H["ppg10"] - A["ppg10"], "recent_gd10_diff": H["gd10"] - A["gd10"], "recent_elochg10_diff": H["ec10"] - A["ec10"],
        "rest_days_diff": H["days"] - A["days"], "home_matches_prior_log": math.log1p(H["n"]), "away_matches_prior_log": math.log1p(A["n"]),
        "matches_prior_log_diff": math.log1p(H["n"]) - math.log1p(A["n"]),
    }
    probs = v27.predict_models(artifact, [row])
    p = probs["ensemble"][0]
    rule = artifact["pass_rules"]["ensemble"]
    pick = v26.pick_with_pass(probs["ensemble"], rule["min_confidence"], rule["min_gap"], rule["draw_risk_min"], rule["draw_gap_max"])[0]
    notes = _horizon_note(dt, data_end) + [f"Team ratings and form are as of {asof}; results after that date are not reflected.",
             f"Venue assumption: {'neutral ground' if venue == 'neutral' else home + ' has home advantage'}."]
    if comp["badge"] == C.PARTIAL:
        notes.append("Partially validated: the model was tested on all internationals 2023-26 pooled, not on this competition specifically.")
    return dict(**_base(key), home=home, away=away, date=str(fixture_date.date()), data_through=asof,
                primary=dict(model="International v2.7 ensemble (50% gradient boosting, 30% Elo, 20% logistic; temperature-calibrated)",
                             home=float(p[0]), draw=float(p[1]), away=float(p[2])),
                elo_only=dict(model="Elo formula", home=float(probs["elo_formula"][0][0]), draw=float(probs["elo_formula"][0][1]), away=float(probs["elo_formula"][0][2])),
                gate=dict(public_pick=pick, meaning="'pass' = the project's confidence gate declines to call this match"),
                history=dict(home_prior_matches=int(H["n"]), away_prior_matches=int(A["n"])),
                inputs=dict(home=dict(elo=H["elo"], ppg5=H["ppg5"], gd5=H["gd5"], days_rest=H["days"], prior_matches=int(H["n"])),
                            away=dict(elo=A["elo"], ppg5=A["ppg5"], gd5=A["gd5"], days_rest=A["days"], prior_matches=int(A["n"]))), notes=notes)


def predict(key: str, home: str, away: str, date: str | None = None, venue: str | None = None, now=None) -> dict:
    if key not in C.BY_KEY:
        raise PredictionError(f"unknown competition '{key}'")
    if C.BY_KEY[key]["kind"] != "club":
        raise PredictionError(f"'{key}' is not a supported competition: only the five domestic leagues and the Champions League are predicted")
    return predict_club(key, home, away, date, now)
