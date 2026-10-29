"""Phase 4.33 approved cleanup: condition checks for A4 (p417 duplicates), A12 (dataset zip) and A14 (logs). Read-only. Prints the files that satisfy each condition and writes conditions.json."""
import csv
import hashlib
import json
import os
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


inv = [r for r in csv.DictReader(open(HERE / "inventory.csv", encoding="utf-8"))]
paths = [r["path"] for r in inv]
out = {}

# ---- A4: p417 private_ratings and staging/*/unpacked: every file must have a byte-identical twin OUTSIDE the deleted set
a4 = [p for p in paths if p.startswith("data/supervised/phase4/p417/private_ratings/") or ("data/supervised/phase4/p417/staging/" in p and "/unpacked/" in p)]
a4set = set(a4)
size = {r["path"]: int(r["bytes"]) for r in inv}
by_size = {}
for p in paths:
    if p not in a4set and not p.startswith(("data/supervised/pytest_tmp/", "data/backups/")) and size[p] > 0:
        by_size.setdefault(size[p], []).append(p)
ok4, keep4 = [], []
cache = {}
for p in a4:
    cands = by_size.get(size[p], [])
    if not cands:
        keep4.append((p, "no file of the same size elsewhere"))
        continue
    h = sha(ROOT / p)
    twin = None
    for c in cands:
        if c not in cache:
            cache[c] = sha(ROOT / c)
        if cache[c] == h:
            twin = c
            break
    if twin:
        ok4.append((p, size[p], h, twin))
    else:
        keep4.append((p, "same size but different content"))
out["A4_delete"] = ok4
out["A4_keep"] = keep4
print(f"A4: {len(a4)} files in the approved group; {len(ok4)} have a byte-identical twin elsewhere (deletable); {len(keep4)} have none (PRESERVED)")
for p, why in keep4[:15]:
    print("   keep:", p, "-", why)

# ---- A12: dataset zip vs unpacked folder
z = zipfile.ZipFile(ROOT / "FootIQ_Dataset_Submission.zip")
members = [i for i in z.infolist() if not i.is_dir()]
missing, differ, same = [], [], 0
for i in members:
    name = i.filename
    cand = ROOT / name
    if not cand.exists():
        cand = ROOT / "FootIQ_Dataset_Submission" / name
    if not cand.exists() and name.startswith("FootIQ_Dataset_Submission/"):
        cand = ROOT / name
    if not cand.exists():
        missing.append(name)
        continue
    h = hashlib.sha256(z.read(i)).hexdigest() if i.file_size < 150_000_000 else None
    if h is not None and sha(cand) != h:
        differ.append(name)
    else:
        same += 1
out["A12"] = dict(members=len(members), identical=same, missing=missing[:20], n_missing=len(missing), differ=differ[:20], n_differ=len(differ))
print(f"A12: zip has {len(members)} files: {same} identical in the unpacked folder, {len(missing)} missing there, {len(differ)} different")
for m in missing[:20]:
    print("   missing in folder:", m)
for m in differ[:20]:
    print("   differs:", m)

# ---- A14: logs and loose debug output: are they cited by name anywhere as evidence?
a14 = [p for p in paths if p.startswith("logs/") or (p.startswith("data/supervised/") and p.count("/") == 2 and (p.endswith(".log") or "full_backend_run" in p or p.endswith(("rehearsal_run_output.txt", "investigation_output.txt", "investigation_analysis.txt"))))]
docs = [p for p in paths if p.endswith((".md", ".py", ".json", ".txt", ".csv", ".jsx", ".js", ".ps1")) and not p.startswith(("data/supervised/phase4/p433/", "data/supervised/pytest_tmp/")) and size[p] < 3_000_000]
text = {}
for p in docs:
    try:
        text[p] = (ROOT / p).read_text(encoding="utf-8", errors="ignore").replace("\\", "/")
    except OSError:
        pass
cited = {}
for p in a14:
    name = os.path.basename(p)
    hits = [d for d, t in text.items() if name in t and d != p]
    cited[p] = hits
out["A14"] = {p: v for p, v in cited.items()}
print(f"A14: {len(a14)} files")
for p in a14:
    print(f"   {size[p]:7d} B  cited by {len(cited[p]):2d}: {p}  {(cited[p][:2] if cited[p] else '')}")
(HERE / "conditions.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
