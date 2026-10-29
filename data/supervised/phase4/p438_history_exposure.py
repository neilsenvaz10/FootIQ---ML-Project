"""Phase 4.38: which files of the PUBLISHED history (origin/main, origin/feat/*) are restricted? Read-only: git ls-tree / log only. Writes p438/out/history_exposure.csv and history_exposure_summary.json."""
import csv, json, subprocess, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/supervised/phase4/p438/out"; OUT.mkdir(parents=True, exist_ok=True)
git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
excl = {r["path"]: r["reason"] for r in csv.DictReader(open(ROOT / "data/supervised/phase4/p437/out/final_exclusion_manifest.csv", encoding="utf-8"))}
plan = {r["path"]: r for r in csv.DictReader(open(ROOT / "data/supervised/phase4/p437/out/restricted_removal_plan.csv", encoding="utf-8"))}
LEGAL = ("tatsbomb", "API-Football", "football-data", "FixtureDownload", "FIFA", "copyrighted", "RSSSF", "restricted category", "replaced by the sanitized")
refs = [l for l in git("for-each-ref", "--format=%(refname)", "refs/remotes/origin").splitlines() if not l.endswith("/HEAD")]
paths = {}
for ref in refs:
    for l in git("ls-tree", "-r", "-l", ref).splitlines():
        meta, p = l.split("\t", 1)
        size = meta.split()[-1]
        paths.setdefault(p, {"size": int(size) if size.isdigit() else 0, "refs": set()})["refs"].add(ref.replace("refs/remotes/", ""))
firstc = {}
for p in paths:
    pass
rows = []
for p, d in sorted(paths.items()):
    reason = excl.get(p) or (plan[p]["reason"] if p in plan and plan[p]["category"] in "ABCEM" else None)
    if not reason or not any(k.lower() in reason.lower() for k in LEGAL):
        continue
    cat = plan[p]["category"] if p in plan else ("B" if "tatsbomb" in reason.lower() else "A" if "API-Football" in reason else "C" if "FIFA" in reason else "L")
    rows.append((p, cat, d["size"], ";".join(sorted(d["refs"])), reason))
with open(OUT / "history_exposure.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["path", "category", "bytes", "published_refs", "reason"]); w.writerows(rows)
c = collections.Counter(r[1] for r in rows); b = collections.Counter()
for r in rows: b[r[1]] += r[2]
commits = {h: git("show", "-s", "--format=%h %ad %s", "--date=short", h).strip() for h in ("edb6e0a", "c3a6fb1", "970f461")}
tot_files = len(paths)
summ = dict(refs=refs, files_in_published_trees=tot_files, restricted_files=len(rows), by_category=dict(c), bytes_by_category=dict(b), commits=commits,
            first_commit_of_categories={cat: sorted({h for r in rows if r[1] == cat for h in git("log", "--all", "--format=%h", "--diff-filter=A", "--", r[0]).split()}) for cat in sorted(c)})
json.dump(summ, open(OUT / "history_exposure_summary.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
