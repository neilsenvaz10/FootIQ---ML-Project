"""Phase 4.8D final safeguards: scheduler/quarantine monitoring in the sync status, and the auditable baseline monitor. Synthetic stores; no network, no production file."""
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))
from store import baseline_monitor as BM  # noqa: E402
from store import db, sync  # noqa: E402
from test_featured import add_match, add_team  # noqa: E402

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%SZ"


@pytest.fixture
def store(tmp_path):
    p = tmp_path / "s.sqlite"
    c = db.connect(p)
    db.init(c)
    for slug in ("a", "b", "c", "d"):
        add_team(c, slug, f"Team {slug.upper()} FC")
    add_match(c, "bl:1", "BUNDESLIGA", "2026-27", 1, "2026-10-10", "a", "b", status="completed", score=(1, 0))
    add_match(c, "bl:2", "BUNDESLIGA", "2026-27", 2, "2026-10-17", "c", "d")
    add_match(c, "bl:3", "BUNDESLIGA", "2026-27", 2, "2026-10-17", "a", "c")
    add_match(c, "epl:1", "EPL", "2026-27", 1, "2026-10-10", "a", "d", status="completed", score=(2, 2))
    c.execute("UPDATE matches SET content_hash='h-' || record_id")
    c.execute("INSERT INTO sync_runs(run_id, kind, source, started_utc, finished_utc, outcome) VALUES (1, 'baseline_import', 'repository CSV baseline', '2026-10-25T08:00:00Z', '2026-10-25T08:00:05Z', 'ok')")
    c.execute("INSERT INTO quarantine(run_id, source, source_ref, reason, created_utc) VALUES (1, 'openfootball', 'x1', 'baseline data-quality note', '2026-10-25T08:00:01Z')")
    c.commit()
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    return p


def ex(path, sql, *a):
    c = sqlite3.connect(path)
    c.execute(sql, a)
    c.commit()
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()


def status(path, **cfg):
    c = db.connect(path, readonly=True)
    try:
        return sync.status(c, sync.SyncConfig(**cfg), NOW)
    finally:
        c.close()


def check(path, outcome, at, **kw):
    cols = dict(kind="periodic_check", source="all approved", started_utc=at, finished_utc=at, outcome=outcome, requests=1)
    cols.update(kw)
    ex(path, f"INSERT INTO sync_runs({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", *cols.values())


# ------------------------------------------------------------------------------------------------ scheduler monitoring
def test_a_disabled_scheduler_says_so_and_names_no_next_check(store):
    sch = status(store)["scheduler"]
    assert sch["live_enabled"] is False and sch["status"].startswith("off") and sch["next_scheduled_check_utc"] is None and sch["consecutive_failed_cycles"] == 0
    assert sch["max_requests_per_cycle"] == 3 and sch["max_retries"] == 2


def test_idle_overdue_and_backing_off_are_told_apart(store):
    check(store, "ok", (NOW - timedelta(hours=2)).strftime(FMT))
    idle = status(store, live_enabled=True, periodic_minutes=360)["scheduler"]
    assert idle["status"].startswith("idle; next check") and idle["next_scheduled_check_utc"] == (NOW + timedelta(hours=4)).strftime(FMT) and idle["consecutive_failed_cycles"] == 0
    over = status(store, live_enabled=True, periodic_minutes=60)["scheduler"]
    assert over["status"].startswith("check overdue")
    check(store, "error", (NOW - timedelta(hours=1)).strftime(FMT))
    check(store, "error", (NOW - timedelta(minutes=30)).strftime(FMT))
    back = status(store, live_enabled=True, periodic_minutes=360)["scheduler"]
    assert back["consecutive_failed_cycles"] == 2 and "backing off after 2 failed cycle(s)" in back["status"]
    assert back["next_scheduled_check_utc"] == (NOW - timedelta(minutes=30) + timedelta(hours=24)).strftime(FMT)


def test_a_young_running_row_shows_as_running(store):
    check(store, "running", (NOW - timedelta(minutes=3)).strftime(FMT))
    assert status(store, live_enabled=True)["scheduler"]["status"] == "running a check now"


