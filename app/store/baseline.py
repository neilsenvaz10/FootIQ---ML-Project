"""Offline baseline import: repository CSV/pickle baseline -> SQLite. No network access anywhere in this module.

Inputs (all read-only; their sha256 is recorded in `source_snapshots`):
  * FootIQ_ML_Training_Preparation/_build/work/V_universe.pkl   the frozen model universe (all club matches the models use)
  * FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv  dashboard source for the 8 club competitions
  * data/miniproject/matches.csv                                 dashboard rows for the 3 international competitions
  * FootIQ_Dataset_Submission/09_Upcoming_Fixtures.csv           2026-27 schedule snapshot (2026-10-15)
Importing twice changes nothing (rows are matched on record_id and compared by content hash).
"""
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import config as C  # noqa: E402

ROOT = C.ROOT
V_PATH = ROOT / "FootIQ_ML_Training_Preparation" / "_build" / "work" / "V_universe.pkl"
FIXTURES_CSV = ROOT / "FootIQ_Dataset_Submission" / "09_Upcoming_Fixtures.csv"
ENC = "utf-8-sig"

MATCH_COLS = ["record_id", "kind", "competition_id", "competition_key", "season", "stage", "matchday_label", "matchday_no", "match_date", "kickoff_local", "kickoff_utc", "time_precision",
              "home_entity_id", "away_entity_id", "model_home_entity", "model_away_entity", "home_name", "away_name", "status", "home_goals_final", "away_goals_final", "home_goals_90", "away_goals_90", "label_90_status", "outcome",
              "shootout_winner", "neutral", "rated", "regular", "in_universe", "tier", "competition_type", "source_system", "licence", "src_order"]
