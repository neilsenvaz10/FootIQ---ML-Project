"""Phase 4.17: ONE controlled download of a CC0 repository archive into PRIVATE staging (data/supervised/phase4/p417/staging/<name>/). One HTTPS GET per run (GitHub answers it with a
redirect to codeload.github.com; both hops are recorded), no retry, no other URL. Nothing is imported: the archive is hashed, unpacked beside itself and described in <name>/evidence.json.

    python fetch_source.py martj42        https://github.com/martj42/international_results/archive/refs/heads/master.zip
    python fetch_source.py openfootball   https://github.com/openfootball/champions-league/archive/refs/heads/master.zip
"""
import hashlib
import json
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
URLS = {"martj42": "https://github.com/martj42/international_results/archive/refs/heads/master.zip",
        "openfootball": "https://github.com/openfootball/champions-league/archive/refs/heads/master.zip"}
LICENCE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")


class NoRedirectLog(urllib.request.HTTPRedirectHandler):
    hops = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append(dict(from_url=req.full_url, status=code, to_url=newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main(name):
    url = URLS[name]
    out = HERE / "staging" / name
    if (out / "evidence.json").exists():
        raise SystemExit(f"{name} was already downloaded ({out}); one download per source: refusing a second")
    out.mkdir(parents=True, exist_ok=True)
    h = NoRedirectLog()
    opener = urllib.request.build_opener(h)
    req = urllib.request.Request(url, headers={"User-Agent": "FootIQ-college-project/1.0 (single read-only archive download)"})
    started = datetime.now(timezone.utc)
    with opener.open(req, timeout=180) as r:                            # <<< the one download
        body = r.read()
        info = dict(final_url=r.geturl(), status=r.status, headers={k: v for k, v in r.headers.items() if k.lower() in ("content-type", "content-length", "etag", "last-modified", "content-disposition", "date")})
    zpath = out / f"{name}-master.zip"
    zpath.write_bytes(body)
    ev = dict(source=name, requested_url=url, retrieved_utc=started.strftime("%Y-%m-%dT%H:%M:%SZ"), redirects=h.hops, response=info, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    with zipfile.ZipFile(zpath) as z:
        ev["zip_test"] = "ok" if z.testzip() is None else "CORRUPT"
        ev["zip_comment_commit"] = z.comment.decode("utf-8", "replace")                  # GitHub puts the commit id of the archived revision here
        ev["files"] = [dict(name=i.filename, size=i.file_size) for i in z.infolist() if not i.is_dir()][:400]
        lic = next((i for i in z.infolist() if i.filename.split("/")[-1] in LICENCE_FILES), None)
        if lic:
            txt = z.read(lic).decode("utf-8", "replace")
            ev["licence_file"] = lic.filename
            ev["licence_head"] = " ".join(txt.split())[:160]
            ev["licence_is_cc0"] = "CC0 1.0" in txt or "Creative Commons Zero" in txt or "Public Domain Dedication" in txt
        z.extractall(out / "unpacked")
    (out / "evidence.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in ev.items() if k != "files"}, indent=1, ensure_ascii=False))
    print("files:", len(ev["files"]))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in URLS:
        raise SystemExit(__doc__)
    main(sys.argv[1])
