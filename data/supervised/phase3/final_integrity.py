"""Final integrity checks of a stage (read-only): frozen model and data hashes, the protected-file manifest, the production database, sync settings and the git index."""
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))
out = {}

before = json.loads((ROOT / "data" / "supervised" / "hashes_before.json").read_text(encoding="utf-8"))
changed = [k for k, v in before.items() if hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != v]
out["frozen_files_in_hashes_before_json"] = dict(count=len(before), changed=changed)

from store import rehearse_openligadb as R  # noqa: E402

saved = json.loads((ROOT / "data" / "supervised" / "phase3" / "final_manifest.json").read_text(encoding="utf-8"))
now = R.manifest()
out["protected_manifest"] = dict(files=len(now), identical_to_the_one_taken_at_the_start_of_this_stage=(saved == now), differences=[k for k in set(saved) | set(now) if saved.get(k) != now.get(k)])

prod = ROOT / "data" / "footiq.sqlite"
rec = (ROOT / "data" / "supervised" / "production_import" / "prod_sha_after_import.txt").read_text(encoding="utf-8").split()[0]
out["production_database"] = dict(sha256_matches_post_import_record=hashlib.sha256(prod.read_bytes()).hexdigest() == rec)
c = sqlite3.connect(f"file:{prod.as_posix()}?mode=ro", uri=True)
out["production_database"].update(integrity_check=c.execute("pragma integrity_check").fetchone()[0], simulation_runs=c.execute("select count(*) from simulation_runs").fetchone()[0])
c.close()

sync = json.loads((ROOT / "config" / "sync.json").read_text(encoding="utf-8"))
sim = json.loads((ROOT / "config" / "season_sim.json").read_text(encoding="utf-8"))
out["settings"] = dict(live_enabled=sync.get("live_enabled"), scoreline_method=sim.get("scoreline_method"), scoreline_validation_status=sim["scoreline_validation"]["status"], position_bounds_enabled=sim["points_only"]["position_bounds"]["enabled"])

git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
out["git"] = dict(staged_files=[x for x in git("diff", "--cached", "--name-only").splitlines() if x], head=git("log", "--oneline", "-1"), branch=git("branch", "--show-current"))
prospective = [k for k in now if "prospective" in k]
out["prospective_evaluation_files_in_manifest"] = len(prospective)
print(json.dumps(out, indent=1))
