"""Phase 4.8B offline rehearsal: NO network, NO production write. Everything happens in private copies under data/supervised/phase4/p48b/work/.

 A. Alias verification: the five proposed aliases are re-verified against canonical ids, membership, history and fixture structure on a copy of the PRE-IMPORT backup.
 B. Reproduction: the saved snapshots replayed onto that pre-import copy must give exactly the matches/quarantine/alias content that production holds today.
 C. Idempotence: replaying the same snapshots onto a copy of production changes nothing (0 inserted, 0 updated) and creates no second quarantine finding.
 D. Safety rules: stored scores are never overwritten (the two conflicts stay quarantined), the 55 date disagreements stay held, nothing is deleted.
"""
import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "app" / "store"))
import rehearse_openligadb as R  # noqa: E402
from store import db, sync  # noqa: E402

OUT = ROOT / "data" / "supervised" / "phase4" / "p48b"
WORK = OUT / "work"
PRE = ROOT / "data" / "supervised" / "production_import" / "footiq.20261025T142618Z.backup.sqlite"
PROD = ROOT / "data" / "footiq.sqlite"


def copy_db(src: Path, dst: Path) -> None:
    for ext in ("", "-wal", "-shm"):
        Path(str(dst) + ext).unlink(missing_ok=True)
    shutil.copyfile(src, dst)
    if Path(str(src) + "-wal").exists() and Path(str(src) + "-wal").stat().st_size:
        shutil.copyfile(str(src) + "-wal", str(dst) + "-wal")
    c = sqlite3.connect(dst)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.execute("PRAGMA journal_mode=DELETE")
    c.close()


def table_hash(conn, table, where="", order="1,2"):
    h = hashlib.sha256()
    n = 0
    for r in conn.execute(f'SELECT * FROM "{table}" {where} ORDER BY {order}'):
        h.update(repr(tuple(r)).encode())
        n += 1
    return n, h.hexdigest()[:16]


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    prod_before = hashlib.sha256(PROD.read_bytes()).hexdigest()
    snaps = R.load_snapshots()
    pre, prodcopy = WORK / "pre_import.sqlite", WORK / "prod_copy.sqlite"
    copy_db(PRE, pre)
    copy_db(PROD, prodcopy)
    rep = dict(production_sha256_before=prod_before, snapshots={k: dict(sha256=v["sha256"], retrieved_utc=v["retrieved_utc"], path=v["rel"]) for k, v in snaps.items()})

    # A. alias verification on the pre-import copy
    c = db.connect(pre)
    ver = R.verify_identities(c, snaps)
    c.close()
    pc = sqlite3.connect(f"file:{prodcopy.as_posix()}?mode=ro", uri=True)
    prod_alias = {(r[0], r[1]): (r[2], r[3]) for r in pc.execute("select competition_id, alias, entity_id, method from team_aliases where method like 'reviewed_alias%'")}
    pc.close()
    rep["A_alias_verification"] = [dict(source_name=v["source_name"], canonical_entity_id=v["canonical_entity_id"], canonical_display_name=v["canonical_display_name"], proposed_text_as_written=v["proposed_name_as_written"],
                                        proposed_text_is_a_stored_name=bool(v["proposed_name_equals_a_stored_name"]), checks=v["checks"], accepted=v["accepted"],
                                        in_production_with_same_entity=any(k[1] == v["source_name"] and val[0] == v["canonical_entity_id"] for k, val in prod_alias.items())) for v in ver["verdicts"]]
    rep["A_all_five_pass_every_check"] = all(v["accepted"] for v in ver["verdicts"])

    # B. reproduction: aliases + snapshot replay on the pre-import copy == production
    R.apply(pre, snaps, ver["aliases"], kind="offline_snapshot_import")
    a, b = sqlite3.connect(pre), sqlite3.connect(f"file:{prodcopy.as_posix()}?mode=ro", uri=True)
    rep["B_reproduction"] = {t: dict(rehearsal=table_hash(a, t), production=table_hash(b, t), identical=table_hash(a, t) == table_hash(b, t)) for t in ("matches", "quarantine", "team_aliases", "match_sources")}
    a.close()
    b.close()

    # C. idempotence on a production copy
    bconn = sqlite3.connect(prodcopy)
    before = {t: table_hash(bconn, t) for t in ("matches", "quarantine", "match_sources", "team_aliases")}
    bconn.close()
    res = R.apply(prodcopy, snaps, [], kind="offline_rehearsal_replay")
    bconn = sqlite3.connect(prodcopy)
    after = {t: table_hash(bconn, t) for t in ("matches", "quarantine", "match_sources", "team_aliases")}
    rep["C_idempotence"] = dict(results={k: {x: v[x] for x in ("inserted", "updated", "unchanged", "confirmed", "quarantined") if x in v} for k, v in res.items()}, tables_before=before, tables_after=after,
                                matches_identical=before["matches"] == after["matches"], quarantine_identical=before["quarantine"] == after["quarantine"], aliases_identical=before["team_aliases"] == after["team_aliases"])
    # D. the held items
    q = bconn.execute("select reason from quarantine where reason like 'CONFLICT%' or reason like 'CONTRADICTORY%'").fetchall()
    rep["D_conflicts_still_quarantined"] = [r[0] for r in q]
    rep["D_date_differences_quarantined"] = bconn.execute("select count(*) from quarantine where reason like 'DATE_DIFFERENCE%'").fetchone()[0]
    stored = {r[0]: (r[1], r[2]) for r in bconn.execute("select record_id, home_goals_90, away_goals_90 from matches where season='2026-27' and competition_key='EPL' and ((home_name like '%Bournemouth%' and away_name like '%Brentford%') or (home_name like '%Aston Villa%' and away_name like '%Forest%'))")}
    rep["D_stored_scores_of_the_two_conflicts"] = stored
    bconn.close()
    rep["production_sha256_after"] = hashlib.sha256(PROD.read_bytes()).hexdigest()
    rep["production_untouched"] = rep["production_sha256_before"] == rep["production_sha256_after"]
    (OUT / "offline_rehearsal.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("A_all_five_pass_every_check", "B_reproduction", "C_idempotence", "D_conflicts_still_quarantined", "D_date_differences_quarantined", "D_stored_scores_of_the_two_conflicts", "production_untouched")}, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
