"""Offline, repeatable import of verified 2026-27 domestic league RESULTS that the store lacks (Phase 4.21): Premier League, Serie A and Ligue 1. No network access anywhere in this module.

Input: the staging files written by Phase 4.20 (data/supervised/phase4/p420/staging/staged_results_<KEY>.csv). A staged row exists only when the Wikipedia results grid (CC BY-SA 4.0) and an independent
cross-check source gave the SAME score and the same date; the date is the stored fixture's own date. Only the result is added to an existing stored fixture; no fixture is created, no date is changed.

Default is a DRY RUN: the store is opened read-only and a report is written; nothing changes. `--apply` writes, in one transaction, to the store named by --store; applying to the production store needs
--production and a --backup that is a byte-identical copy of it.
Rules: a stored result is never overwritten (a different one is quarantined); a stored fixture whose date differs from the staged date, a fixture with a disputed date, a postponed / cancelled match, a reversed
or unknown pairing and any row that fails validation are quarantined instead of imported; importing twice changes nothing (rows are matched on the stored record id and compared by content hash).
A result stored here enters the model universe exactly as a result from an approved sync does (rated, regular, in_universe), so predictions use it; the frozen models themselves are not touched."""
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
import disputes  # noqa: E402
from store import baseline as B  # noqa: E402
from store import published_evidence as PE  # noqa: E402

ROOT = C.ROOT
SEASON = "2026-27"
ALLOWED = ("EPL", "SERIEA", "LIGUE1")                      # leagues without an approved sync source; Bundesliga and La Liga get their results from the startup sync
STAGING_DIR = ROOT / "data" / "supervised" / "phase4" / "p420" / "staging"
PRODUCTION = ROOT / "data" / "footiq.sqlite"
PUBLISHED = ROOT / "data" / "evidence" / "published" / "published_evidence_2026-10-28.csv"
SOURCE, LICENCE = "wikipedia", "CC BY-SA 4.0"
MAX_GOALS = 15
OPEN_STATES = ("scheduled", "awaiting_result")
RESULT_STATES = ("completed", "awarded")
REQUIRED = ["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_date", "wikipedia_score", "wikipedia_revision", "footballdatauk_date", "footballdatauk_score", "tier",
            "date", "home_goals", "away_goals"]


def staged_paths(keys=ALLOWED, directory: Path = STAGING_DIR) -> list[Path]:
    return [directory / f"staged_results_{k}.csv" for k in keys if (directory / f"staged_results_{k}.csv").exists()]


def load_staged(paths) -> pd.DataFrame:
    frames = []
    for p in paths:
        df = pd.read_csv(p, encoding="utf-8-sig")
        df["staged_file"] = Path(p).name
        frames.append(df)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=REQUIRED + ["staged_file"])
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"staged file lacks columns: {missing}")
    return df