def test_a_successful_check_with_nothing_new_is_said_plainly_and_is_not_a_claim_of_completeness(store):
    ex(store, "INSERT INTO sync_runs(kind, source, competition_key, started_utc, finished_utc, outcome, requests, inserted, updated) VALUES ('sync','openligadb','BUNDESLIGA','2026-11-01T06:00:00Z','2026-11-01T06:00:03Z','ok',1,0,0)")
    bl = {c["competition_key"]: c for c in status(store, live_enabled=True)["competitions"]}["BUNDESLIGA"]
    assert bl["last_check_found_new_results"] is False and "returned no new results" in bl["last_check_summary"] and "2026-11-01T06:00:03Z" in bl["last_check_summary"]
    assert bl["last_successful_external_check_utc"] == "2026-11-01T06:00:03Z" and bl["latest_verified_result_date"] == "2026-10-10"
    ex(store, "INSERT INTO sync_runs(kind, source, competition_key, started_utc, finished_utc, outcome, requests, inserted, updated) VALUES ('sync','openligadb','BUNDESLIGA','2026-11-01T11:00:00Z','2026-11-01T11:00:03Z','ok',1,0,2)")
    bl2 = {c["competition_key"]: c for c in status(store, live_enabled=True)["competitions"]}["BUNDESLIGA"]
    assert bl2["last_check_found_new_results"] is True and "2 new or changed record(s) stored" in bl2["last_check_summary"]
    epl = {c["competition_key"]: c for c in status(store)["competitions"]}["EPL"]
    assert epl["last_check_summary"].startswith("No successful source check yet")


def test_quarantine_is_counted_by_kind_with_a_warning_and_baseline_notes_are_kept_apart(store):
    q0 = status(store)["quarantine"]
    assert q0["needs_operator_review"] == 0 and q0["warning"] is None and q0["baseline_data_quality_notes"] == 1 and q0["open_total"] == 1
    ex(store, "INSERT INTO sync_runs(run_id, kind, source, started_utc, outcome) VALUES (5,'sync','openligadb','2026-11-01T06:00:00Z','ok')")
    for reason in ("CONFLICT: stored 2-2 vs source 2-1", "DATE_DIFFERENCE: stored 2026-10-25 vs source 2026-10-24: x v y", "DATE_DIFFERENCE: stored 2026-10-26 vs source 2026-10-25: z v w", "CONTRADICTORY SOURCE RESULT: several scores"):
        ex(store, "INSERT INTO quarantine(run_id, source, source_ref, reason, created_utc) VALUES (5,'openligadb',?,?, '2026-11-01T06:00:00Z')", reason[:12], reason)
    q1 = status(store)["quarantine"]
    assert q1["needs_operator_review"] == 4 and q1["open_total"] == 5 and q1["by_kind"] == {"score_conflict": 1, "date_disagreement": 2, "contradictory_record": 1}
    assert "4 unresolved sync finding(s) need a human decision" in q1["warning"] and "Nothing is applied automatically" in q1["warning"] and sync.QUARANTINE_PROCEDURE in q1["warning"]
    assert (ROOT / sync.QUARANTINE_PROCEDURE).exists()                                                         # the documented procedure exists


# ------------------------------------------------------------------------------------------------ baseline monitor
@pytest.fixture
def cps(tmp_path):
    return tmp_path / "baselines" / "checkpoints.jsonl"


def import_run(path, inserted=0, updated=1, run_id=20):
    ex(path, "INSERT INTO sync_runs(run_id, kind, source, competition_key, started_utc, finished_utc, outcome, requests, inserted, updated) VALUES (?, 'sync','openligadb','BUNDESLIGA','2026-11-01T06:00:00Z','2026-11-01T06:00:03Z','ok',1,?,?)", run_id, inserted, updated)


def result_arrives(path, rid="bl:2", source="openligadb"):
    ex(path, "UPDATE matches SET status='completed', home_goals_final=1, away_goals_final=0, source_system=?, content_hash='new-' || record_id WHERE record_id=?", source, rid)


