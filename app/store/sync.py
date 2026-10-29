"""Results synchronisation (Phase 1).

What this does
  * Ingests results/fixtures from APPROVED sources into the SQLite store, idempotently, never creating a second row for the same match.
  * Runs a cheap freshness check in the background at start-up (non-blocking) and then periodically (low frequency).
  * Records every run (`sync_runs`), every conflict (`quarantine`) and every payload (`source_snapshots`), so the UI can show
    "Last updated / Latest match result / Source" truthfully and stale data is never presented as live.

What it never does
  * It makes NO network request unless `live_enabled` is true in config/sync.json AND a real contact string is configured (adapter safeguard).
  * It never reads or writes a model artifact. New results only extend the historical state the frozen models read.
  * Only the sources approved in config/sync.json are used; today that is OpenLigaDB for the Bundesliga (bl1, season 2026). Wikipedia stays
    confirmation-only and is not wired here; no other provider exists in this module.
"""
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import config as C  # noqa: E402
from store import baseline, db  # noqa: E402

ROOT = C.ROOT
CONFIG_PATH = ROOT / "config" / "sync.json"
ADAPTER_DIR = ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"

# approved competition -> (source competition_id in the store, adapter league shortcut, season label in the store, season token in the source)
APPROVED = {"BUNDESLIGA": dict(source="openligadb", competition_id="deutschland:1-bundesliga", league="bl1", season_label="2026-27", season="2026"),
            "LALIGA": dict(source="openligadb", competition_id="espana:1-liga", league="la1", season_label="2026-27", season="2026")}      # Phase 4.9: approved in code; it is scheduled only when config/sync.json lists it

# Leagues whose integration is PREPARED from saved snapshots only (offline replay with `replay_payload(spec=...)`, tested in tests/test_refresh_integration.py and
# data/supervised/phase4/p48b/offline_rehearsal.py). They are NOT in APPROVED, so neither the scheduler nor `config/sync.json` can ever request them.
OFFLINE_PREPARED = {
    "EPL": dict(source="openligadb", competition_id="england:1-premierleague", league="pl", season_label="2026-27", season="2026"),
    "LALIGA": APPROVED["LALIGA"],
}
# Phase 4.11: football-data.org leagues are PREPARED offline (app/store/footballdata.py, tests/test_footballdata_sync.py). They are deliberately NOT in APPROVED: moving one into APPROVED
# and listing it in config/sync.json is the activation step, taken only after a supervised real read has been reviewed.
PREPARED_PROVIDERS = {
    "EPL": dict(source="footballdata", competition_id="england:1-premierleague", league="PL", season_label="2026-27", season="2026"),
    "SERIEA": dict(source="footballdata", competition_id="italy:1-seriea", league="SA", season_label="2026-27", season="2026"),
    "LIGUE1": dict(source="footballdata", competition_id="europe/france:fr1", league="FL1", season_label="2026-27", season="2026"),
}
PROVIDER_PAUSE_S = {"openligadb": 3.0, "footballdata": 7.0}          # pause between two leagues' requests to the same provider (football-data.org free tier: 10 requests a minute)
PROVIDER_NAMES = {"openligadb": "OpenLigaDB", "footballdata": "football-data.org"}
PROVIDER_ATTRIBUTION = {"openligadb": "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0", "footballdata": "Football data provided by the Football-Data.org API"}
READINESS = {
    "BUNDESLIGA": ("approved_live_disabled", "OpenLigaDB is approved; live access is switched off in config/sync.json."),
    "EPL": ("prepared_offline", "OpenLigaDB snapshots were reviewed and imported once (2026-10-25); no live source is approved. Its Premier League feed is lagging: the responses of 2026-10-25, 2026-10-27 (two) were byte-identical (provider's last update 2026-10-20) and held no result after 2026-10-12, so it is not approved for automatic retrieval (Phase 4.10). A football-data.org adapter is prepared offline; it needs an API token and your approval."),
    "LALIGA": ("approved_live_disabled", "OpenLigaDB is approved for La Liga; it is not listed in config/sync.json yet, so no live request is made for it."),
    "SERIEA": ("prepared_needs_token", "A football-data.org adapter is prepared and tested offline; it needs your account, an API token and your approval. Nothing is requested."),
    "LIGUE1": ("prepared_needs_token", "A football-data.org adapter is prepared and tested offline; it needs your account, an API token and your approval. Nothing is requested."),
}


def _adapters():
    if str(ADAPTER_DIR) not in sys.path:
        sys.path.insert(0, str(ADAPTER_DIR))
    from footiq_sources import common, identity, openligadb
    return common, identity, openligadb


CONTACT_FILE = ROOT / "config" / "contact.local"      # untracked (config/.gitignore); the contact is never printed or stored


def _adapter_config():
    """Adapter settings with the contact taken from FOOTIQ_CONTACT or the repo-root config/contact.local (not the adapters' own config folder)."""
    common, _, _ = _adapters()
    import os

    return common.AdapterConfig.load(contact_file=os.environ.get("FOOTIQ_CONTACT_FILE") or str(CONTACT_FILE))


@dataclass
class SyncConfig:
    live_enabled: bool = False
    startup_check: bool = True
    startup_delay_seconds: float = 5.0
    periodic_minutes: float = 60.0
    max_retries: int = 2                          # HTTP retries per request inside a check (0 = none); a whole cycle never makes more than MAX_REQUESTS_PER_CYCLE attempts, whatever this says
    stale_after_hours: float = 72.0
    refresh_mode: str = "full_season"             # routine check = ONE request for the whole league-season (sees older-matchday corrections, postponed and delayed results); "polling" = current+previous matchday only
    sources: dict = field(default_factory=lambda: {"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA"]}})
    sync_mode: str = "periodic"                   # "periodic": the six-hour scheduler (default, unchanged) | "startup": ONE refresh attempt per backend launch, no recurring scheduler
    startup_min_gap_minutes: float = 15.0         # startup mode: a league checked successfully more recently than this is not asked again (rapid restarts must not hammer the provider)

    def __post_init__(self):
        if self.sync_mode not in ("periodic", "startup"):
            raise ValueError(f"sync_mode must be 'periodic' or 'startup', not {self.sync_mode!r}")
        if self.refresh_mode not in ("full_season", "polling"):
            raise ValueError(f"refresh_mode must be 'full_season' or 'polling', not {self.refresh_mode!r}")

    def spec_for(self, key: str) -> dict:
        """The approved source spec of a competition, with the season taken from config when it differs: sources.<name>.season_overrides.<KEY> = {"season": "2027", "season_label": "2027-28"}.
        The adapter still refuses a league-season it has not validated; list it in sources.<name>.verified_seasons ([["bl1", "2027"]]) after a reconciliation run."""
        spec = dict(APPROVED[key])
        override = self.sources.get(spec["source"], {}).get("season_overrides", {}).get(key, {})
        spec.update({k: v for k, v in override.items() if k in ("season", "season_label", "league", "competition_id")})
        return spec

    def token_env(self, source: str = "footballdata") -> str:
        """Name of the environment variable that holds the provider's API token (the token itself is never in a file of the project)."""
        return self.sources.get(source, {}).get("token_env") or "FOOTBALL_DATA_API_TOKEN"

    def verified_seasons(self, source: str = "openligadb") -> list:
        return [tuple(x) for x in self.sources.get(source, {}).get("verified_seasons", [])]

    @staticmethod
    def load(path: Path = CONFIG_PATH) -> "SyncConfig":
        path = Path(os.environ.get("FOOTIQ_SYNC_CONFIG") or path)         # a private process (a trial launch, a test) can read another config file without touching config/sync.json
        raw = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}        # utf-8-sig: Notepad and PowerShell add a byte-order mark
        return SyncConfig(**{k: v for k, v in raw.items() if k in SyncConfig.__dataclass_fields__})

    def approved_competitions(self) -> list[str]:
        out = []
        for name, s in self.sources.items():
            if s.get("enabled"):
                out += [k for k in s.get("competitions", []) if APPROVED.get(k, {}).get("source") == name]
        return out


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------------------------------------------- ingestion
def build_resolver(conn: sqlite3.Connection):
    _, identity, _ = _adapters()
    return identity.IdentityResolver(set(conn.execute("SELECT competition_id, alias, entity_id FROM team_aliases").fetchall()))