def validate(df: pd.DataFrame, known_entities: set, as_of: str) -> tuple[list, set]:
    """Row-level checks. Returns (issues, bad_row_indexes). Issue = dict(row, code, detail)."""
    issues, bad = [], set()
    seen = {}

    def flag(i, code, detail):
        issues.append(dict(row=int(i), code=code, detail=detail))
        bad.add(int(i))

    for r in df.itertuples():
        i = r.Index
        if r.competition_key not in ALLOWED:
            flag(i, "competition_not_allowed", str(r.competition_key))
        if str(r.season) != SEASON:
            flag(i, "bad_season", str(r.season))
        if r.tier != "verified_two_sources":
            flag(i, "not_two_source_verified", str(r.tier))
        for side in (r.home_entity, r.away_entity):
            if not isinstance(side, str) or not side:
                flag(i, "missing_team_identifier", f"{r.home} v {r.away}")
            elif side not in known_entities:
                flag(i, "unknown_team_identifier", side)
        if r.home_entity == r.away_entity:
            flag(i, "home_equals_away", str(r.home_entity))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.date)):
            flag(i, "bad_date", str(r.date))
        elif str(r.date) > as_of:
            flag(i, "result_dated_in_the_future", f"{r.date} > {as_of}")
        elif not "2026-07-01" <= str(r.date) <= "2027-06-30":
            flag(i, "date_outside_season", str(r.date))
        if not (str(r.date) == str(r.store_date) == str(r.footballdatauk_date)):
            flag(i, "dates_disagree", f"staged {r.date}, store {r.store_date}, cross-check {r.footballdatauk_date}")
        try:
            hg, ag = float(r.home_goals), float(r.away_goals)
            ok = hg.is_integer() and ag.is_integer() and 0 <= hg <= MAX_GOALS and 0 <= ag <= MAX_GOALS
        except (TypeError, ValueError):
            ok = False
        if not ok:
            flag(i, "implausible_score", f"{r.home_goals}-{r.away_goals}")
        elif not (str(r.wikipedia_score) == str(r.footballdatauk_score) == f"{int(hg)}-{int(ag)}"):
            flag(i, "sources_disagree_on_score", f"{r.wikipedia_score} / {r.footballdatauk_score} / {int(hg)}-{int(ag)}")
        if r.record_id in seen:
            flag(i, "duplicate_in_file", f"{r.record_id} also on row {seen[r.record_id]}")
        else:
            seen[r.record_id] = i
    pairs = {}
    for r in df.itertuples():
        pairs.setdefault((r.competition_key, r.home_entity, r.away_entity), []).append(r.Index)
    for k, idx in pairs.items():
        if len(idx) > 1:
            for i in idx[1:]:
                if int(i) not in bad:
                    flag(i, "duplicate_pairing_in_file", f"{k[1]} v {k[2]}")
    return issues, bad


def load_published(path: Path) -> pd.DataFrame:
    """Rows of the published-evidence file for this importer, shaped like a staged file (see published_evidence.py)."""
    df = PE.load(Path(path), "league_results")
    df["date"] = df["new_date"]
    df["store_date"] = df["expected_store_date"]
    df["staged_file"] = Path(path).name
    return df


def validate_published(df: pd.DataFrame, known_entities: set, as_of: str) -> tuple[list, set]:
    """Published-evidence mode: the same row checks as `validate`, with the second-source rule applied to redistributable sources only (score from two distinct allowed sources, date from two)."""
    issues, bad = [], set()
    seen = {}

    def flag(i, code, detail):
        issues.append(dict(row=int(i), code=code, detail=detail))
        bad.add(int(i))

    for r in df.itertuples():
        i = r.Index
        if r.action != "update_result":
            flag(i, "bad_action", str(r.action))
        if r.competition_key not in ALLOWED:
            flag(i, "competition_not_allowed", str(r.competition_key))
        if str(r.season) != SEASON:
            flag(i, "bad_season", str(r.season))
        for side in (r.home_entity, r.away_entity):
            if not isinstance(side, str) or not side:
                flag(i, "missing_team_identifier", f"{r.home} v {r.away}")
            elif side not in known_entities:
                flag(i, "unknown_team_identifier", side)
        if r.home_entity == r.away_entity:
            flag(i, "home_equals_away", str(r.home_entity))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.date)):
            flag(i, "bad_date", str(r.date))
        elif str(r.date) > as_of:
            flag(i, "result_dated_in_the_future", f"{r.date} > {as_of}")
        elif not "2026-07-01" <= str(r.date) <= "2027-06-30":
            flag(i, "date_outside_season", str(r.date))
        if str(r.date) != str(r.store_date):
            flag(i, "dates_disagree", f"published {r.date}, store {r.store_date}")
        try:
            hg, ag = float(r.home_goals), float(r.away_goals)
            ok = hg.is_integer() and ag.is_integer() and 0 <= hg <= MAX_GOALS and 0 <= ag <= MAX_GOALS
        except (TypeError, ValueError):
            ok = False
        if not ok:
            flag(i, "implausible_score", f"{r.home_goals}-{r.away_goals}")
            continue
        target = f"{int(hg)}-{int(ag)}"
        sufficient, found = PE.assess(r, True, True, target, str(r.date))
        for code, detail in found + PE.check_label(r, sufficient):
            flag(i, code, detail)
        if r.record_id in seen:
            flag(i, "duplicate_in_file", f"{r.record_id} also on row {seen[r.record_id]}")
        else:
            seen[r.record_id] = i
    pairs = {}
    for r in df.itertuples():
        pairs.setdefault((r.competition_key, r.home_entity, r.away_entity), []).append(r.Index)
    for k, idx in pairs.items():
        if len(idx) > 1:
            for i in idx[1:]:
                if int(i) not in bad:
                    flag(i, "duplicate_pairing_in_file", f"{k[1]} v {k[2]}")
    return issues, bad


