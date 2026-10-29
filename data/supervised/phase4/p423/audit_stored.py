"""Phase 4.23: re-audit EVERY stored completed 2026-27 result of the five leagues against Wikipedia (parser fixed for piped derby cells), football-data.co.uk and FixtureDownload. OFFLINE, read-only."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence as E  # noqa: E402

conn = E.connect()
out = {}
for k in E.LEAGUES:
    d = E.load(k, conn)
    done = {p: r for p, r in d["rows"].items() if r["status"] == "completed"}
    res = dict(stored_completed=len(done), checked_wikipedia=0, checked_fduk=0, checked_fxd=0, score_differs=[], date_differs=[], not_in_any_source=0)
    for p, r in done.items():
        sc = (r["hg"], r["ag"])
        seen = False
        for name, src in (("wikipedia", d["wiki"]), ("fduk", d["fduk"]), ("fxd", d["fxd"])):
            v = src.get(p)
            if v and v.get("score"):
                seen = True
                res["checked_" + ("wikipedia" if name == "wikipedia" else name)] += 1
                if tuple(v["score"]) != sc:
                    res["score_differs"].append((name, r["home_name"], r["away_name"], sc, tuple(v["score"])))
            if name != "wikipedia" and v and v.get("score") and v.get("date") and v["date"] != r["match_date"] and name == "fduk":
                res["date_differs"].append((name, r["home_name"], r["away_name"], r["match_date"], v["date"]))
        res["not_in_any_source"] += 0 if seen else 1
    out[k] = res
(HERE / "staging" / "stored_results_audit.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
for k, v in out.items():
    print(k, {x: (y if not isinstance(y, list) else len(y)) for x, y in v.items()}, v["score_differs"][:3], v["date_differs"][:3])
