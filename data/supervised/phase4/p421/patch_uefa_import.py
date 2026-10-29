"""Phase 4.21 part C: one-off edit script for app/store/uefa_import.py (verified-fixtures gate, league-phase matchday check) (record of exactly what changed)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
p = ROOT / "app" / "store" / "uefa_import.py"
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, f"expected one: {old[:80]!r} ({s.count(old)})"
    s = s.replace(old, new)


rep('''Default is a DRY RUN:''', '''Fixtures: `--include-fixtures` inserts only fixtures that are also in the verified-fixtures gate (a list compared with UEFA's own fixture list: date and both clubs); a staged fixture that is not in the gate is
skipped. Only league-phase matchdays 1-8 are ever read: no knockout pairing exists in the staging, and none is created.
Default is a DRY RUN:''')
rep('''GATE = ROOT / "data" / "supervised" / "phase4" / "p419" / "md2_verified_results.csv"''', '''GATE = ROOT / "data" / "supervised" / "phase4" / "p419" / "md2_verified_results.csv"
FIXTURES_GATE = ROOT / "data" / "supervised" / "phase4" / "p421" / "ucl_verified_fixtures.csv"''')
rep('''def validate(df: pd.DataFrame, known_entities: set) -> tuple[list, set]:''', '''def load_fixture_gate(path: Path = FIXTURES_GATE) -> set:
    """{(home_entity, away_entity, date)} of the fixtures that were verified against UEFA's fixture list."""
    if not path or not Path(path).exists():
        return set()
    g = pd.read_csv(path, encoding="utf-8-sig")
    return {(r.home_entity, r.away_entity, str(r.date)) for r in g.itertuples()}


def validate(df: pd.DataFrame, known_entities: set) -> tuple[list, set]:''')
rep('''        if r.status not in ("played", "scheduled"):
            flag(i, "bad_status", str(r.status))''', '''        if r.status not in ("played", "scheduled"):
            flag(i, "bad_status", str(r.status))
        if pd.isna(r.matchday) or not 1 <= int(r.matchday) <= MATCHES_PER_TEAM:
            flag(i, "not_a_league_phase_matchday", str(r.matchday))              # knockout rounds are never staged or imported here''')
rep('''def classify(df: pd.DataFrame, bad: set, stored: dict, gate: dict, include_fixtures: bool, as_of: str) -> list:
    """One decision per staged row: insert_result | complete_fixture | insert_fixture | unchanged | skip_unverified_result | skip_fixture_not_requested | quarantine_conflict | quarantine_invalid."""''',
    '''def classify(df: pd.DataFrame, bad: set, stored: dict, gate: dict, include_fixtures: bool, as_of: str, fixture_gate: set | None = None) -> list:
    """One decision per staged row: insert_result | complete_fixture | insert_fixture | unchanged | skip_unverified_result | skip_unverified_fixture | skip_fixture_not_requested | quarantine_conflict | quarantine_invalid.
    `fixture_gate` None = no check (library use); a set = only fixtures in it are inserted."""''')
rep('''            if old is None:
                out.append(dict(d, action="insert_fixture" if include_fixtures else "skip_fixture_not_requested", reason="" if include_fixtures else "fixtures need --include-fixtures (pairings are not independently verified)",
                                new_status="scheduled" if d["date"] >= as_of else "awaiting_result"))''', '''            if old is None:
                if not include_fixtures:
                    out.append(dict(d, action="skip_fixture_not_requested", reason="fixtures need --include-fixtures"))
                elif fixture_gate is not None and (r.home_entity, r.away_entity, d["date"]) not in fixture_gate:
                    out.append(dict(d, action="skip_unverified_fixture", reason="the fixture (date and pairing) is not in the verified-fixtures gate"))
                else:
                    out.append(dict(d, action="insert_fixture", reason="", new_status="scheduled" if d["date"] >= as_of else "awaiting_result"))''')
rep('''def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, include_fixtures: bool = False, staging: Path = STAGING, gate_path: Path = GATE,
        as_of: str | None = None, report_dir: Path | None = None) -> dict:''', '''def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, include_fixtures: bool = False, staging: Path = STAGING, gate_path: Path = GATE,
        as_of: str | None = None, report_dir: Path | None = None, fixtures_gate_path: Path = FIXTURES_GATE, verify_fixtures: bool = True) -> dict:''')
rep('''        decisions = classify(df, bad, stored_rows(conn), gate, include_fixtures, as_of)''', '''        fixture_gate = load_fixture_gate(fixtures_gate_path) if verify_fixtures else None
        decisions = classify(df, bad, stored_rows(conn), gate, include_fixtures, as_of, fixture_gate)''')
rep('''wikipedia_revision=revid, rows_staged=len(df), validation_issues=issues, counts=counts, decisions=decisions, include_fixtures=include_fixtures)''',
    '''wikipedia_revision=revid, rows_staged=len(df), validation_issues=issues, counts=counts, decisions=decisions, include_fixtures=include_fixtures,
                      fixtures_gate_sha256=B.sha256_file(Path(fixtures_gate_path)) if verify_fixtures and Path(fixtures_gate_path).exists() else None)''')
rep('''    ap.add_argument("--as-of", help''', '''    ap.add_argument("--fixtures-gate", help="verified-fixtures CSV (default: the Phase 4.21 gate)")
    ap.add_argument("--as-of", help''')
rep("as_of=a.as_of, report_dir=Path(a.report_dir) if a.report_dir else None)", "as_of=a.as_of, report_dir=Path(a.report_dir) if a.report_dir else None,\n              fixtures_gate_path=Path(a.fixtures_gate) if a.fixtures_gate else FIXTURES_GATE)")
p.write_text(s, encoding="utf-8")
print("uefa_import patched")
