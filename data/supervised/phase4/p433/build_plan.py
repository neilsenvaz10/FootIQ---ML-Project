"""Phase 4.33: builds the cleanup plan from inventory.csv (read-only). Writes
  safe_delete_manifest.csv   exact files proposed as SAFE TO DELETE (path, bytes, group, reason)
  cleanup_plan.csv           one row per group: class, path/pattern, files, bytes, purpose, reason, evidence
No file is touched."""
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
rows = []
for r in csv.DictReader(open(HERE / "inventory.csv", encoding="utf-8")):
    r["bytes"] = int(r["bytes"])
    rows.append(r)

SAFE = [
    ("S1", "Python bytecode caches (__pycache__, *.pyc) outside .venv", lambda p: "/__pycache__/" in p or p.endswith(".pyc"),
     "Regenerated automatically by Python on the next import; contains no information. 0 git-tracked files; includes 3.14 and 3.12 caches."),
    ("S2", "pytest scratch under data/supervised/pytest_tmp (contents only)", lambda p: p.startswith("data/supervised/pytest_tmp/"),
     "Temporary folders of earlier test runs (tmp_path copies, snapshots). tests/conftest.py recreates the directory and every run writes fresh files; the folder itself stays. 0 git-tracked files; no report or unique data inside (extensions: .sqlite test copies, .json test snapshots)."),
    ("S3", "frontend/dist production build output", lambda p: p.startswith("frontend/dist/"),
     "Output of `npm run build`; regenerable; git-ignored; not served or read by the backend, the dev server or any test (the application is started with `npm run dev`)."),
]
safe_rows, plan = [], []
claimed = set()
for gid, name, f, reason in SAFE:
    sel = [r for r in rows if f(r["path"]) and r["path"] not in claimed]
    for r in sel:
        claimed.add(r["path"])
        safe_rows.append((r["path"], r["bytes"], gid, reason))
    tr = sum(1 for r in sel if r["git_tracked"] == "1")
    plan.append((gid, "SAFE TO DELETE", name, len(sel), sum(r["bytes"] for r in sel), "regenerable build or test byproduct", reason, f"git-tracked files in group: {tr}"))

