"""Phase 4.17: the staged-source evidence stays what the report says it is (read-only on data/supervised/phase4/p417/). Skipped when the evidence folder is absent."""
import json
from pathlib import Path

import pytest

P = Path(__file__).resolve().parents[1] / "data" / "supervised" / "phase4" / "p417"
needs = pytest.mark.skipif(not (P / "staging" / "martj42" / "evidence.json").exists(), reason="Phase 4.17 staging evidence not present")


def load(name):
    return json.loads((P / name).read_text(encoding="utf-8"))


@needs
def test_each_source_was_downloaded_once_verified_and_is_cc0():
    for name, commit in (("martj42", "d5bd6de0"), ("openfootball", "abfaeddc")):
        ev = json.loads((P / "staging" / name / "evidence.json").read_text(encoding="utf-8"))
        assert ev["zip_test"] == "ok" and ev["licence_is_cc0"] is True and ev["zip_comment_commit"].startswith(commit) and len(ev["sha256"]) == 64
        assert ev["response"]["status"] == 200 and len(ev["redirects"]) == 1 and ev["requested_url"].startswith("https://github.com/")
        assert (P / "staging" / name / f"{name}-master.zip").stat().st_size == ev["bytes"]


@needs
def test_the_international_comparison_findings():
    r = load("compare_intl2_report.json")
    assert r["wc2026_staged"]["rows"] == 104 and r["wc2026_staged"]["scored"] == 104 and r["wc2026_staged"]["last"] == "2026-07-19"
    assert r["unl_2026_27_staged"]["rows"] == 104 and r["unl_2026_27_staged"]["first"] == "2026-09-24"
    assert r["staged_rows_after_local_cutoff"] == 583
    t = load("compare_intl_report.json")
    assert t["duplicates_27"]["total"] == 27 and t["duplicates_27"]["staged_matches_knockout_row"] == 27 and t["duplicates_27"]["staged_matches_group_row"] == 0
    assert [c["pair"] for c in t["duplicates_27"]["conflicts_4"]] == ["2026-07-01|Belgium|Senegal", "2026-07-03|Argentina|Cape Verde", "2026-07-11|Argentina|Switzerland", "2026-07-11|Norway|England"]


@needs
def test_openfootball_upstream_has_nothing_newer_than_the_local_clone():
    files = json.loads((P / "staging" / "openfootball" / "evidence.json").read_text(encoding="utf-8"))["files"]
    names = [f["name"] for f in files]
    assert not any("/2026-27/" in n for n in names) and any("/2025-26/cl.txt" in n for n in names)


@needs
def test_the_staged_2026_27_league_phases_are_structurally_sound():
    r = load("uefa_staging_report.json")
    for k, per in (("UCL", 8), ("UEL", 8), ("UECL", 6)):
        x = r[k]
        assert x["teams"] == 36 and x["expected_per_team"] == per and x["teams_with_wrong_count"] == [] and x["teams_not_balanced_home_away"] == [] and x["duplicate_pairings"] == 0 and x["undated"] == 0 and x["scores_implausible"] == 0
        assert x["new_results_beyond_dataset"] == 18 and x["dataset_rows_missing_from_staging"] == []
    assert r["UEL"]["unresolved_identities"] == [["NK Celje", "no_country"]] and r["UCL"]["unresolved_identities"] == [] and r["UECL"]["unresolved_identities"] == []


@needs
def test_the_private_rating_refresh_reproduces_production_and_is_chronological():
    r = load("rating_refresh_report.json")
    assert all(v is True for v in r["A_parity_with_production_processed"].values())
    assert r["C_chronology"]["rows_whose_pre_rating_is_not_the_previous_post"] == 0 and r["C_chronology"]["first_match_rating_is_1500"] and r["C_chronology"]["dates_sorted_in_match_order"]
    assert r["B_rows"]["last_date_after"] == "2026-10-06" and r["B_rows"]["matches_after"] > r["B_rows"]["matches_before"] and r["B_new_teams"] == ["Rouet-Provence"]
    assert all(v is True for v in r["D_production_processed_untouched"].values())
    assert all(p[3] == "ok" for p in r["D_predictions_before_production_ratings"] + r["D_predictions_after_private_refresh"])
    assert r["D_predictions_after_private_refresh"][0][4] == "2026-10-06" and r["D_predictions_before_production_ratings"][0][4] == "2026-06-02"
