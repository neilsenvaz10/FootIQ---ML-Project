"""Integrity checks for Phase 4 (read-only): protected files, frozen models, production store, sync settings, backend sources and the git index.

    python data/supervised/phase4/phase4_integrity.py start   record the state before the first Phase 4 edit (writes start_manifest.json)
    python data/supervised/phase4/phase4_integrity.py check   compare the current state with it and with the end-of-Phase-3 manifest

Nothing here writes to data/footiq.sqlite or to any file other than start_manifest.json.
"""
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
START = HERE / "start_manifest.json"
sys.path.insert(0, str(ROOT / "app"))

from store import rehearse_openligadb as R  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def backend_sources() -> dict:
    """Hashes of everything the backend and its tests are made of. P4.0 and P4.1 changed none of it; P4.2 added exactly the files in P42_EXPECTED."""
    out = {}
    patterns = [("app", "*.py"), ("app/store", "*.py"), ("app/seasonsim", "*.py"), ("app/static", "*"), ("config", "*.json"), ("tests", "*.py")]
    for folder, pattern in patterns:
        for p in sorted((ROOT / folder).glob(pattern)):
            if p.is_file():
                out[p.relative_to(ROOT).as_posix()] = sha(p)
    return out


# Phase 4.8B additions (quiet disabled sync, 6 h schedule, kickoff safeguard, readiness registry) and the approved config change periodic_minutes 60 -> 360.
P48B_EXPECTED = ["app/kickoff.py", "app/predict.py", "app/store/sync.py", "app/store/db.py", "app/forecast.py", "config/sync.json", "tests/test_gameweeks.py", "tests/test_store.py", "tests/test_sync_scheduler.py", "tests/test_refresh_integration.py"]

# Phase 4.8C additions: two-part baseline tool, supervised verification script (not run against the network yet), freshness facts, live-path date protection and their tests.
P48D_EXPECTED = ["app/store/import_p48d_stage1.py", "tests/test_provenance_link.py", "tests/test_seasonsim_service.py", "app/disputes.py", "app/store/daily_audit.py", "config/operations.json", "tests/test_full_season_refresh.py", "app/store/baseline_monitor.py", "tests/test_sync_monitoring.py", "tests/conftest.py", "app/store/run_one_cycle_p48d.py"]
P48C_EXPECTED = ["app/store/baseline_hash.py", "app/store/verify_openligadb_p48c.py", "tests/test_baseline_hash.py", "app/kickoff_tz.py", "tests/test_kickoff_tz.py"]

# The only backend files stage P4.2 may differ in: the read-only featured-fixture endpoint (new module, new tests, and the route, imports and cache clearing in main.py).
P42_EXPECTED = ["app/featured.py", "app/main.py", "tests/test_featured.py", "app/gameweeks.py", "app/matches.py", "tests/test_matches.py", "tests/test_team_form_hint.py"]  # P4.2 and P4.3


def snapshot_state() -> dict:
    return dict(
        created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        protected=R.manifest(),
        backend_sources=backend_sources(),
        git=dict(head=git("rev-parse", "HEAD"), branch=git("branch", "--show-current"), staged=[x for x in git("diff", "--cached", "--name-only").splitlines() if x],
                 tracked_files_under_frontend=len([x for x in git("ls-files", "frontend").splitlines() if x])),
    )


def diff(a: dict, b: dict) -> list:
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def check() -> dict:
    start = json.loads(START.read_text(encoding="utf-8"))
    now = snapshot_state()
    out = {}
    before = json.loads((ROOT / "data" / "supervised" / "hashes_before.json").read_text(encoding="utf-8"))
    out["frozen_files_in_hashes_before_json"] = dict(count=len(before), changed=[k for k, v in before.items() if sha(ROOT / k) != v])
    phase3 = json.loads((ROOT / "data" / "supervised" / "phase3" / "final_manifest.json").read_text(encoding="utf-8"))
    out["protected_manifest"] = dict(
        files=len(now["protected"]),
        identical_to_start_of_phase_4=(now["protected"] == start["protected"]), differences_from_start=diff(now["protected"], start["protected"]),
        identical_to_end_of_phase_3=(now["protected"] == phase3), differences_from_phase_3=diff(now["protected"], phase3),
    )
    changed = diff(now["backend_sources"], start["backend_sources"])
    out["backend_sources"] = dict(files=len(now["backend_sources"]), identical_to_start_of_phase_4=(now["backend_sources"] == start["backend_sources"]),
                                  differences=changed, expected_since_p4_2=P42_EXPECTED, only_the_expected_differences=(changed == sorted(set(P42_EXPECTED) | set(P48B_EXPECTED) | set(P48C_EXPECTED) | set(P48D_EXPECTED))), expected_since_p4_8b=P48B_EXPECTED, expected_since_p4_8c=P48C_EXPECTED)
    prod = ROOT / "data" / "footiq.sqlite"
    rec = (ROOT / "data" / "supervised" / "production_import" / "prod_sha_after_import.txt").read_text(encoding="utf-8").split()[0]
    out["production_database"] = dict(sha256_matches_post_import_record=(sha(prod) == rec))
    from store import baseline_hash as BH  # noqa: E402

    # baseline v2 (Phase 4.8C, cut-off run 7) is history; baseline v3 (Phase 4.8D Stage 1, after the six approved results, cut-off run 10) is the current one
    for tag, fname in (("baseline_v3", "db_baseline_v3.json"), ("baseline_v2", "db_baseline_v2.json")):
        rec2 = json.loads((HERE / "p48c" / fname).read_text(encoding="utf-8"))
        now_logical = BH.logical(prod, rec2.get("last_baseline_run_id", 7))
        out["production_database"][tag] = dict(physical_sha256_matches=(BH.physical_sha256(prod) == rec2["physical_sha256"]), logical_sha256_matches=(now_logical["logical_sha256"] == rec2["logical_sha256"]),
                                               excluded_rows=[r["run_id"] for r in now_logical["excluded_rows"]], recorded_excluded_rows=[r["run_id"] for r in rec2["excluded_rows"]], current=(tag == "baseline_v3"))
    c = sqlite3.connect(f"file:{prod.as_posix()}?mode=ro", uri=True)
    out["production_database"].update(integrity_check=c.execute("pragma integrity_check").fetchone()[0], simulation_runs=c.execute("select count(*) from simulation_runs").fetchone()[0])
    c.close()
    sync = json.loads((ROOT / "config" / "sync.json").read_text(encoding="utf-8"))
    sim = json.loads((ROOT / "config" / "season_sim.json").read_text(encoding="utf-8"))
    out["settings"] = dict(live_enabled=sync.get("live_enabled"), scoreline_method=sim.get("scoreline_method"), scoreline_validation_status=sim["scoreline_validation"]["status"],
                           position_bounds_enabled=sim["points_only"]["position_bounds"]["enabled"])
    out["git"] = dict(staged_files=now["git"]["staged"], head_unchanged=(now["git"]["head"] == start["git"]["head"]), head=git("log", "--oneline", "-1"), branch=now["git"]["branch"],
                      tracked_files_under_frontend=now["git"]["tracked_files_under_frontend"])
    out["prospective_evaluation_files_in_manifest"] = len([k for k in now["protected"] if "prospective" in k])
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "start":
        if START.exists():
            sys.exit(f"refusing to overwrite {START}")
        state = snapshot_state()
        START.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
        print(f"recorded {len(state['protected'])} protected files and {len(state['backend_sources'])} backend sources at {state['created_utc']}; head {state['git']['head'][:7]}")
    else:
        print(json.dumps(check(), indent=1))
