"""OFFLINE REHEARSAL of the proposed OpenLigaDB import for the Premier League and La Liga 2026-27 into a PRIVATE COPY of the store.

Scope approved 2026-10-25: deterministic replay of the saved snapshots (no network, no live request), reviewed team aliases only, no date overwritten,
the two contradictory scores quarantined, production database / original CSVs / frozen models / prospective-evaluation files untouched.

    python app/store/rehearse_openligadb.py            run the rehearsal and write data/supervised/rehearsal/*

Nothing here writes to data/footiq.sqlite: it is copied (read-only file copy) and every change happens in the copy.
"""
import csv
import hashlib
import json
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
import gameweeks  # noqa: E402
from store import baseline, db, sync, views  # noqa: E402

PROD = C.ROOT / "data" / "footiq.sqlite"
REH = C.ROOT / "data" / "supervised" / "rehearsal"
SNAP = C.ROOT / "data" / "snapshots" / "investigation"
SEASON = "2026-27"
SNAPSHOT_DATE = date(2026, 10, 25)                       # day the snapshots were taken ("today" for every eligibility calculation)
FIXED_NOW = "2026-10-25T09:07:13Z"                       # every wall-clock stamp in the copy: makes the replay byte-reproducible
LEAGUES = {
    "EPL": dict(shortcut="pl", spec=dict(source="openligadb", competition_id="england:1-premierleague", league="pl", season_label=SEASON, season="2026")),
    "LALIGA": dict(shortcut="la1", spec=dict(source="openligadb", competition_id="espana:1-liga", league="la1", season_label=SEASON, season="2026")),
}
# Proposed by the user, NOT unconditional: each is verified below and only inserted when every check passes.
PROPOSED = [
    dict(comp="EPL", source_name="Brentford F.C.", proposed_text="Brentford FC", entity="CLUB:ENG:brentford-fc"),
    dict(comp="LALIGA", source_name="Celta Vigo", proposed_text="RC Celta de Vigo", entity="CLUB:ESP:rc-celta-vigo"),
    dict(comp="LALIGA", source_name="Deportivo A Coruña", proposed_text="Deportivo de La Coruña", entity="CLUB:ESP:rcd-la-coruna"),
    dict(comp="LALIGA", source_name="FC Villareal", proposed_text="Villarreal CF", entity="CLUB:ESP:villarreal-cf"),
    dict(comp="LALIGA", source_name="Racing Santander", proposed_text="Racing de Santander", entity="CLUB:ESP:real-racing-santander"),
]
FORBIDDEN = {"Brentford F.C.": {"CLUB:ENG:arsenal-fc"}}   # the wrong suggestion the fuzzy ladder offered


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------ fingerprints
def table_fingerprints(conn) -> dict:
    out = {}
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
        h = hashlib.sha256()
        n = 0
        for r in conn.execute(f'SELECT * FROM "{t}" ORDER BY rowid'):
            h.update(repr(tuple(r)).encode("utf-8"))
            n += 1
        out[t] = dict(rows=n, sha256=h.hexdigest())
    return out


def manifest() -> dict:
    """sha256 of the things that must not change: production store, original data files, frozen models, prospective-evaluation files, sync config."""
    files = {}
    dev = C.ROOT / "FootIQ_Club_Model_Development_v2"
    singles = [PROD, C.ROOT / "data" / "miniproject" / "matches.csv", C.ROOT / "config" / "sync.json",
               C.ROOT / "FootIQ_Dataset_Submission" / "09_Upcoming_Fixtures.csv", C.ROOT / "FootIQ_ML_Data_Readiness" / "04d_COMBINED_CLUB_MATCHES_v1.0.csv",
               C.ROOT / "FootIQ_ML_Training_Preparation" / "_build" / "work" / "V_universe.pkl",
               C.ROOT / "FootIQ_Club_Model_Baseline_v1" / "artifacts" / "multinomial_logreg.pkl", C.ROOT / "FootIQ_Club_Model_Baseline_v1" / "artifacts" / "preprocessing_train_fitted.json",
               dev / "final_refit_v2_r1" / "artifacts" / "club_v2_lr_final_candidate.pkl", dev / "final_refit_v2_r1" / "artifacts" / "feature_contract_v2_final.json",
               C.ROOT / "data" / "model_artifacts" / "v27" / "live_match_model.pkl",
               dev / "_scripts" / "d11_prospective_logger.py", dev / "shadow_integration_r1" / "prospective_logger_v2.py"]
    dirs = [dev / "final_refit_v2_r1" / "prospective_log", dev / "matched_v1_prospective_r1" / "prospective_log", C.ROOT / "data" / "model_artifacts" / "v27"]
    for p in singles:
        files[p.relative_to(C.ROOT).as_posix()] = sha_file(p) if p.exists() else "absent"
    for d in dirs:
        for p in sorted(d.rglob("*")) if d.exists() else []:
            if p.is_file() and "__pycache__" not in p.parts:
                files[p.relative_to(C.ROOT).as_posix()] = sha_file(p)
    return files


