"""Offline, repeatable import of UEFA Champions League 2026-27 league-phase rows from the locally staged file (Phase 4.19). No network access anywhere in this module.

Inputs (all local; their sha256 is recorded in the report and in `source_snapshots` when applied):
  * staging CSV           data/supervised/phase4/p417/uefa_2026_27_staging.csv  (parsed from a saved Wikipedia revision, CC BY-SA 4.0)
  * verified-results gate data/supervised/phase4/p419/md2_verified_results.csv   (results compared with UEFA's own page; only these results may be imported)
  * Wikipedia snapshot    FootIQ_ML_Data_Readiness/raw_external/wikipedia/27c90c1b45_...json (provenance only)

Fixtures: `--include-fixtures` inserts only fixtures that are also in the verified-fixtures gate (a list compared with UEFA's own fixture list: date and both clubs); a staged fixture that is not in the gate is
skipped. Only league-phase matchdays 1-8 are ever read: no knockout pairing exists in the staging, and none is created.
Default is a DRY RUN: the store is opened read-only and a report is written; nothing changes. `--apply` writes, in one transaction, to the store named by --store.
Applying to the production store additionally needs --production and a verified --backup file (see docs/mini-project/phase4/P4_19_UCL_DATA_COMPLETION.md section 7).
Rules: a result is imported only if it is in the verified gate; a fixture without a result is imported only with --include-fixtures; any row that disagrees with a stored row (date, score, reversed pairing,
status regression) is quarantined and never overwrites; importing twice changes nothing (rows are matched on the natural key competition + season + home + away)."""
import argparse
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import config as C  # noqa: E402
from store import baseline as B  # noqa: E402

ROOT = C.ROOT
KEY, SEASON, COMPETITION_ID = "UCL", "2026-27", "champions-league:cl"
SEASON_WINDOW = ("2026-07-01", "2027-06-30")
STAGING = ROOT / "data" / "supervised" / "phase4" / "p417" / "uefa_2026_27_staging.csv"
GATE = ROOT / "data" / "supervised" / "phase4" / "p419" / "md2_verified_results.csv"
FIXTURES_GATE = ROOT / "data" / "supervised" / "phase4" / "p421" / "ucl_verified_fixtures.csv"
SNAPSHOT = ROOT / "FootIQ_ML_Data_Readiness" / "raw_external" / "wikipedia" / "27c90c1b45_2026_27_UEFA_Champions_League_league_phase.json"
PRODUCTION = ROOT / "data" / "footiq.sqlite"
SOURCE, LICENCE = "wikipedia", "CC BY-SA 4.0"
MAX_GOALS = 12                                           # a league-phase score above this is treated as a data error
MATCHES_PER_TEAM, TEAMS = 8, 36
RESULT_STATES = ("completed", "awarded")


# ---------------------------------------------------------------- loading and validation (pure)
def load_staging(path: Path = STAGING) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[(df.competition_key == KEY) & (df.season == SEASON)].copy().reset_index(drop=True)
    for c in ("home", "away", "home_entity", "away_entity", "status"):
        df[c] = df[c].astype("string").str.strip()
    df["date"] = df["date"].astype("string").str.strip()
    return df


def load_gate(path: Path = GATE) -> dict:
    """(home_entity, away_entity) -> (date, home_goals, away_goals) of the results that were verified against UEFA."""
    if not path.exists():
        return {}
    g = pd.read_csv(path, encoding="utf-8-sig")
    return {(r.home_entity, r.away_entity): (str(r.date), int(r.home_goals), int(r.away_goals)) for r in g.itertuples()}


def load_fixture_gate(path: Path = FIXTURES_GATE) -> set:
    """{(home_entity, away_entity, date)} of the fixtures that were verified against UEFA's fixture list."""
    if not path or not Path(path).exists():
        return set()
    g = pd.read_csv(path, encoding="utf-8-sig")
    return {(r.home_entity, r.away_entity, str(r.date)) for r in g.itertuples()}


