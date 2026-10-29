"""Phase 4.26: deletes EXACTLY the files of the approved manifest (data/supervised/phase4/p425/cleanup_manifest_files_AB.csv), one stage at a time: `cleanup.py A` or `cleanup.py B1|B2|B3|B4`.
Never recursive: each file is removed individually, only if it is in the manifest, not protected, and still has its audited size. Empty directories are left in place. Every file is logged to deletion_log.csv
(timestamp, stage, item, path, bytes, sha256 for databases from the audit survey, status)."""
import csv
import os
import re
import shutil
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
P425 = ROOT / "data" / "supervised" / "phase4" / "p425"
LOG = HERE / "deletion_log.csv"
man = pd.read_csv(P425 / "cleanup_manifest_files_AB.csv")
sur = pd.read_csv(P425 / "sqlite_survey.csv").set_index("path")
SQL = r"\.sqlite(-wal|-shm)?$"
ITEMS = [  # (item, regex over the path)  -- the same sets as cleanup_manifest.csv (build_manifest.py)
    ("A5", r"^\.pytest_cache/"),
    ("A4", r"^data/supervised/phase4/p44/production-build(-final|-release)?/"),
    ("A2", r"^data/supervised/pytest_tmp/pytest-of-DELL/"),
    ("A3", r"^data/supervised/phase4/(p44/chrome-profile(-p45)?|p46/chrome-profile-p46)/"),
    ("A1", r"^data/supervised/phase4/p44/pytest_baseline/"),
    ("B2", r"^data/supervised/phase4/p4(19|21|23)/rehearsal/.*" + SQL),
    ("B4t", r"^data/supervised/phase4/p4[456]/tests" + SQL),
    ("B5r", r"^data/supervised/(rehearsal/footiq\.(before|rehearsal|rehearsal_repeat)|live_test_copy)" + SQL),
    ("B3", r"^data/supervised/phase4/(p410/private_copy|p412/private_copy|p49/private_copy|p49/restore_test|p48d/restore_test_activation)" + SQL),
    ("B4p", r"^data/supervised/phase4/p4[456]/preview" + SQL),
    ("B5d", r"^data/supervised/demo" + SQL),
    ("B5i", r"^data/supervised/production_import/footiq\.\d+T\d+Z\.backup" + SQL),
    ("B1", r"^data/backups/(footiq\.2026\d+T\d+Z\.[a-z\-]+\.sqlite|p42[012]_[a-z_0-9]+/footiq\.sqlite)(-wal|-shm)?$"),
]
STAGES = {"A": ["A5", "A4", "A2", "A3", "A1"], "B1": ["B2", "B4t", "B5r"], "B2": ["B3", "B4p", "B5d"], "B3": ["B5i"], "B4": ["B1"]}
PROTECT_EXACT = {"data/footiq.sqlite", "data/footiq.sqlite-wal", "data/footiq.sqlite-shm", "data/supervised/footiq.before-sync.sqlite", "data/supervised/footiq.before-sync.sqlite-wal", "data/supervised/footiq.before-sync.sqlite-shm"}
PROTECT_PREFIX = ("data/backups/p424_pre_reconcile_20261028/", "data/backups/p418_rollback_20261028/", "data/backups/p420_code_before/", "data/supervised/phase3/", "data/supervised/rules_research/", "data/snapshots/", "FootIQ_", "app/", "tests/", "config/", "docs/", ".git/")


def lp(p: Path) -> str:
    return "\\\\?\\" + str(p.resolve()) if os.name == "nt" else str(p)


def classify(path):
    hits = [i for i, rx in ITEMS if re.search(rx, path)]
    return hits[0] if len(hits) == 1 else None


# every manifest path belongs to exactly one item
unclassified = [p for p in man.path if classify(p) is None]
if unclassified:
    sys.exit(f"STOP: {len(unclassified)} manifest paths do not belong to exactly one approved item: {unclassified[:3]}")
man["item"] = man.path.map(classify)
stage = sys.argv[1]
if stage not in STAGES:
    sys.exit("stage must be one of " + ", ".join(STAGES))
if stage == "B4":                                                                        # before the older backups: re-verify the retained rollback backup
    import hashlib
    h = hashlib.sha256()
    with open(ROOT / "data/backups/p424_pre_reconcile_20261028/footiq.sqlite", "rb") as fh:
        for c in iter(lambda: fh.read(1 << 23), b""):
            h.update(c)
    if h.hexdigest() != (ROOT / "data/backups/p424_pre_reconcile_20261028/SHA256.txt").read_text().strip():
        sys.exit("STOP: the retained rollback backup no longer matches its recorded hash")
    print("retained rollback backup re-verified:", h.hexdigest()[:16])
free0 = shutil.disk_usage(ROOT).free
new = not LOG.exists()
tot_files = tot_bytes = 0
skipped = []
with open(LOG, "a", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    if new:
        w.writerow(["timestamp_utc", "stage", "item", "path", "bytes", "sha256_from_audit", "status"])
    for item in STAGES[stage]:
        sel = man[man.item == item]
        sub_files = sub_bytes = 0
        # small files first inside an item, large ones last
        for r in sel.sort_values("bytes").itertuples():
            f = ROOT / r.path
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            sha = sur.loc[r.path, "sha256"] if r.path in sur.index else ""
            if r.path in PROTECT_EXACT or r.path.startswith(PROTECT_PREFIX):
                skipped.append((r.path, "protected")); w.writerow([ts, stage, item, r.path, r.bytes, sha, "SKIPPED protected"]); continue
            if not os.path.isfile(lp(f)):
                skipped.append((r.path, "missing")); w.writerow([ts, stage, item, r.path, r.bytes, sha, "SKIPPED missing"]); continue
            if os.path.getsize(lp(f)) != r.bytes:
                skipped.append((r.path, "size changed")); w.writerow([ts, stage, item, r.path, r.bytes, sha, "SKIPPED size changed"]); continue
            try:
                os.remove(lp(f))
            except OSError as e:
                skipped.append((r.path, f"{type(e).__name__}: {e}")); w.writerow([ts, stage, item, r.path, r.bytes, sha, f"SKIPPED {type(e).__name__}"]); continue
            w.writerow([ts, stage, item, r.path, r.bytes, sha, "deleted"])
            sub_files += 1
            sub_bytes += r.bytes
        fh.flush()
        print(f"  {item}: deleted {sub_files} of {len(sel)} files, {sub_bytes / 1e9:.3f} GB")
        tot_files += sub_files
        tot_bytes += sub_bytes
free1 = shutil.disk_usage(ROOT).free
print(f"STAGE {stage}: deleted {tot_files} files, {tot_bytes / 1e9:.3f} GB (free space +{(free1 - free0) / 1e9:.3f} GB); skipped {len(skipped)}")
for s in skipped[:20]:
    print("  skipped:", s)