def private_copy(dst: Path) -> None:
    """Read-only copy of the production file(s) into `dst` (the production database is never opened)."""
    assert dst.resolve() != PROD.resolve() and REH.resolve() in dst.resolve().parents, "refusing: the target must be inside the rehearsal folder"
    REH.mkdir(parents=True, exist_ok=True)
    for ext in ("", "-wal", "-shm"):
        (Path(str(dst) + ext)).unlink(missing_ok=True)
    shutil.copyfile(PROD, dst)
    wal = Path(str(PROD) + "-wal")
    if wal.exists() and wal.stat().st_size:
        shutil.copyfile(wal, str(dst) + "-wal")
    conn = sqlite3.connect(dst)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.close()


# ------------------------------------------------------------------------------------------------------------ snapshots
def load_snapshots() -> dict:
    run = json.loads((SNAP / "run_summary.json").read_text(encoding="utf-8"))["snapshots"]
    out = {}
    for name, info in run.items():
        p = SNAP / "openligadb" / info["snapshot_id"]
        data = p.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        assert sha == info["sha256"], f"snapshot {name} does not match its recorded sha256"
        out[name] = dict(info, path=p, payload=data, rel=p.relative_to(C.ROOT).as_posix())
    return out


def records_of(snap: dict, comp_id: str):
    _, _, ol = sync._adapters()
    ts = snap["retrieved_utc"]
    now = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return ol.parse_payload(snap["payload"], ts, snap["snapshot_id"], now, comp_id)


# ------------------------------------------------------------------------------------------------------------ identity verification
def participants(conn, comp_id: str) -> dict:
    return {r[0]: r[1] for r in conn.execute("SELECT home_entity_id, MAX(home_name) FROM matches WHERE competition_id=? AND season=? GROUP BY home_entity_id", (comp_id, SEASON))}


def verify_identities(conn, snaps: dict) -> dict:
    """Check each proposed alias against canonical ids and 2026-27 membership. Returns per-alias verdicts and the list of aliases that may be written."""
    verdicts, accept = [], []
    for pr in PROPOSED:
        lg = LEAGUES[pr["comp"]]
        cid = lg["spec"]["competition_id"]
        recs = records_of(snaps[lg["shortcut"]], cid)
        resolver = sync.build_resolver(conn)
        members = participants(conn, cid)
        teams_row = conn.execute("SELECT entity_id, display_name FROM teams WHERE entity_id=?", (pr["entity"],)).fetchone()
        history = sorted({r[0] for r in conn.execute("SELECT home_name FROM matches WHERE home_entity_id=? AND competition_id=? UNION SELECT away_name FROM matches WHERE away_entity_id=? AND competition_id=?", (pr["entity"], cid, pr["entity"], cid))})
        # every other source name must already resolve WITHOUT this alias, so the unmatched store team is forced; then the alias is tested by fixture structure
        before = resolver.resolve("openligadb", cid, pr["source_name"])
        names = sorted({r.home_raw for r in recs} | {r.away_raw for r in recs})
        mapped = {n: resolver.resolve("openligadb", cid, n) for n in names}
        others = {n: e for n, (e, _) in mapped.items() if e and n != pr["source_name"]}
        unmapped_members = sorted(set(members) - set(others.values()))
        fixtures = [r for r in recs if pr["source_name"] in (r.home_raw, r.away_raw)]
        probe = dict(others, **{q["source_name"]: q["entity"] for q in PROPOSED if q["comp"] == pr["comp"]})   # the proposals of one league are tested together, as they would be applied
        store_pairs = defaultdict(list)
        for r in conn.execute("SELECT home_entity_id h, away_entity_id a, matchday_no md, match_date d FROM matches WHERE competition_id=? AND season=?", (cid, SEASON)):
            store_pairs[(r["h"], r["a"])].append(r)
        paired = md_ok = 0
        for r in fixtures:
            he, ae = probe.get(r.home_raw), probe.get(r.away_raw)
            rows = store_pairs.get((he, ae), []) if he and ae else []
            if len(rows) == 1:
                paired += 1
                md_ok += str(rows[0]["md"]) == str(r.round)
        checks = dict(
            entity_exists_in_teams=bool(teams_row),
            entity_is_2026_27_member_of_competition=pr["entity"] in members,
            entity_seen_in_this_competition_before_2026=len(history) > 0,
            not_resolved_before_alias=before[0] is None,
            not_a_forbidden_fuzzy_target=pr["entity"] not in FORBIDDEN.get(pr["source_name"], set()),
            entity_not_already_used_by_another_source_name=pr["entity"] not in others.values(),
            entity_is_among_the_unmatched_store_teams=pr["entity"] in unmapped_members,
            all_source_fixtures_pair_with_exactly_one_store_fixture=paired == len(fixtures) == 38,
            matchday_agrees_for_every_fixture=md_ok == len(fixtures) == 38,
        )
        ok = all(checks.values())
        v = dict(competition=pr["comp"], source_name=pr["source_name"], proposed_name_as_written=pr["proposed_text"], canonical_entity_id=pr["entity"],
                 canonical_display_name=teams_row["display_name"] if teams_row else None, historical_names_in_competition=history,
                 proposed_name_equals_a_stored_name=pr["proposed_text"] in history or (teams_row and pr["proposed_text"] == teams_row["display_name"]),
                 unmatched_store_teams_at_this_point=unmapped_members, source_fixtures=len(fixtures), paired=paired, matchday_agrees=md_ok, checks=checks, accepted=ok)
        verdicts.append(v)
        if ok:
            accept.append(dict(competition_id=cid, source="openligadb", alias=pr["source_name"], entity_id=pr["entity"], method="reviewed_alias_2026-10-25"))
    return dict(verdicts=verdicts, aliases=accept)