def validate(df: pd.DataFrame, known_entities: set) -> tuple[list, set]:
    """Row-level and file-level checks. Returns (issues, bad_row_indexes). Issue = dict(row, code, detail)."""
    issues, bad = [], set()

    def flag(i, code, detail):
        issues.append(dict(row=None if i is None else int(i), code=code, detail=detail))
        if i is not None:
            bad.add(int(i))

    seen = {}
    for r in df.itertuples():
        i = r.Index
        if not isinstance(r.home_entity, str) or not isinstance(r.away_entity, str) or not r.home_entity or not r.away_entity:
            flag(i, "missing_team_identifier", f"{r.home} v {r.away}")
            continue
        if r.home_entity not in known_entities or r.away_entity not in known_entities:
            flag(i, "unknown_team_identifier", f"{r.home_entity} / {r.away_entity} not in teams")
        if r.home_entity == r.away_entity:
            flag(i, "home_equals_away", r.home_entity)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.date)) or pd.isna(r.date):
            flag(i, "bad_date", str(r.date))
        elif not SEASON_WINDOW[0] <= str(r.date) <= SEASON_WINDOW[1]:
            flag(i, "date_outside_season", str(r.date))
        if r.status not in ("played", "scheduled"):
            flag(i, "bad_status", str(r.status))
        if pd.isna(r.matchday) or not 1 <= int(r.matchday) <= MATCHES_PER_TEAM:
            flag(i, "not_a_league_phase_matchday", str(r.matchday))              # knockout rounds are never staged or imported here
        hg, ag = r.home_goals, r.away_goals
        has_score = not (pd.isna(hg) or pd.isna(ag))
        if r.status == "played":
            if not has_score:
                flag(i, "played_without_score", f"{r.home} v {r.away}")
            elif not (float(hg).is_integer() and float(ag).is_integer() and 0 <= hg <= MAX_GOALS and 0 <= ag <= MAX_GOALS):
                flag(i, "implausible_score", f"{hg}-{ag}")
        elif has_score:
            flag(i, "scheduled_with_score", f"{hg}-{ag}")
        k = (r.home_entity, r.away_entity)
        if k in seen:
            flag(i, "duplicate_in_file", f"{r.home} v {r.away} also on row {seen[k]}")
        else:
            seen[k] = i
        if (r.away_entity, r.home_entity) in seen:
            flag(i, "reversed_pairing_in_file", f"{r.home} v {r.away}: the reverse fixture is also listed")
    # file-level structure of a 36-team league phase: every club 8 matches (4 home, 4 away), one match per club per matchday, matchday dates in order
    ok = df.loc[~df.index.isin(bad)]
    teams = sorted(set(ok.home_entity) | set(ok.away_entity))
    if len(df) == 144 and not bad:
        if len(teams) != TEAMS:
            flag(None, "team_count", f"{len(teams)} clubs, expected {TEAMS}")
        for t in teams:
            h, a = int((ok.home_entity == t).sum()), int((ok.away_entity == t).sum())
            if h + a != MATCHES_PER_TEAM or h != a:
                flag(None, "club_fixture_count", f"{t}: {h} home, {a} away")
        for md, g in ok.groupby("matchday"):
            twice = pd.concat([g.home_entity, g.away_entity]).value_counts()
            for t in twice[twice > 1].index:
                flag(None, "club_twice_in_matchday", f"{t} in matchday {md}")
        spans = ok.groupby("matchday").date.agg(["min", "max"]).sort_index()
        for a, b in zip(spans.index[:-1], spans.index[1:]):
            if spans.loc[a, "max"] >= spans.loc[b, "min"]:
                flag(None, "matchday_dates_overlap", f"matchday {a} ends {spans.loc[a, 'max']}, matchday {b} starts {spans.loc[b, 'min']}")
    return issues, bad


