"""Phase 4.26: the files skipped with 'Access is denied' in stage A carry the Windows read-only attribute (the snapshot store writes its evidence files read-only). They are in the approved manifest: clear the attribute on exactly
those files and delete them. Same checks as cleanup.py (in the manifest, not protected, audited size)."""
import csv
import os
import stat
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
man = set(pd.read_csv(ROOT / "data/supervised/phase4/p425/cleanup_manifest_files_AB.csv").path)
sizes = dict(pd.read_csv(ROOT / "data/supervised/phase4/p425/cleanup_manifest_files_AB.csv").values)
log = pd.read_csv(HERE / "deletion_log.csv")
done = set(log[log.status.str.startswith("deleted")].path)
todo = log[log.status.str.startswith("SKIPPED PermissionError") & ~log.path.isin(done)]
lp = lambda p: str(p)
n = b = 0
rows = []
for r in todo.drop_duplicates("path").itertuples():
    assert r.path in man and r.item in ("A1", "A2"), r.path
    f = ROOT / r.path
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not os.path.isfile(lp(f)) or os.path.getsize(lp(f)) != sizes[r.path]:
        rows.append([ts, "A", r.item, r.path, r.bytes, "", "SKIPPED missing or size changed on retry"]); continue
    try:
        os.chmod(lp(f), stat.S_IWRITE)
        os.remove(lp(f))
    except OSError as e:
        rows.append([ts, "A", r.item, r.path, r.bytes, "", f"SKIPPED {type(e).__name__} on retry"]); continue
    rows.append([ts, "A", r.item, r.path, r.bytes, "", "deleted (after clearing the read-only attribute)"]); n += 1; b += r.bytes
with open(HERE / "deletion_log.csv", "a", newline="", encoding="utf-8") as fh:
    csv.writer(fh).writerows(rows)
print(f"retry: deleted {n} of {len(todo.drop_duplicates('path'))} files, {b / 1e6:.2f} MB; still skipped: {sum(1 for r in rows if r[-1].startswith('SKIPPED'))}")
