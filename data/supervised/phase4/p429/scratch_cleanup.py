"""Phase 4.29 part D: removes ONLY the contents of data/supervised/pytest_tmp/p428 (approved test scratch of the Phase 4.28 full test run). Usage: scratch_cleanup.py preflight | delete.
Safety: every path is resolved and must lie strictly inside the directory; links are never followed (a link is only unlinked, never entered); regular files are removed one by one and logged;
the directory itself is kept (empty). Nothing outside it is touched."""
import csv
import os
import stat
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TARGET = ROOT / "data" / "supervised" / "pytest_tmp" / "p428"
LOG = HERE / "scratch_deletion_log.csv"
mode = sys.argv[1]
real_root = os.path.realpath(TARGET)
if os.path.realpath(ROOT / "data" / "supervised" / "pytest_tmp") + os.sep + "p428" != real_root:
    sys.exit("STOP: the target does not resolve to data/supervised/pytest_tmp/p428")


def inside(p):
    r = os.path.realpath(p)
    return r.startswith(real_root + os.sep)


def is_link(p):
    return os.path.islink(p) or (hasattr(os.path, "isjunction") and os.path.isjunction(p))


files, links, dirs = [], [], []
for dp, dn, fn in os.walk(TARGET, topdown=True, followlinks=False):
    keep = []
    for d in dn:
        q = os.path.join(dp, d)
        if is_link(q):
            links.append(q)
        else:
            dirs.append(q)
            keep.append(d)
    dn[:] = keep
    for f in fn:
        q = os.path.join(dp, f)
        (links if is_link(q) else files).append(q)
bad = [f for f in files if not inside(f)] + [l for l in links if not os.path.realpath(os.path.dirname(l)).startswith(real_root)]
total = sum(os.path.getsize(f) for f in files)
print(f"regular files {len(files)}, {total} bytes ({total / 1e9:.3f} GB); links {len(links)}; directories {len(dirs)}; outside the target: {len(bad)}")
if mode == "preflight":
    sys.exit(1 if bad else 0)
if bad:
    sys.exit("STOP: some paths are not strictly inside the target")
n = b = 0
with open(LOG, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["timestamp_utc", "kind", "path", "bytes", "status"])
    for f in files:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        size = os.path.getsize(f)
        try:
            try:
                os.remove(f)
            except PermissionError:
                os.chmod(f, stat.S_IWRITE)
                os.remove(f)
            w.writerow([ts, "file", os.path.relpath(f, ROOT), size, "deleted"])
            n += 1
            b += size
        except OSError as e:
            w.writerow([ts, "file", os.path.relpath(f, ROOT), size, f"SKIPPED {type(e).__name__}"])
    for l in links:                                                                    # a link is removed itself; its target is never entered
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            os.unlink(l)
            w.writerow([ts, "link", os.path.relpath(l, ROOT), 0, "unlinked"])
        except OSError:
            try:
                os.rmdir(l)
                w.writerow([ts, "link", os.path.relpath(l, ROOT), 0, "unlinked"])
            except OSError as e:
                w.writerow([ts, "link", os.path.relpath(l, ROOT), 0, f"SKIPPED {type(e).__name__}"])
    removed = 0
    for d in sorted(dirs, key=len, reverse=True):
        try:
            os.rmdir(d)
            removed += 1
        except OSError:
            pass
print(f"deleted {n} of {len(files)} files, {b} bytes ({b / 1e9:.3f} GB); empty directories removed {removed}")