# ---------------------------------------------------------------- comparison with the store (read-only)
def stored_rows(conn: sqlite3.Connection) -> dict:
    cur = conn.execute("SELECT record_id, home_entity_id, away_entity_id, match_date, status, home_goals_final, away_goals_final FROM matches WHERE competition_key=? AND season=?", (KEY, SEASON))
    return {(r[1], r[2]): dict(record_id=r[0], date=r[3], status=r[4], hg=r[5], ag=r[6]) for r in cur}


def classify(df: pd.DataFrame, bad: set, stored: dict, gate: dict, include_fixtures: bool, as_of: str, fixture_gate: set | None = None) -> list:
    """One decision per staged row: insert_result | complete_fixture | insert_fixture | unchanged | skip_unverified_result | skip_unverified_fixture | skip_fixture_not_requested | quarantine_conflict | quarantine_invalid.
    `fixture_gate` None = no check (library use); a set = only fixtures in it are inserted."""
    out = []
    for r in df.itertuples():
        d = dict(row=int(r.Index), matchday=int(r.matchday), date=str(r.date), home=r.home, away=r.away, home_entity=r.home_entity, away_entity=r.away_entity, status=r.status,
                 hg=None if pd.isna(r.home_goals) else int(r.home_goals), ag=None if pd.isna(r.away_goals) else int(r.away_goals))
        k = (r.home_entity, r.away_entity)
        if r.Index in bad:
            out.append(dict(d, action="quarantine_invalid", reason="failed validation"))
            continue
        old = stored.get(k)
        if old is None and (r.away_entity, r.home_entity) in stored:
            out.append(dict(d, action="quarantine_conflict", reason="the reverse pairing is already stored"))
            continue
        if r.status == "played":
            verified = gate.get(k) == (d["date"], d["hg"], d["ag"])
            if old is None:
                out.append(dict(d, action="insert_result" if verified else "skip_unverified_result", reason="" if verified else "result not in the verified gate (or differs from it)"))
            elif old["status"] in RESULT_STATES:
                same = old["date"] == d["date"] and old["hg"] == d["hg"] and old["ag"] == d["ag"]
                out.append(dict(d, action="unchanged" if same else "quarantine_conflict", reason="" if same else f"store has {old['date']} {old['hg']}-{old['ag']}"))
            elif verified and old["date"] == d["date"]:
                out.append(dict(d, action="complete_fixture", reason="stored fixture gets its verified result", record_id=old["record_id"]))
            else:
                out.append(dict(d, action="quarantine_conflict", reason="stored fixture differs in date or the result is not verified"))
        else:                                                                    # scheduled in the staging
            if old is None:
                if not include_fixtures:
                    out.append(dict(d, action="skip_fixture_not_requested", reason="fixtures need --include-fixtures"))
                elif fixture_gate is not None and (r.home_entity, r.away_entity, d["date"]) not in fixture_gate:
                    out.append(dict(d, action="skip_unverified_fixture", reason="the fixture (date and pairing) is not in the verified-fixtures gate"))
                else:
                    out.append(dict(d, action="insert_fixture", reason="", new_status="scheduled" if d["date"] >= as_of else "awaiting_result"))
            elif old["date"] != d["date"] and old["status"] not in RESULT_STATES:
                out.append(dict(d, action="quarantine_conflict", reason=f"stored fixture is dated {old['date']}"))
            else:
                out.append(dict(d, action="unchanged", reason="stored row is at least as advanced" if old["status"] in RESULT_STATES else ""))
    return out


