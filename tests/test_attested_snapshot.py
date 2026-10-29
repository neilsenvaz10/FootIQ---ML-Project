"""Phase 4.37: the explicit `--evidence attested` mode (snapshot rebuild), the sanitized evidence CSVs and the CC0-only player extracts. Throw-away stores only.

Run:  python -X utf8 -m pytest tests/test_attested_snapshot.py -q
"""
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from store import league_results_import as L  # noqa: E402
from store import published_evidence as PE
from test_league_results_import import store  # noqa: F401
from test_published_evidence import AS_OF, DAY, league, prow, row_of, write, codes

ROOT = Path(__file__).resolve().parents[1]


def single(**over):
    """What production recorded for most results: Wikipedia's score and the stored (openfootball) date; the second source was a restricted one that cannot be published."""
    base = dict(openligadb_score=None, openligadb_date=None, openligadb_ref=None, evidence_classification=PE.INSUFFICIENT, restricted_cross_check_used_in_production="true")
    base.update(over)
    return prow(**base)


def attested(store, path, apply=True):
    return L.run(store, apply=apply, as_of=AS_OF, evidence="attested", published=path)


def test_published_mode_still_refuses_a_single_source_result_and_attested_mode_labels_what_it_accepts(tmp_path, store):
    p = write(tmp_path, [single()])
    assert league(store, p)["counts"] == {} or "insufficient_published_evidence" in codes(league(store, p, apply=False))
    assert row_of(store, "EPL:1")[0] == "awaiting_result"
    rep = attested(store, p)
    assert rep["evidence"] == "attested" and rep["counts"] == {"update_result": 1}
    status, hg, ag, d, src, _ = row_of(store, "EPL:1")
    assert (status, hg, ag, d, src) == ("completed", 1, 0, DAY, "wikipedia")
    c = sqlite3.connect(store)
    prov = c.execute("SELECT provenance FROM match_sources WHERE record_id='EPL:1' AND source='wikipedia'").fetchone()[0]
    run = c.execute("SELECT source FROM sync_runs WHERE kind='league_results_import' ORDER BY run_id DESC").fetchone()[0]
    c.close()
    assert "NOT independently reproducible" in prov and "attested" in run


def test_attested_mode_needs_the_attestation_flag_and_wikipedia_support(tmp_path, store):
    for over, code in ((dict(restricted_cross_check_used_in_production="false"), "attestation_missing"), (dict(wikipedia_score="2-2"), "no_wikipedia_support_for_score"),
                       (dict(wikipedia_score=None), "no_wikipedia_support_for_score"), (dict(openfootball_score="3-0"), "allowed_sources_disagree_on_score"), (dict(openfootball_date=None), "no_redistributable_source_for_date")):
        rep = attested(store, write(tmp_path, [single(**over)]), apply=False)
        assert code in codes(rep), (over, codes(rep))
        assert rep["counts"] == {} or "update_result" not in rep["counts"]


def test_attested_mode_never_leaks_into_a_later_run(tmp_path, store):
    p = write(tmp_path, [single()])
    attested(store, p, apply=False)
    assert "insufficient_published_evidence" in codes(league(store, p, apply=False))       # the next published run is strict again
    assert PE.ATTESTED is False


def test_standard_mode_is_untouched(tmp_path, store):
    with pytest.raises(SystemExit):
        L.run(store, apply=False, as_of=AS_OF, evidence="bogus")


# ---------------------------------------------------------------- shipped sanitized evidence and extracts
RESTRICT = re.compile(r"football-?data|fixturedownload|api-?football|provider|statsbomb", re.I)


def test_sanitized_evidence_csvs_carry_no_restricted_column_or_value():
    files = sorted((ROOT / "data" / "evidence" / "sanitized").glob("*.csv"))
    if not files:
        pytest.skip("sanitized evidence not generated")
    assert len(files) == 12
    for f in files:
        df = pd.read_csv(f, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        assert not [c for c in df.columns if RESTRICT.search(c)], f.name
        assert not df.apply(lambda s: s.str.contains(RESTRICT)).any().any(), f.name
        assert not [c for c in df.columns if c in ("diff_days", "shift_days")], f.name              # derived from a provider date


def test_cc0_player_extracts_contain_no_statsbomb_row():
    d = ROOT / "FootIQ_Dataset_Submission" / "cc0_extracts"
    if not d.exists():
        pytest.skip("extracts not generated")
    for f in sorted(d.glob("*_CC0.csv")):
        df = pd.read_csv(f, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        assert not df.apply(lambda s: s.str.contains(r"statsbomb|\bsb_", case=False)).any().any(), f.name
        src = [c for c in df.columns if c in ("source_dataset", "source_name")]
        assert src and df[src[0]].str.match(r"^(openfootball|martj42)", case=False).all(), f.name


def test_sanitized_dashboard_files_have_no_provider_or_news_row():
    d = ROOT / "data" / "release_candidates" / "miniproject"
    if not d.exists():
        pytest.skip("release candidates not generated")
    m = pd.read_csv(d / "matches.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    assert set(m.source) <= {"openfootball", "martj42/international_results", "wikipedia", "openligadb"}
    assert not (m.competition_key.eq("WC") & m.season.eq("2026")).any()


# ---------------------------------------------------------------- Phase 4.38 policy: opt-in, labelled, provenance kept, three results stay missing
def test_attested_mode_is_never_the_default_of_either_importer():
    import inspect

    from store import reconcile_import as R
    for mod in (L, R):
        src = inspect.getsource(mod.main)
        assert 'default="restricted"' in src and 'default="attested"' not in src
        assert "attested" in inspect.signature(mod.run).parameters["evidence"].default or inspect.signature(mod.run).parameters["evidence"].default == "restricted"
    assert PE.ATTESTED is False


def test_the_shipped_attested_list_labels_80_results_and_31_date_corrections_and_names_the_three_missing_results():
    d = ROOT / "data" / "evidence" / "published"
    a = pd.read_csv(d / "ATTESTED_RECORDS.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    u = pd.read_csv(d / "UNSUPPORTED_RESULTS.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    assert (a.kind == "result").sum() == 80 and (a.kind == "fixture_date_correction").sum() == 31 and len(u) == 3
    assert (a.independently_reproducible == "false").all() and a.label.str.contains("NOT independently reproducible").all()
    assert a.source_reference.str.len().gt(0).all() and a.review_decision.str.len().gt(0).all() and a.evidence_id.str.len().gt(0).all()      # references and review provenance are kept
    assert (a[a.kind == "result"].score.str.match(r"^\d+-\d+$")).all() and (a[a.kind != "result"].score == "").all()
    for df in (a, u):
        assert not df.apply(lambda s: s.str.contains(RESTRICT)).any().any()                                                              # no provider name or value
    assert not set(u.record_id) & set(a.record_id)                                                                                       # the three stay missing: none is attested
