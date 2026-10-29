"""Phase 4.17: the 36-team UEFA league-phase table. Synthetic cases pin each tie-breaker; the real 2024-25 and 2025-26 league phases in the dataset must be structurally consistent."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import config as C  # noqa: E402
import uefa_league_phase as U  # noqa: E402

CSV = C.MATCHES_CSV
needs_data = pytest.mark.skipif(not CSV.exists(), reason="data/miniproject/matches.csv is not built")


def m(h, a, hg, ag):
    return dict(home=h, away=a, hg=hg, ag=ag)


def order(rows):
    return [r["team"] for r in rows]


def test_points_then_goal_difference_then_goals_scored():
    ms = [m("A", "X", 1, 0), m("B", "Y", 3, 2), m("C", "Z", 4, 3)]            # A,B,C all win: 3 points; GD +1,+1,+1; GF 1,3,4
    assert order(U.table(ms)[:3]) == ["C", "B", "A"]
    ms = [m("A", "X", 2, 0), m("B", "Y", 1, 0)]                                 # same points, GD +2 beats +1
    assert order(U.table(ms)[:2]) == ["A", "B"]


def test_away_goals_break_a_tie_on_points_goal_difference_and_goals_scored():
    # P: wins 2-1 away, loses 0-1 at home. Q: wins 2-1 at home, loses 0-1 away. Both 3 pts, GF 2, GA 2; P scored its goals away.
    ms = [m("R", "P", 1, 2), m("P", "S", 0, 1), m("Q", "R", 2, 1), m("S", "Q", 1, 0)]
    t = U.table(ms)
    p, q = (next(r for r in t if r["team"] == x) for x in "PQ")
    assert (p["points"], p["gd"], p["gf"]) == (q["points"], q["gd"], q["gf"]) and p["away_gf"] == 2 and q["away_gf"] == 0 and p["position"] < q["position"] and not p["tied_unresolved"]


def test_a_tie_on_every_available_criterion_is_shared_and_alphabetical_never_guessed():
    t = U.table([m("X", "A", 1, 1), m("Y", "B", 1, 1)])                         # A and B are identical; X and Y are identical
    assert order(t) == ["A", "B", "X", "Y"] and [r["position"] for r in t] == [1, 1, 3, 3] and all(r["tied_unresolved"] for r in t)


def test_opponent_criteria_apply_only_when_the_phase_is_complete():
    # A and B are level on criteria 1-5; their opponents differ in points
    ms = [m("A", "C", 1, 0), m("B", "D", 1, 0), m("E", "C", 5, 0), m("D", "F", 1, 1)]
    prov = U.table(ms, complete=False)
    final = U.table(ms, complete=True)
    a, b = (next(r for r in prov if r["team"] == x) for x in "AB")
    assert a["position"] == b["position"] and a["tied_unresolved"]            # in progress: criteria 1-5 only
    fa, fb = (next(r for r in final if r["team"] == x) for x in "AB")
    assert fa["position"] != fb["position"] and not fa["tied_unresolved"]     # final: opponents' points decide


def test_zones_follow_the_positions_and_a_boundary_tie_is_undetermined():
    teams = [f"T{i:02d}" for i in range(36)]
    ms = [m(teams[i], teams[(i + 1) % 36], 36 - i, 0) for i in range(36)]      # distinct goal differences: no ties
    t = U.table(ms)
    assert {r["zone"] for r in t[:8]} == {"round of 16 (direct)"} and {r["zone"] for r in t[8:24]} == {"knockout play-off"} and {r["zone"] for r in t[24:]} == {"eliminated"}
    tie = U.table([m(f"H{i:02d}", f"A{i:02d}", 1, 1) for i in range(18)])      # 36 teams all level: one shared rank across every boundary
    assert all(r["zone"].startswith("undetermined") for r in tie)


def test_stage_filter_keeps_league_phase_rows_and_drops_knockouts():
    for s in ("League, Matchday 3", "League phase", "Matches > Matchday 1"):
        assert U.is_league_phase_stage(s), s
    for s in ("Playoffs, Matchday 1", "Knockout phase play-offs > Matches", "Finals, Round of 16", "Round of 16 > Matches", "Final", "Quarterfinals", None):
        assert not U.is_league_phase_stage(s), s


def test_group_stage_seasons_and_unknown_competitions_are_refused():
    df = pd.DataFrame(columns=["competition_key", "season", "stage", "home", "away", "home_goals", "away_goals"])
    with pytest.raises(ValueError):
        U.league_phase(df, "UCL", "2023-24")
    with pytest.raises(ValueError):
        U.league_phase(df, "EPL", "2025-26")
    with pytest.raises(ValueError):
        U.league_phase(df, "UEL", "2025-26")                                                     # the Europa and Conference League are outside the supported scope
    with pytest.raises(ValueError):
        U.league_phase(df, "UECL", "2025-26")
    empty = U.league_phase(df, "UCL", "2026-27")
    assert empty["matches_played"] == 0 and empty["table"] == [] and "no result yet" in empty["coverage_note"]


@needs_data
@pytest.mark.parametrize("key,per_team", [("UCL", 8)])
@pytest.mark.parametrize("season", ["2024-25", "2025-26"])
def test_the_completed_league_phases_in_the_data_are_consistent(key, per_team, season):
    df = pd.read_csv(CSV, low_memory=False, dtype={"season": str})
    r = U.league_phase(df, key, season)
    t = r["table"]
    assert r["complete"] and r["matches_played"] == r["matches_expected"] == per_team * 18 and r["teams"] == 36
    assert {x["played"] for x in t} == {per_team} and [x["position"] for x in t] == list(range(1, 37))
    assert sum(x["gf"] for x in t) == sum(x["ga"] for x in t) and sum(x["gd"] for x in t) == 0
    assert sum(x["won"] for x in t) == sum(x["lost"] for x in t)
    assert sum(1 for x in t if x["zone"] == "round of 16 (direct)") == 8 and sum(1 for x in t if x["zone"] == "knockout play-off") == 16 and sum(1 for x in t if x["zone"] == "eliminated") == 12
    assert r["criteria_applied"].startswith("1-8")


@needs_data
def test_the_known_2024_25_leaders_are_reproduced():
    df = pd.read_csv(CSV, low_memory=False, dtype={"season": str})
    top = U.league_phase(df, "UCL", "2024-25")["table"][0]
    assert (top["team"], top["points"]) == ("Liverpool FC", 21)


@needs_data
def test_the_current_league_phase_is_provisional_and_says_how_little_is_in_the_data():
    df = pd.read_csv(CSV, low_memory=False, dtype={"season": str})
    r = U.league_phase(df, "UCL", "2026-27")
    assert not r["complete"] and r["criteria_applied"].startswith("1-5") and r["matches_played"] < r["matches_expected"] and r["coverage_note"]
