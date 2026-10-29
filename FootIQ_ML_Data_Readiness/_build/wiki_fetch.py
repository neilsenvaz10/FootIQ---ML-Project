"""Polite Wikipedia wikitext fetcher (CC BY-SA 4.0 source). Serial requests, >=1.5 s apart, cached on disk."""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import EXTERNAL  # noqa

UA = "FootIQ-DataReadinessBot/1.0 (academic student project, local research use, no redistribution of raw dumps) python-urllib"
DIR = os.path.join(EXTERNAL, "wikipedia")
os.makedirs(DIR, exist_ok=True)
_last = [0.0]


def fetch(title):
    """Return dict(wikitext, revid, timestamp, url). Caches JSON under raw_external/wikipedia."""
    key = hashlib.md5(title.encode()).hexdigest()[:10] + "_" + "".join(c if c.isalnum() else "_" for c in title)[:60]
    path = os.path.join(DIR, key + ".json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    q = urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "content|ids|timestamp",
                                "rvslots": "main", "titles": title, "format": "json", "formatversion": "2",
                                "redirects": "1"})
    req = urllib.request.Request("https://en.wikipedia.org/w/api.php?" + q, headers={"User-Agent": UA})
    data = None
    for attempt in range(8):
        wait = 4.0 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            _last[0] = time.time()
            break
        except urllib.error.HTTPError as e:
            _last[0] = time.time()
            if e.code in (429, 503):
                ra = e.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.isdigit() else 30 * (attempt + 1))
                continue
            raise
    if data is None:
        raise RuntimeError("rate limited repeatedly for " + title)
    pg = data["query"]["pages"][0]
    if "missing" in pg:
        out = dict(title=title, missing=True)
    else:
        rev = pg["revisions"][0]
        out = dict(title=pg["title"], missing=False, revid=rev["revid"], timestamp=rev["timestamp"],
                   wikitext=rev["slots"]["main"]["content"],
                   url="https://en.wikipedia.org/wiki/" + urllib.parse.quote(pg["title"].replace(" ", "_")),
                   retrieved=time.strftime("%Y-%m-%d"))
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return out


if __name__ == "__main__":
    for t in sys.argv[1:]:
        r = fetch(t)
        print(t, "missing" if r.get("missing") else f"rev {r['revid']} {r['timestamp']} len {len(r['wikitext'])}")
