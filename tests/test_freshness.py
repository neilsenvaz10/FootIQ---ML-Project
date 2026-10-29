"""Phase 4.17: competition-level data freshness. Synthetic frames pin each rule; the real dataset gives the 11-competition record with honest statuses."""
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import config as C  # noqa: E402
import freshness as F  # noqa: E402

TODAY = date(2026, 10, 28)
needs_data = pytest.mark.skipif(not C.MATCHES_CSV.exists(), reason="data/miniproject/matches.csv is not built")
COLS = ["competition_key", "season", "stage", "date", "home", "away", "home_goals", "away_goals"]


def frame(rows):
    return pd.DataFrame(rows, columns=COLS)


def by_key(res):
    return {r["key"]: r for r in res}


def test_every_competition_of_the_six_is_reported_in_order_with_a_status():
    res = F.build(frame([]), None, [], True, "startup", TODAY)
    assert [r["key"] for r in res] == ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"] and len(res) == 6
    assert {r["data_status"] for r in res} == {"historical_only"}


def test_only_competitions_the_sync_refreshes_are_startup_updated_and_nothing_is_called_live():
    res = by_key(F.build(frame([]), {"competitions": [{"competition_key": "BUNDESLIGA", "last_successful_external_check_utc": "2026-10-28T01:52:38Z", "approved_sources": ["openligadb"]}]},
                         ["BUNDESLIGA", "LALIGA"], True, "startup", TODAY))
    assert res["BUNDESLIGA"]["data_status"] == "startup_updated" and res["BUNDESLIGA"]["last_successful_refresh_utc"] == "2026-10-28T01:52:38Z"
    assert res["EPL"]["data_status"] == "historical_only" and res["EPL"]["last_successful_refresh_utc"] is None and "permission" in res["EPL"]["update_note"]
    for r in res.values():
        assert "live" not in (r["data_status_label"] + " ").lower().replace("not a live feed", "")
    off = by_key(F.build(frame([]), None, ["BUNDESLIGA"], False, "startup", TODAY))                # live access off: nothing is "updated"
    assert off["BUNDESLIGA"]["data_status"] == "historical_only"


def test_latest_result_and_age_are_computed_from_scored_rows_only():
    df = frame([("EPL", "2026-27", "Matchday 1", "2026-10-12", "A", "B", 1, 0), ("EPL", "2026-27", "Matchday 9", "2026-11-01", "C", "D", None, None)])
    r = by_key(F.build(df, None, [], True, "startup", TODAY))["EPL"]
    assert r["latest_result"] == "2026-10-12" and r["days_since_latest_result"] == 16


def test_stale_and_missing_season_warnings_for_a_historical_only_league():
    df = frame([("SERIEA", "2025-26", "x", "2026-05-24", "A", "B", 1, 0)])
    w = [x["text"] for x in by_key(F.build(df, None, [], True, "startup", TODAY))["SERIEA"]["warnings"]]
    assert any("not updated automatically" in x for x in w) and any("No matches of the 2026-27 season" in x for x in w)


def test_league_phase_progress_is_reported_against_the_expected_144():
    rows = [("UCL", "2026-27", "Matches > Matchday 1", "2026-09-08", f"H{i}", f"A{i}", 1, 0) for i in range(18)]
    r = by_key(F.build(frame(rows), None, [], True, "startup", TODAY))["UCL"]
    assert any("18 of 144" in w["text"] for w in r["warnings"])


def test_an_awaiting_result_in_an_updated_league_is_a_warning():
    st = {"competitions": [{"competition_key": "LALIGA", "awaiting_result": 7, "oldest_awaiting": "2026-10-10", "approved_sources": ["openligadb"], "last_successful_external_check_utc": "2026-10-28T01:52:43Z"}]}
    r = by_key(F.build(frame([]), st, ["LALIGA"], True, "startup", TODAY))["LALIGA"]
    assert any("7 fixture(s) are past their date" in w["text"] for w in r["warnings"])


@needs_data
def test_the_real_dataset_gives_an_honest_record_for_all_eleven():
    df = pd.read_csv(C.MATCHES_CSV, low_memory=False, dtype={"season": str})
    res = by_key(F.build(df, None, ["BUNDESLIGA", "LALIGA"], True, "startup", TODAY))
    assert set(res) == {"EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"}
    assert res["BUNDESLIGA"]["data_status"] == "startup_updated" and res["LALIGA"]["data_status"] == "startup_updated"
    assert all(res[k]["data_status"] == "historical_only" for k in ("EPL", "SERIEA", "LIGUE1", "UCL"))           # nothing else is refreshed, and the Champions League stays historical
    assert any("18 of 144" in w["text"] for w in res["UCL"]["warnings"]) and "not updated automatically" in " ".join(w["text"] for w in res["UCL"]["warnings"])
    assert "permission" in res["EPL"]["update_note"]