def build_row(d: dict, revid, status: str) -> dict:
    """A matches row in the same shape as the existing Wikipedia rows of this competition (Matches > Matchday N, date only, not part of the frozen model universe)."""
    stage = f"Matches > Matchday {d['matchday']}"
    done = status in RESULT_STATES
    outcome = None
    if done:
        outcome = "H" if d["hg"] > d["ag"] else "A" if d["hg"] < d["ag"] else "D"
    return dict(record_id=f"WP:UCL:{SEASON}:{d['home_entity']}:{d['away_entity']}", kind="club", competition_id=COMPETITION_ID, competition_key=KEY, season=SEASON, stage=stage, matchday_label=stage, matchday_no=None,
                match_date=d["date"], kickoff_local=None, kickoff_utc=None, time_precision="date_only", home_entity_id=d["home_entity"], away_entity_id=d["away_entity"], model_home_entity=None, model_away_entity=None,
                home_name=d["home"], away_name=d["away"], status=status, home_goals_final=d["hg"] if done else None, away_goals_final=d["ag"] if done else None, home_goals_90=None, away_goals_90=None,
                label_90_status="confirmed" if done else None, outcome=outcome, shootout_winner=None, neutral=None, rated=None, regular=None, in_universe=0, tier=None, competition_type="continental_club",
                source_system=SOURCE, licence=LICENCE, src_order=None)


