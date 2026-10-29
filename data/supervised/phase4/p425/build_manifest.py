"""Phase 4.25: builds the PROPOSED cleanup manifest (cleanup_manifest.csv) from inventory.csv. READ-ONLY: it only reads the inventory and writes the manifest; nothing is moved, changed or deleted.
Every row says what the files are, whether anything loads them, whether they can be regenerated, the risk and the recommended action; sizes are the sum of the files matched."""
import csv
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
inv = pd.read_csv(HERE / "inventory.csv")
P = inv.path

SQL = r"\.sqlite(-wal|-shm)?$"


def m(pattern=None, prefix=None, exclude=None):
    sel = pd.Series(True, index=inv.index)
    if prefix:
        sel &= P.str.startswith(prefix)
    if pattern:
        sel &= P.str.contains(pattern, regex=True)
    if exclude:
        sel &= ~P.str.contains(exclude, regex=True)
    return sel


ITEMS = [
    # ---- Category A: confirmed unused, regenerable temporary files
    ("A1", "A", "data/supervised/phase4/p44/pytest_baseline/", m(prefix="data/supervised/phase4/p44/pytest_baseline/"), "pytest working folders of the Phase 4.4 baseline run (copies of the store and synthetic test databases)", "no: 0 references in app, tests, scripts, config",
     "yes: pytest recreates them", "none", "delete the folder"),
    ("A2", "A", "data/supervised/pytest_tmp/pytest-of-DELL/ (contents)", m(prefix="data/supervised/pytest_tmp/pytest-of-DELL/"), "pytest's configured temp root (tests/conftest.py); failed-run folders", "the folder itself is created by tests/conftest.py; its contents are not",
     "yes", "none", "delete the contents, keep the pytest_tmp folder"),
    ("A3", "A", "data/supervised/phase4/p44/chrome-profile*, p46/chrome-profile-p46", m(pattern=r"^data/supervised/phase4/(p44/chrome-profile(-p45)?|p46/chrome-profile-p46)/"), "headless-browser profiles from the Phase 4.4-4.6 UI probes (cache, model stores)", "no: 0 references",
     "yes: a new profile is created on demand", "none", "delete the folders"),
    ("A4", "A", "data/supervised/phase4/p44/production-build*", m(pattern=r"^data/supervised/phase4/p44/production-build(-final|-release)?/"), "old frontend production builds", "no (only named in the P4.4 report)", "yes: npm run build", "none", "delete the folders"),
    ("A5", "A", ".pytest_cache/", m(prefix=".pytest_cache/"), "pytest cache", "no", "yes", "none", "delete"),
    # ---- Category B: redundant database copies
    ("B1", "B", "data/backups/*.sqlite (all except p424_pre_reconcile_20261028)", m(pattern=r"^data/backups/(footiq\.2026\d+T\d+Z\.[a-z\-]+\.sqlite|p42[012]_[a-z_0-9]+/footiq\.sqlite)(-wal|-shm)?$"),
     "older pre-change backups of the production store (Oct 27 pre-sync / pre-activation / pre-import, p420, p421, p422 x2); each is superseded by a later state and by p424", "no: only the guards of the importers compare a backup you pass them",
     "no (they are past states) but no longer needed: p424 restores the current system", "low", "delete the .sqlite files; keep their .json / SHA256.txt notes"),
    ("B2", "B", "data/supervised/phase4/p419|p421|p423/rehearsal/*.sqlite", m(pattern=r"^data/supervised/phase4/p4(19|21|23)/rehearsal/.*" + SQL), "private rehearsal copies of production made by my import rehearsals", "no (their reports are kept)", "yes: the rehearse_*.py scripts recreate them in under 2 minutes", "none", "delete the .sqlite files, keep reports and scripts"),
    ("B3", "B", "data/supervised/phase4/p410|p412|p49|p48d private copies and restore tests", m(pattern=r"^data/supervised/phase4/(p410/private_copy|p412/private_copy|p49/private_copy|p49/restore_test|p48d/restore_test_activation)" + SQL),
     "private trial copies and restore tests of Phase 4.8-4.12", "no: the scripts that write them do not read them back", "yes (each is a copy of a store state; the scripts recreate equivalents)", "low", "delete the .sqlite files"),
    ("B4", "B", "data/supervised/phase4/p44|p45|p46 preview.sqlite and tests.sqlite", m(pattern=r"^data/supervised/phase4/p4[456]/(preview|tests)" + SQL), "UI preview and test databases of Phase 4.4-4.6", "no", "yes (copies of the store; the preview server recreates them)", "low", "delete the .sqlite files"),
    ("B5", "B", "data/supervised/{live_test_copy,demo,rehearsal/*,production_import/*.backup}.sqlite", m(pattern=r"^data/supervised/(live_test_copy|demo|rehearsal/footiq\.(before|rehearsal|rehearsal_repeat)|production_import/footiq\.\d+T\d+Z\.backup)" + SQL),
     "early demo, live-test, rehearsal and import-backup databases of Oct 25", "no", "no (past states of Oct 25) but fully superseded; the clean baseline is kept as footiq.before-sync.sqlite", "low", "delete the .sqlite files; keep reports and logs"),
    # ---- Category C: optional historical / archived: needs a separate decision
    ("C1", "C", "FootIQ_Dataset_Submission/_raw_sources/statsbomb_open_data/ (whole clone)", m(prefix="FootIQ_Dataset_Submission/_raw_sources/statsbomb_open_data/"), "shallow git clone of statsbomb/open-data (commit 4b73468f, 2026-09-07) used once to build the player-statistics dataset",
     "no: not used by the application, tests or models (only FootIQ_Dataset_Submission/_build/build_players_statsbomb.py; the built CSVs stay)", "yes, with network: git clone --depth 1 https://github.com/statsbomb/open-data.git and check out 4b73468f (recorded in RAW_SOURCES_MANIFEST.csv)", "medium: removes the raw source of the dataset you submitted",
     "your decision: keep for reproducibility, or delete and keep the recorded commit"),
    ("C1a", "C", "...statsbomb_open_data/.git (history only)", m(prefix="FootIQ_Dataset_Submission/_raw_sources/statsbomb_open_data/.git/"), "git object store of that clone", "no", "yes (re-clone)", "low", "smaller option: delete only .git (the JSON files stay)"),
    ("C2", "C", "FootIQ_Club_Model_Development_v2/source_adapters_r1/pilot/", m(prefix="FootIQ_Club_Model_Development_v2/source_adapters_r1/pilot/"), "pilot snapshots of the adapter research", "no (the adapters' code under footiq_sources/ is loaded; pilot data is not)", "partly", "low", "optional"),
    ("C3", "C", "FootIQ_Club_Model_Development_v2/matched_v1_prospective_r1/", m(prefix="FootIQ_Club_Model_Development_v2/matched_v1_prospective_r1/"), "prospective-evaluation working data of the v2 model study", "no", "yes (scripts)", "low-medium: academic evidence", "optional"),
    ("C4", "C", "FootIQ_Club_Model_Development_v2/_work/ (except features_v2_meta.json)", m(prefix="FootIQ_Club_Model_Development_v2/_work/", exclude=r"features_v2_meta\.json$"), "intermediate feature tables of the v2 study", "only _work/features_v2_meta.json is opened by the application", "yes (scripts)", "medium: needed to rerun the v2 study", "optional"),
    ("C5", "C", "FootIQ_ML_Data_Readiness/_build/", m(prefix="FootIQ_ML_Data_Readiness/_build/"), "build scripts and work files of the data-readiness stage", "no at runtime (only to rebuild the store from scratch)", "yes", "medium: rebuild ability", "keep unless you accept losing a from-scratch rebuild"),
    ("C6", "C", "FootIQ_ML_Training_Preparation/_build/ (except feature_contract.py)", m(prefix="FootIQ_ML_Training_Preparation/_build/", exclude=r"feature_contract\.py$"), "training-preparation work files incl. V_universe.pkl", "feature_contract.py is imported by the application; V_universe.pkl only by a from-scratch store build", "yes", "medium", "keep unless you accept losing a from-scratch rebuild"),
    ("C7", "C", "docs/baseline/capture_2026-10-20/", m(prefix="docs/baseline/capture_2026-10-20/"), "baseline evidence capture (five repeated test-run copies of the same data files)", "no", "no (evidence of the 2026-10-20 baseline)", "medium: audit trail", "optional: keep the manifest, dedupe the repeated copies"),
    ("C8", "C", "FootIQ_ML_Data_Verification/player_form_v1/", m(prefix="FootIQ_ML_Data_Verification/player_form_v1/"), "player-form tables of the data-verification stage", "no", "yes (scripts)", "low", "optional"),
    ("C9", "C", "data/supervised/phase4/p417/staging/*/unpacked/ and private_ratings/ (archived international data)", m(pattern=r"^data/supervised/phase4/p417/(staging/[a-z0-9]+/unpacked/|private_ratings/)"), "unpacked national-team archives and private rating refresh of the removed competitions", "tests/test_phase417_evidence.py reads only the evidence files and zip sizes, not these", "yes (zips and scripts are kept)", "low", "optional"),
]
rows = []
for iid, cat, path, mask, purpose, used, regen, risk, action in ITEMS:
    sel = inv[mask]
    rows.append(dict(id=iid, category=cat, path=path, files=len(sel), bytes=int(sel.bytes.sum()), gb=round(sel.bytes.sum() / 1e9, 3), purpose=purpose, used_now=used, regenerable=regen, risk=risk, recommended_action=action))
