"""Phase 4.20 part B: ONE MediaWiki Action API GET per 2026-27 league season page (CC BY-SA 4.0), >= 5 s apart as the project's Wikipedia adapter policy requires, into PRIVATE staging
(data/supervised/phase4/p420/staging/raw/). The pages carry a results grid (scores only, no dates). Nothing is imported. A page already downloaded is never fetched again."""
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
PAGES = {"EPL": "2026–27 Premier League", "SERIEA": "2026–27 Serie A", "LIGUE1": "2026–27 Ligue 1", "BUNDESLIGA": "2026–27 Bundesliga", "LALIGA": "2026–27 La Liga",
         "LIGUE1_table": "Template:2026–27 Ligue 1 table", "BUNDESLIGA_table": "Template:2026–27 Bundesliga table", "LALIGA_table": "Template:2026–27 La Liga table"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    evp = RAW / "evidence.json"
    ev = json.loads(evp.read_text(encoding="utf-8"))
    for key, title in PAGES.items():
        name = f"wikipedia_{key}_season_api.json"
        if (RAW / name).exists():
            print("skip", name)
            continue
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", prop="revisions", rvprop="ids|timestamp|content", rvslots="main", format="json", formatversion="2", maxlag="5", titles=title))
        started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                info = dict(status=r.status, final_url=r.geturl(), headers={k: v for k, v in r.headers.items() if k.lower() in ("content-type", "content-length", "date")})
        except Exception as e:
            ev[name] = dict(url=url, source="wikipedia", licence="CC BY-SA 4.0", retrieved_utc=started, error=f"{type(e).__name__}: {e}")
            print("FAILED", name, e)
            evp.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
            time.sleep(5.5)
            continue
        (RAW / name).write_bytes(body)
        ev[name] = dict(url=url, source="wikipedia", licence="CC BY-SA 4.0", retrieved_utc=started, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), **info)
        d = json.loads(body)["query"]["pages"][0]
        rev = d.get("revisions", [{}])[0]
        print("ok", name, len(body), "missing" if d.get("missing") else f"rev {rev.get('revid')} {rev.get('timestamp')}")
        evp.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
        time.sleep(5.5)


if __name__ == "__main__":
    main()