def test_no_change_and_log_only_changes_are_told_apart_from_each_other(store, cps):
    cp = BM.init(store, "baseline v3 (test)", "tester", cps)
    assert cp["id"] == 1 and BM.report(store, cp)["verdict"] == "NO_CHANGE"
    ex(store, "INSERT INTO sync_runs(run_id, kind, source, started_utc, outcome) VALUES (30, 'startup_check','all approved','2026-11-01T06:00:00Z','skipped_live_disabled')")
    ex(store, "INSERT INTO source_snapshots(snapshot_id, source, kind, sha256, bytes, retrieved_utc) VALUES ('s1','openligadb','json','abc',1,'2026-11-01T06:00:00Z')")
    r = BM.report(store, cp)
    assert r["verdict"] == "EXPECTED_LOG_ONLY" and set(r["changed_tables"]) <= BM.OPERATIONAL_TABLES and r["current_physical"] != r["checkpoint_physical"]


def test_a_new_result_explained_by_a_successful_run_is_accepted_only_with_a_persons_approval(store, cps):
    BM.init(store, "v3", "tester", cps)
    import_run(store)
    result_arrives(store)
    r = BM.report(store, BM.checkpoints(cps)[-1])
    assert r["verdict"] == "IMPORT_EXPLAINED" and r["approvable"] and r["scope_changes"]["BUNDESLIGA|2026-27"]["n_changed"] == 1 and r["explained_by"]["records_claimed"] == 1
    cp2 = BM.approve(store, "after the first scheduler import", "operator", cps)
    assert cp2["id"] == 2 and cp2["approved_by"] == "operator" and cp2["previous_physical_sha256"] == BM.checkpoints(cps)[0]["physical_sha256"] and len(BM.checkpoints(cps)) == 2
    assert BM.report(store, BM.checkpoints(cps)[-1])["verdict"] == "NO_CHANGE"                                 # the earlier checkpoint is kept, the new one is the reference


def test_a_sync_run_existing_does_not_make_a_change_legitimate(store, cps):
    BM.init(store, "v3", "tester", cps)
    result_arrives(store)                                                                                       # a result with NO run that reports it
    r = BM.report(store, BM.checkpoints(cps)[-1])
    assert r["verdict"] == "UNEXPECTED" and any("no successful sync run" in x for x in r["reasons"])
    with pytest.raises(PermissionError):
        BM.approve(store, "should be refused", "operator", cps)
    assert len(BM.checkpoints(cps)) == 1
    import_run(store, updated=1)                                                                                # one run, but two rows changed: more than it explains
    result_arrives(store, "bl:3")
    r2 = BM.report(store, BM.checkpoints(cps)[-1])
    assert r2["verdict"] == "UNEXPECTED" and any("unexplained" in x for x in r2["reasons"])


def test_a_changed_row_must_name_an_approved_provider(store, cps):
    BM.init(store, "v3", "tester", cps)
    import_run(store)
    result_arrives(store, source="some other source")
    r = BM.report(store, BM.checkpoints(cps)[-1])
    assert r["verdict"] == "UNEXPECTED" and any("approved provider" in x for x in r["reasons"])


@pytest.mark.parametrize("sql", [
    "UPDATE teams SET display_name='Renamed FC' WHERE entity_id='CLUB:TST:a'",
    "UPDATE matches SET content_hash='changed', home_goals_final=9 WHERE record_id='epl:1'",
    "INSERT INTO forecast_runs(created_utc, competition_key, season, matchday_label, model_id, model_artifact_sha256, data_cutoff_date, data_cutoff_note, user_action, notes) VALUES ('2026-11-01T00:00:00Z','EPL','2026-27','Matchday 1','{}','{}','2026-10-24','n','x','n')",
    "DELETE FROM quarantine",
    "DELETE FROM matches WHERE record_id='bl:3'",
    "INSERT INTO team_aliases(competition_id, source, alias, entity_id, method) VALUES ('test:BUNDESLIGA','openligadb','Odd Name','CLUB:TST:a','manual')",
])
def test_changes_to_business_data_outside_an_explained_import_are_unexpected_even_with_a_run_on_record(store, cps, sql):
    BM.init(store, "v3", "tester", cps)
    import_run(store, updated=5)                                                                                # a generous run does not excuse changes elsewhere
    ex(store, sql)
    r = BM.report(store, BM.checkpoints(cps)[-1])
    assert r["verdict"] == "UNEXPECTED" and not r["approvable"] and r["reasons"]


