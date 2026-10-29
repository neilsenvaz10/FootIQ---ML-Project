"""Audit-only launcher; never edits legacy source. Runs on an isolated snapshot.

Usage: python -B -X utf8 isolated_runner.py ROOT ACTION TRACE
ACTION is pytest or an explicitly allowlisted legacy script basename.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import runpy
import sys

root = Path(sys.argv[1]).resolve()
action = sys.argv[2]
trace_path = Path(sys.argv[3]).resolve()
allowed = {
    "build_live_predictions_v27.py", "build_confidence_gate_v28.py",
    "simulate_live_tournament_v213.py", "validate_worldcup_full_v214.py",
}
if action != "pytest" and action not in allowed:
    raise SystemExit("Action not allowlisted")
if not (root / "data/model_artifacts/v27/live_match_model.pkl").is_file():
    raise SystemExit("Existing model required; training fallback prohibited")
reads, writes, blocked = set(), set(), []

def relative(path):
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except (ValueError, TypeError, OSError):
        return None

def audit(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.bind", "subprocess.Popen", "os.system"}:
        blocked.append({"event": event})
        raise PermissionError("Network and subprocesses prohibited in isolated audit")
    if event == "open":
        path, mode, flags = args
        if not isinstance(path, (str, bytes, os.PathLike)):
            return
        rel = relative(path)
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        )
        if writing:
            if rel is None or rel.startswith(("data/raw/", "data/model_artifacts/", "scripts/", "tests/")):
                blocked.append({"event": event, "path": str(path)})
                raise PermissionError("Write outside permitted isolated outputs")
            writes.add(rel)
        elif rel:
            reads.add(rel)
    if event in {"os.remove", "os.rmdir", "os.rename", "os.replace"}:
        blocked.append({"event": event})
        raise PermissionError("Deletion/rename prohibited during audit")

os.chdir(root)
sys.dont_write_bytecode = True
sys.path.insert(0, str(root / "scripts"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
sys.addaudithook(audit)
try:
    if action == "pytest":
        import pytest
        raise SystemExit(pytest.main([
            "tests", "-q", "-s", "-p", "no:cacheprovider", "-p", "no:logging",
            "--junitxml=" + str(root / "test_results.xml")
        ]))
    sys.argv = [str(root / "scripts" / action)]
    runpy.run_path(sys.argv[0], run_name="__main__")
finally:
    with trace_path.open("x", encoding="utf-8") as handle:
        json.dump({"action": action, "root": str(root), "read_paths": sorted(reads),
                   "written_paths": sorted(writes), "blocked_events": blocked}, handle, indent=2)