df = pd.DataFrame(rows)
# every .sqlite file must be accounted for: A, B, or an explicit keep
claimed = pd.Series(False, index=inv.index)
for _, _, _, mask, *_ in ITEMS:
    claimed |= mask
keep = inv[P.str.contains(SQL, regex=True) & ~claimed]
print("SQLITE FILES NOT IN ANY REMOVAL ITEM (kept):")
for r in keep.sort_values("bytes", ascending=False).itertuples():
    if r.bytes > 1_000_000 or True:
        print(f"  {r.bytes / 1e6:9.1f} MB  {r.path}")
print()
print(df[["id", "category", "gb", "files", "path"]].to_string(index=False))
for c in "ABC":
    print(c, round(df[(df.category == c) & ~df.id.isin(["C1a"])].gb.sum(), 3), "GB")
df.to_csv(HERE / "cleanup_manifest.csv", index=False, encoding="utf-8-sig")
# the exact file list of categories A and B (what would be deleted), for the approval step
sel = pd.Series(False, index=inv.index)
for iid, cat, _, mask, *_ in ITEMS:
    if cat in ("A", "B"):
        sel |= mask
inv[sel][["path", "bytes"]].to_csv(HERE / "cleanup_manifest_files_AB.csv", index=False)
print("A+B file list:", int(sel.sum()), "files,", round(inv[sel].bytes.sum() / 1e9, 3), "GB")
