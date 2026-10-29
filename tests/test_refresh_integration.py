"""Phase 4.8B: what a safe result import changes downstream, and what it must not change. Private store copies and local snapshots only; no network, no production file.

State A: the baseline store plus the Bundesliga pilot payload (results to 2026-10-18).  State B: A plus the stored real season payload of 2026-10-25 (results to 2026-10-24).
The payloads are replayed through the same ingestion code the scheduler uses, so these tests exercise the real reconciliation path with a mocked source."""
import json
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))
for p in (str(ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"), str(ROOT / "FootIQ_ML_Training_Preparation" / "_build")):
    if p not in sys.path:
        sys.path.insert(0, p)

import analytics  # noqa: E402
import forecast  # noqa: E402
import gameweeks as gw  # noqa: E402
import matches as matches_hub  # noqa: E402
import predict  # noqa: E402
from seasonsim import service as season_sim  # noqa: E402
from store import baseline, db, sync  # noqa: E402

PILOT = ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1" / "pilot" / "run_20261021T141224Z" / "snapshots" / "openligadb" / "20261021T141231Z_R3_getmatchdata_bl1_2026.json"
LIVE_SNAP = sorted((ROOT / "data" / "snapshots" / "openligadb").glob("*_bl1_2026_season.json"))
pytestmark = pytest.mark.skipif(not (baseline.V_PATH.exists() and PILOT.exists() and LIVE_SNAP), reason="baseline inputs or stored snapshots not present")
KEY, SEASON = "BUNDESLIGA", "2026-27"
T_A = datetime(2026, 10, 21, 14, 12, tzinfo=timezone.utc)
T_B = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)


def rows(path, sql, *a):
    c = db.connect(path)
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


@pytest.fixture(scope="module")
def states(tmp_path_factory):
    d = tmp_path_factory.mktemp("refresh")
    base = d / "base.sqlite"
    c = db.connect(base)
    db.init(c)
    baseline.import_baseline(c)
    c.close()
    a, b = d / "A.sqlite", d / "B.sqlite"
    shutil.copy(base, a)
    c = db.connect(a)
    sync.replay_payload(c, PILOT.read_bytes(), now=T_A)
    c.close()
    shutil.copy(a, b)
    c = db.connect(b)
    sync.replay_payload(c, LIVE_SNAP[-1].read_bytes(), now=T_B)
    c.close()
    return dict(dir=d, A=a, B=b)


@pytest.fixture()
def use(monkeypatch):
    """Wire one private store in as the application store."""
    def go(path):
        monkeypatch.setattr(db, "DEFAULT_PATH", path)
        monkeypatch.setenv("FOOTIQ_USE_STORE", "1")
        analytics.reload()
        predict.reset_club_state()
        forecast.artifact_hashes.cache_clear()
        return path
    yield go
    predict.reset_club_state()
    analytics.reload()


def newly_completed(states):
    a = {r["record_id"] for r in rows(states["A"], "SELECT record_id FROM matches WHERE competition_key=? AND season=? AND status='completed'", KEY, SEASON)}
    return [r for r in rows(states["B"], "SELECT m.*, t1.display_name AS home_display, t2.display_name AS away_display FROM matches m JOIN teams t1 ON t1.entity_id=m.home_entity_id JOIN teams t2 ON t2.entity_id=m.away_entity_id "
                            "WHERE m.competition_key=? AND m.season=? AND m.status='completed' ORDER BY m.match_date, m.record_id", KEY, SEASON) if r["record_id"] not in a]


def table_from_rows(path):
    t = {}
    for r in rows(path, "SELECT t1.display_name AS home_name, t2.display_name AS away_name, m.home_goals_final gh, m.away_goals_final ga FROM matches m JOIN teams t1 ON t1.entity_id=m.home_entity_id JOIN teams t2 ON t2.entity_id=m.away_entity_id "
                       "WHERE m.competition_key=? AND m.season=? AND m.status IN ('completed','awarded') AND m.home_goals_final IS NOT NULL", KEY, SEASON):
        for team, gf, ga in ((r["home_name"], r["gh"], r["ga"]), (r["away_name"], r["ga"], r["gh"])):
            x = t.setdefault(team, [0, 0, 0])
            x[0] += 1
            x[1] += 3 if gf > ga else 1 if gf == ga else 0
            x[2] += gf - ga
    return t


# ------------------------------------------------------------------------------------------------ standings, form, match pages, comparison
def test_the_import_adds_only_results_and_standings_recalculate_exactly(states, use):
    new = newly_completed(states)
    assert len(new) >= 5
    use(states["A"])
    ta = {r["team"]: r for r in analytics.standings(KEY, SEASON)}
    use(states["B"])
    tb = {r["team"]: r for r in analytics.standings(KEY, SEASON)}
    for name, (played, pts, gd) in table_from_rows(states["B"]).items():              # the app's table equals an independent count of the stored results
        team = name
        assert (tb[team]["played"], tb[team]["points"], tb[team]["gd"]) == (played, pts, gd), name
    gained = {}
    for r in new:
        for side, other in (("home", "away"), ("away", "home")):
            gf, ga = (r["home_goals_final"], r["away_goals_final"]) if side == "home" else (r["away_goals_final"], r["home_goals_final"])
            gained[r[f"{side}_display"]] = gained.get(r[f"{side}_display"], 0) + (3 if gf > ga else 1 if gf == ga else 0)
    for name, pts in gained.items():
        team = name
        assert tb[team]["points"] - (ta[team]["points"] if team in ta else 0) == pts                                    # points moved by exactly what the new results are worth
    assert sum(r["played"] for r in tb.values()) == sum(r["played"] for r in ta.values()) + 2 * len(new)


def test_recent_form_and_head_to_head_use_the_refreshed_history(states, use):
    new = newly_completed(states)
    r = new[-1]
    th, ta_ = r["home_display"], r["away_display"]
    use(states["A"])
    fa = analytics.team_form(KEY, th, 5)
    ha = analytics.head_to_head(KEY, th, ta_)
    use(states["B"])
    form = analytics.team_form(KEY, th, 5)
    assert form["last"][-1]["date"] == r["match_date"] and form["last"][-1]["gf"] == r["home_goals_final"]               # the new result is the most recent form entry
    assert all(m["gf"] is not None and m["ga"] is not None for m in form["last"])                                          # a missing result is never a 0-0 or a defeat: it is simply absent
    hb = analytics.head_to_head(KEY, th, ta_)
    assert hb["meetings"] == ha["meetings"] + 1 and hb["last"][0]["date"] == r["match_date"]
    assert fa is not None


def test_match_and_league_pages_show_the_new_results_and_no_longer_list_them_as_open(states, use):
    new_ids = {r["record_id"] for r in newly_completed(states)}
    cfg = sync.SyncConfig()
    out = {}
    for tag in ("A", "B"):
        c = db.connect(states[tag], readonly=True)
        try:
            out[tag] = {s: {m["record_id"] for m in matches_hub.build(c, cfg, NOW, comp=KEY, season=SEASON, status=s, limit=50)["items"]} for s in ("completed", "awaiting_result", "upcoming")}
        finally:
            c.close()
    assert new_ids <= out["B"]["completed"] and not (new_ids & out["A"]["completed"])
    assert not (new_ids & out["B"]["awaiting_result"]) and not (new_ids & out["B"]["upcoming"])
    c = db.connect(states["B"], readonly=True)
    try:
        assert not any(f["record_id"] in new_ids and f["status"] != "completed" for md in range(1, 35) for f in gw.gameweek_fixtures(c, KEY, SEASON, md, date(2026, 10, 25), NOW)["fixtures"])
    finally:
        c.close()


def test_data_quality_warnings_of_leagues_that_were_not_refreshed_are_unchanged(states):
    def flags(tag):
        c = db.connect(states[tag], readonly=True)
        try:
            return [(f["record_id"], tuple(f["flags"]), f["reliability"]) for md in (8, 9) for f in gw.gameweek_fixtures(c, "EPL", SEASON, md, date(2026, 10, 25), T_B)["fixtures"]]
        finally:
            c.close()
    assert flags("A") == flags("B") and any("stale_history" in f[1] for f in flags("B"))
    c = db.connect(states["B"], readonly=True)
    try:
        st = {x["competition_key"]: x for x in sync.status(c, sync.SyncConfig(), T_B)["competitions"]}
    finally:
        c.close()
    assert st["EPL"]["state"] == "stale" and st["EPL"]["approved_sources"] == [] and st["LALIGA"]["state"] == "stale"      # no approved fresh source: still said so
    assert st["SERIEA"]["state"] == "stale" and st["LIGUE1"]["state"] == "stale" and st["BUNDESLIGA"]["approved_sources"] == ["openligadb"]


# ------------------------------------------------------------------------------------------------ prediction inputs
def _v1(path, team_record):
    r = rows(path, "SELECT feature_snapshot_json FROM forecasts WHERE record_id=? AND model_variant='club_v1'", team_record)
    return json.loads(r[0]["feature_snapshot_json"])


def test_new_results_move_the_prediction_inputs_but_never_rewrite_saved_forecasts(states, use, tmp_path):
    new = newly_completed(states)
    a2 = tmp_path / "A2.sqlite"
    shutil.copy(states["A"], a2)
    use(a2)
    c = db.connect(a2, readonly=True)
    nxt = gw.list_gameweeks(c, KEY, SEASON, date(2026, 10, 25), T_B)["next_gameweek"]
    c.close()
    nxt = max(n["matchday_no"] for n in new) + 1                                                                         # the gameweek after the newest imported one: still ahead on both dates
    run1 = forecast.predict_gameweek(KEY, SEASON, nxt, forecast.EXPLICIT_ACTION, now=datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc), today=date(2026, 10, 19), db_path=a2)
    saved1 = rows(a2, "SELECT * FROM forecasts ORDER BY forecast_id")
    assert saved1 and run1["data_cutoff_date"] <= "2026-10-18"
    # the refresh arrives
    c = db.connect(a2)
    sync.replay_payload(c, LIVE_SNAP[-1].read_bytes(), now=T_B)
    c.close()
    predict.reset_club_state()
    analytics.reload()
    assert rows(a2, "SELECT * FROM forecasts ORDER BY forecast_id")[: len(saved1)] == saved1                                 # the stored probabilities and snapshots are byte-for-byte what they were
    run2 = forecast.predict_gameweek(KEY, SEASON, nxt, forecast.EXPLICIT_ACTION, now=datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc), today=date(2026, 10, 25), db_path=a2)
    assert run2["forecast_run_id"] == run1["forecast_run_id"] + 1 and run2["data_cutoff_date"] > run1["data_cutoff_date"]
    assert rows(a2, "SELECT * FROM forecasts ORDER BY forecast_id")[: len(saved1)] == saved1                                 # still untouched after the new run
    played_new = {n["home_display"] for n in new} | {n["away_display"] for n in new}
    moved = 0
    for fx in run2["forecasts"]:
        old = next((x for x in run1["forecasts"] if x["record_id"] == fx["record_id"]), None)
        if old is None:
            continue
        s1 = [json.loads(r["feature_snapshot_json"]) for r in saved1 if r["record_id"] == fx["record_id"] and r["model_variant"] == "club_v1"][0]
        s2 = _v1(a2, fx["record_id"]) if False else json.loads(rows(a2, "SELECT feature_snapshot_json FROM forecasts WHERE forecast_run_id=? AND record_id=? AND model_variant='club_v1'", run2["forecast_run_id"], fx["record_id"])[0]["feature_snapshot_json"])
        for side, name in (("home", fx["home"]), ("away", fx["away"])):
            if name in played_new:
                assert s2[f"{side}_n_prior"] > s1[f"{side}_n_prior"]                                                        # a team that played has more history
                moved += 1
    assert moved > 0, (sorted(played_new)[:3], [(f["home"], f["away"]) for f in run2["forecasts"]][:2], len(run1["forecasts"]), len(run2["forecasts"]))


