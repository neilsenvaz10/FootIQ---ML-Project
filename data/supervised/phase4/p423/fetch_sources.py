"""Phase 4.23: ONE read-only GET per URL into PRIVATE staging (data/supervised/phase4/p423/staging/raw/). No account, token or API key; no retry; >= 1.5 s between requests (>= 5.5 s for Wikipedia).
Nothing is imported anywhere. Each response is hashed and described in evidence.json. A file that already exists is never fetched again.

  Wikipedia (MediaWiki API, CC BY-SA 4.0)   the five league season pages and the three results-grid templates (current revisions): scores
  football-data.co.uk                        results CSVs of the five leagues and fixtures.csv (free download, no explicit licence: cross-check only)
  openfootball (CC0-1.0, GitHub raw)         today's five fixture/result files: dates and results
  fixturedownload.com                        free fixture feeds (JSON) of the five leagues: dates and times, an independent schedule (no explicit licence: cross-check only)
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
UA = "FootIQ-college-project/1.0 (student data-engineering project; serial read-only requests; bot-style client)"
OF = "https://raw.githubusercontent.com/openfootball/{repo}/master/{path}"
FD = "https://www.football-data.co.uk/{path}"
FXD = "https://fixturedownload.com/feed/json/{slug}"
WIKI = "https://en.wikipedia.org/w/api.php?" + "{q}"
PAGES = {"EPL": "2026–27 Premier League", "SERIEA": "2026–27 Serie A", "LIGUE1": "2026–27 Ligue 1", "BUNDESLIGA": "2026–27 Bundesliga", "LALIGA": "2026–27 La Liga",
         "LIGUE1_table": "Template:2026–27 Ligue 1 table", "BUNDESLIGA_table": "Template:2026–27 Bundesliga table", "LALIGA_table": "Template:2026–27 La Liga table"}
PLAIN = [
    ("openfootball_EPL.txt", OF.format(repo="england", path="2026-27/1-premierleague.txt"), "openfootball", "CC0-1.0", 1.5),
    ("openfootball_SERIEA.txt", OF.format(repo="italy", path="2026-27/1-seriea.txt"), "openfootball", "CC0-1.0", 1.5),
    ("openfootball_LIGUE1.txt", OF.format(repo="europe", path="france/2026-27_fr1.txt"), "openfootball", "CC0-1.0", 1.5),
    ("openfootball_BUNDESLIGA.txt", OF.format(repo="deutschland", path="2026-27/1-bundesliga.txt"), "openfootball", "CC0-1.0", 1.5),
    ("openfootball_LALIGA.txt", OF.format(repo="espana", path="2026-27/1-liga.txt"), "openfootball", "CC0-1.0", 1.5),
    ("footballdatauk_EPL.csv", FD.format(path="mmz4281/2627/E0.csv"), "football-data.co.uk", "no explicit licence: cross-check only", 1.5),
    ("footballdatauk_SERIEA.csv", FD.format(path="mmz4281/2627/I1.csv"), "football-data.co.uk", "no explicit licence: cross-check only", 1.5),
    ("footballdatauk_LIGUE1.csv", FD.format(path="mmz4281/2627/F1.csv"), "football-data.co.uk", "no explicit licence: cross-check only", 1.5),
    ("footballdatauk_BUNDESLIGA.csv", FD.format(path="mmz4281/2627/D1.csv"), "football-data.co.uk", "no explicit licence: cross-check only", 1.5),
    ("footballdatauk_LALIGA.csv", FD.format(path="mmz4281/2627/SP1.csv"), "football-data.co.uk", "no explicit licence: cross-check only", 1.5),
    ("footballdatauk_fixtures.csv", FD.format(path="fixtures.csv"), "football-data.co.uk", "no explicit licence: cross-check only", 1.5),
    ("fixturedownload_EPL.json", FXD.format(slug="epl-2026"), "fixturedownload.com", "no explicit licence: cross-check only", 1.5),
    ("fixturedownload_LALIGA.json", FXD.format(slug="la-liga-2026"), "fixturedownload.com", "no explicit licence: cross-check only", 1.5),
    ("fixturedownload_SERIEA.json", FXD.format(slug="serie-a-2026"), "fixturedownload.com", "no explicit licence: cross-check only", 1.5),
    ("fixturedownload_LIGUE1.json", FXD.format(slug="ligue-1-2026"), "fixturedownload.com", "no explicit licence: cross-check only", 1.5),
    ("fixturedownload_BUNDESLIGA.json", FXD.format(slug="bundesliga-2026"), "fixturedownload.com", "no explicit licence: cross-check only", 1.5),
]
SOURCES = list(PLAIN) + [(f"wikipedia_{k}_season_api.json", WIKI.format(q=urllib.parse.urlencode(dict(action="query", prop="revisions", rvprop="ids|timestamp|content", rvslots="main", format="json", formatversion="2", maxlag="5", titles=t))),
                          "wikipedia", "CC BY-SA 4.0", 5.5) for k, t in PAGES.items()]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    evp = RAW / "evidence.json"
    ev = json.loads(evp.read_text(encoding="utf-8")) if evp.exists() else {}
    for name, url, source, licence, pause in SOURCES:
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
            time.sleep(pause)
            continue
        (RAW / name).write_bytes(body)
        ev[name] = dict(url=url, source=source, licence=licence, retrieved_utc=started, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), **info)
        print("ok", name, len(body), info["status"])
        evp.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
        time.sleep(pause)


if __name__ == "__main__":
    main()
