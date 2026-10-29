"""Offline, repeatable application of the Phase 4.23 reconciliation proposals (results the store lacks, played-day corrections, fixture-date corrections, one postponement). No network access anywhere in this module.

Input: data/supervised/phase4/p423/staging/proposed_changes.csv, one row per change with its evidence trail (sources, their dates and scores, the tier of the evidence).
  add_result            an open fixture gets its result (>= 2 sources agree on the score); the stored date is right
  add_result_with_date  the same, and the stored date was a placeholder: the played day comes from two sources
  correct_date          an unplayed fixture's date changes (>= 2 independent sources give the new date)
  set_postponed         a fixture past its date, with no result anywhere and a moved date in the approved feed, becomes 'postponed' (its date is not touched)
Tiers: strong | provider_assisted (decided only when football-data.org's date is counted; needs --include-provider-assisted) | decision (needs --include-decisions).

Default is a DRY RUN: the store is opened read-only and a report is written; nothing changes. `--apply` writes, in one transaction, to the store named by --store; applying to the production store needs --production
and a --backup that is a byte-identical copy of it.
Rules: a stored result is never overwritten; every change states the store's date and status it was prepared against and is quarantined (not applied) if the store no longer matches; a played match's date is only
changed together with its result; a corrected date moves a fixture by at most four days and never into the past; a corrected fixture loses its stored kickoff time (it belonged to the old date; the date is all the
evidence gives); a change already in place is `unchanged`, so importing twice changes nothing; quarantine rows of the original findings are never deleted (the evidence trail stays)."""
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
from store import league_results_import as L  # noqa: E402

ROOT = C.ROOT
SEASON = "2026-27"
ALLOWED = ("EPL", "SERIEA", "LIGUE1", "LALIGA")
ACTIONS = ("add_result", "add_result_with_date", "correct_date", "set_postponed")
TIERS = ("strong", "provider_assisted", "decision")
PROPOSALS = ROOT / "data" / "supervised" / "phase4" / "p423" / "staging" / "proposed_changes.csv"
PRODUCTION = ROOT / "data" / "footiq.sqlite"
MAX_SHIFT_DAYS = 4
MAX_GOALS = 15
OPEN = ("scheduled", "awaiting_result")
DONE = ("completed", "awarded")
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
REQUIRED = ["change_id", "record_id", "competition_key", "home_entity", "away_entity", "action", "tier", "expected_store_status", "expected_store_date", "new_date", "home_goals", "away_goals", "wikipedia_score",
            "footballdatauk_score", "fixturedownload_score", "fixturedownload_date", "footballdatauk_date", "openligadb_date", "provider_date", "evidence"]


def load_proposals(path: Path = PROPOSALS) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"proposal file lacks columns: {missing}")
    return df


def _isnull(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v))


def _days(a: str, b: str) -> int:
    return abs((pd.Timestamp(a) - pd.Timestamp(b)).days)