def stored_by_record(conn: sqlite3.Connection, keys) -> dict:
    marks = ",".join("?" * len(keys))
    cur = conn.execute(f"SELECT * FROM matches WHERE season=? AND competition_key IN ({marks})", (SEASON, *keys))
    return {r["record_id"]: dict(r) for r in cur}


def classify(df: pd.DataFrame, bad: set, stored: dict, disputed: dict) -> list:
    """One decision per staged row: update_result | unchanged | quarantine_conflict | quarantine_invalid."""
    out = []
    for r in df.itertuples():
        d = dict(row=int(r.Index), competition_key=r.competition_key, record_id=r.record_id, date=str(r.date), home=r.home, away=r.away, home_entity=r.home_entity, away_entity=r.away_entity,
                 hg=None if pd.isna(r.home_goals) else int(r.home_goals), ag=None if pd.isna(r.away_goals) else int(r.away_goals), wikipedia_revision=r.wikipedia_revision)
        if r.Index in bad:
            out.append(dict(d, action="quarantine_invalid", reason="failed validation"))
            continue
        s = stored.get(r.record_id)
        if s is None:
            out.append(dict(d, action="quarantine_conflict", reason="the record is not in the store"))
        elif (s["home_entity_id"], s["away_entity_id"], s["competition_key"]) != (r.home_entity, r.away_entity, r.competition_key):
            out.append(dict(d, action="quarantine_conflict", reason="the stored record has a different pairing or league (reversed or mismatched)"))
        elif s["status"] in RESULT_STATES:
            same = s["match_date"] == d["date"] and s["home_goals_final"] == d["hg"] and s["away_goals_final"] == d["ag"]
            out.append(dict(d, action="unchanged" if same else "quarantine_conflict", reason="" if same else f"the store already has {s['match_date']} {s['home_goals_final']}-{s['away_goals_final']}; verified results are never overwritten"))
        elif s["status"] not in OPEN_STATES:
            out.append(dict(d, action="quarantine_conflict", reason=f"the stored match is {s['status']}"))
        elif s["match_date"] != d["date"]:
            out.append(dict(d, action="quarantine_conflict", reason=f"the stored fixture is dated {s['match_date']}"))
        elif r.record_id in disputed:
            out.append(dict(d, action="quarantine_conflict", reason=f"the fixture date is disputed (sources give {sorted(set(disputed[r.record_id]))}); not resolved here"))
        else:
            out.append(dict(d, action="update_result", reason=""))
    return out


def result_row(stored: dict, d: dict) -> dict:
    """The stored fixture row with its result filled in, shaped like a result from an approved sync (see store/sync.py ingest_records)."""
    row = {c: stored.get(c) for c in B.MATCH_COLS}
    he, ae = stored["home_entity_id"], stored["away_entity_id"]
    outcome = "H" if d["hg"] > d["ag"] else "A" if d["hg"] < d["ag"] else "D"
    row.update(status="completed", home_goals_final=d["hg"], away_goals_final=d["ag"], home_goals_90=d["hg"], away_goals_90=d["ag"], label_90_status="confirmed", outcome=outcome, rated=1, regular=1, in_universe=1,
               model_home_entity=he, model_away_entity=ae, source_system=SOURCE, licence=LICENCE)
    return row


