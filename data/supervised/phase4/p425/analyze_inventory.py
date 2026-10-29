"""Phase 4.25: READ-ONLY analysis of inventory.csv: folder sizes, largest files, duplicates (size + sha256 of same-size large files), temp / rehearsal / staging classification. Writes summary files here only."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
df = pd.read_csv(HERE / "inventory.csv")
df["top"] = df.path.str.split("/").str[0]
GB = 1e9
tot = df.bytes.sum()
print(f"TOTAL {tot / GB:.2f} GB, {len(df)} files")
top = df.groupby("top").bytes.agg(["sum", "count"]).sort_values("sum", ascending=False)
print("\nTOP-LEVEL")
for k, r in top.head(25).iterrows():
    print(f"  {r['sum'] / GB:8.3f} GB  {int(r['count']):6d} files  {k}")


def level(prefix, depth, n=25):
    d = df[df.path.str.startswith(prefix)].copy()
    d["k"] = d.path.map(lambda p: "/".join(p.split("/")[:depth]))
    g = d.groupby("k").bytes.agg(["sum", "count"]).sort_values("sum", ascending=False)
    print(f"\n{prefix}* (depth {depth})")
    for k, r in g.head(n).iterrows():
        print(f"  {r['sum'] / GB:8.3f} GB  {int(r['count']):6d}  {k}")
    return g


level("data/", 2, 12)
level("data/supervised/", 3, 25)
level("data/supervised/phase4/", 4, 30)
level("data/backups/", 3, 40)
for p in ("FootIQ_", ".venv", "frontend/", "node_modules", ".git/", "logs/", "docs/", "app/", "tests/", "scripts/"):
    d = df[df.path.str.startswith(p)]
    if len(d):
        print(f"\n{p:14s} {d.bytes.sum() / GB:8.3f} GB  {len(d)} files")
print("\nTOP-LEVEL ENTRIES 2nd level for FootIQ_*")
for pre in sorted({p.split("/")[0] for p in df.path if p.startswith("FootIQ_")}):
    level(pre + "/", 2, 8)

print("\nTOP 40 FILES")
big = df.sort_values("bytes", ascending=False).head(40)
for r in big.itertuples():
    print(f"  {r.bytes / 1e6:10.1f} MB  {r.path}")
big.to_csv(HERE / "top40_files.csv", index=False)

# duplicates among files >= 1 MB: same size, then sha256
cands = df[df.bytes >= 1_000_000].copy()
by_size = cands.groupby("bytes").path.apply(list)
dups = []
for size, paths in by_size.items():
    if len(paths) < 2:
        continue
    groups = defaultdict(list)
    for p in paths:
        h = hashlib.sha256()
        with open(ROOT / p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        groups[h.hexdigest()].append(p)
    for h, ps in groups.items():
        if len(ps) > 1:
            dups.append(dict(sha256=h, bytes=size, copies=len(ps), wasted=size * (len(ps) - 1), paths=ps))
dups.sort(key=lambda d: -d["wasted"])
(HERE / "duplicates_over_1MB.json").write_text(json.dumps(dups, indent=1), encoding="utf-8")
print(f"\nBYTE-IDENTICAL DUPLICATE GROUPS (>=1 MB): {len(dups)}, wasted {sum(d['wasted'] for d in dups) / GB:.2f} GB")
for d in dups[:25]:
    print(f"  {d['wasted'] / 1e6:9.1f} MB wasted, {d['copies']} copies of {d['bytes'] / 1e6:.1f} MB: {d['paths'][0]}  (+{len(d['paths']) - 1} more: {d['paths'][1][:90]})")
# extensions
df["ext"] = df.path.str.extract(r"(\.[A-Za-z0-9]+)$")[0].str.lower().fillna("(none)")
print("\nBY EXTENSION (top 15)")
for k, r in df.groupby("ext").bytes.agg(["sum", "count"]).sort_values("sum", ascending=False).head(15).iterrows():
    print(f"  {r['sum'] / GB:8.3f} GB  {int(r['count']):6d}  {k}")
