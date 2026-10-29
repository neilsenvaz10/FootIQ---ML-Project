"""Final scope (Phase 4.18): exactly SIX supported competitions, read-only. The five domestic leagues and the UEFA Champions League are supported; the Europa League, Conference League, World Cup, Nations
League and Copa America are ARCHIVED (their data is preserved, nothing in the application shows or predicts them). Dataset integrity, prediction routing, the known-gap registry and the
startup-only synchronisation guard. Nothing here touches the network, the production store or any model file."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import config as C  # noqa: E402
from store import sync  # noqa: E402

DOMESTIC = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]
SUPPORTED = DOMESTIC + ["UCL"]
ARCHIVED = ["UEL", "UECL", "WC", "UNL", "COPA"]
needs_data = pytest.mark.skipif(not C.MATCHES_CSV.exists(), reason="data/miniproject/matches.csv is not built")


@pytest.fixture(scope="module")
def m():
    d = pd.read_csv(C.MATCHES_CSV, low_memory=False)
    d["date"] = pd.to_datetime(d["date"])
    return d


def test_the_supported_scope_is_exactly_six_competitions():
    assert [c["key"] for c in C.COMPETITIONS] == SUPPORTED and len(C.COMPETITIONS) == 6 and set(C.BY_KEY) == set(SUPPORTED)
    assert {c["key"] for c in C.COMPETITIONS if c["group"] == "Domestic league"} == set(DOMESTIC)
    assert [c["key"] for c in C.COMPETITIONS if c["group"] == "Continental club"] == ["UCL"]
    assert all(c["kind"] == "club" and c["model"] == "club" for c in C.COMPETITIONS)                  # every supported competition uses the frozen club models


def test_the_five_removed_competitions_are_archived_not_supported():
    assert [c["key"] for c in C.ARCHIVED_COMPETITIONS] == ["WC", "UEL", "UECL", "UNL", "COPA"] or sorted(c["key"] for c in C.ARCHIVED_COMPETITIONS) == sorted(ARCHIVED)
    assert not set(ARCHIVED) & set(C.BY_KEY) and set(ARCHIVED) <= set(C.ALL_BY_KEY) and len(C.ALL_COMPETITIONS) == 11       # still described, for the data-building code


@needs_data
def test_the_archived_competitions_data_is_preserved_in_the_dataset(m):
    for k in ARCHIVED:
        assert (m.competition_key == k).sum() > 600, k                                                # rows are kept (not deleted): WC 1,094; UEL 1,424; UECL 729; UNL 658; COPA 869


@needs_data
def test_the_application_frame_contains_only_the_six(m):
    import analytics
    assert set(analytics.matches().competition_key) == set(SUPPORTED)


@needs_data
def test_every_supported_competition_has_scored_rows_and_no_missing_score(m):
    for k in SUPPORTED:
        d = m[m.competition_key == k]
        assert len(d) > 0 and d.home_goals.notna().all() and d.away_goals.notna().all() and (d.home_goals >= 0).all() and (d.away_goals >= 0).all(), k


@needs_data
def test_domestic_leagues_have_nine_seasons_unique_matches_and_resolved_club_identities(m):
    for k in DOMESTIC:
        d = m[m.competition_key == k]
        assert d.season.nunique() == 9 and "2026-27" in set(d.season) and "2018-19" in set(d.season), k
        assert not d.duplicated(subset=["season", "date", "home", "away"]).any(), k
        assert d.home_entity_id.notna().all() and d.away_entity_id.notna().all(), k
        assert (d.outcome_basis.astype(str).str.contains("90 min")).all(), k
    ucl = m[m.competition_key == "UCL"]
    assert not ucl.duplicated(subset=["season", "date", "home", "away", "stage"]).any() and ucl.home_entity_id.notna().all()


@needs_data
def test_known_gaps_registry(m):
    cnt = m.groupby(["competition_key", "season"]).size()
    assert cnt[("LIGUE1", "2019-20")] == 279                                                          # curtailed season (380 expected)
    assert m[m.competition_key == "UCL"].date.max() == pd.Timestamp("2026-09-10")                      # matchday 2 (13-14 October) is not in the dataset
    assert cnt[("UCL", "2026-27")] == 18                                                              # 18 of the 144 league-phase matches


@needs_data
@pytest.mark.parametrize("key", SUPPORTED)
def test_a_prediction_uses_the_requested_competition_and_carries_its_validation_status(m, key):
    import predict
    d = m[m.competition_key == key].sort_values("date")
    last = d[d.season.astype(str) == d.season.astype(str).iloc[-1]].iloc[-1]
    comp = C.BY_KEY[key]
    r = predict.predict(key, last.home, last.away, None, None)
    assert r["competition_key"] == key and r["validation_badge"] == comp["badge"] and "primary" in r and "secondary" in r
    p = r["primary"]
    assert abs(p["home"] + p["draw"] + p["away"] - 1) < 1e-6
    if comp["badge"] != C.VALIDATED:
        assert any("NOT validated" in n for n in r["notes"]), key


@needs_data
@pytest.mark.parametrize("key", ARCHIVED)
def test_archived_competitions_are_refused_by_the_prediction_pipeline(key):
    import predict
    with pytest.raises(predict.PredictionError):
        predict.predict(key, "A", "B")


@needs_data
def test_a_team_from_another_competition_is_refused_not_silently_predicted(m):
    import predict
    other = m[m.competition_key == "BUNDESLIGA"].iloc[-1].home
    mate = m[m.competition_key == "EPL"].iloc[-1].home
    with pytest.raises(predict.PredictionError):
        predict.predict("EPL", other, mate)


def test_synchronisation_stays_startup_only_with_only_bundesliga_and_la_liga_active():
    cfg = sync.SyncConfig.load()
    assert cfg.sync_mode == "startup" and cfg.live_enabled and cfg.approved_competitions() == ["BUNDESLIGA", "LALIGA"]
    assert not {"EPL", "SERIEA", "LIGUE1"} & set(sync.APPROVED) and {"EPL", "SERIEA", "LIGUE1"} <= set(sync.PREPARED_PROVIDERS)
    assert "UCL" not in sync.APPROVED and "UCL" not in cfg.approved_competitions()                      # the Champions League stays historical-only
    assert cfg.sources["footballdata"]["enabled"] is False and cfg.sources["footballdata"]["competitions"] == []
    users = sorted(p.name for p in (ROOT / "app").rglob("*.py") if "threading.Thread(" in p.read_text(encoding="utf-8"))
    assert users == ["main.py", "sync.py"], users                                                       # no other file starts a thread: no second scheduler or background loop anywhere in the application
    main_threads = [ln for ln in (ROOT / "app" / "main.py").read_text(encoding="utf-8").splitlines() if "threading.Thread(" in ln]
    assert main_threads and all("predict.warm_up" in ln for ln in main_threads)
    sync_src = (ROOT / "app" / "store" / "sync.py").read_text(encoding="utf-8")
    assert sync_src.count("threading.Thread(") == 1 and "self._startup_once if startup else self._loop" in sync_src


def test_the_champions_league_has_no_update_source():
    assert "UCL" not in sync.APPROVED and "UCL" not in sync.PREPARED_PROVIDERS and "UCL" not in sync.OFFLINE_PREPARED
