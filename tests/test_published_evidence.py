"""Phase 4.36: the published-evidence mode of the domestic importers (app/store/published_evidence.py, `--evidence published`). Throw-away stores only; production is never opened for writing.

Run:  .venv\\Scripts\\python.exe -X utf8 -m pytest tests/test_published_evidence.py -q
"""
import hashlib
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

from seasonsim import eligibility  # noqa: E402
from store import league_results_import as L  # noqa: E402
from store import published_evidence as PE  # noqa: E402
from store import reconcile_import as R  # noqa: E402
from test_league_results_import import ENT, store  # noqa: E402,F401  (the same throw-away store fixture)

AS_OF = "2026-10-28"
DAY = "2026-10-17"


def prow(eid="LR-1", importer="league_results", action="update_result", rid="EPL:1", key="EPL", h="a", a="b", day=DAY, hg=1, ag=0, **over):
    """A published-evidence row: two redistributable sources agree (Wikipedia and OpenLigaDB on the score, openfootball and OpenLigaDB on the date) unless overridden."""
    row = dict(evidence_id=eid, importer=importer, action=action, competition_key=key, season="2026-27", record_id=rid, home_entity=ENT[h], away_entity=ENT[a], home=f"{h} fc", away=f"{a} fc",
               expected_store_status="awaiting_result", expected_store_date=day, new_date=day, home_goals=hg, away_goals=ag, wikipedia_score=f"{hg}-{ag}", wikipedia_revision=555, wikipedia_date=None,
               openligadb_score=f"{hg}-{ag}", openligadb_date=day, openligadb_ref="matchID 1", openfootball_score=None, openfootball_date=day, production_tier="strong",
               evidence_classification=PE.TWO, restricted_cross_check_used_in_production="false", review_decision="test decision", confidence="verified_two_redistributable_sources", uncertainty="",
               licence="test", provenance="test")
    row.update(over)
    return row


def write(tmp_path, rows, name="published.csv"):
    p = tmp_path / name
    pd.DataFrame(rows, columns=PE.COLUMNS).to_csv(p, index=False, encoding="utf-8-sig")
    return p


def league(store, path, apply=True, as_of=AS_OF):
    return L.run(store, apply=apply, as_of=as_of, evidence="published", published=path)


def row_of(store, rid):
    c = sqlite3.connect(store)
    r = c.execute("SELECT status, home_goals_final, away_goals_final, match_date, source_system, content_hash FROM matches WHERE record_id=?", (rid,)).fetchone()
    c.close()
    return r


def codes(rep):
    return {i["code"] for i in rep["validation_issues"]}


# ---------------------------------------------------------------- restricted columns are neither required nor allowed
def test_restricted_provider_columns_are_not_required_and_a_file_that_carries_them_is_refused(tmp_path, store):
    assert not PE.forbidden_columns(PE.COLUMNS)                                            # the published schema has no restricted column
    rep = league(store, write(tmp_path, [prow()]))
    assert rep["counts"] == {"update_result": 1} and rep["evidence"] == "published"
    for bad in ("footballdatauk_score", "fixturedownload_date", "provider_date", "statsbomb_id", "footballdata_org_score"):
        df = pd.DataFrame([prow()], columns=PE.COLUMNS)
        df[bad] = "1-0"
        p = tmp_path / f"{bad}.csv"
        df.to_csv(p, index=False, encoding="utf-8-sig")
        with pytest.raises(SystemExit, match="restricted provider columns"):
            league(store, p, apply=False)


def test_a_published_file_lacking_a_required_column_is_refused(tmp_path, store):
    df = pd.DataFrame([prow()], columns=PE.COLUMNS).drop(columns=["openligadb_date"])
    p = tmp_path / "x.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    with pytest.raises(SystemExit, match="lacks columns"):
        league(store, p, apply=False)


