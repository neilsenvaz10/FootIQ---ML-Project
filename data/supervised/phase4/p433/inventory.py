"""Phase 4.33: read-only inventory of the whole project. Writes inventory.csv (path, bytes, mtime, ext, top, tracked-by-git flag) and duplicates.csv (identical files by sha256).
Hashes only files >= 1 KB that share their size with another file. node_modules, .venv and .git internals are counted but not listed per file."""
import csv
import hashlib
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OPAQUE = {".venv", "node_modules", ".git"}
rows, opaque = [], defaultdict(lambda: [0, 0])
tracked = set(subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True).stdout.decode("utf-8", "replace").split("\0"))
for dp, dn, fn in os.walk(ROOT):
    rel = Path(dp).relative_to(ROOT)
    parts = rel.parts
    if parts and parts[0] in OPAQUE or (len(parts) >= 2 and parts[1] in {"node_modules"}):
        key = parts[0] if parts[0] in OPAQUE else "/".join(parts[:2])
        for f in fn:
            try:
                opaque[key][0] += 1
                opaque[key][1] += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
        dn[:] = []
        continue
    for f in fn:
        p = Path(dp) / f
        try:
            st = p.stat()
        except OSError:
            continue
        r = p.relative_to(ROOT).as_posix()
        rows.append((r, st.st_size, time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)), p.suffix.lower(), parts[0] if parts else "", int(r in tracked)))
with open(HERE / "inventory.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["path", "bytes", "mtime", "ext", "top", "git_tracked"])
    w.writerows(rows)
by_size = defaultdict(list)
for r in rows:
    if r[1] >= 1024:
        by_size[r[1]].append(r[0])
dups = []
for size, paths in by_size.items():
    if len(paths) < 2:
        continue
    groups = defaultdict(list)
    for p in paths:
        h = hashlib.sha256()
        with open(ROOT / p, "rb") as fh:
            for c in iter(lambda: fh.read(1 << 22), b""):
                h.update(c)
        groups[h.hexdigest()].append(p)
    for h, ps in groups.items():
        if len(ps) > 1:
            dups.append((h, size, ps))
with open(HERE / "duplicates.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["sha256", "bytes", "copies", "wasted_bytes", "paths"])
    for h, s, ps in sorted(dups, key=lambda d: -(d[1] * (len(d[2]) - 1))):
        w.writerow([h, s, len(ps), s * (len(ps) - 1), " | ".join(ps)])
tot = sum(r[1] for r in rows)
print(f"listed files {len(rows)}  {tot / 1e9:.3f} GB")
for k, (n, b) in sorted(opaque.items(), key=lambda x: -x[1][1]):
    print(f"opaque {k}: {n} files {b / 1e6:.1f} MB")
print(f"duplicate groups {len(dups)}  wasted {sum(d[1] * (len(d[2]) - 1) for d in dups) / 1e6:.1f} MB")