def mapping_table(conn, snaps, aliases_applied: bool) -> dict:
    """Source team name -> store entity, with method, for both leagues (after aliases)."""
    out = {}
    resolver = sync.build_resolver(conn)
    for key, lg in LEAGUES.items():
        cid = lg["spec"]["competition_id"]
        recs = records_of(snaps[lg["shortcut"]], cid)
        members = participants(conn, cid)
        rows, used = [], Counter()
        for n in sorted({r.home_raw for r in recs} | {r.away_raw for r in recs}):
            e, m = resolver.resolve("openligadb", cid, n)
            is_alias = conn.execute("SELECT 1 FROM team_aliases WHERE competition_id=? AND source='openligadb' AND alias=?", (cid, n)).fetchone()
            rows.append(dict(source_name=n, entity_id=e, store_name=members.get(e), method=("reviewed alias" if is_alias else m)))
            if e:
                used[e] += 1
        out[key] = dict(rows=rows, unresolved=[r["source_name"] for r in rows if not r["entity_id"]], store_teams_without_source_name=sorted(set(members) - set(used)),
                        entities_used_twice=[e for e, k in used.items() if k > 1], one_to_one=len(rows) == len(set(r["entity_id"] for r in rows if r["entity_id"])) == len(members))
    return out


# ------------------------------------------------------------------------------------------------------------ comparisons
def date_comparison(conn_before, conn_after, snaps) -> list[dict]:
    """Fixture-by-fixture date comparison (store date vs source date), with prediction-eligibility effect. Uses the AFTER state only for freshness."""
    resolver = sync.build_resolver(conn_after)
    rows = []
    for key, lg in LEAGUES.items():
        cid = lg["spec"]["competition_id"]
        recs = records_of(snaps[lg["shortcut"]], cid)
        latest_after = gameweeks.competition_latest_result(conn_after, key)
        by_pair = {(r["home_entity_id"], r["away_entity_id"]): dict(r) for r in conn_before.execute("SELECT * FROM matches WHERE competition_id=? AND season=?", (cid, SEASON))}
        for rec in recs:
            he, _ = resolver.resolve("openligadb", cid, rec.home_raw)
            ae, _ = resolver.resolve("openligadb", cid, rec.away_raw)
            st = by_pair.get((he, ae))
            if not st or st["match_date"] == rec.match_date:
                continue
            d_store, d_src = date.fromisoformat(st["match_date"]), date.fromisoformat(rec.match_date)
            lo, hi = sorted((d_store, d_src))
            ents = (st["home_entity_id"], st["away_entity_id"])
            between = conn_before.execute(
                "SELECT COUNT(*) FROM matches WHERE status IN ('completed','awarded') AND match_date>=? AND match_date<? AND (home_entity_id IN (?,?) OR away_entity_id IN (?,?))",
                (lo.isoformat(), hi.isoformat(), *ents, *ents)).fetchone()[0]
            store_past, src_past = d_store < SNAPSHOT_DATE, d_src < SNAPSHOT_DATE
            played = rec.status == "completed" or st["status"] in ("completed", "awarded")
            stale = lambda d: (d - date.fromisoformat(latest_after)).days > gameweeks.STALE_DAYS if latest_after else False  # noqa: E731
            effects = []
            if between:
                effects.append(f"history window: {between} result(s) of these teams dated {lo}..{hi} would enter or leave the form/rating history")
            if store_past != src_past:
                effects.append("played/awaiting status: one date is before the snapshot date and the other is not (changes 'awaiting result' and missing-result flags)")
            if stale(d_store) != stale(d_src):
                effects.append(f"staleness: crosses the {gameweeks.STALE_DAYS}-day stale-history threshold")
            if rec.status == "completed" and st["status"] in ("awaiting_result", "scheduled"):
                effects.append("a verified result exists in the source but is HELD back until the date is decided")
            rows.append(dict(
                competition=key, matchday=st["matchday_no"], home=st["home_name"], away=st["away_name"], store_record_id=st["record_id"], original_store_date=st["match_date"],
                source_date_utc=rec.match_date, source_kickoff_utc=rec.kickoff_utc, source_kickoff_local=rec.kickoff_local, difference_days=(d_src - d_store).days,
                store_status=st["status"], source_status=rec.status, played_by_snapshot=played, source_result=(f"{rec.regulation_home}-{rec.regulation_away}" if rec.status == "completed" else ""),
                affects_prediction_eligibility="yes" if effects else "no", effect="; ".join(effects) if effects else "future fixture on both dates, no result of either team in between: features and flags identical",
                anomaly=abs((d_src - d_store).days) > 30))
    return sorted(rows, key=lambda r: (r["competition"], r["matchday"], r["home"]))