# ---------------------------------------------------------------- insufficient or contradictory evidence is never accepted
@pytest.mark.parametrize("over, code", [
    (dict(openligadb_score=None, evidence_classification=PE.INSUFFICIENT), "insufficient_published_evidence"),                    # the score rests on Wikipedia alone
    (dict(openligadb_date=None, evidence_classification=PE.INSUFFICIENT), "insufficient_published_evidence"),                    # the day rests on openfootball alone
    (dict(openligadb_score="2-0"), "allowed_sources_disagree_on_score"),
    (dict(openligadb_score=None), "label_contradicts_recorded_evidence"),                                                         # the label claims two sources the values do not show
    (dict(evidence_classification=PE.INSUFFICIENT), "label_contradicts_recorded_evidence"),                                       # the values meet the rule but the label denies it
    (dict(evidence_classification="verified"), "bad_evidence_classification"),
    (dict(new_date="2026-10-18", openligadb_date="2026-10-18", openfootball_date="2026-10-18"), "dates_disagree"),                 # the played day differs from the stored fixture's day
    (dict(home_goals=16, wikipedia_score="16-0", openligadb_score="16-0"), "implausible_score"),
    (dict(action="correct_date"), "bad_action"),
])
def test_published_mode_rejects_insufficient_or_contradictory_evidence_and_applies_nothing(tmp_path, store, over, code):
    before = row_of(store, "EPL:1")
    rep = league(store, write(tmp_path, [prow(**over)]))
    assert code in codes(rep)
    assert rep["counts"].get("quarantine_invalid") == 1 and "update_result" not in rep["counts"]
    assert row_of(store, "EPL:1") == before                                                 # the stored fixture is untouched: no silent acceptance


def test_a_result_on_a_single_source_is_not_accepted_however_it_is_labelled(tmp_path, store):
    p = write(tmp_path, [prow(openligadb_score=None, openligadb_date=None, openfootball_date=DAY, evidence_classification=PE.TWO)])
    rep = league(store, p)
    assert {"insufficient_published_evidence", "label_contradicts_recorded_evidence"} <= codes(rep)
    assert row_of(store, "EPL:1")[0] == "awaiting_result"


# ---------------------------------------------------------------- accepted evidence: result, provenance, idempotence, determinism
def test_two_redistributable_sources_apply_the_result_with_published_evidence_provenance(tmp_path, store):
    rep = league(store, write(tmp_path, [prow()]))
    assert rep["applied"]["updated"] == 1
    st, hg, ag, day, src, _ = row_of(store, "EPL:1")
    assert (st, hg, ag, day, src) == ("completed", 1, 0, DAY, "wikipedia")
    c = sqlite3.connect(store)
    prov = c.execute("SELECT provenance FROM match_sources WHERE record_id='EPL:1' AND source='wikipedia'").fetchone()[0]
    kind = c.execute("SELECT source FROM sync_runs WHERE kind='league_results_import'").fetchone()[0]
    c.close()
    assert "published evidence" in prov and "cross-check only, not stored" not in prov and "published evidence file" in kind


def test_importing_the_same_published_evidence_twice_changes_nothing(tmp_path, store):
    p = write(tmp_path, [prow()])
    league(store, p)
    h1 = row_of(store, "EPL:1")
    rep2 = league(store, p)
    assert rep2["counts"] == {"unchanged": 1} and row_of(store, "EPL:1") == h1


def test_the_replay_is_deterministic_on_two_independent_copies(tmp_path, store):
    twin = tmp_path / "twin.sqlite"
    shutil.copy2(store, twin)
    p = write(tmp_path, [prow(), prow(eid="LR-2", rid="EPL:2", h="c", a="d", hg=2, ag=2)])
    league(store, p)
    league(twin, p)
    assert row_of(store, "EPL:1")[5] == row_of(twin, "EPL:1")[5] and row_of(store, "EPL:2")[5] == row_of(twin, "EPL:2")[5]


def test_dry_run_in_published_mode_writes_nothing(tmp_path, store):
    h = hashlib.sha256(Path(store).read_bytes()).hexdigest()
    rep = league(store, write(tmp_path, [prow()]), apply=False)
    assert rep["mode"] == "dry-run" and rep["counts"] == {"update_result": 1}
    assert hashlib.sha256(Path(store).read_bytes()).hexdigest() == h


# ---------------------------------------------------------------- the standard mode is unchanged
def test_the_standard_mode_is_still_the_default_and_still_needs_its_restricted_cross_check(tmp_path, store):
    import inspect
    assert inspect.signature(L.run).parameters["evidence"].default == "restricted"
    assert inspect.signature(R.run).parameters["evidence"].default == "restricted"
    p = write(tmp_path, [prow()], name="staged_results_EPL.csv")                            # a published file is NOT a valid staged file
    with pytest.raises(SystemExit, match="lacks columns"):
        L.run(store, apply=False, as_of=AS_OF, paths=[p])
    with pytest.raises(SystemExit):
        L.run(store, apply=False, as_of=AS_OF, evidence="elsewhere")


# ---------------------------------------------------------------- reconciliation
def rrow(eid="RC-1", action="add_result", rid="EPL:1", h="a", a="b", day=DAY, **over):
    r = prow(eid=eid, importer="reconcile", action=action, rid=rid, h=h, a=a, day=day)
    r.update(over)
    return r


