"""Phase 4.20 part B: ONE read-only GET per URL below into PRIVATE staging (data/supervised/phase4/p420/staging/raw/). No retry, no other URL, 1.5 s between requests, a User-Agent that names the project.
Nothing is imported anywhere. Each response is hashed and described in evidence.json. A file that already exists is never fetched again.

  openfootball (CC0-1.0, GitHub raw)    current 2026-27 fixture/result files of the five domestic leagues: PRIMARY source for staging
  football-data.co.uk                   free CSV result/fixture files: used ONLY to cross-check scores and dates (no explicit licence is published, so it is never stored in the app)
  Wikipedia (MediaWiki API, CC BY-SA)   current revision of the Champions League league-phase page (same page the existing staging came from)
No account, token or API key is used anywhere.
"""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "staging" / "raw"
UA = "FootIQ-college-project/1.0 (single read-only downloads for a student data-engineering project)"
OF = "https://raw.githubusercontent.com/openfootball/{repo}/master/{path}"
FD = "https://www.football-data.co.uk/{path}"
WIKI_TITLE = "2026–27 UEFA Champions League league phase"
WIKI = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", prop="revisions", rvprop="ids|timestamp|content", rvslots="main", format="json", formatversion="2", titles=WIKI_TITLE))
SOURCES = [
    ("openfootball_EPL.txt", OF.format(repo="england", path="2026-27/1-premierleague.txt"), "openfootball", "CC0-1.0"),
    ("openfootball_SERIEA.txt", OF.format(repo="italy", path="2026-27/1-seriea.txt"), "openfootball", "CC0-1.0"),
    ("openfootball_LIGUE1.txt", OF.format(repo="europe", path="france/2026-27_fr1.txt"), "openfootball", "CC0-1.0"),
    ("openfootball_BUNDESLIGA.txt", OF.format(repo="deutschland", path="2026-27/1-bundesliga.txt"), "openfootball", "CC0-1.0"),
    ("openfootball_LALIGA.txt", OF.format(repo="espana", path="2026-27/1-liga.txt"), "openfootball", "CC0-1.0"),
    ("footballdatauk_EPL.csv", FD.format(path="mmz4281/2627/E0.csv"), "football-data.co.uk", "no explicit licence: cross-check only"),
    ("footballdatauk_SERIEA.csv", FD.format(path="mmz4281/2627/I1.csv"), "football-data.co.uk", "no explicit licence: cross-check only"),
    ("footballdatauk_LIGUE1.csv", FD.format(path="mmz4281/2627/F1.csv"), "football-data.co.uk", "no explicit licence: cross-check only"),
    ("footballdatauk_BUNDESLIGA.csv", FD.format(path="mmz4281/2627/D1.csv"), "football-data.co.uk", "no explicit licence: cross-check only"),
    ("footballdatauk_LALIGA.csv", FD.format(path="mmz4281/2627/SP1.csv"), "football-data.co.uk", "no explicit licence: cross-check only"),
    ("footballdatauk_fixtures.csv", FD.format(path="fixtures.csv"), "football-data.co.uk", "no explicit licence: cross-check only"),
    ("wikipedia_ucl_league_phase_api.json", WIKI, "wikipedia", "CC BY-SA 4.0"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    evp = RAW / "evidence.json"
    ev = json.loads(evp.read_text(encoding="utf-8")) if evp.exists() else {}
    for name, url, source, licence in SOURCES:
        if (RAW / name).exists():
            print("skip (already downloaded):", name)
            continue
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                info = dict(status=r.status, final_url=r.geturl(), headers={k: v for k, v in r.headers.items() if k.lower() in ("content-type", "content-length", "etag", "last-modified", "date")})
        except Exception as e:                                                              # recorded, not retried
            ev[name] = dict(url=url, source=source, licence=licence, retrieved_utc=started, error=f"{type(e).__name__}: {e}")
            print("FAILED", name, e)
            evp.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
            time.sleep(1.5)
            continue
        (RAW / name).write_bytes(body)
        ev[name] = dict(url=url, source=source, licence=licence, retrieved_utc=started, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), **info)
        print("ok", name, len(body), info["status"])
        evp.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
        time.sleep(1.5)


if __name__ == "__main__":
    main()