def standings(conn, key: str) -> list[dict]:
    t = {}
    for r in conn.execute("SELECT home_entity_id h, away_entity_id a, home_name hn, away_name an, home_goals_final gh, away_goals_final ga FROM matches WHERE competition_key=? AND season=? AND status IN ('completed','awarded') AND home_goals_final IS NOT NULL", (key, SEASON)):
        for ent, name, gf, ga in ((r["h"], r["hn"], r["gh"], r["ga"]), (r["a"], r["an"], r["ga"], r["gh"])):
            x = t.setdefault(ent, dict(team=name, played=0, won=0, drawn=0, lost=0, gf=0, ga=0))
            x["played"] += 1
            x["gf"] += gf
            x["ga"] += ga
            x["won"] += gf > ga
            x["drawn"] += gf == ga
            x["lost"] += gf < ga
    rows = []
    for ent, x in t.items():
        rows.append(dict(entity=ent, **x, gd=x["gf"] - x["ga"], points=3 * x["won"] + x["drawn"]))
    rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))          # indicative only: official tie-break rules are not applied
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def eligibility(conn, key: str) -> dict:
    cmp_latest = gameweeks.competition_latest_result(conn, key)
    lst = gameweeks.list_gameweeks(conn, key, SEASON, SNAPSHOT_DATE)
    agg = Counter()
    flags = Counter()
    per_gw = []
    for g in lst["gameweeks"]:
        fx = gameweeks.gameweek_fixtures(conn, key, SEASON, g["matchday_no"], SNAPSHOT_DATE)["fixtures"]
        pred = [f for f in fx if f["predictable"]]
        per_gw.append(dict(matchday=g["matchday_no"], predictable=len(pred), full=sum(f["reliability"] == "full" for f in pred), provisional=sum(f["reliability"] == "provisional" for f in pred)))
        for f in pred:
            agg["predictable"] += 1
            agg[f["reliability"]] += 1
            agg["kickoff_known"] += f["kickoff_utc"] is not None
            for fl in set(f["flags"]):
                flags[fl.replace("_home", "").replace("_away", "")] += 1
    return dict(latest_result=cmp_latest, next_gameweek=lst["next_gameweek"], totals=dict(agg), flags=dict(flags), per_gameweek=per_gw,
                next_gameweek_detail=next((p for p in per_gw if p["matchday"] == lst["next_gameweek"]), None))