def test_new_quarantine_findings_are_logged_not_waved_through_silently(store, cps):
    BM.init(store, "v3", "tester", cps)
    ex(store, "INSERT INTO quarantine(run_id, source, source_ref, reason, created_utc) VALUES (NULL,'openligadb','9','CONFLICT: stored 1-0 vs source 2-0','2026-11-01T06:00:00Z')")
    r = BM.report(store, BM.checkpoints(cps)[-1])
    assert r["verdict"] == "EXPECTED_LOG_ONLY" and any("new quarantine finding" in x for x in r["reasons"])


def test_the_daily_report_is_written_to_disk_and_init_refuses_to_overwrite(store, cps, tmp_path):
    BM.init(store, "v3", "tester", cps)
    with pytest.raises(PermissionError):
        BM.init(store, "again", "tester", cps)
    rep = BM.daily_report(store, cps, tmp_path / "reports")
    files = list((tmp_path / "reports").glob("*.json"))
    assert len(files) == 1 and json.loads(files[0].read_text(encoding="utf-8"))["verdict"] == rep["verdict"] == "NO_CHANGE"


# ------------------------------------------------------------------------------------------------ Phase 4.8E: exactly one scheduler, never under tests
def test_exactly_one_scheduler_thread_and_none_when_off_or_under_tests(store, monkeypatch):
    import time
    monkeypatch.setenv("FOOTIQ_SCHEDULER_LOCK", str(store.parent / "private-scheduler.lock"))                  # the real backend may hold the production lock
    monkeypatch.delenv("FOOTIQ_DISABLE_SYNC", raising=False)
    off = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=False))
    off.start()
    assert off._thread is None and sync.active_scheduler_threads() == 0
    mgr = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True, startup_delay_seconds=30), opener=lambda u, h: pytest.fail("no request in this test"))
    mgr.start()
    mgr.start()                                                                                                  # a second start() on the same manager does not add a thread
    time.sleep(0.2)
    assert sync.active_scheduler_threads() == 1
    mgr.stop()
    mgr._thread.join(5)
    assert sync.active_scheduler_threads() == 0
    monkeypatch.setenv("FOOTIQ_DISABLE_SYNC", "1")                                                              # what tests/conftest.py sets
    guarded = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True))
    guarded.start()
    assert guarded._thread is None and sync.active_scheduler_threads() == 0


def test_the_shipped_configuration_is_bundesliga_and_la_liga_every_six_hours_full_season_with_two_retries():
    cfg = sync.SyncConfig.load()
    assert cfg.approved_competitions() == ["BUNDESLIGA", "LALIGA"] and cfg.sources == {"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA"]}, "footballdata": {"enabled": False, "competitions": [], "token_env": "FOOTBALL_DATA_API_TOKEN"}}
    assert cfg.periodic_minutes == 360 and cfg.max_retries == 2 and cfg.refresh_mode == "full_season" and cfg.startup_check is True
    assert set(sync.APPROVED) == {"BUNDESLIGA", "LALIGA"}                                                        # no other league can be requested even if listed


def test_the_provider_status_follows_the_live_switch(store):
    on = {c["competition_key"]: c for c in status(store, live_enabled=True)["competitions"]}
    off = {c["competition_key"]: c for c in status(store)["competitions"]}
    assert on["BUNDESLIGA"]["provider_readiness"] == "approved_live_enabled" and "ON" in on["BUNDESLIGA"]["provider_note"]
    assert off["BUNDESLIGA"]["provider_readiness"] == "approved_live_disabled"
    assert on["EPL"]["provider_readiness"] == "prepared_offline" and on["SERIEA"]["provider_readiness"] == "prepared_needs_token"      # no other league changes


# ------------------------------------------------------------------------------------------------ Phase 4.8F: one scheduler per machine
def _hold_lock_in_another_process(lock_path, seconds):
    import subprocess
    code = ("import sys,time;sys.path.insert(0,r'%s');from store import sync;l=sync.SchedulerLock(r'%s');print('LOCKED' if l.acquire() else 'FAILED',flush=True);time.sleep(%s)" % (ROOT / "app", lock_path, seconds))
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "LOCKED"
    return p


