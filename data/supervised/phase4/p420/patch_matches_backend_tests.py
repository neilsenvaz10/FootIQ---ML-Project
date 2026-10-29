"""Phase 4.20 part C: update tests/test_matches.py for the Champions League in the hub (record of exactly what changed)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
p = ROOT / "tests" / "test_matches.py"
s = p.read_text(encoding="utf-8")
old = '''    assert p["facets"] == dict(seasons=["2026-27", "2025-26"], matchdays=[1, 2, 3, 4])
    assert build(store, comp="LALIGA")["facets"]["matchdays"] == [1, 2]
    assert build(store)["facets"]["seasons"] == ["2026-27", "2025-26"] and build(store)["facets"]["matchdays"] == [1, 2, 3, 4]'''
new = '''    assert {k: v for k, v in p["facets"].items() if k != "teams"} == dict(seasons=["2026-27", "2025-26"], matchdays=[1, 2, 3, 4])
    assert build(store, comp="LALIGA")["facets"]["matchdays"] == [1, 2]
    assert build(store)["facets"]["seasons"] == ["2026-27", "2025-26"] and build(store)["facets"]["matchdays"] == [1, 2, 3, 4]
    assert build(store)["facets"]["teams"] == []                                      # the teams facet belongs to one league-season'''
assert s.count(old) == 1
s = s.replace(old, new)
s += '''

# ------------------------------------------------------------------------------------------------------------ the Champions League in the hub (Phase 4.20)
def ucl_store(tmp_path):
    """The domestic synthetic store plus a Champions League 2026-27 league phase as the real rows are stored: stage 'Matches > Matchday N', no matchday number, wikipedia source."""
    path = build_store(tmp_path / "ucl.sqlite")
    conn = db.connect(path)
    for slug in ("u1", "u2", "u3", "u4"):
        add_team(conn, slug, f"Test {slug.upper()} FC")
    rows = [("ucl:1a", 1, "2026-09-09", "u1", "u2", "completed", (2, 0)), ("ucl:1b", 1, "2026-09-09", "u3", "u4", "completed", (1, 1)), ("ucl:2a", 2, "2026-10-14", "u1", "u3", "completed", (0, 3)),
            ("ucl:2b", 2, "2026-10-14", "u2", "u4", "completed", (2, 2)), ("ucl:3a", 3, "2026-10-21", "u1", "u4", "scheduled", None),                           # dated in the past, no result yet
            ("ucl:3b", 3, "2026-10-21", "u2", "u3", "scheduled", None), ("ucl:11a", 11, "2026-12-09", "u1", "u2", "scheduled", None)]
    for rid, md, day, h, a, status, score in rows:
        add_match(conn, rid, "UCL", "2026-27", md, day, h, a, status=status, score=score, source="wikipedia")
    conn.execute("UPDATE matches SET matchday_no=NULL, matchday_label='Matches > Matchday ' || substr(matchday_label, 11) WHERE competition_key='UCL'")
    conn.commit()
    conn.close()
    return path


def test_the_champions_league_is_listed_with_a_matchday_taken_from_its_stage_label(tmp_path):
    path = ucl_store(tmp_path)
    p = build(path, comp="UCL", status="all", limit=50)
    assert p["scope"]["competitions"] == ["UCL"] and p["counts"] == dict(upcoming=1, awaiting_result=2, completed=4, other=0, all=7)
    by = {i["record_id"]: i for i in p["items"]}
    assert by["ucl:2a"]["matchday_no"] == 2 and by["ucl:11a"]["matchday_no"] == 11 and by["ucl:2a"]["matchday_label"] == "Matches > Matchday 2"
    assert by["ucl:2a"]["result"] == dict(home_goals=0, away_goals=3, source="wikipedia")
    assert {i["validation_badge"] for i in p["items"]} == {"Not validated (indicative only)"}
    assert build(path, status="all", limit=50)["scope"]["competitions"] == ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"]


def test_the_matchday_filter_and_facet_work_for_the_champions_league_and_do_not_confuse_1_with_11(tmp_path):
    path = ucl_store(tmp_path)
    assert build(path, comp="UCL")["facets"]["matchdays"] == [1, 2, 3, 11]
    assert ids(build(path, comp="UCL", matchday=1, status="all")) == ["ucl:1b", "ucl:1a"] or sorted(ids(build(path, comp="UCL", matchday=1, status="all"))) == ["ucl:1a", "ucl:1b"]
    p = build(path, comp="UCL", matchday=11, status="all")
    assert ids(p) == ["ucl:11a"] and p["counts"]["all"] == 1
    assert build(path, comp="UCL", matchday=3, status="awaiting_result")["counts"]["awaiting_result"] == 2


def test_the_team_filter_restricts_rows_and_counts_and_needs_a_league(tmp_path):
    path = ucl_store(tmp_path)
    p = build(path, comp="UCL", status="all", team="CLUB:TST:u4", limit=50)
    assert sorted(ids(p)) == ["ucl:1b", "ucl:2b", "ucl:3a"] and p["counts"]["all"] == 3 and p["scope"]["team"] == "CLUB:TST:u4"
    assert [t["entity"] for t in build(path, comp="UCL")["facets"]["teams"]] == ["CLUB:TST:u1", "CLUB:TST:u2", "CLUB:TST:u3", "CLUB:TST:u4"]
    epl = build(path, comp="EPL", status="all", team="CLUB:TST:e1", limit=50)
    assert epl["counts"]["all"] == len(epl["items"]) > 0 and all("CLUB:TST:e1" in (i["home"]["entity"], i["away"]["entity"]) for i in epl["items"])
    for kw in (dict(team="CLUB:TST:u4"), dict(comp="UCL", team="x;drop table"), dict(comp="UCL", team="a")):
        with pytest.raises(matches.MatchesError):
            build(path, **kw)
    with pytest.raises(matches.MatchesError):
        build(path, comp="UEL")                                                       # an archived competition is not a hub competition


def test_champions_league_rows_carry_no_gameweek_eligibility_and_the_freshness_has_an_entry(tmp_path):
    path = ucl_store(tmp_path)
    p = build(path, comp="UCL", status="awaiting_result", limit=50)
    assert [i["eligibility"] for i in p["items"]] == [None, None]                         # the gameweek rules are domestic-only
    fresh = p["freshness"]["competitions"]["UCL"]
    assert fresh["latest_result"] == "2026-10-14" and fresh["approved_sources"] == [] and fresh["state"] != "fresh"
    assert "UCL" in build(path)["freshness"]["competitions"] and set(build(path)["freshness"]["competitions"]) == {"EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"}


def test_the_champions_league_adds_a_fixed_number_of_statements(tmp_path):
    path = ucl_store(tmp_path)
    counts = []
    for kw in (dict(comp="UCL", status="all"), dict(comp="UCL", status="all", team="CLUB:TST:u1"), dict(comp="UCL", status="completed", matchday=2)):
        conn = db.connect(path, readonly=True)
        seen = []
        conn.set_trace_callback(seen.append)
        matches.build(conn, CFG, NOW, **kw)
        conn.close()
        counts.append(len([x for x in seen if x.lstrip().upper().startswith("SELECT")]))
    assert max(counts) - min(counts) <= 1 and max(counts) < 20
'''
p.write_text(s, encoding="utf-8")
print("backend tests patched")