# ------------------------------------------------------------------------------------------------------------ the rehearsal
def apply(dst: Path, snaps: dict, aliases: list[dict], kind: str = "offline_rehearsal") -> dict:
    original_now, sync.now_utc = sync.now_utc, (lambda: FIXED_NOW)      # deterministic stamps (restored below)
    try:
        return _apply(dst, snaps, aliases, kind)
    finally:
        sync.now_utc = original_now


def _apply(dst: Path, snaps: dict, aliases: list[dict], kind: str) -> dict:
    conn = db.connect(dst)
    for a in aliases:
        conn.execute("INSERT OR IGNORE INTO team_aliases(competition_id, source, alias, entity_id, method) VALUES (?,?,?,?,?)", (a["competition_id"], a["source"], a["alias"], a["entity_id"], a["method"]))
    _, _, ol = sync._adapters()
    for name in ("leagues", "pl", "pl1", "la1"):                      # all four snapshots are registered, including the empty pl1 and the league listing
        s = snaps[name]
        conn.execute("INSERT OR IGNORE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (s["snapshot_id"], "openligadb", "json", s["url"], s["rel"], s["sha256"], s["bytes"], s["retrieved_utc"], None, ol.LICENCE, ol.ATTRIBUTION))
    conn.commit()
    results = {}
    for key, lg in LEAGUES.items():
        s = snaps[lg["shortcut"]]
        now = datetime.strptime(s["retrieved_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        results[key] = sync.replay_payload(conn, s["payload"], key, retrieved_utc=s["retrieved_utc"], now=now, kind=kind, spec=lg["spec"], snapshot_id=s["snapshot_id"], url=s["url"], path=s["rel"], protect_dates=True)
    conn.close()
    return results


def diff_matches(before, after) -> tuple[list[dict], dict]:
    b = {r["record_id"]: dict(r) for r in before.execute("SELECT * FROM matches")}
    a = {r["record_id"]: dict(r) for r in after.execute("SELECT * FROM matches")}
    changes, kinds = [], Counter()
    skip = {"last_changed_utc", "change_count", "content_hash"}
    for rid, new in a.items():
        old = b.get(rid)
        if old is None:
            kinds["inserted"] += 1
            changes.append(dict(record_id=rid, competition=new["competition_key"], change="INSERTED", field="", before="", after=json.dumps({k: new[k] for k in ("match_date", "status", "home_name", "away_name")})))
            continue
        fields = [k for k in new if k not in skip and new[k] != old[k]]
        if fields:
            kinds["changed_rows"] += 1
            for f in fields:
                changes.append(dict(record_id=rid, competition=new["competition_key"], change="UPDATED", field=f, before=old[f], after=new[f]))
    kinds["deleted"] = len(set(b) - set(a))
    return changes, dict(kinds)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> dict:
    REH.mkdir(parents=True, exist_ok=True)
    man_before = manifest()
    snaps = load_snapshots()
    before_db, after_db, repeat_db = REH / "footiq.before.sqlite", REH / "footiq.rehearsal.sqlite", REH / "footiq.rehearsal_repeat.sqlite"
    private_copy(before_db)
    private_copy(after_db)
    private_copy(repeat_db)
    cb = db.connect(before_db)
    fp_before = table_fingerprints(cb)
    ident = verify_identities(cb, snaps)
    aliases = ident["aliases"]
    run1 = apply(after_db, snaps, aliases)
    run_repeat = apply(repeat_db, snaps, aliases)                       # an independent copy: must end identical (determinism)
    ca, cr = db.connect(after_db), db.connect(repeat_db)
    fp_after, fp_repeat = table_fingerprints(ca), table_fingerprints(cr)
    ca.close()
    again = apply(after_db, snaps, aliases)                              # a second pass over the same copy: must change nothing (idempotency)
    ca = db.connect(after_db)
    fp_again = table_fingerprints(ca)

    changes, kinds = diff_matches(cb, ca)
    write_csv(REH / "import_diff_matches.csv", changes)
    mapping = mapping_table(ca, snaps, True)
    dates = date_comparison(cb, ca, snaps)
    write_csv(REH / "date_comparison.csv", dates)

    recovered = {}
    for key in LEAGUES:
        rec = [dict(record_id=r["record_id"], date=r["match_date"], home=r["home_name"], away=r["away_name"], score=f"{r['home_goals_90']}-{r['away_goals_90']}", store_source=r["source_system"])
               for r in ca.execute("SELECT * FROM matches WHERE competition_key=? AND season=? AND status='completed'", (key, SEASON))
               if cb.execute("SELECT status FROM matches WHERE record_id=?", (r["record_id"],)).fetchone()["status"] in ("awaiting_result", "scheduled")]
        recovered[key] = rec
    held_completed = [d for d in dates if d["source_status"] == "completed" and d["store_status"] in ("awaiting_result", "scheduled")]
    quarantine = [dict(r) for r in ca.execute("SELECT id, run_id, source_ref, reason, created_utc FROM quarantine WHERE run_id IN (SELECT run_id FROM sync_runs WHERE kind='offline_rehearsal') ORDER BY id")]
    for q in quarantine:
        q["category"] = q["reason"].split(":")[0].split("(")[0].strip()[:40]
    write_csv(REH / "quarantine.csv", quarantine)

    new_sources = ca.execute("SELECT role, licence, snapshot_id, COUNT(*) n FROM match_sources WHERE snapshot_id IN (SELECT snapshot_id FROM source_snapshots WHERE path LIKE 'data/snapshots/investigation/%') GROUP BY 1,2,3 ORDER BY 3,1").fetchall()
    snaprows = [dict(r) for r in ca.execute("SELECT snapshot_id, url, path, sha256, bytes, retrieved_utc, licence, attribution FROM source_snapshots WHERE path LIKE 'data/snapshots/investigation/%' ORDER BY retrieved_utc")]
    fresh = lambda c: {r["competition_key"]: r for r in views.freshness(c) if r["competition_key"] in LEAGUES}  # noqa: E731
    stand = {k: dict(before=standings(cb, k), after=standings(ca, k)) for k in LEAGUES}
    elig = {k: dict(before=eligibility(cb, k), after=eligibility(ca, k)) for k in LEAGUES}

    cp = lambda c: {t: c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in ("matches", "match_sources", "source_snapshots", "team_aliases", "sync_runs", "quarantine", "forecast_runs", "forecasts")}  # noqa: E731
    counts, fresh_state = dict(before=cp(cb), after=cp(ca)), dict(before=fresh(cb), after=fresh(ca))
    for c in (cb, ca, cr):
        c.close()
    man_after = manifest()
    report = dict(
        generated_for_snapshot_utc=FIXED_NOW, identities=ident, mapping=mapping,
        replay=dict(first_pass=run1, second_pass_same_copy=again, independent_repeat=run_repeat),
        recovered_results=recovered, results_held_for_date_decision=held_completed,
        quarantine=quarantine, quarantine_counts=Counter(q["category"] for q in quarantine),
        date_differences=dict(total=len(dates), by_league=Counter(d["competition"] for d in dates), by_difference_days=Counter(d["difference_days"] for d in dates),
                              affects_eligibility=Counter(d["affects_prediction_eligibility"] for d in dates), anomalies=[d for d in dates if d["anomaly"]]),
        diff_matches_summary=kinds, diff_fields=Counter((c["competition"], c["field"], c["change"]) for c in changes).most_common(),
        table_counts=counts, freshness=fresh_state,
        provenance=dict(match_sources=[dict(r) for r in new_sources], snapshots=snaprows),
        standings=stand, eligibility=elig,
        fingerprints=dict(before=fp_before, after=fp_after, repeat_copy_equals_first_copy=fp_after == fp_repeat,
                          second_pass_changed_nothing=all(again[k]["inserted"] == 0 and again[k]["updated"] == 0 for k in again) and all(fp_again[t] == fp_after[t] for t in fp_after if t not in ("sync_runs",)),
                          changed_tables=[t for t in fp_after if fp_after[t] != fp_before.get(t)]),
        manifest=dict(before=man_before, after=man_after, identical=man_before == man_after, files=len(man_before)),
    )
    (REH / "rehearsal_report.json").write_text(json.dumps(report, indent=1, default=lambda o: dict(o) if isinstance(o, Counter) else str(o), ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    rep = main()
    print("accepted aliases:", [(a["alias"], a["entity_id"]) for a in rep["identities"]["aliases"]])
    print("replay:", json.dumps(rep["replay"], default=str)[:900])
    print("manifest identical:", rep["manifest"]["identical"], "files:", rep["manifest"]["files"])
    print("deterministic:", rep["fingerprints"]["repeat_copy_equals_first_copy"], "idempotent:", rep["fingerprints"]["second_pass_changed_nothing"], "changed tables:", rep["fingerprints"]["changed_tables"])