def validate(df: pd.DataFrame, known: set, as_of: str) -> tuple[list, set]:
    """Row-level checks. Returns (issues, bad_row_indexes)."""
    issues, bad = [], set()
    seen_id, seen_rec = {}, {}

    def flag(i, code, detail):
        issues.append(dict(row=int(i), code=code, detail=detail))
        bad.add(int(i))

    for r in df.itertuples():
        i = r.Index
        if r.action not in ACTIONS:
            flag(i, "bad_action", str(r.action))
            continue
        if r.tier not in TIERS:
            flag(i, "bad_tier", str(r.tier))
        if r.competition_key not in ALLOWED:
            flag(i, "competition_not_allowed", str(r.competition_key))
        for e in (r.home_entity, r.away_entity):
            if _isnull(e) or e not in known:
                flag(i, "unknown_team_identifier", str(e))
        if r.home_entity == r.away_entity:
            flag(i, "home_equals_away", str(r.home_entity))
        if _isnull(r.evidence) or not str(r.evidence).strip():
            flag(i, "no_evidence", str(r.change_id))
        if r.change_id in seen_id:
            flag(i, "duplicate_change_id", f"{r.change_id} also on row {seen_id[r.change_id]}")
        seen_id.setdefault(r.change_id, i)
        if r.record_id in seen_rec:
            flag(i, "two_changes_for_one_fixture", f"{r.record_id} also on row {seen_rec[r.record_id]}")
        seen_rec.setdefault(r.record_id, i)
        if _isnull(r.expected_store_date) or not ISO.fullmatch(str(r.expected_store_date)):
            flag(i, "bad_expected_date", str(r.expected_store_date))
        if r.action in ("add_result", "add_result_with_date"):
            try:
                hg, ag = float(r.home_goals), float(r.away_goals)
                good = hg.is_integer() and ag.is_integer() and 0 <= hg <= MAX_GOALS and 0 <= ag <= MAX_GOALS
            except (TypeError, ValueError):
                good = False
            if not good:
                flag(i, "implausible_score", f"{r.home_goals}-{r.away_goals}")
                continue
            target = f"{int(hg)}-{int(ag)}"
            recorded = [str(x) for x in (r.wikipedia_score, r.footballdatauk_score, r.fixturedownload_score) if not _isnull(x)]
            if len(recorded) < 2 or any(x != target for x in recorded):
                flag(i, "scores_not_two_source_verified", f"staged {target}, sources {recorded}")
            if _isnull(r.new_date) or not ISO.fullmatch(str(r.new_date)):
                flag(i, "bad_date", str(r.new_date))
            elif str(r.new_date) > as_of:
                flag(i, "result_dated_in_the_future", f"{r.new_date} > {as_of}")
            elif r.action == "add_result" and str(r.new_date) != str(r.expected_store_date):
                flag(i, "date_differs_for_add_result", f"{r.new_date} vs stored {r.expected_store_date}")
            elif r.action == "add_result_with_date":
                dates = [str(x) for x in (r.footballdatauk_date, r.fixturedownload_date) if not _isnull(x)]
                if len(dates) < 2 or any(x != str(r.new_date) for x in dates):
                    flag(i, "played_day_not_two_source_verified", f"{r.new_date} vs {dates}")
                elif _days(str(r.new_date), str(r.expected_store_date)) > MAX_SHIFT_DAYS or str(r.new_date) == str(r.expected_store_date):
                    flag(i, "bad_date_shift", f"{r.expected_store_date} -> {r.new_date}")
            if r.tier != "strong":
                flag(i, "result_must_be_strong", str(r.tier))
        elif r.action == "correct_date":
            if _isnull(r.new_date) or not ISO.fullmatch(str(r.new_date)):
                flag(i, "bad_date", str(r.new_date))
                continue
            if str(r.new_date) == str(r.expected_store_date):
                flag(i, "no_change", str(r.new_date))
            elif _days(str(r.new_date), str(r.expected_store_date)) > MAX_SHIFT_DAYS:
                flag(i, "date_shift_too_large", f"{r.expected_store_date} -> {r.new_date}")
            if str(r.new_date) < as_of:
                flag(i, "corrected_date_in_the_past", str(r.new_date))
            own = [str(x) for x in (r.fixturedownload_date, r.openligadb_date, r.footballdatauk_date) if not _isnull(x) and str(x) == str(r.new_date)]
            prov = not _isnull(r.provider_date) and str(r.provider_date) == str(r.new_date)
            if r.tier == "strong" and len(own) < 2:
                flag(i, "strong_needs_two_sources_without_the_provider", f"{own}")
            if r.tier == "provider_assisted" and len(own) + (1 if prov else 0) < 2:
                flag(i, "provider_assisted_needs_two_sources", f"{own} provider={prov}")
            if r.tier == "decision":
                flag(i, "date_correction_cannot_be_a_decision", str(r.tier))
        elif r.action == "set_postponed":
            if r.tier != "decision":
                flag(i, "postponement_must_be_a_decision", str(r.tier))
            if str(r.expected_store_date) >= as_of:
                flag(i, "postponement_of_a_future_fixture", str(r.expected_store_date))
            if not _isnull(r.home_goals) or not _isnull(r.away_goals):
                flag(i, "postponement_with_a_score", f"{r.home_goals}-{r.away_goals}")
    return issues, bad