def recon(store, path, apply=True, tiers=("strong",)):
    return R.run(store, apply=apply, proposals=path, tiers=tiers, as_of=AS_OF, evidence="published")


def test_reconcile_published_applies_a_two_source_result_without_restricted_columns(tmp_path, store):
    rep = recon(store, write(tmp_path, [rrow()]))
    assert rep["counts"] == {"apply": 1} and row_of(store, "EPL:1")[:3] == ("completed", 1, 0)


@pytest.mark.parametrize("over, code", [
    (dict(openligadb_score=None, evidence_classification=PE.INSUFFICIENT), "insufficient_published_evidence"),
    (dict(production_tier="provider_assisted"), "provider_assisted_not_available_in_published_mode"),
    (dict(openligadb_score="0-3"), "allowed_sources_disagree_on_score"),
])
def test_reconcile_published_rejects_insufficient_evidence(tmp_path, store, over, code):
    before = row_of(store, "EPL:1")
    rep = recon(store, write(tmp_path, [rrow(**over)]), tiers=("strong", "provider_assisted"))
    assert code in codes(rep) and "apply" not in rep["counts"] and row_of(store, "EPL:1") == before


def test_a_date_correction_needs_two_redistributable_sources_for_the_new_date(tmp_path, store):
    one = rrow(eid="RC-D1", action="correct_date", rid="EPL:future", h="b", a="d", day="2026-11-07", new_date="2026-11-06", openligadb_date="2026-11-06", openfootball_date="2026-11-07", expected_store_status="scheduled",
               hg=None, ag=None, wikipedia_score=None, openligadb_score=None, expected_store_date="2026-11-07", evidence_classification=PE.INSUFFICIENT)
    rep = recon(store, write(tmp_path, [one]), apply=False)
    assert "insufficient_published_evidence" in codes(rep)                                  # OpenLigaDB alone (the old date is openfootball's own) is one source
    two = dict(one, wikipedia_date="2026-11-06", evidence_classification=PE.TWO)
    rep2 = recon(store, write(tmp_path, [two], name="two.csv"), apply=False)
    assert rep2["counts"] == {"apply": 1} and not rep2["validation_issues"]


# ---------------------------------------------------------------- simulator eligibility follows the evidence
def test_simulation_eligibility_follows_the_published_evidence(tmp_path, store):
    def state():
        conn = sqlite3.connect(store)
        conn.row_factory = sqlite3.Row
        try:
            a = eligibility.assess(conn, "EPL", "2026-27", date.fromisoformat(AS_OF))
            return a["state"], a["counts"]["missing_results"]
        finally:
            conn.close()

    assert state() == ("not_eligible", 2)                                                  # two played-date fixtures without a result: 67% missing
    league(store, write(tmp_path, [prow(openligadb_score=None, evidence_classification=PE.INSUFFICIENT)], name="weak.csv"))
    assert state() == ("not_eligible", 2)                                                  # insufficient evidence changes nothing
    league(store, write(tmp_path, [prow(), prow(eid="LR-2", rid="EPL:2", h="c", a="d", hg=2, ag=2)], name="good.csv"))
    st, missing = state()
    assert missing == 0 and st in ("ready", "provisional")                                 # the two results are in: no fixture is missing any more


# ---------------------------------------------------------------- the shipped evidence file
SHIPPED = Path(__file__).resolve().parents[1] / "data" / "evidence" / "published" / "published_evidence_2026-10-28.csv"


@pytest.mark.skipif(not SHIPPED.exists(), reason="published evidence not generated")
def test_the_shipped_published_evidence_carries_no_restricted_value_and_its_labels_follow_its_values():
    text = SHIPPED.read_text(encoding="utf-8-sig").lower()
    assert not any(w in text for w in ("footballdata", "football-data", "fixturedownload", "provider_date"))
    for importer in ("league_results", "reconcile"):
        df = PE.load(SHIPPED, importer)
        assert len(df) > 0
        for r in df.itertuples():
            if r.action == "set_postponed":
                continue
            target = None if pd.isna(r.home_goals) else f"{int(r.home_goals)}-{int(r.away_goals)}"
            ok, _ = PE.assess(r, r.action in ("add_result", "add_result_with_date", "update_result"), r.action in ("update_result", "add_result_with_date", "correct_date"), target, str(r.new_date))
            assert (r.evidence_classification == PE.TWO) == ok, r.evidence_id