# ---------------------------------------------------------------- the run
def _rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, include_fixtures: bool = False, staging: Path = STAGING, gate_path: Path = GATE,
        as_of: str | None = None, report_dir: Path | None = None, fixtures_gate_path: Path = FIXTURES_GATE, verify_fixtures: bool = True) -> dict:
    as_of = as_of or date.today().isoformat()
    store = Path(store).resolve()
    if apply and store == PRODUCTION.resolve():
        if not production:
            raise SystemExit("refusing to write to the production store without --production")
        if backup is None or not Path(backup).is_file() or B.sha256_file(Path(backup)) != B.sha256_file(store):
            raise SystemExit("refusing to write to the production store: --backup must be a copy of it (identical sha256) taken just before the import")
    conn = sqlite3.connect(f"file:{store.as_posix()}?mode=ro", uri=True) if not apply else sqlite3.connect(store)
    conn.row_factory = sqlite3.Row
    try:
        known = {r[0] for r in conn.execute("SELECT entity_id FROM teams")}
        df = load_staging(staging)
        gate = load_gate(gate_path)
        issues, bad = validate(df, known)
        fixture_gate = load_fixture_gate(fixtures_gate_path) if verify_fixtures else None
        decisions = classify(df, bad, stored_rows(conn), gate, include_fixtures, as_of, fixture_gate)
        counts = {}
        for d in decisions:
            counts[d["action"]] = counts.get(d["action"], 0) + 1
        revid = int(df.page_revid.iloc[0]) if len(df) else None
        report = dict(mode="apply" if apply else "dry-run", store=str(store), as_of=as_of, staging_sha256=B.sha256_file(staging), gate_sha256=B.sha256_file(gate_path) if Path(gate_path).exists() else None,
                      wikipedia_revision=revid, rows_staged=len(df), validation_issues=issues, counts=counts, decisions=decisions, include_fixtures=include_fixtures,
                      fixtures_gate_sha256=B.sha256_file(Path(fixtures_gate_path)) if verify_fixtures and Path(fixtures_gate_path).exists() else None)
        if apply:
            ts = B.utc()
            run_id = conn.execute("INSERT INTO sync_runs(kind, source, competition_key, started_utc, outcome) VALUES ('uefa_import','local staging file (Wikipedia revision %s)',?,?,'running')" % revid, (KEY, ts)).lastrowid
            rows = []
            for d in decisions:
                if d["action"] in ("insert_result", "complete_fixture"):
                    rows.append(build_row(d, revid, "completed"))
                elif d["action"] == "insert_fixture":
                    rows.append(build_row(d, revid, d["new_status"]))
            stored = stored_rows(conn)
            for r in rows:                                               # a completed fixture keeps its stored record id so no second row appears
                old = stored.get((r["home_entity_id"], r["away_entity_id"]))
                if old:
                    r["record_id"] = old["record_id"]
            snap = f"uefa-ucl-2026-27-staging-rev{revid}"
            conn.execute("INSERT OR REPLACE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (snap, SOURCE, "csv", None, _rel(staging), report["staging_sha256"], staging.stat().st_size, ts, str(revid), LICENCE,
                          "Wikipedia contributors, '2026-27 UEFA Champions League league phase', CC BY-SA 4.0; results cross-checked with uefa.com"))
            stats = B.upsert_matches(conn, rows, ts)
            conn.executemany("INSERT OR IGNORE INTO match_sources(source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, source_revision, provenance) VALUES (?,?,?, 'primary',?,?,?,?,?)",
                             [(SOURCE, r["record_id"], r["record_id"], snap, LICENCE, ts, str(revid), f"staging row {d['row']}; verified against uefa.com" if d["action"] != "insert_fixture" else f"staging row {d['row']}; fixture, pairing not independently verified")
                              for r, d in zip(rows, [x for x in decisions if x["action"] in ("insert_result", "complete_fixture", "insert_fixture")])])
            q = [(run_id, SOURCE, f"UCL {SEASON} md{d['matchday']} {d['home_entity']} v {d['away_entity']}", f"{d['action']}: {d['reason']}", json.dumps(d, default=str), ts)
                 for d in decisions if d["action"].startswith("quarantine")]
            conn.executemany("INSERT INTO quarantine(run_id, source, source_ref, reason, payload, created_utc) VALUES (?,?,?,?,?,?)", q)
            latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (KEY,)).fetchone()[0]
            conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                         (B.utc(), stats["inserted"], stats["updated"], stats["unchanged"], len(q), latest, json.dumps(dict(counts=counts, include_fixtures=include_fixtures)), run_id))
            conn.commit()
            report["applied"] = dict(stats, quarantined=len(q), run_id=run_id)
    except Exception:
        if apply:
            conn.rollback()
        raise
    finally:
        conn.close()
    if report_dir:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = ("apply" if apply else "dryrun") + ("_fixtures" if include_fixtures else "")
        (report_dir / f"uefa_import_{stamp}.json").write_text(json.dumps(report, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
        pd.DataFrame(decisions).to_csv(report_dir / f"uefa_import_{stamp}_decisions.csv", index=False, encoding="utf-8-sig")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--store", default=str(PRODUCTION), help="store to read (dry run) or write (--apply); default is the production store")
    ap.add_argument("--apply", action="store_true", help="write to --store (default: dry run, read-only)")
    ap.add_argument("--production", action="store_true", help="required to --apply to the production store")
    ap.add_argument("--backup", help="copy of the production store taken just before the import (identical sha256)")
    ap.add_argument("--include-fixtures", action="store_true", help="also insert the scheduled fixtures (default: verified results only)")
    ap.add_argument("--staging", help="staging CSV (default: the Phase 4.17 file)")
    ap.add_argument("--gate", help="verified-results CSV (default: the Phase 4.19 matchday-2 gate)")
    ap.add_argument("--fixtures-gate", help="verified-fixtures CSV (default: the Phase 4.21 gate)")
    ap.add_argument("--as-of", help="date used to decide scheduled vs awaiting_result (default today)")
    ap.add_argument("--report-dir", help="write the JSON report and decisions CSV here")
    a = ap.parse_args(argv)
    rep = run(Path(a.store), a.apply, a.production, Path(a.backup) if a.backup else None, a.include_fixtures, staging=Path(a.staging) if a.staging else STAGING, gate_path=Path(a.gate) if a.gate else GATE, as_of=a.as_of, report_dir=Path(a.report_dir) if a.report_dir else None,
              fixtures_gate_path=Path(a.fixtures_gate) if a.fixtures_gate else FIXTURES_GATE)
    print(json.dumps(dict(mode=rep["mode"], store=rep["store"], rows_staged=rep["rows_staged"], counts=rep["counts"], issues=len(rep["validation_issues"]), applied=rep.get("applied")), indent=1))


if __name__ == "__main__":
    main()