def test_a_second_process_never_starts_a_second_scheduler_and_a_crash_leaves_no_stale_lock(store, tmp_path, monkeypatch):
    import time
    monkeypatch.delenv("FOOTIQ_DISABLE_SYNC", raising=False)
    monkeypatch.delenv("FOOTIQ_SCHEDULER_LOCK", raising=False)
    lock = tmp_path / "run" / "scheduler.lock"
    holder = _hold_lock_in_another_process(lock, 60)
    try:
        mgr = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True, startup_delay_seconds=30), lock_path=lock, opener=lambda u, h: pytest.fail("no request"))
        mgr.start()
        assert mgr._thread is None and mgr.lock_state == "held_by_another_process" and sync.active_scheduler_threads() == 0
        assert "pid=" in lock.read_text(encoding="utf-8")                                                          # the file says who holds it
    finally:
        holder.kill()                                                                                              # a crash: no cleanup code runs
        holder.wait(10)
    mgr2 = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True, startup_delay_seconds=30), lock_path=lock, opener=lambda u, h: pytest.fail("no request"))
    for _ in range(60):                                                                                            # the OS may take a few milliseconds to release a dead process's lock
        mgr2.start()
        if mgr2.lock_state == "held":
            break
        time.sleep(0.05)
    time.sleep(0.2)
    assert mgr2.lock_state == "held" and sync.active_scheduler_threads() == 1                                       # the OS released the dead holder's lock: the next process schedules
    other = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True), lock_path=lock)
    other.start()
    assert other._thread is None and other.lock_state == "held_by_another_process"                                 # two managers in ONE machine: only one schedules
    mgr2.stop()
    assert sync.active_scheduler_threads() == 0
    other.start()
    assert other.lock_state == "held"                                                                              # stopping releases the lock
    other.stop()


def test_the_disable_override_wins_over_the_lock_and_the_config(store, tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTIQ_DISABLE_SYNC", "1")
    mgr = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True), lock_path=tmp_path / "l.lock")
    mgr.start()
    assert mgr._thread is None and mgr.lock_state == "not_applicable" and not (tmp_path / "l.lock").exists()      # it did not even take the lock


# ------------------------------------------------------------------------------------------------ Phase 4.8F: daily audit and the service script
from store import daily_audit as DA  # noqa: E402