def classify(df: pd.DataFrame, bad: set, stored: dict, tiers: set) -> list:
    """One decision per row: apply | unchanged | skip_tier_not_enabled | quarantine_conflict | quarantine_invalid."""
    out = []
    for r in df.itertuples():
        d = dict(row=int(r.Index), change_id=r.change_id, record_id=r.record_id, competition_key=r.competition_key, action_type=r.action, tier=r.tier, home=r.home, away=r.away, expected_store_date=str(r.expected_store_date),
                 new_date=None if _isnull(r.new_date) else str(r.new_date), hg=None if _isnull(r.home_goals) else int(r.home_goals), ag=None if _isnull(r.away_goals) else int(r.away_goals), evidence=r.evidence)
        if r.Index in bad:
            out.append(dict(d, action="quarantine_invalid", reason="failed validation"))
            continue
        if r.tier not in tiers:
            out.append(dict(d, action="skip_tier_not_enabled", reason=f"tier '{r.tier}' is not enabled for this run"))
            continue
        s = stored.get(r.record_id)
        if s is None:
            out.append(dict(d, action="quarantine_conflict", reason="the record is not in the store"))
            continue
        if (s["home_entity_id"], s["away_entity_id"], s["competition_key"]) != (r.home_entity, r.away_entity, r.competition_key):
            out.append(dict(d, action="quarantine_conflict", reason="the stored record has a different pairing or league"))
            continue
        if r.action in ("add_result", "add_result_with_date"):
            target_date = str(r.new_date)
            if s["status"] in DONE:
                same = s["match_date"] == target_date and s["home_goals_final"] == d["hg"] and s["away_goals_final"] == d["ag"]
                out.append(dict(d, action="unchanged" if same else "quarantine_conflict", reason="" if same else f"the store already has {s['match_date']} {s['home_goals_final']}-{s['away_goals_final']}; verified results are never overwritten"))
                continue
        elif r.action == "correct_date":
            if s["status"] in OPEN and s["match_date"] == str(r.new_date):
                out.append(dict(d, action="unchanged", reason=""))
                continue
        elif r.action == "set_postponed":
            if s["status"] == "postponed":
                out.append(dict(d, action="unchanged", reason=""))
                continue
        if s["status"] not in OPEN:
            out.append(dict(d, action="quarantine_conflict", reason=f"the stored match is {s['status']}, not an open fixture"))
        elif s["status"] != r.expected_store_status or s["match_date"] != str(r.expected_store_date):
            out.append(dict(d, action="quarantine_conflict", reason=f"the store changed since the proposal was prepared (now {s['status']} {s['match_date']}, prepared against {r.expected_store_status} {r.expected_store_date})"))
        else:
            out.append(dict(d, action="apply", reason=""))
    return out


def new_row(stored: dict, d: dict) -> dict:
    """The stored row after the change."""
    if d["action_type"] in ("add_result", "add_result_with_date"):
        row = L.result_row(stored, d)
        if d["action_type"] == "add_result_with_date":
            row.update(match_date=d["new_date"], kickoff_local=None, kickoff_utc=None, time_precision="date_only")
        return row
    row = {c: stored.get(c) for c in B.MATCH_COLS}
    if d["action_type"] == "correct_date":
        row.update(match_date=d["new_date"], kickoff_local=None, kickoff_utc=None, time_precision="date_only")
    else:
        row.update(status="postponed")
    return row


