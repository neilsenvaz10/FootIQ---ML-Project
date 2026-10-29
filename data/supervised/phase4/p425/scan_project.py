"""Phase 4.25: READ-ONLY inventory of the whole FootIQ project directory. Walks every file once (no hashing here), writes inventory.csv (path, bytes, mtime) next to this script and prints totals.
Nothing is moved, changed or deleted."""
import csv
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "inventory.csv"
t0 = time.time()
rows = 0
total = 0
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["path", "bytes", "mtime"])
    stack = [str(ROOT)]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            st = e.stat(follow_symlinks=False)
                            if Path(e.path).resolve() == OUT.resolve():
                                continue
                            w.writerow([os.path.relpath(e.path, ROOT).replace("\\", "/"), st.st_size, int(st.st_mtime)])
                            rows += 1
                            total += st.st_size
                    except OSError as ex:
                        print("skip", e.path, ex, file=sys.stderr)
        except OSError as ex:
            print("skip dir", d, ex, file=sys.stderr)
print(f"{rows} files, {total / 1e9:.2f} GB, {time.time() - t0:.0f}s")