APPROVAL = [
    ("A1", "data/backups/p424_pre_reconcile_20261028/", lambda p: p.startswith("data/backups/p424_pre_reconcile_20261028/"), "database backup before the Phase 4.24 reconciliation (verified, hash in SHA256.txt)", "Backups need your explicit approval. Superseded by the newer verified backups p428 and p430 (both contain the reconciled data); only needed to undo the 4.24 reconciliation.", "recommend delete; keep p428 (clean state) and p430 (state with your saved records)"),
    ("A2", "data/supervised/footiq.before-sync.sqlite (+ -shm, -wal)", lambda p: p.startswith("data/supervised/footiq.before-sync.sqlite"), "store snapshot taken on 25 Oct before the first synchronisation", "A third database copy kept by the Phase 4.26 decision; referenced only by audit scripts and P4_25/P4_26 reports; not used by app or tests. Regenerable in principle from the baseline with `app/store/build.py --fresh`, but it records the pre-sync state.", "recommend delete if you do not need the pre-sync snapshot"),
    ("A3", "docs/baseline/capture_2026-10-20/isolated_execution/ (run1, run2, tests_verified copies)", lambda p: p.startswith("docs/baseline/capture_2026-10-20/isolated_execution/"), "evidence capture of the ORIGINAL baseline project executed in isolation three times", "1,699 files, mostly the same data and outputs repeated per run (duplicate groups: data/raw x4, data/processed x4, PDFs x4, xlsx x4, v27 model x4). The manifests, dataset inventory and traces outside this folder are separate. Evidence that the original baseline was reproducible; archived competition material.", "recommend keep run1 only (about 100 MB saved) or delete all three if the baseline reproducibility evidence is not needed"),
    ("A4", "data/supervised/phase4/p417/private_ratings/ and staging/*/unpacked/", lambda p: p.startswith("data/supervised/phase4/p417/private_ratings/") or ("data/supervised/phase4/p417/staging/" in p and "/unpacked/" in p), "archived international rating and staging copies (Phase 4.17)", "Byte-identical to data/processed and data/raw files in 5 copies (see duplicates). tests/test_phase417_evidence.py reads the p417 folder (it skips when the folder is absent); app/store/uefa_import.py mentions p417 staging.", "recommend delete after checking the test still skips cleanly"),
    ("A5", "FootIQ_Club_Model_Development_v2/matched_v1_prospective_r1/", lambda p: p.startswith("FootIQ_Club_Model_Development_v2/matched_v1_prospective_r1/"), "prospective-study ingestion data (academic evidence)", "242 MB of ingestion tables; reports of the same folder (protocol, manifest, sensitivity CSVs) are small. Referenced by app/store/rehearse_openligadb.py (a rehearsal tool) and docs.", "keep the reports, optional to delete `ingestion/` (242 MB)"),
    ("A6", "FootIQ_Club_Model_Development_v2/_work/ (except features_v2_meta.json)", lambda p: p.startswith("FootIQ_Club_Model_Development_v2/_work/") and not p.endswith("features_v2_meta.json"), "intermediate feature tables and out-of-fold predictions of the v2 study", "`features_v2_meta.json` is loaded by the application (kept). The rest regenerates from the v2 scripts and the baseline data; used only for rebuilding the study.", "optional delete (about 202 MB), reproducibility cost: rebuild from scripts"),
    ("A7", "FootIQ_Club_Model_Development_v2/source_adapters_r1/pilot/", lambda p: p.startswith("FootIQ_Club_Model_Development_v2/source_adapters_r1/pilot/"), "adapter pilot snapshots (OpenLigaDB / Wikipedia responses)", "Adapter code (`footiq_sources`) is imported by the application and is kept; only the pilot downloads would go. Provenance of the first source trials.", "optional delete (about 221 MB)"),
    ("A8", "FootIQ_ML_Data_Readiness/_build/work/", lambda p: p.startswith("FootIQ_ML_Data_Readiness/_build/work/"), "pickles from the from-scratch dataset build (data_all.pkl 181 MB, M_of 82 MB, U_of 78 MB)", "Only the `_build/*.py` scripts reference these; the final datasets (04a..08 CSVs) are kept. Needed only to rerun the dataset build from the raw sources.", "optional delete (about 351 MB), reproducibility cost: rerun s3..s9 scripts"),
    ("A9", "FootIQ_ML_Training_Preparation/_build/work/ (E_final.pkl, calendar_audit_rows.pkl, logs)", lambda p: p.startswith("FootIQ_ML_Training_Preparation/_build/work/") and not p.endswith("V_universe.pkl"), "training-preparation build intermediates", "`V_universe.pkl` (117 MB) is KEPT: `app/store/baseline.py` uses it for the from-scratch store build and `predict.py` falls back to it. E_final.pkl and the calendar audit rows are used only by p2_build/p3_tests/p4_docs.", "optional delete (about 105 MB)"),
    ("A10", "FootIQ_ML_Data_Verification/player_form_v1/", lambda p: p.startswith("FootIQ_ML_Data_Verification/player_form_v1/"), "player recent-form and season-statistics tables", "For the planned player module, which is not implemented; referenced only by its own verification scripts and the archive README.", "optional delete (about 149 MB) or keep as data-engineering evidence"),
    ("A11", "FootIQ_Dataset_Submission/_build/work/", lambda p: p.startswith("FootIQ_Dataset_Submission/_build/work/"), "intermediate tables of the dataset-submission build (club_matches_all.csv 117 MB, player match tables)", "The final submission CSVs and the _build scripts are kept; these intermediates regenerate from `_raw_sources` with the build scripts.", "optional delete (about 174 MB)"),
    ("A12", "FootIQ_Dataset_Submission.zip (root)", lambda p: p == "FootIQ_Dataset_Submission.zip", "compressed copy of the dataset-submission folder (git-ignored)", "Redundant with the unpacked `FootIQ_Dataset_Submission/` CSVs; you said no ZIP is needed. Referenced by dataset manifests only.", "recommend delete (18 MB) if the folder is your deliverable"),
    ("A13", "docs/mini-project/phase4/p4.1 ... p4.6, audit (117 screenshots)", lambda p: p.startswith("docs/mini-project/phase4/p4.") or p.startswith("docs/mini-project/phase4/audit/"), "screenshots of EARLIER interface versions (eleven-competition design)", "Not valid evidence of the final application; but the P4_1..P4_6 checkpoint reports link to them, so deleting breaks those links.", "optional; recommend keep until final screenshots exist, then delete with the link note"),
    ("A14", "logs/ and loose Oct-25 debug output in data/supervised/", lambda p: p.startswith("logs/") or (p.startswith("data/supervised/") and p.count("/") == 2 and (p.endswith(".log") or "full_backend_run" in p or p.endswith(("rehearsal_run_output.txt", "investigation_output.txt", "investigation_analysis.txt")))), "old backend/supervisor logs and rehearsal output", "Tiny (about 0.1 MB); referenced by P4_14 / P4_15 reports as examples; no unique data.", "recommend delete; low value"),
    ("A15", "Rollback copies created by earlier phases: data/supervised/phase4/p428|p429|p432/before, data/backups/p418_rollback..., p420_code_before", lambda p: ("/before/" in p and p.startswith("data/supervised/phase4/p4")) or p.startswith("data/backups/p418_rollback_20261028/") or p.startswith("data/backups/p420_code_before/"), "before-copies of documents and code changed in Phases 4.18-4.32", "Needed only to undo those edits; small.", "keep until you accept the final documents"),
    ("A16", "Older planning and rehearsal reports in docs/mini-project (UPGRADE_PLAN, PHASE4_UI_AUDIT_AND_PLAN, SOURCE_INVESTIGATION, OPENLIGADB_IMPORT_REHEARSAL, OPENLIGADB_PL_LALIGA_FINDINGS, DATA_FRESHNESS_OPTIONS, FOOTBALL_DATA_ORG_CHECKLIST, IMPLEMENTATION_STATUS, MINI_PROJECT_PLAN)", lambda p: p in {f"docs/mini-project/{n}" for n in ("UPGRADE_PLAN.md", "PHASE4_UI_AUDIT_AND_PLAN.md", "SOURCE_INVESTIGATION.md", "OPENLIGADB_IMPORT_REHEARSAL.md", "OPENLIGADB_PL_LALIGA_FINDINGS.md", "DATA_FRESHNESS_OPTIONS.md", "FOOTBALL_DATA_ORG_CHECKLIST.md", "IMPLEMENTATION_STATUS.md", "MINI_PROJECT_PLAN.md")}, "early plans and investigation notes", "Superseded by `docs/mini-project/final/` but they record decisions and source evidence; some are linked from phase reports.", "keep unless you want a leaner docs folder (about 170 KB)"),
]
for gid, name, f, purpose, reason, rec in APPROVAL:
    sel = [r for r in rows if f(r["path"]) and r["path"] not in claimed]
    plan.append((gid, "REQUIRES APPROVAL", name, len(sel), sum(r["bytes"] for r in sel), purpose, reason, rec))

