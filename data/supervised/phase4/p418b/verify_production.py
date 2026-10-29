"""Phase 4.18B: READ-ONLY verification of the production database and the frozen ML artifacts. The database is opened with mode=ro; nothing is written."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
DB = ROOT / "data" / "footiq.sqlite"
out = {}
files = {p.name: p.stat().st_size for p in DB.parent.glob("footiq.sqlite*")}
out["db_files"] = files
out["db_sha256_before"] = hashlib.sha256(DB.read_bytes()).hexdigest()
c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
c.row_factory = sqlite3.Row
out["integrity_check"] = c.execute("PRAGMA integrity_check").fetchone()[0]
out["foreign_key_problems"] = len(c.execute("PRAGMA foreign_key_check").fetchall())
out["journal_mode"] = c.execute("PRAGMA journal_mode").fetchone()[0]
out["schema_version"] = c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
out["table_rows"] = {t: c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tabs}
sims = [dict(r) for r in c.execute("SELECT simulation_run_id, created_utc, competition_key, season, n_simulations FROM simulation_runs ORDER BY simulation_run_id")]
out["saved_simulations"] = sims
out["saved_simulations_content_sha256"] = hashlib.sha256(json.dumps([tuple(r) for r in c.execute("SELECT * FROM simulation_runs ORDER BY simulation_run_id")], default=str).encode()).hexdigest()
out["forecasts"] = [c.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0], c.execute("SELECT COUNT(*) FROM forecast_runs").fetchone()[0]]
out["matches_by_competition_2026_27"] = {r[0]: r[1] for r in c.execute("SELECT competition_key, COUNT(*) FROM matches WHERE season='2026-27' GROUP BY 1")}
out["archived_rows_still_stored"] = {r[0]: r[1] for r in c.execute("SELECT competition_key, COUNT(*) FROM matches WHERE competition_key IN ('WC','UEL','UECL','UNL','COPA') GROUP BY 1")}
out["last_sync_runs"] = [tuple(r) for r in c.execute("SELECT run_id, kind, competition_key, outcome, started_utc FROM sync_runs ORDER BY run_id DESC LIMIT 5")]
out["quarantine_rows"] = c.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
c.close()
out["db_sha256_after"] = hashlib.sha256(DB.read_bytes()).hexdigest()
out["db_file_unchanged_by_this_check"] = out["db_sha256_before"] == out["db_sha256_after"]
# frozen ML artifacts: integrity module + the hashes recorded at the start of Phase 4
import integrity  # noqa: E402
integrity.check.cache_clear()
res = integrity.check()
out["integrity_module"] = {k: (v.get("ok") if isinstance(v, dict) else v) for k, v in res.items()}
rec = json.loads((ROOT / "data" / "supervised" / "hashes_before.json").read_text(encoding="utf-8"))
out["recorded_hashes_vs_now"] = {k: (hashlib.sha256((ROOT / k).read_bytes()).hexdigest() == v) for k, v in rec.items() if (ROOT / k).exists() and not k.endswith("sync.json")}
out["recorded_hash_missing_files"] = [k for k in rec if not (ROOT / k).exists()]
v27 = ROOT / "data" / "model_artifacts" / "v27" / "live_match_model.pkl"
out["archived_international_artifact"] = dict(exists=v27.exists(), sha256=hashlib.sha256(v27.read_bytes()).hexdigest() if v27.exists() else None)
(Path(__file__).resolve().parent / "production_verification.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("table_rows",)}, indent=1, default=str)[:5000])
print("tables:", {k: v for k, v in out["table_rows"].items() if v})