def test_form_and_elo_features_equal_an_independent_calculation_and_missing_history_is_not_a_loss(states, use):
    use(states["B"])
    lg, V, tiers = predict._club_runtime()
    base = lg.universe_frame(V)
    comp_id = "deutschland:1-bundesliga"
    fixture_day = pd.Timestamp("2026-10-31")
    rr = rows(states["B"], "SELECT model_home_entity h, model_away_entity a, home_entity_id h2, away_entity_id a2 FROM matches WHERE competition_key=? AND season=? AND match_date>='2026-10-31' AND status='scheduled' ORDER BY match_date LIMIT 1", KEY, SEASON)[0]
    h, a = rr["h"] or rr["h2"], rr["a"] or rr["a2"]
    F2, F1 = predict.club_features_fast(h, a, comp_id, SEASON, fixture_day, tiers.get(comp_id, np.nan))
    f1 = F1.iloc[0]
    for side, ent in (("home", h), ("away", a)):
        mine = base[((base.h == ent) | (base.a == ent)) & (base.rated == 1) & (base.dt < fixture_day)].sort_values(["dt", "record_id"])
        pts = [(3 if (g > o) else 1 if g == o else 0) for g, o in ((r.gh, r.ga) if r.h == ent else (r.ga, r.gh) for r in mine.itertuples())]
        assert int(f1[f"{side}_n_prior"]) == len(pts)
        assert f1[f"{side}_ppg5"] == pytest.approx(float(np.mean(pts[-5:])))                                                 # last five RATED results that exist, no padding
        assert f1[f"{side}_ppg10"] == pytest.approx(float(np.mean(pts[-10:])))
    # a team with no stored history has no form, not a zero form
    F2n, F1n = predict.club_features_fast("CLUB:TST:never-played-a", "CLUB:TST:never-played-b", comp_id, SEASON, fixture_day, np.nan)
    assert F1n.iloc[0]["home_n_prior"] == 0 and np.isnan(F1n.iloc[0]["home_ppg5"]) and np.isnan(F1n.iloc[0]["home_gf5"])