def audit(store, tmp_path, cps, ledger_lines=(), http=False, live=True, name="project owner"):
    ops = tmp_path / "operations.json"
    ops.write_text(json.dumps(dict(operational_reviewer=name, assigned_utc="2026-10-27")), encoding="utf-8")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(dict(ts=t, url="u", status=200)) for t in ledger_lines), encoding="utf-8")
    return DA.run_audit(store, cps, tmp_path / "audit", NOW, http=http, ledger=ledger, operations=ops, backups=tmp_path / "b", cfg=sync.SyncConfig(live_enabled=live, periodic_minutes=360, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA"]}}))


def good_state(store):
    ex(store, "INSERT INTO sync_runs(run_id, kind, source, competition_key, started_utc, finished_utc, outcome, requests, inserted, updated) VALUES (40,'sync','openligadb','BUNDESLIGA','2026-11-01T10:00:00Z','2026-11-01T10:00:03Z','ok',1,0,0)")
    ex(store, "INSERT INTO sync_runs(run_id, kind, source, started_utc, finished_utc, outcome, requests) VALUES (41,'periodic_check','all approved','2026-11-01T10:00:00Z','2026-11-01T10:00:03Z','ok',1)")
    ex(store, "INSERT INTO sync_runs(run_id, kind, source, competition_key, started_utc, finished_utc, outcome, requests, inserted, updated) VALUES (42,'sync','openligadb','LALIGA','2026-11-01T10:00:05Z','2026-11-01T10:00:08Z','ok',1,0,0)")
    ex(store, "INSERT INTO sync_runs(run_id, kind, source, started_utc, finished_utc, outcome, requests, detail) VALUES (43,'periodic_check','all approved','2026-11-01T10:00:05Z','2026-11-01T10:00:08Z','ok',1,'[{\"competition\": \"LALIGA\", \"requests\": 1}]')")


def test_a_healthy_day_passes_names_the_reviewer_and_writes_the_report_without_approving_anything(store, cps, tmp_path):
    BM.init(store, "v3", "tester", cps)
    before = cps.read_text(encoding="utf-8")
    good_state(store)
    rep = audit(store, tmp_path, cps, ledger_lines=["2026-11-01T10:00:02Z"])
    assert rep["verdict"] == "PASS" and rep["operational_reviewer"] == "project owner" and rep["owner_actions"] == [] and rep["requests_last_24h"] == 1
    assert (tmp_path / "audit" / "2026-11-01.json").exists() and "daily audit 2026-11-01: PASS" in (tmp_path / "audit" / "2026-11-01.md").read_text(encoding="utf-8")
    assert cps.read_text(encoding="utf-8") == before                                                             # nothing was approved


def test_the_audit_asks_the_reviewer_when_something_needs_a_decision_and_still_approves_nothing(store, cps, tmp_path):
    BM.init(store, "v3", "tester", cps)
    before = cps.read_text(encoding="utf-8")
    good_state(store)
    import_run(store, run_id=50)
    result_arrives(store)                                                                                        # explained but not yet approved
    rep = audit(store, tmp_path, cps)
    assert rep["verdict"] == "ATTENTION" and rep["baseline_verdict"] == "IMPORT_EXPLAINED" and any("approve" in a for a in rep["owner_actions"])
    assert cps.read_text(encoding="utf-8") == before
    ex(store, "INSERT INTO quarantine(run_id, source, source_ref, reason, created_utc) VALUES (NULL,'openligadb','77','CONFLICT: stored 1-0 vs source 2-0','2026-11-01T11:00:00Z')")
    rep2 = audit(store, tmp_path, cps)                                                                           # a second audit the same day compares with the first
    assert any("NEW quarantine finding" in i["text"] for i in rep2["items"])


def test_failures_stale_checks_and_extra_requests_are_flagged_and_unexpected_changes_are_an_alert(store, cps, tmp_path):
    BM.init(store, "v3", "tester", cps)
    ex(store, "INSERT INTO sync_runs(run_id, kind, source, started_utc, finished_utc, outcome, requests) VALUES (60,'periodic_check','all approved','2026-11-01T09:00:00Z','2026-11-01T09:00:03Z','error',3)")
    rep = audit(store, tmp_path, cps, ledger_lines=["2026-11-01T0%d:00:00Z" % i for i in range(1, 10)] * 2)
    texts = " | ".join(i["text"] for i in rep["items"])
    assert rep["verdict"] == "ATTENTION" and "failed cycle(s) in a row" in texts and "never" in texts and "18 provider requests" in texts
    ex(store, "UPDATE teams SET display_name='Renamed FC' WHERE entity_id='CLUB:TST:a'")
    alert = audit(store, tmp_path, cps)
    assert alert["verdict"] == "ALERT" and alert["baseline_verdict"] == "UNEXPECTED"


def test_the_service_and_audit_scripts_parse_and_the_task_is_only_planned_never_created(tmp_path):
    import subprocess
    for script in ("footiq_service.ps1",):
        path = ROOT / "scripts" / "ops" / script
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('%s',[ref]$null,[ref]$e);if($e){$e|%%{$_.Message};exit 1}else{'OK'}" % path], capture_output=True, text=True)
        assert out.stdout.strip() == "OK", out.stdout + out.stderr
    plan = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "ops" / "footiq_service.ps1"), "task-plan"], capture_output=True, text=True, cwd=ROOT)
    assert plan.returncode == 0 and "(not created)" in plan.stdout and "at log on" in plan.stdout and "Existing task    :" in plan.stdout
    count = lambda: subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-ScheduledTask -TaskName 'FootIQ*' -ErrorAction SilentlyContinue | Measure-Object).Count"], capture_output=True, text=True).stdout.strip()
    before = count()
    refuse = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "ops" / "footiq_service.ps1"), "task-install"], capture_output=True, text=True, cwd=ROOT)
    assert refuse.returncode == 6 and "Refusing without -Apply" in refuse.stdout
    assert count() == before                                                                                      # task-install without -Apply changes nothing (the task itself was installed deliberately in Phase 4.8F)