def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, proposals: Path = PROPOSALS, tiers=("strong",), as_of: str | None = None, report_dir: Path | None = None) -> dict:
    as_of = as_of or date.today().isoformat()
    store = Path(store).resolve()
    tiers = set(tiers)
    if apply and store == PRODUCTION.resolve():
        if not production:
            raise SystemExit("refusing to write to the production store without --production")
        if backup is None or not Path(backup).is_file() or B.sha256_file(Path(backup)) != B.sha256_file(store):
            raise SystemExit("refusing to write to the production store: --backup must be a copy of it (identical sha256) taken just before the import")
    conn = sqlite3.connect(store) if apply else sqlite3.connect(f"file:{store.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        known = {r[0] for r in conn.execute("SELECT entity_id FROM teams")}
        df = load_proposals(proposals)
        issues, bad = validate(df, known, as_of)
        stored = L.stored_by_record(conn, ALLOWED)
        decisions = classify(df, bad, stored, tiers)
        counts, by = {}, {}
        for d in decisions:
            counts[d["action"]] = counts.get(d["action"], 0) + 1
            by.setdefault(d["competition_key"], {}).setdefault(f"{d['action_type']}:{d['action']}", 0)
            by[d["competition_key"]][f"{d['action_type']}:{d['action']}"] += 1
        report = dict(mode="apply" if apply else "dry-run", store=str(store), as_of=as_of, tiers_enabled=sorted(tiers), proposals_sha256=B.sha256_file(Path(proposals)), rows=len(df), validation_issues=issues,
                      counts=counts, by_league=by, decisions=decisions)
        if apply:
            ts = B.utc()
            run_id = conn.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES ('reconcile_import','Phase 4.23 reconciliation proposals (offline evidence)',?,'running')", (ts,)).lastrowid
            todo = [d for d in decisions if d["action"] == "apply"]
            rows = [new_row(stored[d["record_id"]], d) for d in todo]
            snap = f"reconcile-p423-{report['proposals_sha256'][:12]}"
            conn.execute("INSERT OR REPLACE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (snap, "reconciliation", "csv", None, L._rel(Path(proposals)), report["proposals_sha256"], Path(proposals).stat().st_size, ts, None, "scores: Wikipedia CC BY-SA 4.0; dates are facts cross-checked in several public sources",
                          "evidence trail per change in the proposals file"))
            stats = B.upsert_matches(conn, rows, ts)
            conn.executemany("INSERT OR IGNORE INTO match_sources(source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, source_revision, provenance) VALUES ('reconciliation',?,?,'primary',?,?,?,NULL,?)",
                             [(f"RECON:{d['change_id']}", d["record_id"], snap, "see evidence", ts, f"{d['action_type']} ({d['tier']}): {d['evidence']} | store before: {stored[d['record_id']]['status']} {stored[d['record_id']]['match_date']}") for d in todo])
            q = [(run_id, "reconciliation", f"{d['competition_key']} {SEASON} {d['record_id']}", f"{d['action']}: {d['reason']}", json.dumps(d, default=str), ts) for d in decisions if d["action"].startswith("quarantine")]
            conn.executemany("INSERT INTO quarantine(run_id, source, source_ref, reason, payload, created_utc) VALUES (?,?,?,?,?,?)", q)
            latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE status IN ('completed','awarded') AND season=?", (SEASON,)).fetchone()[0]
            conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                         (B.utc(), stats["inserted"], stats["updated"], stats["unchanged"], len(q), latest, json.dumps(dict(counts=counts, tiers=sorted(tiers))), run_id))
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
        stamp = ("apply" if apply else "dryrun") + "_" + "-".join(sorted(tiers))
        (report_dir / f"reconcile_{stamp}.json").write_text(json.dumps(report, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
        pd.DataFrame(decisions).to_csv(report_dir / f"reconcile_{stamp}_decisions.csv", index=False, encoding="utf-8-sig")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--store", default=str(PRODUCTION), help="store to read (dry run) or write (--apply); default is the production store")
    ap.add_argument("--apply", action="store_true", help="write to --store (default: dry run, read-only)")
    ap.add_argument("--production", action="store_true", help="required to --apply to the production store")
    ap.add_argument("--backup", help="copy of the production store taken just before the import (identical sha256)")
    ap.add_argument("--proposals", help="proposal CSV (default: the Phase 4.23 file)")
    ap.add_argument("--include-provider-assisted", action="store_true", help="also apply date corrections decided only with football-data.org's date counted")
    ap.add_argument("--include-decisions", action="store_true", help="also apply changes that need the owner's judgement (the postponement)")
    ap.add_argument("--as-of", help="today's date for the date checks (default today)")
    ap.add_argument("--report-dir", help="write the JSON report and decisions CSV here")
    a = ap.parse_args(argv)
    tiers = ["strong"] + (["provider_assisted"] if a.include_provider_assisted else []) + (["decision"] if a.include_decisions else [])
    rep = run(Path(a.store), a.apply, a.production, Path(a.backup) if a.backup else None, Path(a.proposals) if a.proposals else PROPOSALS, tiers, a.as_of, Path(a.report_dir) if a.report_dir else None)
    print(json.dumps(dict(mode=rep["mode"], store=rep["store"], tiers=rep["tiers_enabled"], rows=rep["rows"], counts=rep["counts"], by_league=rep["by_league"], issues=len(rep["validation_issues"]), applied=rep.get("applied")), indent=1))


if __name__ == "__main__":
    main()