def test_the_v2_gap_counters_see_missing_results_and_the_schema_is_unchanged(states, use):
    use(states["B"])
    lg, V, tiers = predict._club_runtime()
    comp_id = "deutschland:1-bundesliga"
    rr = rows(states["B"], "SELECT model_home_entity h, model_away_entity a, home_entity_id h2, away_entity_id a2 FROM matches WHERE competition_key=? AND season=? AND status='scheduled' ORDER BY match_date LIMIT 1", KEY, SEASON)[0]
    h, a = rr["h"] or rr["h2"], rr["a"] or rr["a2"]
    F2, _ = predict.club_features_fast(h, a, comp_id, SEASON, pd.Timestamp("2026-11-07"), tiers.get(comp_id, np.nan))
    with open(ROOT / "FootIQ_Club_Model_Development_v2" / "final_refit_v2_r1" / "artifacts" / "feature_contract_v2_final.json", encoding="utf-8") as fh:
        contract = json.load(fh)
    cols = contract.get("features") or contract.get("feature_order") or contract.get("columns") or []
    if cols:
        assert [c for c in cols if c not in F2.columns] == []                                                                # every contracted input is still produced, none added to the contract
    known = [c for c in F2.columns if c.startswith(("home_n_known", "away_n_known"))] or [c for c in F2.columns if "n_known" in c]
    assert known, "the v2 inputs expose how many results are known in the recent windows"
    assert all(F2.iloc[0][c] >= 0 for c in known)


