"""Disputed fixture dates (Phase 4.8D Stage 2). A DATE_DIFFERENCE quarantine row means the store and a source disagree about the day of a fixture. For prediction eligibility every
candidate date counts and the earliest decides (kickoff_tz.py), so a dispute can only make the answer stricter. Read-only: nothing is written and no dispute is resolved here.

`by_record(conn)` -> {record_id: [source dates that differ from the stored one]}, rebuilt only when the quarantine's DATE_DIFFERENCE rows change.
"""
import json
import re
import threading

_LOCK = threading.Lock()
_CACHE: dict = {}
_RX = re.compile(r"DATE_DIFFERENCE: stored (\d{4}-\d\d-\d\d) vs source (\d{4}-\d\d-\d\d)")


def by_record(conn) -> dict:
    sig = conn.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%'").fetchone()
    path = conn.execute("PRAGMA database_list").fetchone()[2]
    key = (path, sig[0], sig[1])
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    out: dict = {}
    if sig[0]:
        from store import sync                                      # the same identity resolver the importer uses (aliases included); imported lazily

        resolver = sync.build_resolver(conn)
        for row in conn.execute("SELECT payload, reason FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%'").fetchall():
            m = _RX.match(row["reason"])
            if not m or not row["payload"]:
                continue
            pl = json.loads(row["payload"])
            comp = pl.get("competition_key")
            he, _ = resolver.resolve("openligadb", comp, pl.get("home_raw", ""))
            ae, _ = resolver.resolve("openligadb", comp, pl.get("away_raw", ""))
            if not (he and ae):
                continue
            for r in conn.execute("SELECT record_id FROM matches WHERE competition_id=? AND home_entity_id=? AND away_entity_id=? AND match_date=?", (comp, he, ae, m.group(1))).fetchall():
                out.setdefault(r["record_id"], []).append(m.group(2))
    with _LOCK:
        _CACHE.clear()
        _CACHE[key] = out
    return out
