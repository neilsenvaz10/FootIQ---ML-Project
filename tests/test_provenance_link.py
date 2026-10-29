"""Phase 4.8D: the source link of an imported result names the snapshot that supplied it, keeps its history, and never touches unrelated provenance. Synthetic store."""
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))
from store import db, sync  # noqa: E402
from test_featured import add_match, add_team  # noqa: E402

OLD, NEW = "20261025T083829Z_bl1_2026_season.json", "20261027T125704Z_p48c_bl1.json"


def rec(ref="83213", rev=None):
    return SimpleNamespace(source="openligadb", source_ref=ref, licence="ODbL-1.0", retrieved_utc=None, source_revision=rev)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "p.sqlite")
    db.init(c)
    add_team(c, "a", "A FC")
    add_team(c, "b", "B FC")
    add_match(c, "bun:1", "BUNDESLIGA", "2026-27", 7, "2026-10-25", "a", "b")
    add_match(c, "bun:2", "BUNDESLIGA", "2026-27", 7, "2026-10-25", "b", "a")
    c.execute("INSERT INTO match_sources(source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, provenance) VALUES ('openfootball','of-1','bun:1','primary','fixtures-2026-10-15','CC0-1.0','2026-10-15T00:00:00Z','openfootball L110')")
    c.commit()
    return c


def links(c):
    return {(r["source"], r["source_ref"]): dict(r) for r in c.execute("SELECT * FROM match_sources")}


def test_initial_import_writes_a_link_to_the_snapshot_that_supplied_it(conn):
    sync._link_source(conn, rec(), "bun:1", "primary", NEW, "2026-10-27T12:57:04Z")
    l = links(conn)[("openligadb", "83213")]
    assert (l["role"], l["snapshot_id"], l["record_id"], l["retrieved_utc"]) == ("primary", NEW, "bun:1", "2026-10-27T12:57:04Z")
    assert l["provenance"] == "openligadb matchID 83213"


def test_a_confirmation_that_becomes_the_supplier_is_upgraded_with_its_history_kept(conn):
    sync._link_source(conn, rec(), "bun:1", "confirmation", OLD, "2026-10-25T08:38:29Z")
    before = links(conn)
    sync._link_source(conn, rec(), "bun:1", "primary", NEW, "2026-10-27T12:57:04Z")
    after = links(conn)
    l = after[("openligadb", "83213")]
    assert (l["role"], l["snapshot_id"], l["retrieved_utc"]) == ("primary", NEW, "2026-10-27T12:57:04Z")
    assert l["provenance"].startswith("openligadb matchID 83213 | upgraded to primary") and OLD in l["provenance"] and "was confirmation" in l["provenance"] and "2026-10-25T08:38:29Z" in l["provenance"]
    assert after[("openfootball", "of-1")] == before[("openfootball", "of-1")]            # an unrelated link is byte-identical
    assert len(after) == len(before)                                                       # nothing was added or removed


def test_a_repeated_import_changes_nothing(conn):
    sync._link_source(conn, rec(), "bun:1", "confirmation", OLD, "t0")
    sync._link_source(conn, rec(), "bun:1", "primary", NEW, "t1")
    once = links(conn)
    sync._link_source(conn, rec(), "bun:1", "primary", NEW, "t2")
    sync._link_source(conn, rec(), "bun:1", "confirmation", NEW, "t3")                    # a later confirmation never downgrades
    assert links(conn) == once


def test_an_updated_source_row_of_another_match_or_a_primary_is_never_overwritten(conn):
    sync._link_source(conn, rec(), "bun:1", "primary", OLD, "t0")                         # already primary from an earlier snapshot
    first = links(conn)
    sync._link_source(conn, rec(), "bun:1", "primary", NEW, "t1")
    assert links(conn) == first                                                            # existing primary history is not rewritten
    sync._link_source(conn, rec(), "bun:2", "primary", NEW, "t2")                          # same source ref, different match: refused silently, not repointed
    assert links(conn)[("openligadb", "83213")]["record_id"] == "bun:1"


def test_a_rolled_back_import_leaves_the_old_link_exactly_as_it_was(conn):
    sync._link_source(conn, rec(), "bun:1", "confirmation", OLD, "t0")
    conn.commit()
    before = links(conn)
    sync._link_source(conn, rec(), "bun:1", "primary", NEW, "t1")
    assert links(conn) != before
    conn.rollback()
    assert links(conn) == before
