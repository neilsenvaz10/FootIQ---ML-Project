"""Phase 4.33: read-only reference search. For each candidate path token, counts files that mention it, split into runtime code (app, config, frontend/src), tests, other project code (*.py/*.js under FootIQ_*, scripts), and documentation (*.md, *.txt, *.json reports)."""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TOKENS = {
    "pytest_tmp": "pytest_tmp",
    "before-sync": "before-sync",
    "docs/baseline": "docs/baseline",
    "private_ratings": "private_ratings",
    "p417 (dir)": "phase4/p417",
    "V_universe": "V_universe",
    "E_final": "E_final.pkl",
    "_build/work": "_build/work",
    "Data_Readiness/_build": "FootIQ_ML_Data_Readiness/_build",
    "matched_v1_prospective_r1": "matched_v1_prospective_r1",
    "Development_v2/_work": "Development_v2/_work",
    "source_adapters_r1/pilot": "source_adapters_r1/pilot",
    "player_form_v1": "player_form_v1",
    "Dataset_Submission/_build": "FootIQ_Dataset_Submission/_build",
    "Dataset_Submission/_raw_sources": "_raw_sources",
    "FootIQ_Dataset_Submission.zip": "FootIQ_Dataset_Submission.zip",
    "data/backups": "data/backups",
    "data/snapshots": "data/snapshots",
    "data/raw": "data/raw",
    "data/processed": "data/processed",
    "outputs/": "outputs/",
    "hardened_logger_r2_draft": "hardened_logger_r2_draft",
    "shadow_integration_r1": "shadow_integration_r1",
    "frontend/dist": "frontend/dist",
    "logs/": "logs/",
    "scratch/": "scratch/",
    "scripts/": "scripts/",
    "rehearsal": "supervised/rehearsal",
    "production_import": "production_import",
}
SKIP = {".git", ".venv", "node_modules", "__pycache__", "pytest_tmp"}
EXT = {".py", ".js", ".jsx", ".json", ".md", ".txt", ".ini", ".ps1", ".csv", ".html", ".yml", ".yaml", ".cfg", ".toml"}


def kind(rel):
    if rel.startswith(("app/", "config/", "frontend/src/")):
        return "runtime"
    if rel.startswith(("tests/", "frontend/tests/")):
        return "tests"
    if rel.endswith((".py", ".js", ".jsx", ".ps1")):
        return "code"
    return "docs"


res = {k: {"runtime": [], "tests": [], "code": [], "docs": []} for k in TOKENS}
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in SKIP and not (d == "baseline" and "docs" in dp.replace("\\", "/") and False)]
    for f in fn:
        p = Path(dp) / f
        if p.suffix.lower() not in EXT:
            continue
        try:
            if p.stat().st_size > 3_000_000:
                continue
            s = p.read_text(encoding="utf-8", errors="ignore").replace("\\", "/")
        except OSError:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("data/supervised/phase4/p433/"):
            continue
        for k, tok in TOKENS.items():
            if tok in s:
                res[k][kind(rel)].append(rel)
for k, v in res.items():
    print(f"{k:32s} runtime {len(v['runtime']):3d} tests {len(v['tests']):3d} code {len(v['code']):3d} docs {len(v['docs']):4d}  " + (" | ".join((v['runtime'] + v['tests'])[:4]) if v['runtime'] or v['tests'] else ""))
import json
Path(__file__).with_name("refs.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