def _row(conn, record_id) -> Optional[dict]:
    r = conn.execute("SELECT * FROM matches WHERE record_id=?", (record_id,)).fetchone()
    return {k: r[k] for k in baseline.MATCH_COLS} if r else None


def _outcome(h, a):
    return "H" if h > a else "A" if h < a else "D"


def _quarantine(conn, run_id, source, ref, reason, payload=None):
    if conn.execute("SELECT 1 FROM quarantine WHERE source=? AND source_ref=? AND reason=?", (source, ref, reason)).fetchone():
        return                                                          # the same finding is recorded once, however often a payload is replayed
    conn.execute("INSERT INTO quarantine(run_id, source, source_ref, reason, payload, created_utc) VALUES (?,?,?,?,?,?)", (run_id, source, ref, reason, json.dumps(payload, default=str) if payload else None, now_utc()))


def _link_source(conn, rec, record_id, role, snapshot_id, ts):
    """Record which source row and snapshot a stored match comes from. The table keeps ONE row per (source, source_ref), so history is kept inside that row:
      * no row yet                                   -> insert it (as before);
      * a 'confirmation' row of the same match, and this snapshot now SUPPLIES the result ('primary')
                                                     -> upgrade it to primary, point it at THIS snapshot, and append the old role/snapshot/time to `provenance`
                                                        (Phase 4.8D: before, the insert was ignored and the result kept pointing at the older snapshot);
      * anything else (same state again, a later confirmation, a row of another match) -> untouched, so a repeated import changes nothing and nothing is downgraded."""
    prov = f"{rec.source} matchID {rec.source_ref}"
    retrieved = rec.retrieved_utc or ts
    row = conn.execute("SELECT record_id, role, snapshot_id, retrieved_utc, provenance FROM match_sources WHERE source=? AND source_ref=?", (rec.source, rec.source_ref)).fetchone()
    if row is None:
        conn.execute("INSERT INTO match_sources(source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, source_revision, provenance) VALUES (?,?,?,?,?,?,?,?,?)",
                     (rec.source, rec.source_ref, record_id, role, snapshot_id, rec.licence, retrieved, rec.source_revision, prov))
    elif row["record_id"] == record_id and role == "primary" and row["role"] == "confirmation" and row["snapshot_id"] != snapshot_id:
        history = f"{row['provenance'] or prov} | upgraded to primary by snapshot {snapshot_id} (retrieved {retrieved}); was confirmation via snapshot {row['snapshot_id']} (retrieved {row['retrieved_utc']})"
        conn.execute("UPDATE match_sources SET role='primary', snapshot_id=?, retrieved_utc=?, source_revision=?, licence=?, provenance=? WHERE source=? AND source_ref=? AND record_id=?",
                     (snapshot_id, retrieved, rec.source_revision, rec.licence, history, rec.source, rec.source_ref, record_id))


def ingest_records(conn: sqlite3.Connection, records: list, competition_id: str, competition_key: str, season_label: str, run_id: int, snapshot_id: str, ts: Optional[str] = None, protect_dates: bool = False) -> dict:
    """Merge staging records of ONE competition-season into `matches`. Idempotent; conflicts go to quarantine and never overwrite.
    protect_dates: a stored fixture whose date differs from the source's is HELD untouched (no date, kickoff, matchday or result change) and the
    difference is quarantined as DATE_DIFFERENCE for a human decision."""
    ts = ts or now_utc()
    resolver = build_resolver(conn)
    tier, ctype = conn.execute("SELECT tier, competition_type FROM competitions WHERE competition_id=?", (competition_id,)).fetchone()
    stats = dict(inserted=0, updated=0, unchanged=0, confirmed=0, quarantined=0)
    by_pair: dict = {}
    for r in conn.execute("SELECT * FROM matches WHERE competition_id=? AND season=?", (competition_id, season_label)):
        by_pair.setdefault((r["home_entity_id"], r["away_entity_id"]), []).append({k: r[k] for k in baseline.MATCH_COLS})
    pending = []
    for rec in records:
        he, hm = resolver.resolve(rec.source, competition_id, rec.home_raw)
        ae, am = resolver.resolve(rec.source, competition_id, rec.away_raw)
        for alt in (rec.source_ids or {}).get("home_alts", ()) if not he else ():       # a provider's own short name for the same club; still an exact/normalised lookup, never fuzzy
            he, hm = resolver.resolve(rec.source, competition_id, alt)
            if he:
                break
        for alt in (rec.source_ids or {}).get("away_alts", ()) if not ae else ():
            ae, am = resolver.resolve(rec.source, competition_id, alt)
            if ae:
                break
        if not he or not ae:
            _quarantine(conn, run_id, rec.source, rec.source_ref, f"unresolved team identity ({hm}/{am}): {rec.home_raw} v {rec.away_raw}")
            stats["quarantined"] += 1
            continue
        cands = by_pair.get((he, ae), [])
        if len(cands) > 1:
            _quarantine(conn, run_id, rec.source, rec.source_ref, "ambiguous: several stored matches for this pairing", rec.to_dict())
            stats["quarantined"] += 1
            continue
        ex = cands[0] if cands else None
        if protect_dates and ex and ex["match_date"] and rec.match_date and ex["match_date"] != rec.match_date and rec.status != "completed_unclassified_score":
            held = " (a completed result is held back until the date is decided)" if rec.status == "completed" else ""
            _quarantine(conn, run_id, rec.source, rec.source_ref, f"DATE_DIFFERENCE: stored {ex['match_date']} vs source {rec.match_date}: {rec.home_raw} v {rec.away_raw}{held}", rec.to_dict())
            stats["quarantined"] += 1
            stats["held_date_difference"] = stats.get("held_date_difference", 0) + 1
            continue
        completed = rec.status == "completed" and rec.label_eligible_90min and rec.regulation_home is not None
        if rec.status == "completed_unclassified_score" and "multiple_after90_results" in (rec.flags or []):
            _quarantine(conn, run_id, rec.source, rec.source_ref, f"CONTRADICTORY SOURCE RESULT: the source holds several differing final scores ({rec.result_type}); {rec.home_raw} v {rec.away_raw} is not imported", rec.to_dict())
            stats["quarantined"] += 1
            continue
        if rec.status in ("completed", "completed_unclassified_score") and not completed:
            _quarantine(conn, run_id, rec.source, rec.source_ref, f"completed without an explicit 90-minute result ({rec.result_type})", rec.to_dict())
            stats["quarantined"] += 1
            continue
        if ex and ex["status"] in ("completed", "awarded") and ex["home_goals_90"] is not None:
            if completed and (int(ex["home_goals_90"]), int(ex["away_goals_90"])) != (rec.regulation_home, rec.regulation_away):
                _quarantine(conn, run_id, rec.source, rec.source_ref, f"CONFLICT: stored {ex['home_goals_90']}-{ex['away_goals_90']} vs source {rec.regulation_home}-{rec.regulation_away}", rec.to_dict())
                stats["quarantined"] += 1
            else:
                _link_source(conn, rec, ex["record_id"], "confirmation", snapshot_id, ts)
                stats["confirmed"] += 1
            continue
        new = dict(ex) if ex else dict(
            record_id=f"{rec.source}:{rec.source_ref}", kind="club", competition_id=competition_id, competition_key=competition_key, season=season_label,
            stage=None, matchday_label=None, matchday_no=None, match_date=None, kickoff_local=None, kickoff_utc=None, time_precision=None, home_entity_id=he, away_entity_id=ae,
            model_home_entity=he, model_away_entity=ae, home_name=rec.home_raw, away_name=rec.away_raw, status="scheduled", home_goals_final=None, away_goals_final=None,
            home_goals_90=None, away_goals_90=None, label_90_status=None, outcome=None, shootout_winner=None, neutral=None, rated=None, regular=None, in_universe=0, tier=tier,
            competition_type=ctype, source_system=rec.source, licence=rec.licence, src_order=None)
        if rec.round:
            new["matchday_label"] = new["stage"] = f"Matchday {rec.round}"
            new["matchday_no"] = int(rec.round)
        if rec.match_date:
            new["match_date"] = rec.match_date
        if rec.kickoff_utc:
            new["kickoff_utc"], new["time_precision"] = rec.kickoff_utc, rec.time_precision
        if completed:
            new.update(status="completed", home_goals_final=rec.regulation_home, away_goals_final=rec.regulation_away, home_goals_90=rec.regulation_home, away_goals_90=rec.regulation_away,
                       label_90_status="confirmed", outcome=_outcome(rec.regulation_home, rec.regulation_away), rated=1, regular=1, in_universe=1, model_home_entity=he, model_away_entity=ae,
                       source_system=rec.source, licence=rec.licence)
        elif rec.status == "past_date_no_result" and new["status"] == "scheduled":
            new["status"] = "awaiting_result"
        pending.append((rec, new, ex is None or bool(completed)))   # True when this source supplies the stored result (or the row itself)
    # write inside one transaction
    res = baseline.upsert_matches(conn, [p[1] for p in pending], ts)
    for k in ("inserted", "updated", "unchanged"):
        stats[k] += res[k]
    for rec, new, supplies in pending:
        _link_source(conn, rec, new["record_id"], "primary" if supplies else "confirmation", snapshot_id, ts)
    return stats


