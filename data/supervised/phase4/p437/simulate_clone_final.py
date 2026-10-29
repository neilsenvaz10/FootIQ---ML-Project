"""Phase 4.37: simulates `git clone` + `git lfs pull` of the FINAL proposed contents into a new folder outside the project (copies out/final_inclusion_manifest.csv, mapping each file to its publish_path). Usage: simulate_clone_final.py <dest>"""
import csv, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent / "out"
dest = Path(sys.argv[1]).resolve()
if ROOT in dest.parents or dest == ROOT:
    sys.exit("STOP: destination must be outside the project")
if dest.exists() and any(dest.iterdir()):
    sys.exit("STOP: destination not empty")
n = b = 0
for r in csv.DictReader(open(HERE / "final_inclusion_manifest.csv", encoding="utf-8")):
    t = dest / r["publish_path"]
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / r["path"], t)
    n += 1; b += int(r["bytes"])
print(f"copied {n} files, {b / 1e6:.1f} MB to {dest}")
