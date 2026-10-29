"""Phase 4.26 step 1: READ-ONLY preflight of the approved cleanup manifest. Exits non-zero (and the cleanup must not start) if any check fails. Writes preflight_report.json."""
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
P425 = ROOT / "data" / "supervised" / "phase4" / "p425"
rep = {"checks": {}, "problems": []}


def check(name, ok, detail=""):
    rep["checks"][name] = dict(ok=bool(ok), detail=detail)
    if not ok:
        rep["problems"].append(f"{name}: {detail}")


man = pd.read_csv(P425 / "cleanup_manifest_files_AB.csv")
inv = pd.read_csv(P425 / "inventory.csv").set_index("path")
sur = pd.read_csv(P425 / "sqlite_survey.csv").set_index("path")
check("manifest_has_1960_files", len(man) == 1960 and man.path.is_unique, f"{len(man)} rows, unique={man.path.is_unique}")
check("manifest_total_is_15.10_GB", abs(man.bytes.sum() / 1e9 - 15.098) < 0.01, f"{man.bytes.sum() / 1e9:.3f} GB")

# every candidate exists, size equals the recorded size, modification time equals the audited one, sqlite identity (sha256) equals the survey
missing, size_mismatch, mtime_changed, hash_mismatch = [], [], [], []
for r in man.itertuples():
    f = ROOT / r.path
    if not f.is_file():
        missing.append(r.path)
        continue
    st = f.stat()
    if st.st_size != r.bytes:
        size_mismatch.append((r.path, st.st_size, r.bytes))
    if r.path in inv.index and int(st.st_mtime) != int(inv.loc[r.path, "mtime"]):
        mtime_changed.append(r.path)
check("all_candidates_exist", not missing, f"{len(missing)} missing {missing[:3]}")
check("sizes_match_the_audit", not size_mismatch, f"{len(size_mismatch)} differ {size_mismatch[:3]}")
check("modification_times_match_the_audit", not mtime_changed, f"{len(mtime_changed)} changed {mtime_changed[:3]}")
sq = man[man.path.str.endswith(".sqlite")]
for r in sq.itertuples():
    h = hashlib.sha256()
    with open(ROOT / r.path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 23), b""):
            h.update(c)
    if r.path in sur.index and h.hexdigest() != sur.loc[r.path, "sha256"]:
        hash_mismatch.append(r.path)
    elif r.path not in sur.index:
        hash_mismatch.append(r.path + " (not in survey)")
check("sqlite_identity_matches_the_survey", not hash_mismatch, f"{len(sq)} database files hashed, {len(hash_mismatch)} differ")

# protected paths and prefixes: none may be in the manifest
PROTECT_EXACT = {"data/footiq.sqlite", "data/footiq.sqlite-wal", "data/footiq.sqlite-shm", "data/supervised/footiq.before-sync.sqlite", "data/supervised/footiq.before-sync.sqlite-wal", "data/supervised/footiq.before-sync.sqlite-shm",
                 "data/supervised/hashes_before.json"}
PROTECT_PREFIX = ("data/backups/p424_pre_reconcile_20261028/", "data/backups/p418_rollback_20261028/", "data/backups/p420_code_before/", "data/supervised/phase3/", "data/supervised/rules_research/", "data/supervised/phase4/baselines/",
                  "data/model_artifacts/", "data/snapshots/", "data/miniproject/", "config/", "app/", "tests/", "scripts/", "frontend/src/", "frontend/tests/", "docs/", ".git/", "FootIQ_", "data/raw/", "data/processed/",
                  "data/supervised/phase4/p417/", "data/supervised/phase4/p420/", "data/supervised/phase4/p421/staging", "data/supervised/phase4/p423/staging", "data/supervised/phase4/p423/evidence", "data/supervised/phase4/p424/", "data/supervised/phase4/p425/", "data/supervised/phase4/p426/")
hit = [p for p in man.path if p in PROTECT_EXACT or p.startswith(PROTECT_PREFIX)]
check("no_protected_path_in_the_manifest", not hit, f"{hit[:5]}")
# only allowed file types: sqlite (+ wal/shm) in the B items, and the A item files
ext_bad = [p for p in man.path if not (p.endswith((".sqlite", ".sqlite-wal", ".sqlite-shm")) or p.startswith(("data/supervised/phase4/p44/pytest_baseline/", "data/supervised/pytest_tmp/pytest-of-DELL/", ".pytest_cache/"))
                                        or re.match(r"data/supervised/phase4/(p44/chrome-profile|p44/chrome-profile-p45|p46/chrome-profile-p46|p44/production-build)", p))]