def replay_payload(conn: sqlite3.Connection, payload: bytes, competition_key: str = "BUNDESLIGA", retrieved_utc: Optional[str] = None, snapshot_name: str = "offline-replay", now: Optional[datetime] = None, kind: str = "offline_replay",
                   spec: Optional[dict] = None, snapshot_id: Optional[str] = None, url: Optional[str] = None, path: Optional[str] = None, protect_dates: bool = False) -> dict:
    """Ingest a saved OpenLigaDB payload (no network). Used by tests and for rebuilding from stored snapshots.
    `spec` replaces the APPROVED entry (offline rehearsals of competitions that are not yet approved for live sync)."""
    _, _, ol = _adapters()
    spec = spec or APPROVED[competition_key]
    ts = retrieved_utc or now_utc()
    sha = hashlib.sha256(payload).hexdigest()
    sid = snapshot_id or f"{snapshot_name}-{sha[:12]}"
    conn.execute("INSERT OR IGNORE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (sid, "openligadb", "json", url, path, sha, len(payload), ts, None, ol.LICENCE, ol.ATTRIBUTION))
    run_id = conn.execute("INSERT INTO sync_runs(kind, source, competition_key, started_utc, outcome) VALUES (?,?,?,?, 'running')", (kind, "openligadb", competition_key, now_utc())).lastrowid
    recs = ol.parse_payload(payload, ts, sid, now or datetime.now(timezone.utc), spec["competition_id"])
    stats = ingest_records(conn, recs, spec["competition_id"], competition_key, spec["season_label"], run_id, sid, ts, protect_dates=protect_dates)
    latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (competition_key,)).fetchone()[0]
    conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                 (now_utc(), stats["inserted"], stats["updated"], stats["unchanged"], stats["quarantined"], latest, json.dumps(dict(stats, records=len(recs), snapshot=sid)), run_id))
    conn.commit()
    return dict(stats, records=len(recs), run_id=run_id, snapshot_id=sid)


# ---------------------------------------------------------------------------------------------------------------- freshness status
def _freshness_facts(runs: list, key: str) -> dict:
    """What actually happened for one competition, from its `sync_runs` rows (oldest first, baseline import excluded). Offline imports (kind 'offline_*') are imports, never
    external checks: an external check is a live provider call, i.e. a run of kind 'sync' that finished 'ok' having made at least one request."""
    mine = [r for r in runs if r["competition_key"] == key]
    live = [r for r in mine if r["kind"] == "sync"]
    ext = [r for r in live if r["outcome"] == "ok" and (r["requests"] or 0) > 0]
    imp = [r for r in mine if r["outcome"] == "ok" and (r["inserted"] or 0) + (r["updated"] or 0) > 0]
    ok_runs = [r for r in mine if r["outcome"] == "ok"]
    return dict(last_successful_external_check_utc=ext[-1]["finished_utc"] if ext else None,
                last_external_check_new_records=(ext[-1]["inserted"] + ext[-1]["updated"]) if ext else None,
                last_successful_import_utc=imp[-1]["finished_utc"] if imp else None, last_import_kind=imp[-1]["kind"] if imp else None,
                last_import_records=(imp[-1]["inserted"] + imp[-1]["updated"]) if imp else None,
                last_attempted_sync_utc=max((r["started_utc"] for r in live), default=None), last_attempt_outcome=live[-1]["outcome"] if live else None,
                imported_records=sum((r["inserted"] or 0) + (r["updated"] or 0) for r in ok_runs), quarantined_records=sum(r["quarantined"] or 0 for r in ok_runs))


QUARANTINE_PROCEDURE = "docs/mini-project/phase4/QUARANTINE_REVIEW_PROCEDURE.md"


