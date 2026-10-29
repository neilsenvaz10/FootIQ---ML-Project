"""Phase 4.37: scans the file CONTENT of every file proposed for Git/LFS (and, separately, every tracked file) for restricted-source markers. Read-only.
Writes out/content_scan.csv (path, decision, markers, bytes)."""
import csv, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "out"
MARK = {
    "api-football": rb"api-?football|apifootball|api_football|api-sports|apisports|provider_fixture_id|provider_score|provider_status",
    "statsbomb": rb"statsbomb",
    "footballdata-uk": rb"footballdatauk|football-data\.co\.uk|football_data_co_uk",
    "fixturedownload": rb"fixturedownload",
    "footballdata-org": rb"football-data\.org|football_data_org|api\.football-data",
    "fifa-page": rb"fifa\.com/",
    "news-article": rb"theguardian\.com|apnews\.com|sportsmole|lequipe|tkcgroup|theanalyst\.com|efe\.com",
}
RX = {k: re.compile(v, re.I) for k, v in MARK.items()}
manifest = list(csv.DictReader(open(OUT / "proposed_manifest.csv", encoding="utf-8")))
tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines())
rows = []
for r in manifest:
    if r["decision"] not in ("GIT", "LFS"):
        continue
    p = ROOT / r["path"]
    hits = {}
    try:
        with open(p, "rb") as fh:
            tail = b""
            while True:
                chunk = fh.read(1 << 24)
                if not chunk:
                    break
                buf = tail + chunk
                for k, rx in RX.items():
                    n = len(rx.findall(buf))
                    if n:
                        hits[k] = hits.get(k, 0) + n
                tail = buf[-200:]
    except OSError:
        continue
    if hits:
        rows.append((r["path"], r["decision"], "tracked" if r["path"] in tracked else "new", r["bytes"], ";".join(f"{k}={v}" for k, v in sorted(hits.items()))))
with open(OUT / "content_scan.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["path", "decision", "git_state", "bytes", "markers"]); w.writerows(rows)
print(len(rows), "files with markers")
