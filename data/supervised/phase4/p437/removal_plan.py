"""Phase 4.37: forward-only removal plan for restricted data. Read-only on Git (ls-files / log only); writes out/restricted_removal_plan.csv, out/git_rm_paths.txt, out/summary.json.
Categories: A API-Football data, B StatsBomb-derived data, C FIFA page copy, D provider cross-check values (football-data.co.uk / FixtureDownload / football-data.org), E media-article / unverified rows,
M mixed file (keep, sanitize rows), K keep (name mention only)."""
import csv, json, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "out"
git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
tracked = set(git("ls-files").splitlines())
hist = set(l for l in git("log", "--all", "--name-only", "--format=").splitlines() if l)
head_files = set(git("ls-tree", "-r", "--name-only", "HEAD").splitlines())
manifest = {r["path"]: r for r in csv.DictReader(open(OUT / "proposed_manifest.csv", encoding="utf-8"))}
scan = {r["path"]: r for r in csv.DictReader(open(OUT / "content_scan.csv", encoding="utf-8"))}
P435 = ROOT / "data/supervised/phase4/p435"
api19 = set(l.strip() for l in open(P435 / "tracked_api_football_tier1_19.txt", encoding="utf-8") if l.strip())
sb = set(l.strip() for l in open(P435 / "tracked_statsbomb.txt", encoding="utf-8") if l.strip())
CODE = (".py", ".md", ".txt", ".js", ".jsx", ".ps1", ".sha256", ".example", ".pdf", ".yml", ".yaml", ".toml", ".gitignore", ".gitattributes")
rows = {}


def add(path, cat, action, why):
    rows.setdefault(path, (cat, action, why))


for p in sorted(api19):
    add(p, "A", "git rm --cached", "API-Football-derived (Phase 4.35 list)")
for p in sorted(sb):
    add(p, "B", "git rm --cached", "StatsBomb Open Data files / derived (user agreement 1.2.1)")
for p in tracked:
    if p.startswith("data/raw/fifa/"):
        add(p, "C", "git rm --cached", "copy of a FIFA web page, no redistribution permission")
    if p.startswith("data/raw/statsbomb/"):
        add(p, "B", "git rm --cached", "StatsBomb Open Data")
    if p.startswith("data/snapshots/footballdata/"):
        add(p, "D", "git rm --cached", "football-data.org API responses")
# CSV headers that name a provider column (API-Football / football-data): the first content scan only searched a few markers
HDR = re.compile(r"provider_|apifootball|api_football|footballdatauk|fixturedownload", re.I)
for p, r in manifest.items():
    if r["decision"] in ("GIT", "LFS") and p.lower().endswith(".csv") and not p.startswith(("docs/", "data/evidence/", "data/supervised/phase4/p4")) and p not in rows:
        try:
            with open(ROOT / p, encoding="utf-8-sig", errors="replace") as fh:
                h = fh.readline()
        except OSError:
            continue
        if HDR.search(h):
            add(p, "A" if re.search("provider_|api", h, re.I) else "D", "git rm --cached" if p in tracked else "do not add", "CSV header names a provider column (" + HDR.search(h).group(0) + "): provider-derived rows")
for p, r in scan.items():
    if p in rows:
        continue
    low = p.lower()
    mk = r["markers"]
    if low.endswith(CODE) or p.startswith(("docs/", "scripts/", "app/", "tests/", "frontend/", "config/")) and not low.endswith((".csv", ".json")):
        continue                                                            # code / documentation: names a source, carries no data
    if p in ("data/miniproject/matches.csv", "data/miniproject/data_audit.csv"):
        add(p, "M", "replace by sanitized file", "contains 130 World Cup 2026 rows taken from an API-Football provider file (99+9) and news / FIFA pages (22+2); licence not asserted")
    elif p.startswith("data/processed/") and "api-football" in mk:
        add(p, "A", "git rm --cached" if p in tracked else "do not add", "carries API-Football provider identifiers / scores / snapshots")
    elif p.startswith("data/processed/") and ("news-article" in mk or "fifa-page" in mk):
        add(p, "E", "git rm --cached" if p in tracked else "do not add", "World Cup 2026 results compiled from news / FIFA articles, licence not asserted")
    elif p.startswith("outputs/") and "api-football" in mk and low.endswith(".json"):
        continue                                                            # run configuration naming the provider
    elif p.startswith("data/supervised/") and re.search("fixturedownload|footballdata", mk):
        add(p, "D", "git rm --cached" if p in tracked else "do not add", "carries football-data.co.uk / FixtureDownload / football-data.org values")
    elif p.startswith("data/supervised/") and "api-football" in mk and not p.endswith(("inventory.csv", "duplicates.csv", "manifest.csv", "deletion_log.csv", "cleanup_plan.csv")):
        add(p, "A", "do not add", "working report carrying API-Football fixture details")
    elif p.startswith("data/snapshots/request_ledger"):
        add(p, "D", "do not add", "football-data.org request ledger")
    elif p.startswith("FootIQ_ML_Data_Verification/12_PLAYER_STATISTICS_COVERAGE"):
        add(p, "B", "do not add", "per-competition StatsBomb coverage statistics (derived)")
# every manifest-excluded file that is TRACKED is a forward removal as well
for p, r in manifest.items():
    if p in tracked and r["decision"] == "EXCLUDE" and p not in rows:
        why = r["rule"]
        cat = "B" if "tatsbomb" in why else "A" if "API-Football" in why else "D" if "football-data" in why or "FixtureDownload" in why else "X"
        add(p, cat, "git rm --cached", why)
out = []
for p, (cat, act, why) in sorted(rows.items()):
    size = manifest.get(p, {}).get("bytes") or (ROOT / p).stat().st_size if (ROOT / p).exists() else 0
    out.append((p, cat, "tracked" if p in tracked else "untracked", "yes" if p in hist else "no", "yes" if p in head_files else "no", size, act, why))
with open(OUT / "restricted_removal_plan.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["path", "category", "git_state", "in_git_history", "in_HEAD", "bytes", "action", "reason"]); w.writerows(out)
rm = [r[0] for r in out if r[6] == "git rm --cached" and r[2] == "tracked"]
(OUT / "git_rm_paths.txt").write_text("\n".join(rm) + "\n", encoding="utf-8")
summ = {}
for r in out:
    k = f"{r[1]} {r[2]} history={r[3]}"
    summ[k] = summ.get(k, 0) + 1
summ["_commits_in_repo"] = len(git("rev-list", "--all").split())
summ["_tracked_files_to_remove_forward"] = len(rm)
json.dump(summ, open(OUT / "summary.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