def _scheduler_view(conn: sqlite3.Connection, cfg: SyncConfig, now: datetime) -> dict:
    """What the scheduler is doing, from `sync_runs` only: off, running, idle, overdue or backing off, with the next check and the number of failed cycles in a row."""
    kinds = ",".join("?" * len(CHECK_KINDS))
    period = max(MIN_PERIOD_MINUTES, float(cfg.periodic_minutes)) * 60
    leagues = {k: league_schedule(conn, k, period, now) for k in cfg.approved_competitions()}
    if leagues:                                                         # one scheduler, one cycle, but each league keeps its own due time and failure count
        st = dict(next_due=min(v["next_due"] for v in leagues.values()), consecutive_failed_cycles=max(v["consecutive_failed_cycles"] for v in leagues.values()),
                  last_attempt_utc=max((v["last_attempt_utc"] for v in leagues.values() if v["last_attempt_utc"]), default=None), last_outcome=None)
        st["last_outcome"] = next((v["last_outcome"] for v in leagues.values() if v["last_attempt_utc"] == st["last_attempt_utc"]), None)
    else:
        rows = [dict(r) for r in conn.execute(f"SELECT started_utc, outcome FROM sync_runs WHERE kind IN ({kinds}) AND outcome NOT IN ('running','abandoned','skipped_already_running','skipped_live_disabled') ORDER BY run_id DESC LIMIT 50", CHECK_KINDS)]
        st = schedule_state(rows, period, now)
    cutoff = (now - timedelta(minutes=RUN_LOCK_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
    running = conn.execute(f"SELECT 1 FROM sync_runs WHERE outcome='running' AND kind IN ({kinds}) AND started_utc>?", (*CHECK_KINDS, cutoff)).fetchone() is not None
    due = st["next_due"]
    if not cfg.live_enabled:
        label, due_s = "off: live synchronisation is disabled, cached data only", None
    else:
        due_s = due.strftime("%Y-%m-%dT%H:%M:%SZ")
        if running:
            label = "running a check now"
        elif st["consecutive_failed_cycles"]:
            label = f"backing off after {st['consecutive_failed_cycles']} failed cycle(s); next check {due_s}"
        elif now > due:
            label = f"check overdue (was due {due_s})"
        else:
            label = f"idle; next check {due_s}"
    per_league = {k: dict(next_check_utc=(v["next_due"].strftime("%Y-%m-%dT%H:%M:%SZ") if cfg.live_enabled else None), consecutive_failed_cycles=v["consecutive_failed_cycles"], last_attempt_utc=v["last_attempt_utc"], last_outcome=v["last_outcome"]) for k, v in leagues.items()}
    if cfg.sync_mode == "startup":                                       # no recurring schedule: nothing is "due"; say when the last launch refresh ran and what went wrong
        per_league = {k: dict(next_check_utc=None, consecutive_failed_cycles=v["consecutive_failed_cycles"], last_attempt_utc=v["last_attempt_utc"], last_outcome=v["last_outcome"], last_error=_league_last_error(conn, k)) for k, v in leagues.items()}
        due_s = None
        if cfg.live_enabled:
            label = "startup refresh only (no recurring schedule); " + (f"last attempt {st['last_attempt_utc']}: {st['last_outcome']}" if st["last_attempt_utc"] else "no attempt recorded yet")
    return dict(mode=cfg.sync_mode, live_enabled=cfg.live_enabled, status=label, interval_minutes=cfg.periodic_minutes, next_scheduled_check_utc=due_s, consecutive_failed_cycles=st["consecutive_failed_cycles"], leagues=per_league,
                last_attempt_utc=st["last_attempt_utc"], last_cycle_outcome=st["last_outcome"], max_requests_per_cycle=MAX_REQUESTS_PER_CYCLE, max_retries=min(cfg.max_retries, MAX_REQUESTS_PER_CYCLE - 1))


def _quarantine_view(conn: sqlite3.Connection) -> dict:
    """Unresolved quarantine findings. Rows written by the baseline import are data-quality notes of the original files; every other row is a SYNC finding that needs a human decision."""
    rows = conn.execute("SELECT CASE WHEN q.reason LIKE 'DATE_DIFFERENCE%' THEN 'date_disagreement' WHEN q.reason LIKE 'CONFLICT%' THEN 'score_conflict' WHEN q.reason LIKE 'CONTRADICTORY%' THEN 'contradictory_record' "
                        "WHEN q.reason LIKE 'unresolved team%' THEN 'unresolved_team' ELSE 'other' END AS kind, COALESCE(r.kind, '') = 'baseline_import' AS baseline, COUNT(*) AS n "
                        "FROM quarantine q LEFT JOIN sync_runs r ON r.run_id = q.run_id GROUP BY 1, 2").fetchall()
    by_kind, baseline_n = {}, 0
    for r in rows:
        if r["baseline"]:
            baseline_n += r["n"]
        else:
            by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + r["n"]
    review = sum(by_kind.values())
    warning = None
    if review:
        parts = ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in sorted(by_kind.items()))
        warning = (f"{review} unresolved sync finding(s) need a human decision ({parts}). Nothing is applied automatically; the stored values stay in place. "
                   f"Review procedure: {QUARANTINE_PROCEDURE}")
    return dict(open_total=review + baseline_n, needs_operator_review=review, baseline_data_quality_notes=baseline_n, by_kind=by_kind, warning=warning, procedure=QUARANTINE_PROCEDURE)


def status(conn: sqlite3.Connection, cfg: SyncConfig, now: Optional[datetime] = None) -> dict:
    """Per-competition freshness, with the facts kept apart (Phase 4.8C):
      latest_result                      newest verified result date stored (from `matches`)
      last_successful_external_check_utc last live provider call that succeeded (offline imports and the baseline never count)
      last_successful_import_utc         last run that stored new or changed verified records, from any source (live or offline)
      last_attempted_sync_utc            last live attempt, successful or not
      provider_readiness / provider_note what may be done for this league
      imported_records / quarantined_records  totals over all non-baseline runs
    `state` is 'fresh' only when an approved source was successfully checked within `stale_after_hours`, the latest attempt did not fail and no played fixture lacks a result.
    A successful check that found nothing new proves the source had nothing newer, not that the stored history is complete: `history_note` says so whenever fixtures are missing results."""
    from store import views

    now = now or datetime.now(timezone.utc)
    approved = set(cfg.approved_competitions())
    last_checks = [dict(r) for r in conn.execute("SELECT run_id, kind, source, started_utc, finished_utc, outcome, requests, detail FROM sync_runs WHERE kind IN ('startup_check','periodic_check','manual_check') ORDER BY run_id DESC LIMIT 5")]
    runs = conn.execute("SELECT run_id, kind, competition_key, started_utc, finished_utc, outcome, requests, inserted, updated, quarantined FROM sync_runs "
                        "WHERE kind<>'baseline_import' AND competition_key IS NOT NULL ORDER BY run_id").fetchall()
    comps = []
    for f in views.freshness(conn):
        key = f["competition_key"]
        facts = _freshness_facts(runs, key)
        ok = facts["last_successful_external_check_utc"]
        src = [APPROVED[key]["source"]] if key in approved else []
        reasons = []
        if not src:
            state, reasons = "stale", ["no approved fresh source for this competition"]
            if facts["last_successful_import_utc"]:
                reasons.append(f"results were last imported from a saved snapshot ({facts['last_import_kind']}) on {facts['last_successful_import_utc']}; that was not a check of a live source")
        elif not ok:
            state, reasons = "stale", ["no successful external source check yet" + (" (live access is disabled)" if not cfg.live_enabled else "")]
            if facts["last_successful_import_utc"]:
                reasons.append(f"results were last imported on {facts['last_successful_import_utc']} ({facts['last_import_kind']}); an import is not an external check")
        else:
            age_h = (now - datetime.strptime(ok, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds() / 3600
            if age_h > cfg.stale_after_hours:
                state, reasons = "stale", [f"last successful external check {age_h:.0f} h ago"]
            elif facts["last_attempt_outcome"] not in (None, "ok", "running"):
                state, reasons = "stale", [f"latest sync attempt: {facts['last_attempt_outcome']}"]
            else:
                state = "fresh"
        note = None
        if f["awaiting_result"]:
            reasons.append(f"{f['awaiting_result']} played match(es) without a result since {f['oldest_awaiting']}")
            state = "stale"
            note = "A successful source check does not make the history complete: the fixtures above are past their date and have no verified result in the store."
        provider = READINESS.get(key)
        if provider and key in approved and cfg.live_enabled:
            provider = ("approved_live_enabled", f"{PROVIDER_NAMES[APPROVED[key]['source']]} is approved and live checking is ON: one full-season request about every {cfg.periodic_minutes:g} minutes.")
        if ok:                                                                  # say plainly what a successful check did and did not find
            new_n = facts["last_external_check_new_records"] or 0
            summary = f"Source checked successfully at {ok}: " + (f"{new_n} new or changed record(s) stored." if new_n else "reachable, and it returned no new results (the stored history is unchanged).")
        else:
            summary = "No successful source check yet." + (" Live checking is off." if not cfg.live_enabled else "")
        feed_lag = None
        if f["awaiting_result"] and f["oldest_awaiting"]:                          # judged by the newest VERIFIED MATCH DATE and the fixtures still missing results, never by when we last asked the provider
            behind = (now.date() - datetime.strptime(f["latest_result"], "%Y-%m-%d").date()).days if f["latest_result"] else None
            overdue = (now.date() - datetime.strptime(f["oldest_awaiting"], "%Y-%m-%d").date()).days
            if overdue >= 3:
                feed_lag = dict(lagging=True, latest_verified_result_date=f["latest_result"], days_since_latest_verified_result=behind, fixtures_past_date_without_result=f["awaiting_result"], oldest_fixture_without_result=f["oldest_awaiting"],
                                message=f"Results lagging: newest verified result {f['latest_result']}" + (f" ({behind} days ago)" if behind is not None else "") + f"; {f['awaiting_result']} fixture(s) past their date have no verified result (oldest {f['oldest_awaiting']}).")
        comps.append(dict(f, feed_lag=feed_lag, last_check_summary=summary, last_check_found_new_results=bool(ok) and bool(facts["last_external_check_new_records"]), approved_sources=src, last_successful_sync_utc=ok, state=state, state_reasons=reasons, provider_readiness=provider[0] if provider else None,
                          provider_note=provider[1] if provider else None, latest_verified_result_date=f["latest_result"], history_note=note, **facts))
    return dict(generated_utc=now_utc(), live_enabled=cfg.live_enabled, sync_mode=cfg.sync_mode, startup_min_gap_minutes=cfg.startup_min_gap_minutes, periodic_minutes=cfg.periodic_minutes, approved_sources=sorted({APPROVED[k]["source"] for k in approved}),
                recent_checks=last_checks, competitions=comps, scheduler=_scheduler_view(conn, cfg, now), quarantine=_quarantine_view(conn),
                attribution=[dict(source=PROVIDER_NAMES[src], text=PROVIDER_ATTRIBUTION[src], used_for=sorted(k for k in approved if APPROVED[k]["source"] == src)) for src in sorted({APPROVED[k]["source"] for k in approved})] or
                [dict(source="OpenLigaDB", text=PROVIDER_ATTRIBUTION["openligadb"], used_for=[])],
                note="Data is historical or periodically synchronised; nothing here is a live score feed.")


# ---------------------------------------------------------------------------------------------------------------- request cap, payload check, snapshot reuse (Phase 4.8D final safeguards)
MAX_REQUESTS_PER_CYCLE = 3          # hard cap on HTTP attempts (first try + retries) in one scheduled cycle


class RequestCapReached(RuntimeError):
    """Raised by the capped opener; the HTTP client does not retry it, so the cycle ends as an error."""


def _urllib_opener(url, headers):
    import urllib.request

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:                   # HTTPError / URLError propagate exactly as the client's built-in branch would see them
        return r.status, r.read(), dict(r.headers)


def validate_season_payload(body: bytes, league: str) -> list:
    """A full-season answer must be a non-empty JSON list of this league's matches, with unique ids and matchdays 1..N of equal size. Anything else is malformed or contradictory:
    it is rejected BEFORE it is saved or ingested, and it is not retried."""
    try:
        data = json.loads(body)
    except ValueError as exc:
        raise ValueError(f"malformed response: not JSON ({exc})") from exc
    if not isinstance(data, list) or not data:
        raise ValueError("malformed response: not a non-empty list of matches")
    if any(not isinstance(m, dict) or m.get("leagueShortcut") != league for m in data):
        raise ValueError(f"contradictory response: a match does not belong to league {league}")
    if len({m.get("matchID") for m in data}) != len(data):
        raise ValueError("contradictory response: duplicate match ids")
    sizes: dict = {}
    for m in data:
        g = (m.get("group") or {}).get("groupOrderID")
        if not isinstance(g, int):
            raise ValueError("malformed response: a match has no matchday")
        sizes[g] = sizes.get(g, 0) + 1
    if sorted(sizes) != list(range(1, len(sizes) + 1)) or len(set(sizes.values())) != 1:
        raise ValueError("contradictory response: matchdays are not 1..N with equal numbers of matches")
    return data


def latest_authentic_snapshot(folder: Path, league: str, season: str, origin: str) -> Optional[dict]:
    """The newest full-season snapshot of this league-season that (a) carries origin == `origin` in its metadata and (b) still hashes to the sha256 its metadata records.
    Snapshots without an origin (older ones, and the test/replay artifacts such as the tampered trial payload) are never candidates, so they can never be reused as provider data."""
    found = sorted((f for f in folder.glob(f"*_{league}_{season}_season*.json") if not f.name.endswith(".meta.json")), reverse=True)
    for path in found[:1]:                                              # only the LATEST one: a response equal to an older snapshot is a change and is stored again
        meta_path = Path(str(path) + ".meta.json")
        if not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("origin") != origin or hashlib.sha256(path.read_bytes()).hexdigest() != meta.get("sha256"):
            return None
        return meta
    return None


class SchedulerLock:
    """One scheduler per machine. An OS-level exclusive lock on a byte of a small file: a second FootIQ process (a preview server, a second API, a script) cannot take it, so it never starts a
    second scheduler. The operating system releases it when the holder exits or crashes, so a crash can never leave a stale lock behind."""

    def __init__(self, path):
        self.path, self._fh = Path(path), None

    def acquire(self) -> bool:
        if self._fh:
            return True
        key = str(self.path.resolve())
        with _HELD_LOCK:
            if key in _HELD_IN_PROCESS:                                  # byte-range locks do not conflict between two handles of the same process: refuse a second manager here too
                return False
            _HELD_IN_PROCESS.add(key)
        if not self._acquire_os():
            with _HELD_LOCK:
                _HELD_IN_PROCESS.discard(key)
            return False
        return True

    def _acquire_os(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+b")
        try:
            fh.seek(_LOCK_OFFSET)                                          # lock a byte far beyond the text, so the "who holds it" line stays readable while locked
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        self._fh = fh
        fh.seek(0)
        fh.truncate()
        fh.write(("pid=%d since=%s\n" % (os.getpid(), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))).encode())
        fh.flush()
        return True

    def release(self) -> None:
        if not self._fh:
            return
        try:
            self._fh.seek(_LOCK_OFFSET)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self._fh.close()
            self._fh = None
            with _HELD_LOCK:
                _HELD_IN_PROCESS.discard(str(self.path.resolve()))


_LOCK_OFFSET = 1 << 20
_HELD_IN_PROCESS: set = set()
_HELD_LOCK = threading.Lock()
SCHEDULER_LOCK_PATH = ROOT / "data" / "run" / "scheduler.lock"


def active_scheduler_threads() -> int:
    """How many scheduler threads are alive in THIS process (the application must have exactly one when sync is on, none when it is off)."""
    return sum(1 for t in threading.enumerate() if t.name == "footiq-sync" and t.is_alive())


def schedule_state(rows: list, period_seconds: float, now: datetime) -> dict:
    """From the newest-first list of real check attempts [{started_utc, outcome}]: when the next check is due, how many cycles in a row failed, and the last outcome."""
    if not rows:
        return dict(next_due=now, consecutive_failed_cycles=0, last_attempt_utc=None, last_outcome=None)
    failures = 0
    for r in rows:
        if r["outcome"] == "ok":
            break
        failures += 1
    factor = min(2 ** failures, MAX_BACKOFF_FACTOR) if failures else 1
    return dict(next_due=_parse_utc(rows[0]["started_utc"]) + timedelta(seconds=period_seconds * factor), consecutive_failed_cycles=failures, last_attempt_utc=rows[0]["started_utc"], last_outcome=rows[0]["outcome"])


def _league_last_error(conn: sqlite3.Connection, key: str) -> Optional[dict]:
    """The error of a league's newest failed check, if its newest check failed (a later success clears it). From the per-league outcomes the check cycles record."""
    for r in conn.execute(f"SELECT started_utc, outcome, detail FROM sync_runs WHERE kind IN ({','.join('?' * len(CHECK_KINDS))}) AND outcome IN ('ok','error') ORDER BY run_id DESC LIMIT 200", CHECK_KINDS):
        try:
            entries = json.loads(r["detail"]) if r["detail"] else None
        except ValueError:
            entries = None
        for e in (entries if isinstance(entries, list) else []):
            if isinstance(e, dict) and e.get("competition") == key:
                return dict(at_utc=r["started_utc"], error=e["error"]) if "error" in e else None
    return None


def describe_startup(state: dict, gap_minutes: float = 15.0) -> str:
    """One plain sentence about what the startup refresh of THIS backend launch did."""
    s = state.get("state")
    if s == "disabled":
        return f"startup refresh is off: {state.get('reason', 'live synchronisation is disabled')}"
    if s == "pending":
        return "startup refresh pending: it starts a few seconds after launch and never blocks the application"
    if s == "running":
        return "startup refresh running now"
    if s == "skipped_recent":
        return f"startup refresh skipped: every league was refreshed less than {gap_minutes:g} minutes ago"
    if s == "skipped_other_process":
        return "startup refresh not done here: another FootIQ process is refreshing"
    if s == "done":
        return f"startup refresh finished at {state.get('finished_utc')}: " + (f"errors in {', '.join(state.get('failed_leagues', []))}" if state.get("failed_leagues") else "all leagues ok")
    if s == "failed":
        return f"startup refresh failed: {state.get('error', 'unknown error')}"
    return "startup refresh not started in this process"


def league_schedule(conn: sqlite3.Connection, key: str, period_seconds: float, now: datetime) -> dict:
    """Schedule of ONE league from its own attempts, read from the per-league outcomes each check cycle records in its `detail`: a failing league backs off alone, a healthy one keeps its
    six-hour rhythm. A cycle row with no readable detail (older than Phase 4.9) counts for BUNDESLIGA, the only league that was ever scheduled then."""
    rows = []
    for r in conn.execute(f"SELECT started_utc, outcome, detail FROM sync_runs WHERE kind IN ({','.join('?' * len(CHECK_KINDS))}) AND outcome IN ('ok','error') ORDER BY run_id DESC LIMIT 200", CHECK_KINDS):
        try:
            entries = json.loads(r["detail"]) if r["detail"] else None
        except ValueError:
            entries = None
        if not isinstance(entries, list):
            if key == "BUNDESLIGA":
                rows.append(dict(started_utc=r["started_utc"], outcome=r["outcome"]))
            continue
        mine = [e for e in entries if isinstance(e, dict) and e.get("competition") == key]
        if mine:
            rows.append(dict(started_utc=r["started_utc"], outcome="error" if "error" in mine[0] else "ok"))
    return schedule_state(rows, period_seconds, now)


# ---------------------------------------------------------------------------------------------------------------- background manager
MIN_PERIOD_MINUTES = 30.0          # a misconfigured interval can never hammer a provider
RUN_LOCK_MINUTES = 30.0            # a 'running' row younger than this blocks a second run (another process or thread); older ones are treated as abandoned
MAX_BACKOFF_FACTOR = 4             # consecutive failed checks stretch the interval up to this multiple (6 h -> at most 24 h)
CHECK_KINDS = ("startup_check", "periodic_check", "manual_check")


def _parse_utc(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _scrub(cfg: "SyncConfig", text: str) -> str:
    """Remove API tokens (the values of the configured environment variables) from any text before it is stored or shown."""
    from store import footballdata as fd

    return fd.redact(text, (cfg.token_env("footballdata"), fd.DEFAULT_TOKEN_ENV))


class SyncManager:
    """Start-up check (non-blocking) plus a low-frequency periodic check. `opener` lets tests serve payloads without a network.

    With `live_enabled` false the manager is inert: no thread, no database connection, no `sync_runs` row (Phase 4.8B). With it true,
    `tick()` runs a check only when one is due (last attempt + interval, stretched after consecutive failures), so a restart never causes an extra request.
    `clock` lets tests move time without sleeping."""

    def __init__(self, db_path=None, cfg: Optional[SyncConfig] = None, opener: Optional[Callable] = None, on_change: Optional[Callable] = None, sleep: Callable = time.sleep,
                 clock: Optional[Callable[[], datetime]] = None, request_guard: Optional[Callable] = None, lock_path=None):
        self.db_path = db_path or db.DEFAULT_PATH
        self.cfg = cfg or SyncConfig.load()
        self.opener, self.on_change, self._sleep = opener, on_change, sleep
        self.lock_path = Path(os.environ.get('FOOTIQ_SCHEDULER_LOCK') or lock_path or SCHEDULER_LOCK_PATH)
        self._sched_lock = SchedulerLock(self.lock_path)
        self.startup_state: dict = dict(state="not_started")   # startup mode: what THIS launch's refresh did (in memory only: it resets with every launch)
        self.lock_state = 'not_applicable'              # 'held' (this process schedules), 'held_by_another_process' (it does not), 'not_applicable' (sync off or disabled)
        self.request_guard = request_guard             # supervised runs: wraps the REAL opener (exact URL, hard cap) without changing the recorded origin of the bytes ('provider_http')
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ---- schedule (pure of side effects: reads only)
    def period_seconds(self) -> float:
        return max(MIN_PERIOD_MINUTES, float(self.cfg.periodic_minutes)) * 60

    def next_due(self) -> Optional[datetime]:
        """When the next check is due; None when live access is off. A store that was never checked is due now."""
        if not self.cfg.live_enabled or self.cfg.sync_mode == "startup":
            return None                                                  # startup mode has no schedule: nothing is ever "due" in the background
        if not db.exists(self.db_path):
            return self.clock()
        due = self.league_due()
        return min(due.values()) if due else None

    def league_due(self) -> dict:
        """{competition_key: next due datetime} for every enabled league, each from its own attempts."""
        keys = self.cfg.approved_competitions()
        now = self.clock()
        if not keys or not db.exists(self.db_path):
            return {k: now for k in keys}
        conn = db.connect(self.db_path, readonly=True)
        try:
            return {k: league_schedule(conn, k, self.period_seconds(), now)["next_due"] for k in keys}
        finally:
            conn.close()

    def tick(self, kind: str = "periodic_check") -> dict:
        """Run a check if one is due. Never writes when live access is off or nothing is due."""
        if not self.cfg.live_enabled:
            return dict(outcome="skipped_live_disabled", run_id=None)
        if self.cfg.sync_mode == "startup":
            return dict(outcome="not_scheduled_startup_mode")
        dues = self.league_due()
        now = self.clock()
        ready = [k for k, d in dues.items() if now >= d]
        if dues and not ready:
            return dict(outcome="not_due", next_due=min(dues.values()).strftime("%Y-%m-%dT%H:%M:%SZ"))
        return self.check_once(kind, only=ready or None)

    # ---- thread
    def start(self) -> None:
        startup = self.cfg.sync_mode == "startup"
        if self._thread or not db.exists(self.db_path):
            return
        if not self.cfg.live_enabled:
            if startup:
                self.startup_state = dict(state="disabled", reason="live synchronisation is off in config/sync.json")
            return                                                       # inert: nothing to schedule, so no thread, no connection, no write
        if os.environ.get("FOOTIQ_DISABLE_SYNC") == "1":                  # test runs and throw-away backends: never schedule, whatever the config says
            if startup:
                self.startup_state = dict(state="disabled", reason="FOOTIQ_DISABLE_SYNC=1")
            return
        if not self._sched_lock.acquire():                               # another FootIQ process already refreshes/schedules: this one must not start a second
            self.lock_state = "held_by_another_process"
            if startup:
                self.startup_state = dict(state="skipped_other_process")
            return
        self.lock_state = "held"
        if startup:
            self.startup_state = dict(state="pending")
        self._thread = threading.Thread(target=self._startup_once if startup else self._loop, name="footiq-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        t = self._thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(5)
        self._sched_lock.release()
        if self.lock_state == 'held':
            self.lock_state = 'not_applicable'

    def _loop(self) -> None:
        try:
            kind = "startup_check"
            if self.cfg.startup_check and self._stop.wait(self.cfg.startup_delay_seconds):
                return
            while not self._stop.is_set():
                if kind != "startup_check" or self.cfg.startup_check:
                    self.tick(kind)
                kind = "periodic_check"
                due = self.next_due()
                delay = max(60.0, (due - self.clock()).total_seconds()) if due else self.period_seconds()
                if self._stop.wait(min(delay, self.period_seconds())):
                    return
        except Exception as exc:  # noqa: BLE001  (the sync thread must never take the app down)
            print("sync loop stopped:", exc)

    def _startup_targets(self) -> tuple:
        """(leagues to ask, leagues skipped because they were checked successfully less than startup_min_gap_minutes ago). Failed or never-checked leagues are always asked."""
        gap = timedelta(minutes=float(self.cfg.startup_min_gap_minutes))
        now = self.clock()
        conn = db.connect(self.db_path, readonly=True)
        try:
            ask, skip = [], {}
            for key in self.cfg.approved_competitions():
                row = conn.execute("SELECT MAX(started_utc) FROM sync_runs WHERE kind='sync' AND competition_key=? AND outcome='ok' AND requests>0", (key,)).fetchone()[0]
                if row and now - _parse_utc(row) < gap:
                    skip[key] = row
                else:
                    ask.append(key)
            return ask, skip
        finally:
            conn.close()

    def _startup_once(self) -> None:
        """Startup mode: ONE refresh attempt for this backend launch, in this background thread (the application is already serving). Then the thread ends and the scheduler lock is released.
        Leagues are attempted independently by check_once; a failure is recorded and shown, and the stored data stays as it is."""
        try:
            if self._stop.wait(self.cfg.startup_delay_seconds):
                return
            ask, skip = self._startup_targets()
            if not ask:
                self.startup_state = dict(state="skipped_recent", skipped=skip)
                return
            self.startup_state = dict(state="running", started_utc=now_utc(), leagues=ask, skipped=skip)
            res = self.check_once("startup_check", only=ask)
            failed = [d["competition"] for d in res.get("details", []) if "error" in d]
            self.startup_state = dict(state="done", started_utc=self.startup_state["started_utc"], finished_utc=now_utc(), outcome=res["outcome"], leagues=ask, skipped=skip, failed_leagues=failed,
                                      errors={d["competition"]: d["error"] for d in res.get("details", []) if "error" in d}, changed=res.get("changed", 0))
        except Exception as exc:  # noqa: BLE001  (a failed refresh must never take the application down)
            self.startup_state = dict(state="failed", error=_scrub(self.cfg, f"{type(exc).__name__}: {exc}")[:300], finished_utc=now_utc())
        finally:
            self._sched_lock.release()                                   # the refresh is over: nothing keeps running in the background
            if self.lock_state == "held":
                self.lock_state = "released_after_startup_refresh"

    def check_once(self, kind: str = "manual_check", only: Optional[list] = None) -> dict:
        """One cycle over the enabled leagues (or just `only`). Each league is attempted on its own: an error in one is recorded against that league and never stops the next."""
        if not self.cfg.live_enabled:                                    # no connection is opened: a disabled sync leaves the database byte-for-byte alone
            return dict(outcome="skipped_live_disabled", run_id=None)
        if not self._lock.acquire(blocking=False):
            return dict(outcome="skipped_already_running")
        conn = db.connect(self.db_path)
        try:
            run_id = self._begin_run(conn, kind)
            if run_id is None:
                return dict(outcome="skipped_already_running")
            changed, requests, outcomes = 0, 0, []
            for key in [k for k in self.cfg.approved_competitions() if only is None or k in only]:
                src = self.cfg.spec_for(key)["source"]
                if any(o.get("requests") for o in outcomes):
                    self._sleep(PROVIDER_PAUSE_S.get(src, 3.0))           # a pause between two leagues' requests to the same provider
                try:
                    res = self._sync_footballdata(conn, key) if src == "footballdata" else self._sync_openligadb(conn, key)
                    changed += res["inserted"] + res["updated"]
                    requests += res["requests"]
                    outcomes.append(dict(competition=key, **res))
                except Exception as exc:  # noqa: BLE001
                    msg = type(exc).__name__ + ": " + _scrub(self.cfg, _adapter_config().redact(str(exc)))[:300]
                    conn.execute("INSERT INTO sync_errors(run_id, source, at_utc, error) VALUES (?,?,?,?)", (run_id, "openligadb", now_utc(), msg))
                    conn.execute("INSERT INTO sync_runs(kind, source, competition_key, started_utc, finished_utc, outcome, detail) VALUES ('sync','openligadb',?,?,?, 'error', ?)", (key, now_utc(), now_utc(), msg))
                    outcomes.append(dict(competition=key, error=msg))
            ok = all("error" not in o for o in outcomes)
            conn.execute("UPDATE sync_runs SET finished_utc=?, outcome=?, requests=?, inserted=?, detail=? WHERE run_id=?", (now_utc(), "ok" if ok else "error", requests, changed, json.dumps(outcomes, default=str), run_id))
            conn.commit()
            if changed and self.on_change:
                self.on_change()
            return dict(outcome="ok" if ok else "error", run_id=run_id, changed=changed, details=outcomes)
        finally:
            conn.close()
            self._lock.release()

    def _begin_run(self, conn: sqlite3.Connection, kind: str) -> Optional[int]:
        """Claim the run lock and open the run row in one write transaction. A 'running' row younger than RUN_LOCK_MINUTES (another process) refuses the run."""
        cutoff = (self.clock() - timedelta(minutes=RUN_LOCK_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("BEGIN IMMEDIATE")
        try:
            marks = ",".join("?" * len(CHECK_KINDS))
            if conn.execute(f"SELECT 1 FROM sync_runs WHERE outcome='running' AND kind IN ({marks}) AND started_utc>?", (*CHECK_KINDS, cutoff)).fetchone():
                conn.rollback()
                return None
            conn.execute(f"UPDATE sync_runs SET outcome='abandoned', finished_utc=? WHERE outcome='running' AND kind IN ({marks}) AND started_utc<=?", (now_utc(), *CHECK_KINDS, cutoff))
            run_id = conn.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES (?,?,?, 'running')", (kind, "all approved", now_utc())).lastrowid
            conn.commit()
            return run_id
        except Exception:
            conn.rollback()
            raise

    def _sync_footballdata(self, conn, key: str) -> dict:
        """One league-season from football-data.org: one authenticated GET (X-Auth-Token from the environment), validated before anything is saved, ingested with the same reconciliation,
        date protection, provenance and quarantine as every other source. A missing or malformed token raises BEFORE any request."""
        from store import footballdata as fd

        common, _, _ = _adapters()
        spec = self.cfg.spec_for(key)
        token = fd.load_token(self.cfg.token_env("footballdata"))
        acfg = _adapter_config()
        acfg.live_enabled = True
        acfg.snapshot_dir = str(SNAPSHOT_DIR)
        acfg.ledger_path = str(SNAPSHOT_DIR / "request_ledger.jsonl")
        base_opener = self.opener or (self.request_guard(_urllib_opener) if self.request_guard else _urllib_opener)
        attempts = {"n": 0}

        def capped(url, headers):
            if attempts["n"] >= MAX_REQUESTS_PER_CYCLE:
                raise RequestCapReached(f"request cap of {MAX_REQUESTS_PER_CYCLE} attempts per cycle reached")
            attempts["n"] += 1
            return base_opener(url, headers)

        client = common.HttpClient(acfg, "footballdata", min_interval_s=7.0, jitter_s=1.0, max_retries=min(self.cfg.max_retries, MAX_REQUESTS_PER_CYCLE - 1), opener=capped, sleep=self._sleep)
        store = common.SnapshotStore(acfg.snapshot_dir)
        origin = "injected_opener" if self.opener else "provider_http"
        reuse = {"snapshot": None, "sha256": None}

        def snap(name, body, meta):
            sha = hashlib.sha256(body).hexdigest()
            reuse["sha256"] = sha
            prev = latest_authentic_snapshot(SNAPSHOT_DIR / fd.SOURCE, spec["league"], spec["season"], origin)
            if prev and prev["sha256"] == sha:                           # byte-identical to the latest verified snapshot: reuse it, store nothing new
                reuse["snapshot"] = prev["snapshot_id"]
                return dict(prev, reused=True, checked_url=meta.get("url"), checked_retrieved_utc=meta.get("retrieved_utc"))
            return store.save(fd.SOURCE, name, body, dict(meta, source=fd.SOURCE, licence=fd.LICENCE, attribution=fd.ATTRIBUTION, origin=origin))

        adapter = fd.FootballDataAdapter(client, token, snap)
        recs, info = adapter.fetch_season(spec["league"], spec["season"], spec["competition_id"])
        run_id = conn.execute("INSERT INTO sync_runs(kind, source, competition_key, started_utc, outcome) VALUES ('sync','footballdata',?,?, 'running')", (key, now_utc())).lastrowid
        total = dict(inserted=0, updated=0, unchanged=0, confirmed=0, quarantined=0)
        conn.execute("INSERT OR IGNORE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (info["snapshot_id"], fd.SOURCE, "json", info.get("url"), None, info["sha256"], info["bytes"], info["saved_utc"], None, fd.LICENCE, fd.ATTRIBUTION))
        st = ingest_records(conn, recs, spec["competition_id"], key, spec["season_label"], run_id, info["snapshot_id"], protect_dates=True)
        for k in total:
            total[k] += st[k]
        latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (key,)).fetchone()[0]
        conn.execute("INSERT OR REPLACE INTO source_state(source, scope, state_json, updated_utc) VALUES ('footballdata',?,?,?)", (f"{spec['league']}/{spec['season']}", json.dumps(dict(last_ok_utc=now_utc(), latest_result=latest)), now_utc()))
        detail = dict(total, source_url=info.get("checked_url") or info.get("url"), response_sha256=reuse["sha256"], snapshot_id=info["snapshot_id"], snapshot_reused=bool(reuse["snapshot"]), origin=origin, http_attempts=attempts["n"], checked_utc=now_utc())
        conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', requests=?, inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                     (now_utc(), attempts["n"], total["inserted"], total["updated"], total["unchanged"], total["quarantined"], latest, json.dumps(detail), run_id))
        conn.commit()
        return dict(total, requests=attempts["n"], snapshot_reused=bool(reuse["snapshot"]))

    def _sync_openligadb(self, conn, key: str) -> dict:
        common, _, ol = _adapters()
        spec = self.cfg.spec_for(key)
        for league, season in self.cfg.verified_seasons():               # explicit, config-listed league-seasons only; the shipped list is empty
            ol.VERIFIED_LEAGUES.setdefault((league, season), f"{league} {season} (listed in config)")
        if hasattr(ol, "VERIFIED_LEAGUES"):                              # the frozen adapter file is untouched: the approved league-season is registered at runtime
            ol.VERIFIED_LEAGUES.setdefault((spec["league"], spec["season"]), f"{key} {spec['season_label']} (approved in sync.APPROVED, Phase 4.9)")
            ol.COMPETITION_MAP.setdefault(spec["league"], spec["competition_id"])
        acfg = _adapter_config()
        acfg.live_enabled = True                                         # single switch: config/sync.json (still needs a real contact string)
        acfg.snapshot_dir = str(SNAPSHOT_DIR)
        acfg.ledger_path = str(SNAPSHOT_DIR / "request_ledger.jsonl")
        base_opener = self.opener or (self.request_guard(_urllib_opener) if self.request_guard else _urllib_opener)
        attempts = {"n": 0}

        def capped(url, headers):
            if attempts["n"] >= MAX_REQUESTS_PER_CYCLE:
                raise RequestCapReached(f"request cap of {MAX_REQUESTS_PER_CYCLE} attempts per cycle reached")
            attempts["n"] += 1
            return base_opener(url, headers)

        client = common.HttpClient(acfg, "openligadb", min_interval_s=3.0, jitter_s=1.5, max_retries=min(self.cfg.max_retries, MAX_REQUESTS_PER_CYCLE - 1), opener=capped, sleep=self._sleep)
        counter = attempts
        adapter = ol.OpenLigaDBAdapter(acfg, client=client, state_path=str(SNAPSHOT_DIR / "openligadb_state.json"))
        origin = "injected_opener" if self.opener else "provider_http"       # provenance of the bytes: real provider answers vs tests/replays
        reuse = {"snapshot": None, "sha256": None}
        original_snap = adapter._snap

        def snap(name, body, meta):
            if name.endswith("_season"):
                validate_season_payload(body, spec["league"])                # malformed/contradictory: raise now, before anything is saved or ingested
                sha = hashlib.sha256(body).hexdigest()
                reuse["sha256"] = sha
                prev = latest_authentic_snapshot(SNAPSHOT_DIR / "openligadb", spec["league"], spec["season"], origin)
                if prev and prev["sha256"] == sha:                           # byte-identical to the latest verified snapshot: reuse it, store nothing new
                    reuse["snapshot"] = prev["snapshot_id"]
                    return dict(prev, reused=True, checked_url=meta.get("url"), checked_retrieved_utc=meta.get("retrieved_utc"))
            return original_snap(name, body, dict(meta, origin=origin))

        adapter._snap = snap
        first = not conn.execute("SELECT 1 FROM source_state WHERE source='openligadb' AND scope=?", (f"{spec['league']}/{spec['season']}",)).fetchone()
        if first or self.cfg.refresh_mode == "full_season":
            recs, info = adapter.fetch_season(spec["league"], spec["season"])      # one GET: https://api.openligadb.de/getmatchdata/<league>/<season>; every matchday, every cycle
            infos = [info]
        else:
            recs, infos = adapter.poll(spec["league"], spec["season"])
        run_id = conn.execute("INSERT INTO sync_runs(kind, source, competition_key, started_utc, outcome) VALUES ('sync','openligadb',?,?, 'running')", (key, now_utc())).lastrowid
        total = dict(inserted=0, updated=0, unchanged=0, confirmed=0, quarantined=0)
        for info in infos:
            conn.execute("INSERT OR IGNORE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (info["snapshot_id"], "openligadb", "json", info.get("url"), None, info["sha256"], info["bytes"], info["saved_utc"], info.get("last_change_date"), ol.LICENCE, ol.ATTRIBUTION))
        if recs:
            sid = infos[0]["snapshot_id"] if infos else "none"
            st = ingest_records(conn, recs, spec["competition_id"], key, spec["season_label"], run_id, sid, protect_dates=True)      # Phase 4.8C: a differing date is held for a human, never silently applied
            for k in total:
                total[k] += st[k]
        latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (key,)).fetchone()[0]
        conn.execute("INSERT OR REPLACE INTO source_state(source, scope, state_json, updated_utc) VALUES ('openligadb',?,?,?)", (f"{spec['league']}/{spec['season']}", json.dumps(dict(last_ok_utc=now_utc(), latest_result=latest)), now_utc()))
        detail = dict(total, source_url=infos[0].get("checked_url") or infos[0].get("url") if infos else None, response_sha256=reuse["sha256"], snapshot_id=infos[0]["snapshot_id"] if infos else None,
                      snapshot_reused=bool(reuse["snapshot"]), origin=origin, http_attempts=counter["n"], checked_utc=now_utc())
        conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', requests=?, inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                     (now_utc(), counter["n"], total["inserted"], total["updated"], total["unchanged"], total["quarantined"], latest, json.dumps(detail), run_id))
        conn.commit()
        return dict(total, requests=counter["n"], snapshot_reused=bool(reuse["snapshot"]))