check("manifest_contains_only_approved_kinds", not ext_bad, f"{len(ext_bad)} {ext_bad[:3]}")
# dependency recheck: no candidate is opened by the application (runtime footprint), imported, or named in code / tests / config
fp = set(pd.read_csv(P425 / "runtime_footprint.csv", encoding="utf-8-sig").path)
check("none_is_opened_by_the_application", not (set(man.path) & fp), f"{len(set(man.path) & fp)} overlap")
names = ["pytest_baseline", "chrome-profile", "production-build", "live_test_copy", "demo.sqlite", "preview.sqlite", "tests.sqlite", "footiq.20261027", "pre_import_20261028", "p422_after_domestic", "rehearsal/"]
refs = {}
for pat in names:
    hits = []
    for base in ("app", "scripts", "config", "tests", "frontend/src", ".claude", "pytest.ini"):
        b = ROOT / base
        files = [b] if b.is_file() else [x for x in b.rglob("*") if x.is_file() and x.suffix in (".py", ".js", ".jsx", ".json", ".ini", ".ps1")] if b.exists() else []
        for x in files:
            try:
                if pat in x.read_text(encoding="utf-8", errors="ignore"):
                    hits.append(x.relative_to(ROOT).as_posix())
            except OSError:
                pass
    refs[pat] = hits
# references that are not just offline scripts writing their own outputs:
runtime_refs = {k: v for k, v in refs.items() if any(h.startswith(("tests/", "app/main", "app/predict", "app/analytics", "app/config", "app/store/sync", "app/store/db", "app/store/views", "app/matches", "app/featured", "app/forecast", "app/seasonsim", "config/")) for h in v)}
rep["code_references"] = refs
check("no_runtime_test_or_config_reference", not runtime_refs, f"{ {k: v[:3] for k, v in runtime_refs.items()} }")
# the test fixtures and importer inputs that must stay are not in the manifest
must = ["data/supervised/phase3/m2_matches.pkl", "data/supervised/phase4/p417/staging/martj42/evidence.json", "data/supervised/phase4/p420/staging/staged_results_EPL.csv", "data/supervised/phase4/p423/staging/proposed_changes.csv", "data/supervised/phase4/p423/evidence.py"]
check("test_and_importer_inputs_exist_and_are_outside_the_manifest", all((ROOT / m).exists() and m not in set(man.path) for m in must), "ok")

# production database and rollback backup: hash and integrity; simulations; frozen hashes
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 23), b""):
            h.update(c)
    return h.hexdigest()


prod = ROOT / "data" / "footiq.sqlite"
rep["production_sha256"] = sha(prod)
c = sqlite3.connect(f"file:{prod.as_posix()}?mode=ro", uri=True)
check("production_integrity_ok", c.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and not c.execute("PRAGMA foreign_key_check").fetchall())
sims = hashlib.sha256(json.dumps([tuple(x) for x in c.execute("SELECT * FROM simulation_runs ORDER BY simulation_run_id")], default=str).encode()).hexdigest()
rep["simulations"] = dict(rows=[tuple(x) for x in c.execute("SELECT simulation_run_id, competition_key, n_simulations FROM simulation_runs")], sha=sims)
check("two_saved_simulations_unchanged", len(rep["simulations"]["rows"]) == 2 and sims == "33fbf4afae52d531639daff2ce57c68cd4e73908c4b802db425f2baa8cb99c01", sims[:12])
c.close()
bk = ROOT / "data" / "backups" / "p424_pre_reconcile_20261028" / "footiq.sqlite"
rep["backup_sha256"] = sha(bk)
check("rollback_backup_hash_matches_its_note", rep["backup_sha256"] == (bk.parent / "SHA256.txt").read_text().strip() and rep["backup_sha256"].startswith("afe71c44"), rep["backup_sha256"][:12])
c = sqlite3.connect(f"file:{bk.as_posix()}?mode=ro&immutable=1", uri=True)
check("rollback_backup_integrity_ok", c.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "")
c.close()
check("before_sync_baseline_exists", (ROOT / "data/supervised/footiq.before-sync.sqlite").is_file())
check("code_rollback_snapshots_exist", (ROOT / "data/backups/p418_rollback_20261028/files").is_dir() and (ROOT / "data/backups/p420_code_before").is_dir())
(HERE / "preflight_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v["ok"] for k, v in rep["checks"].items()}, indent=1))
print("PROBLEMS:", rep["problems"])
sys.exit(1 if rep["problems"] else 0)
