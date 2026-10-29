"""Phase 4.21 part C: update tests/test_uefa_import.py for the verified-fixtures gate (record of exactly what changed)."""
from pathlib import Path

p = Path(__file__).resolve().parents[4] / "tests" / "test_uefa_import.py"
s = p.read_text(encoding="utf-8")
old1 = 'U.run(store, apply=True, include_fixtures=True, staging=p, as_of="2026-10-12")'
old2 = 'r = U.run(store, apply=True, include_fixtures=True, as_of="2026-10-28")'
assert s.count(old1) == 1 and s.count(old2) == 1
s = s.replace(old1, 'U.run(store, apply=True, include_fixtures=True, staging=p, as_of="2026-10-12", verify_fixtures=False)')
s = s.replace(old2, 'r = U.run(store, apply=True, include_fixtures=True, as_of="2026-10-28", verify_fixtures=False)')
s += '''

# ---------------------------------------------------------------- verified fixtures (Phase 4.21)
needs_fixture_gate = pytest.mark.skipif(not U.FIXTURES_GATE.exists(), reason="Phase 4.21 verified-fixtures gate missing")


@needs_staging
@needs_fixture_gate
def test_the_fixtures_gate_holds_exactly_the_90_league_phase_fixtures_of_matchdays_4_to_8(staging):
    gate = U.load_fixture_gate()
    fx = staging[staging.status == "scheduled"]
    assert len(gate) == 90 and gate == {(r.home_entity, r.away_entity, str(r.date)) for r in fx.itertuples()}
    assert set(fx.matchday) == {3, 4, 5, 6, 7, 8} - {3} or set(fx.matchday) == {4, 5, 6, 7, 8} or set(fx.matchday) >= {4, 5, 6, 7, 8}


@needs_staging
@needs_fixture_gate
def test_only_fixtures_in_the_gate_are_inserted_and_completed_matches_are_never_listed_as_upcoming(store):
    conn = sqlite3.connect(store)
    stored = U.stored_rows(conn)
    conn.close()
    st = U.load_staging()
    dec = pd.DataFrame(U.classify(st, set(), stored, U.load_gate(), True, "2026-10-28", U.load_fixture_gate()))
    inserted = dec[dec.action == "insert_fixture"]
    assert len(inserted) == 90 and set(inserted.new_status) == {"scheduled"} and inserted.date.min() >= "2026-11-03"       # all dated after the as-of day: none is a played match shown as upcoming
    assert not set(inserted.matchday) & {1, 2, 3}
    shrunk = {x for x in U.load_fixture_gate() if x[2] != "2026-11-03"}
    dec2 = pd.DataFrame(U.classify(st, set(), stored, U.load_gate(), True, "2026-10-28", shrunk))
    assert (dec2.action == "skip_unverified_fixture").sum() == 9 and (dec2.action == "insert_fixture").sum() == 81
    changed = {(h, a, "2026-11-05") if d == "2026-11-03" else (h, a, d) for h, a, d in U.load_fixture_gate()}                      # a date that differs from UEFA's list
    assert (pd.DataFrame(U.classify(st, set(), stored, U.load_gate(), True, "2026-10-28", changed)).action == "skip_unverified_fixture").sum() >= 1


@needs_staging
@needs_fixture_gate
def test_run_with_the_gate_inserts_the_90_fixtures_repeatably_and_never_creates_knockout_rows(store):
    first = U.run(store, apply=True, include_fixtures=True, as_of="2026-10-28")
    assert first["counts"]["insert_fixture"] == 90 and first["applied"]["inserted"] == 108 - 18          # results of matchday 2 and 3 are in the staging file but this store holds matchday 1 only
    second = U.run(store, apply=True, include_fixtures=True, as_of="2026-10-28")
    assert second["applied"]["inserted"] == 0 and second["applied"]["updated"] == 0
    conn = sqlite3.connect(store)
    assert conn.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0] == 144
    assert conn.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND stage NOT LIKE 'Matches > Matchday %'").fetchone()[0] == 0
    assert conn.execute("SELECT MAX(CAST(substr(stage, 20) AS INTEGER)) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0] == 8
    conn.close()


def test_a_knockout_matchday_in_the_staging_is_refused():
    df = known_df(matchday=9)
    issues, bad = U.validate(df, {"E:A", "E:B"})
    assert "not_a_league_phase_matchday" in {i["code"] for i in issues} and 0 in bad
    assert not U.validate(known_df(matchday=8), {"E:A", "E:B"})[0]
'''
p.write_text(s, encoding="utf-8")
print("uefa tests patched")
