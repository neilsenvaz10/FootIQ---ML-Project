"""Benchmark v1 (the original scoreline benchmark) is preserved: its files still hash to the values recorded on 2026-10-25 (before Protocol v2 and v3 existed), and its verdict stays "failed".
The hashes are written here on purpose so that changing a benchmark file, or this register, is visible in a diff. Files that are not present (a fresh checkout without the git-ignored data folder) are skipped."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_V1 = {
    "docs/mini-project/PHASE3_SCORELINE_BENCHMARK.md": "48ebb7b05c9bb1ed2f1a4a616928adb9f63de24cacf2a45384c20028f81a8997",
    "data/supervised/phase3/m2_distribution_report.json": "05fe9b100b782f65be27beda2a431d2c3d107beea661548d5b135aa35da97b97",
    "data/supervised/phase3/m2b_report.json": "23741826680ed67cb091f03aaf2d3d31d868915e051ac4d069b84ec9b04765d3",
    "data/supervised/phase3/m2_rule_power.json": "777934c0f3a7e12eb3551f80927a14baf8863c594b3141c09a0e48a965bee93a",
    "data/supervised/phase3/m2_s4_tuning.json": "5bd8dc1fbb13b45a051aaed08fb49d43e2d97e0ec9dd222de8b71ada1b6e4158",
    "data/supervised/phase3/m2_matches.pkl": "3c381bd303f0cb77033bd6474c45569b5dc36c2c53804a55056268ace3878f2a",
}


@pytest.mark.parametrize("rel,expected", sorted(BENCHMARK_V1.items()))
def test_the_original_benchmark_files_are_unchanged(rel, expected):
    p = ROOT / rel
    if not p.exists():
        pytest.skip(f"{rel} is not present in this checkout")
    assert hashlib.sha256(p.read_bytes()).hexdigest() == expected, f"{rel} changed: Benchmark v1 must stay exactly as it was"


def test_the_original_verdict_is_still_failed_and_no_scoreline_method_is_approved():
    cfg = json.loads((ROOT / "config" / "season_sim.json").read_text(encoding="utf-8"))
    assert cfg["scoreline_method"] is None
    assert cfg["scoreline_validation"]["status"] == "failed_predeclared_criteria" and cfg["scoreline_validation"]["approved_by_user"] is False
    doc = ROOT / "docs" / "mini-project" / "PHASE3_SCORELINE_BENCHMARK.md"
    if doc.exists():
        text = doc.read_text(encoding="utf-8").lower()
        assert "fail" in text