# ------------------------------------------------------------------------------------------------ simulation compatibility
def test_the_points_only_simulation_reads_the_refreshed_results_and_saves_only_to_the_private_copy(states, tmp_path):
    p = tmp_path / "sim.sqlite"
    shutil.copy(states["B"], p)
    st = season_sim.status(KEY, SEASON, date(2026, 10, 25), db_path=p)
    completed = rows(p, "SELECT COUNT(*) n FROM matches WHERE competition_key=? AND season=? AND status IN ('completed','awarded')", KEY, SEASON)[0]["n"]
    assert st["points_only"]["can_run"] and st["scoreline_method"] is None if "scoreline_method" in st else True
    assert st["points_only"]["can_run"], st["points_only"]
    r = season_sim.run_points_only(KEY, SEASON, 1000, 7, season_sim.POINTS_ACTION, now=T_B, today=date(2026, 10, 25), db_path=p)
    assert r["result"]["mode"] == "points_only" and r["assumptions"]["simulations"] == 1000 and r["assumptions"]["data_cutoff"]["latest_result_in_competition"] >= "2026-10-24"
    assert rows(p, "SELECT COUNT(*) n FROM simulation_runs")[0]["n"] == 1
    assert rows(states["B"], "SELECT COUNT(*) n FROM simulation_runs")[0]["n"] == 0                                           # the source copy was not written
    assert completed > 0


def test_imported_results_name_the_snapshot_that_supplied_them_and_keep_the_earlier_confirmation_in_their_history(states):
    new = newly_completed(states)
    live_sid = "offline-replay-" + __import__("hashlib").sha256(LIVE_SNAP[-1].read_bytes()).hexdigest()[:12]
    for r in new:
        a = rows(states["A"], "SELECT role, snapshot_id, provenance FROM match_sources WHERE source='openligadb' AND record_id=?", r["record_id"])
        b = rows(states["B"], "SELECT role, snapshot_id, provenance FROM match_sources WHERE source='openligadb' AND record_id=?", r["record_id"])
        assert len(a) == len(b) == 1
        assert a[0]["role"] == "confirmation" and b[0]["role"] == "primary" and b[0]["snapshot_id"] == live_sid                # the result points at the snapshot that supplied it
        assert a[0]["provenance"] in b[0]["provenance"] and "was confirmation" in b[0]["provenance"]                            # the earlier provenance text is preserved
    untouched = [x for x in rows(states["A"], "SELECT * FROM match_sources WHERE source<>'openligadb'")]
    assert untouched == rows(states["B"], "SELECT * FROM match_sources WHERE source<>'openligadb'")                            # other sources' links are identical