HASH_COLS = [c for c in MATCH_COLS if c not in ("src_order",)]


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(v):
    """pandas/numpy value -> plain python (NaN/NaT -> None)."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        return v.item()
    return v


def content_hash(row: dict) -> str:
    return hashlib.sha1(json.dumps([row.get(c) for c in HASH_COLS], default=str).encode()).hexdigest()


def matchday_no(stage):
    m = re.search(r"(\d+)\s*$", stage or "")
    return int(m.group(1)) if m and re.match(r"(Matchday|Regular Season -|\d+\.\s*Round)", stage or "") else None


def upsert_matches(conn: sqlite3.Connection, rows: list[dict], ts: str) -> dict:
    """Idempotent upsert on record_id. Returns counts. A row is rewritten only if its content hash changed."""
    existing = dict(conn.execute("SELECT record_id, content_hash FROM matches"))
    ins, upd, same = [], [], 0
    for r in rows:
        r = {c: r.get(c) for c in MATCH_COLS}
        h = content_hash(r)
        old = existing.get(r["record_id"])
        if old is None:
            ins.append((*[r[c] for c in MATCH_COLS], ts, ts, 0, h))
        elif old != h:
            upd.append((*[r[c] for c in MATCH_COLS if c != "record_id"], ts, h, r["record_id"]))
        else:
            same += 1
    cols = ",".join(MATCH_COLS + ["first_seen_utc", "last_changed_utc", "change_count", "content_hash"])
    conn.executemany(f"INSERT INTO matches ({cols}) VALUES ({','.join('?' * (len(MATCH_COLS) + 4))})", ins)
    sets = ",".join(f"{c}=?" for c in MATCH_COLS if c != "record_id") + ",last_changed_utc=?,change_count=change_count+1,content_hash=?"
    conn.executemany(f"UPDATE matches SET {sets} WHERE record_id=?", upd)
    return dict(inserted=len(ins), updated=len(upd), unchanged=same)


def add_snapshot(conn, snapshot_id, source, kind, path: Path, licence, revision=None):
    sha = sha256_file(path)
    conn.execute("INSERT OR REPLACE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (snapshot_id, source, kind, None, path.relative_to(ROOT).as_posix(), sha, path.stat().st_size, utc(), revision, licence, None))
    return sha


def build_rows():
    """Assemble every baseline match row. Returns (rows, teams, aliases, competitions, quality)."""
    V = pd.read_pickle(V_PATH)
    raw = pd.read_csv(C.CLUB_SOURCE, encoding=ENC, low_memory=False)
    src_order = {rid: i for i, rid in enumerate(raw.record_id)}
    comp_by_source = {c["source_id"]: c for c in C.ALL_COMPETITIONS if c["kind"] == "club"}
    d8 = raw[raw.competition_id.isin(comp_by_source)]

    # display name of a club = its spelling in the most recent match (same rule the dashboard dataset uses)
    ids = pd.concat([raw[["match_date", "home_entity_id", "home_team_name"]].set_axis(["d", "e", "n"], axis=1), raw[["match_date", "away_entity_id", "away_team_name"]].set_axis(["d", "e", "n"], axis=1)]).dropna()
    display = ids.sort_values("d").drop_duplicates("e", keep="last").set_index("e").n.to_dict()
    idsv = pd.concat([V[["dt", "home_entity_id", "home_team_name"]].set_axis(["d", "e", "n"], axis=1), V[["dt", "away_entity_id", "away_team_name"]].set_axis(["d", "e", "n"], axis=1)])
    for e, n in idsv.sort_values("d").drop_duplicates("e", keep="last").set_index("e").n.items():
        display.setdefault(e, n)

    rows: dict[str, dict] = {}
    for r in V.itertuples(index=False):
        status = r.match_status if r.match_status in ("completed", "awarded", "abandoned") else "completed"
        rows[r.record_id] = dict(
            record_id=r.record_id, kind="club", competition_id=r.competition_id, competition_key=None, season=str(r.season_corrected), stage=clean(r.stage), matchday_label=clean(r.stage),
            matchday_no=matchday_no(clean(r.stage)), match_date=str(r.dt)[:10], kickoff_local=clean(r.kickoff_time_local), kickoff_utc=None, time_precision="date_only" if clean(r.kickoff_time_local) is None else "local_unknown_tz",
            home_entity_id=r.home_entity_id, away_entity_id=r.away_entity_id, model_home_entity=r.home_entity_id, model_away_entity=r.away_entity_id, home_name=r.home_team_name, away_name=r.away_team_name, status=status,
            home_goals_final=clean(r.final_excl_pens_home), away_goals_final=clean(r.final_excl_pens_away), home_goals_90=clean(r.gh), away_goals_90=clean(r.ga),
            label_90_status=clean(r.label_90_status), outcome=None, shootout_winner=None, neutral=None, rated=int(bool(r.rated)), regular=int(bool(r.regular_round_robin_stage)), in_universe=1,
            tier=clean(r.tier), competition_type=clean(r.competition_type), source_system=clean(r.source_system), licence=clean(r.source_license), src_order=None)
    n_v = len(rows)
    for r in d8.itertuples(index=False):                                    # dashboard fields come from 04d, model fields stay from V
        key = comp_by_source[r.competition_id]["key"]
        base = rows.get(r.record_id)
        new = dict(
            record_id=r.record_id, kind="club", competition_id=r.competition_id, competition_key=key, season=str(r.season), stage=clean(r.stage), matchday_label=clean(r.stage), matchday_no=matchday_no(clean(r.stage)),
            match_date=str(r.match_date)[:10], kickoff_local=clean(r.kickoff_time_local), kickoff_utc=None, time_precision="date_only" if clean(r.kickoff_time_local) is None else "local_unknown_tz",
            home_entity_id=r.home_entity_id, away_entity_id=r.away_entity_id, home_name=r.home_team_name, away_name=r.away_team_name, status=r.match_status if r.match_status in ("completed", "awarded") else "completed",
            home_goals_final=int(r.final_score_home_excl_penalties), away_goals_final=int(r.final_score_away_excl_penalties), label_90_status=clean(r.label_90_status), outcome=clean(r.outcome_90min_1x2),
            source_system=clean(r.source_system), licence=clean(r.source_license), src_order=src_order[r.record_id])
        if base:
            base.update(new)
        else:                                                               # in the dashboard source but not in the model universe
            rows[r.record_id] = dict(new, matchday_no=new["matchday_no"], home_goals_90=None, away_goals_90=None, shootout_winner=None, neutral=None, rated=None, regular=None, in_universe=0, tier=None,
                                     competition_type=clean(r.competition_type))
    n_dash_only = len(rows) - n_v

    # international dashboard rows (already prepared from the martj42 results and the verified 2026 World Cup files)
    m = pd.read_csv(C.MATCHES_CSV, encoding=ENC, dtype=str, keep_default_na=False)
    intl = m[m.group == "International"]
    seen: dict[str, int] = {}
    for i, r in enumerate(intl.itertuples(index=False)):
        base_id = f"INTL|{r.competition_key}|{r.date}|{r.home}|{r.away}|{r.stage}"
        seen[base_id] = seen.get(base_id, 0) + 1
        rid = base_id if seen[base_id] == 1 else f"{base_id}|{seen[base_id]}"
        rows[rid] = dict(
            record_id=rid, kind="international", competition_id=None, competition_key=r.competition_key, season=r.season, stage=r.stage or None, matchday_label=None, matchday_no=None, match_date=r.date,
            kickoff_local=None, kickoff_utc=None, time_precision="date_only", home_entity_id=None, away_entity_id=None, home_name=r.home, away_name=r.away, status="completed",
            home_goals_final=int(r.home_goals), away_goals_final=int(r.away_goals), home_goals_90=None, away_goals_90=None, label_90_status=None, outcome=r.outcome or None,
            shootout_winner=r.shootout_winner or None, neutral=r.neutral or None, rated=None, regular=None, in_universe=0, tier=None, competition_type="international",
            source_system=r.source, licence=r.licence, src_order=int(intl.index[i]))
    comps = {}
    for r in V.drop_duplicates("competition_id").itertuples(index=False):
        k = comp_by_source.get(r.competition_id)
        comps[r.competition_id] = (r.competition_id, k["key"] if k else None, r.competition_name, k["group"] if k else None, clean(r.competition_type), clean(r.competition_country), clean(r.tier), "club")
    for c in C.ALL_COMPETITIONS:
        if c["kind"] == "intl":
            comps[f"intl:{c['key']}"] = (f"intl:{c['key']}", c["key"], c["name"], c["group"], "international", None, None, "international")
    pairs = pd.concat([V[["competition_id", "home_team_name", "home_entity_id"]].set_axis(["c", "n", "e"], axis=1), V[["competition_id", "away_team_name", "away_entity_id"]].set_axis(["c", "n", "e"], axis=1),
                       d8[["competition_id", "home_team_name", "home_entity_id"]].set_axis(["c", "n", "e"], axis=1), d8[["competition_id", "away_team_name", "away_entity_id"]].set_axis(["c", "n", "e"], axis=1)]).drop_duplicates()
    return rows, display, pairs, comps, dict(v_rows=n_v, dashboard_only_rows=n_dash_only, intl_rows=len(intl))


def import_fixtures(conn, pairs: pd.DataFrame, ts: str, run_id: int):
    """2026-27 schedule snapshot. Unresolved teams and duplicates of completed matches go to quarantine, never into matches."""
    sys.path.insert(0, str(ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1"))
    from footiq_sources.identity import IdentityResolver

    resolver = IdentityResolver(set(zip(pairs.c, pairs.n, pairs.e)))
    fx = pd.read_csv(FIXTURES_CSV, encoding=ENC, low_memory=False)
    key_of = {c["source_id"]: c["key"] for c in C.ALL_COMPETITIONS if c["kind"] == "club"}
    known = {r[0] for r in conn.execute("SELECT DISTINCT competition_id FROM matches WHERE kind='club'")}
    completed_pairs = {(r[0], r[1], r[2], r[3]) for r in conn.execute("SELECT competition_id, season, home_entity_id, away_entity_id FROM matches WHERE status IN ('completed','awarded','abandoned') AND season='2026-27'")}
    rows, quarantined = [], []
    sources = []
    for r in fx.itertuples(index=False):
        if r.competition_id not in known or r.competition_type != "domestic_league":
            continue                                                        # only competitions the models already know
        he, hm = resolver.resolve("openfootball", r.competition_id, r.home_team)
        ae, am = resolver.resolve("openfootball", r.competition_id, r.away_team)
        if not he or not ae:
            quarantined.append((run_id, "openfootball", r.match_id, f"unresolved team identity ({hm}/{am}): {r.home_team} v {r.away_team}", None, ts))
            continue
        if (r.competition_id, str(r.season), he, ae) in completed_pairs:
            quarantined.append((run_id, "openfootball", r.match_id, "fixture duplicates an already completed match", None, ts))
            continue
        status = "scheduled" if r.fixture_status == "upcoming" else "awaiting_result"
        rows.append(dict(
            record_id=r.match_id, kind="club", competition_id=r.competition_id, competition_key=key_of.get(r.competition_id), season=str(r.season), stage=clean(r.stage), matchday_label=clean(r.stage),
            matchday_no=matchday_no(clean(r.stage)), match_date=str(r.match_date)[:10], kickoff_local=clean(r.kickoff_time_local), kickoff_utc=None,
            time_precision="date_only" if clean(r.kickoff_time_local) is None else "local_unknown_tz", home_entity_id=he, away_entity_id=ae, home_name=r.home_team, away_name=r.away_team, status=status,
            home_goals_final=None, away_goals_final=None, home_goals_90=None, away_goals_90=None, label_90_status=None, outcome=None, shootout_winner=None, neutral=None, rated=None, regular=None,
            in_universe=0, tier=None, competition_type="domestic_league", source_system=clean(r.source_name), licence="CC0-1.0", src_order=None))
        sources.append((r.match_id, f"{r.source_file}:{r.source_line}", str(r.source_repo_commit)))
    stats = upsert_matches(conn, rows, ts)
    conn.executemany("INSERT OR IGNORE INTO match_sources(source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, source_revision, provenance) VALUES ('openfootball',?,?, 'primary','fixtures-2026-10-15','CC0-1.0',?,?,?)",
                     [(rid, rid, ts, commit.split("|")[0], prov) for rid, prov, commit in sources])
    conn.execute("DELETE FROM quarantine WHERE source='openfootball' AND run_id<>?", (run_id,))                 # a re-import replaces the previous review list
    conn.executemany("INSERT INTO quarantine(run_id, source, source_ref, reason, payload, created_utc) VALUES (?,?,?,?,?,?)", quarantined)
    stats["quarantined"] = len(quarantined)
    return stats


def import_baseline(conn: sqlite3.Connection) -> dict:
    ts = utc()
    run_id = conn.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES ('baseline_import','repository CSV baseline',?, 'running')", (ts,)).lastrowid
    conn.commit()
    rows, display, pairs, comps, quality = build_rows()
    conn.executemany("INSERT OR REPLACE INTO competitions VALUES (?,?,?,?,?,?,?,?)", list(comps.values()))
    teams = {e: (e, n, e.split(":")[1] if e.startswith("CLUB:") else None) for e, n in display.items()}
    conn.executemany("INSERT OR REPLACE INTO teams VALUES (?,?,?)", list(teams.values()))
    conn.executemany("INSERT OR IGNORE INTO team_aliases(competition_id, source, alias, entity_id, method) VALUES (?,?,?,?, 'baseline_exact')",
                     [(c, "baseline", n, e) for c, n, e in pairs.itertuples(index=False) if e in teams])
    snaps = {}
    for sid, src, kind, path, lic in (("baseline-universe-v1.1", "frozen model universe", "pickle", V_PATH, "CC0-1.0 / CC BY-SA 4.0 (see rows)"),
                                      ("baseline-04d-v1.0", "FootIQ combined club matches", "csv", C.CLUB_SOURCE, "CC0-1.0 / CC BY-SA 4.0 (see rows)"),
                                      ("baseline-dashboard-matches", "app/prepare_data.py output", "csv", C.MATCHES_CSV, "see rows"),
                                      ("fixtures-2026-10-15", "openfootball schedule snapshot", "csv", FIXTURES_CSV, "CC0-1.0")):
        snaps[sid] = add_snapshot(conn, sid, src, kind, path, lic)
    stats = upsert_matches(conn, list(rows.values()), ts)
    conn.executemany("INSERT OR IGNORE INTO match_sources(source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, source_revision, provenance) VALUES (?,?,?, 'primary',?,?,?,NULL,?)",
                     [((r["source_system"] or "unknown").split(" (")[0].lower(), r["record_id"], r["record_id"], "baseline-universe-v1.1" if r["in_universe"] else "baseline-04d-v1.0", r["licence"], ts, r["record_id"]) for r in rows.values()])
    fstats = import_fixtures(conn, pairs, ts, run_id)
    latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE status IN ('completed','awarded')").fetchone()[0]
    detail = json.dumps(dict(quality=quality, fixtures=fstats, input_sha256=snaps), sort_keys=True)
    conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                 (utc(), stats["inserted"] + fstats["inserted"], stats["updated"] + fstats["updated"], stats["unchanged"] + fstats["unchanged"], fstats["quarantined"], latest, detail, run_id))
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('baseline_imported_utc', ?)", (ts,))
    conn.commit()
    return dict(matches=stats, fixtures=fstats, quality=quality, input_sha256=snaps, latest_completed=latest)