PRESERVE = [
    ("P1", "app/, config/*.json, frontend/src, frontend/tests, tests/, pytest.ini, requirements-share.txt, .env.example, .gitignore, .gitattributes, .claude/", "runtime code, configuration, tests", "imported or executed by the application and the 579 + 375 tests"),
    ("P2", "data/footiq.sqlite", "production database", "never touched; hash 9d40c8ef..."),
    ("P3", "data/backups/p428_fresh_20261028/ and p430_pre_restart_20261028/", "verified recoverable backups", "at least one verified backup must remain"),
    ("P4", "FootIQ_Club_Model_Baseline_v1/, FootIQ_Club_Model_Development_v2/final_refit_v2_r1/, _scripts/, reports", "frozen models, feature code, evaluation reports", "frozen hashes verified; code imported by the predictor"),
    ("P5", "FootIQ_ML_Data_Readiness 04a..08 CSVs, FootIQ_ML_Training_Preparation datasets and reports, FootIQ_ML_Data_Verification reports", "datasets and reports of the ML data pipeline", "inputs of store build and evaluation"),
    ("P6", "FootIQ_Dataset_Submission CSVs, QA reports, manifests and _raw_sources (incl. upstream READMEs, licences, statsbomb LICENSE.pdf)", "dataset deliverable and provenance", "attribution and licence evidence"),
    ("P7", "data/supervised/rules_research/ (13 PDFs, 25 MB)", "official league regulations behind the verified rule profiles", "hashes are recorded in config/season_rules.json; unique provenance"),
    ("P8", "data/raw, data/processed, data/snapshots, data/model_artifacts, outputs/, scripts/, root PDFs, PROJECT.md, README_SHARE.md, SHARE_MANIFEST.sha256", "archived-competition research data and models, snapshots, request ledger", "kept by the Phase 4.18 decision; snapshots and the request ledger are provenance"),
    ("P9", "docs/mini-project/final, phase4 reports (P4_*.md), PHASE1-3 reports, API_REFERENCE, FRONTEND_INTEGRATION, docs/architecture, docs/data-sources, docs/archive", "final and historical documentation", "unique evidence; links verified after cleanup"),
    ("P10", "app/worldcup_sim.py, app/bracket.py, frontend Simulator.jsx and Bracket.jsx", "archived-competition code", "not used by the six-competition UI but imported by tests/test_miniproject.py and frontend/tests/app.test.jsx; removing them would change tests and application code (not allowed in this task)"),
    ("P11", "scratch/ (Node probe and e2e scripts)", "verification scripts", "TESTING_REPORT cites e2e_workflow_test.mjs"),
]
for gid, name, purpose, reason in PRESERVE:
    plan.append((gid, "MUST PRESERVE", name, "", "", purpose, reason, ""))

with open(HERE / "safe_delete_manifest.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["path", "bytes", "group", "reason"])
    w.writerows(safe_rows)
with open(HERE / "cleanup_plan.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "class", "path_or_pattern", "files", "bytes", "purpose", "reason", "evidence_or_recommendation"])
    w.writerows(plan)
for p in plan:
    if p[1] != "MUST PRESERVE":
        print(f"{p[0]:4s} {p[1]:18s} {p[3]:6d} files {p[4] / 1e6:9.1f} MB  {p[2][:78]}")
print("SAFE total:", len(safe_rows), "files", round(sum(r[1] for r in safe_rows) / 1e6, 1), "MB")
print("APPROVAL total:", round(sum(p[4] for p in plan if p[1] == "REQUIRES APPROVAL") / 1e6, 1), "MB")