def _rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, paths=None, as_of: str | None = None, report_dir: Path | None = None, evidence: str = "restricted", published: Path | None = None) -> dict:
    as_of = as_of or date.today().isoformat()
    store = Path(store).resolve()
    published_mode = evidence in ("published", "attested")
    if evidence not in ("restricted", "published", "attested"):
        raise SystemExit("--evidence must be 'restricted' (default), 'published' or 'attested'")
    PE.ATTESTED = evidence == "attested"
    published = Path(published) if published else PUBLISHED
    paths = [published] if published_mode else (list(paths) if paths else staged_paths())
    if apply and store == PRODUCTION.resolve():
        if not production:
            raise SystemExit("refusing to write to the production store without --production")
        if backup is None or not Path(backup).is_file() or B.sha256_file(Path(backup)) != B.sha256_file(store):
            raise SystemExit("refusing to write to the production store: --backup must be a copy of it (identical sha256) taken just before the import")
    conn = sqlite3.connect(store) if apply else sqlite3.connect(f"file:{store.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        known = {r[0] for r in conn.execute("SELECT entity_id FROM teams")}
        if published_mode:
            df = load_published(published)
            issues, bad = validate_published(df, known, as_of)
        else:
            df = load_staged(paths)
            issues, bad = validate(df, known, as_of)
        keys = sorted(set(df.competition_key) & set(ALLOWED)) or list(ALLOWED)
        stored = stored_by_record(conn, keys)
        try:
            disputed = disputes.by_record(conn)
        except Exception:                                                       # a store without a quarantine table (tests) has no disputes
            disputed = {}
        decisions = classify(df, bad, stored, disputed)
        counts, by_league = {}, {}
        for d in decisions:
            counts[d["action"]] = counts.get(d["action"], 0) + 1
            by_league.setdefault(d["competition_key"], {}).setdefault(d["action"], 0)
            by_league[d["competition_key"]][d["action"]] += 1
        report = dict(mode="apply" if apply else "dry-run", evidence=evidence, store=str(store), as_of=as_of, staged_files={Path(p).name: B.sha256_file(Path(p)) for p in paths}, rows_staged=len(df),
                      validation_issues=issues, counts=counts, by_league=by_league, decisions=decisions)
        if apply:
            ts = B.utc()
            run_id = conn.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES ('league_results_import',?,?,'running')", ("attested snapshot evidence (Wikipedia values; maintainer-attested cross-check)" if PE.ATTESTED else "published evidence file (Wikipedia, openfootball, OpenLigaDB values)" if published_mode else 'local staging files (Wikipedia results grids, cross-checked)', ts)).lastrowid
            rows, linked = [], []
            for d in decisions:
                if d["action"] == "update_result":
                    rows.append(result_row(stored[d["record_id"]], d))
                    linked.append(d)
            snaps = {}
            for d in linked:
                snap = f"wikipedia-{d['competition_key']}-season-rev{d['wikipedia_revision']}"
                if snap not in snaps:
                    raw = STAGING_DIR / "raw" / f"wikipedia_{d['competition_key']}_season_api.json"
                    stg = published if published_mode else next((Path(p) for p in paths if Path(p).name == f"staged_results_{d['competition_key']}.csv"), None)
                    conn.execute("INSERT OR REPLACE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                 (snap, SOURCE, "json", None, _rel(stg or raw), report["staged_files"].get(stg.name) if stg else None, (stg or raw).stat().st_size if (stg or raw).exists() else None, ts,
                                  str(d["wikipedia_revision"]), LICENCE, (("Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; " + PE.ATTESTED_NOTE) if PE.ATTESTED else "Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; published evidence: score and date confirmed by a second redistributable source recorded in the evidence file" if published_mode else "Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; score and date cross-checked with a second source (not stored)")))
                    snaps[snap] = True
            stats = B.upsert_matches(conn, rows, ts)
            conn.executemany("INSERT OR IGNORE INTO match_sources(source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, source_revision, provenance) VALUES (?,?,?, 'primary',?,?,?,?,?)",
                             [(SOURCE, f"LEAGUE:{d['record_id']}", d["record_id"], f"wikipedia-{d['competition_key']}-season-rev{d['wikipedia_revision']}", LICENCE, ts, str(d["wikipedia_revision"]),
                               (("result from the Wikipedia results grid; fixture date from the stored fixture; " + PE.ATTESTED_NOTE) if PE.ATTESTED else "result from the Wikipedia results grid; fixture date from the stored fixture; published evidence: confirmed by a second redistributable source recorded in the evidence file" if published_mode else "result from the Wikipedia results grid; fixture date from the stored fixture; score and date confirmed by a second, independent source (cross-check only, not stored)")) for d in linked])
            q = [(run_id, SOURCE, f"{d['competition_key']} {SEASON} {d['home_entity']} v {d['away_entity']}", f"{d['action']}: {d['reason']}", json.dumps(d, default=str), ts) for d in decisions if d["action"].startswith("quarantine")]
            conn.executemany("INSERT INTO quarantine(run_id, source, source_ref, reason, payload, created_utc) VALUES (?,?,?,?,?,?)", q)
            latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE status IN ('completed','awarded') AND season=?", (SEASON,)).fetchone()[0]
            conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                         (B.utc(), stats["inserted"], stats["updated"], stats["unchanged"], len(q), latest, json.dumps(dict(counts=counts, by_league=by_league)), run_id))
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
        stamp = "apply" if apply else "dryrun"
        (report_dir / f"league_results_{stamp}.json").write_text(json.dumps(report, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
        pd.DataFrame(decisions).to_csv(report_dir / f"league_results_{stamp}_decisions.csv", index=False, encoding="utf-8-sig")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--store", default=str(PRODUCTION), help="store to read (dry run) or write (--apply); default is the production store")
    ap.add_argument("--apply", action="store_true", help="write to --store (default: dry run, read-only)")
    ap.add_argument("--production", action="store_true", help="required to --apply to the production store")
    ap.add_argument("--backup", help="copy of the production store taken just before the import (identical sha256)")
    ap.add_argument("--staged", nargs="*", help="staged result CSVs (default: staged_results_<KEY>.csv of Phase 4.20)")
    ap.add_argument("--as-of", help="today's date for the future-date check (default today)")
    ap.add_argument("--report-dir", help="write the JSON report and decisions CSV here")
    ap.add_argument("--evidence", choices=("restricted", "published", "attested"), default="restricted", help="attested: like published but ONE redistributable source plus the maintainer's attestation is enough (labelled as such, snapshot use only); restricted (default): the Phase 4.20 staging files with their local cross-check columns; published: only redistributable evidence (see published_evidence.py)")
    ap.add_argument("--published-evidence", help="published evidence CSV (default: data/evidence/published/published_evidence_2026-10-28.csv)")
    a = ap.parse_args(argv)
    rep = run(Path(a.store), a.apply, a.production, Path(a.backup) if a.backup else None, [Path(x) for x in a.staged] if a.staged else None, a.as_of, Path(a.report_dir) if a.report_dir else None, a.evidence, Path(a.published_evidence) if a.published_evidence else None)
    print(json.dumps(dict(mode=rep["mode"], store=rep["store"], rows_staged=rep["rows_staged"], counts=rep["counts"], by_league=rep["by_league"], issues=len(rep["validation_issues"]), applied=rep.get("applied")), indent=1))


if __name__ == "__main__":
    main()
