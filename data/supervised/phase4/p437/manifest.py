"""Phase 4.34: proposed GitHub contents (read-only; nothing is staged or committed). Classifies every project file as GIT (normal), LFS (Git LFS) or EXCLUDE with a reason, and estimates the upload size.
Writes proposed_manifest.csv (path, bytes, decision, rule) and exclusions_summary.csv; prints totals. Rules are ordered; the first match wins."""
import csv
import os
import re
import zlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent / "out"
MIB = 1024 * 1024
LFS_THRESHOLD = 50 * MIB

# (regex on posix path, decision, rule description)  decision: X = exclude, G = git, L = force LFS if present
RULES = [
    (r"^(\.venv|\.git)/", "X", "environment / git internals"),
    (r"(^|/)node_modules/", "X", "npm dependencies (npm ci restores them)"),
    (r"^frontend/dist/", "X", "build output (npm run build)"),
    (r"(^|/)__pycache__/|\.pyc$", "X", "bytecode cache"),
    (r"^data/supervised/pytest_tmp/", "X", "test scratch"),
    (r"^data/backups/", "X", "database backups (rollback copies, not source)"),
    (r"^logs/", "X", "runtime logs"),
    (r"^config/contact\.local$|^\.env$|(^|/)\.env\.local$", "X", "secret / personal contact / machine-local environment"),
    (r"^data/run/", "X", "runtime lock files"),
    (r"\.sqlite(-wal|-shm)?$", "X", "SQLite database: decision pending (see report section 5)"),
    (r"^docs/baseline/capture_2026-10-20/", "X", "baseline isolated-run captures: repeated copies of data already in the repository"),
    (r"^data/processed/(confidence_gate_v212_lineup_audit|friendlies_v24_confirmed_lineups|friendlies_v24_predictions|friendlies_v24_provider_fixture_matches|friendlies_v24_weather_context|road_to_26_v24_provider_fixture_matches|v25_confirmed_lineups_live|v25_data_quality_live|v25_fixtures_live|v25_match_predictions_live|v25_odds_snapshot_live|v25_player_availability_live|v25_postmatch_results_live|v25_provider_status_live|v25_team_strength_live|v25_weather_context_live|v27_v25_comparison|worldcup_matchday_v29_lineup_snapshots|worldcup_matchday_v29_lineups)\.csv$", "X", "API-Football-derived (19 tracked files): redistribution rights unverified"),
    (r"statsbomb", "X", "StatsBomb-derived: user agreement 1.2.1"),
    (r"^data/supervised/phase4/(p413/date_disputes|p420/staging/(date_dispute_resolution|held_[A-Z0-9]+|staged_results_(EPL|LIGUE1|SERIEA))|p423/staging/(date_reconciliation|proposed_changes))\.csv$", "X", "carry football-data.co.uk / FixtureDownload / football-data.org columns: sanitized copies needed (see report section 6)"),
    (r"(^|/)[^/]*(footballdatauk|fixturedownload)[^/]*\.(csv|json|txt|html)$", "X", "football-data.co.uk / FixtureDownload raw copies or unmatched-row extracts: provider terms (private use, no redistribution)"),
    (r"^data/snapshots/footballdata/", "X", "football-data.org API responses: provider terms forbid redistribution"),
    (r"^data/raw/statsbomb/", "X", "StatsBomb Open Data: user agreement 1.2.1 forbids distributing the data"),
    (r"^data/raw/fifa/", "X", "copy of a FIFA web page (not redistributable)"),
    (r"^data/supervised/rules_research/", "X", "copyrighted league regulation PDFs and text (URLs and SHA-256 are in config/season_rules.json)"),
    (r"^FootIQ_Dataset_Submission/_raw_sources/", "X", "copies of upstream repositories (re-clone from RAW_SOURCES_MANIFEST.csv; RSSSF and StatsBomb terms)"),
    (r"^FootIQ_Dataset_Submission/_build/work/", "X", "regenerable intermediate tables"),
    (r"^FootIQ_Dataset_Submission/(04_Football_Players|05_Player_Match_Statistics|08_Player_Team_Memberships|14_StatsBomb_Match_Index|06_Teams|07_Competitions)\.csv$", "X", "contain StatsBomb-derived rows (replaced by generated CC0-only extracts, see report)"),
    (r"^FootIQ_Dataset_Submission\.zip$", "X", "redundant archive (already deleted)"),
    (r"^FootIQ_ML_Data_Verification/player_form_v1/PLAYER_(RECENT_FORM|SEASON_STATS)_STATSBOMB", "X", "StatsBomb-derived player tables"),
    (r"^FootIQ_ML_Data_Readiness/_build/work/", "X", "regenerable intermediate pickles (172 MiB data_all.pkl etc.)"),
    (r"^FootIQ_ML_Training_Preparation/_build/work/(E_final|calendar_audit_rows)\.pkl$", "X", "regenerable intermediate pickles"),
    (r"^FootIQ_Club_Model_Development_v2/_work/(?!features_v2_meta\.json$)", "X", "intermediate feature tables (features_v2_meta.json is kept: loaded by the app)"),
    (r"^FootIQ_Club_Model_Development_v2/source_adapters_r1/pilot/", "X", "pilot downloads and 110 MiB pickles"),
    (r"^FootIQ_Club_Model_Development_v2/matched_v1_prospective_r1/ingestion/runs/.*\.pkl$", "X", "110-117 MiB refreshed-universe pickles (replayable)"),
    (r"^FootIQ_Club_Model_Development_v2/final_refit_v2_r1/training_feature_table_v2_r1\.pkl$", "X", "61 MiB intermediate feature table (already ignored by the repository)"),
    (r"^data/supervised/phase4/p417/(private_ratings|staging)/", "X", "archived international staging copies (duplicates of data/raw and data/processed)"),
    (r"^data/supervised/footiq\.before-sync", "X", "deleted snapshot"),
    (r"^data/supervised/(?!phase3/|phase4/)", "X", "loose Oct-25 debug output"),
    (r"^data/supervised/phase4/.*\.(sqlite|pkl|zip)$", "X", "binary work files"),
    (r"\.(log)$", "X", "log file"),
]
LFS_PATTERNS = [r"^FootIQ_ML_Training_Preparation/_build/work/V_universe\.pkl$"]
G_ROOTS = ("app/", "config/", "frontend/", "tests/", "scripts/", "outputs/", "docs/", "data/", "FootIQ_", "scratch/", ".claude/")
ROOT_FILES = {"DATA_LICENSES.md", "README.md", "PROJECT.md", "README_SHARE.md", "SHARE_MANIFEST.sha256", "requirements-share.txt", ".env.example", "pytest.ini", ".gitignore", ".gitattributes", "World_Cup_Prediction_Model_Project_Journey.pdf", "World_Cup_Prediction_Model_Sources_and_Provenance.pdf"}


def decide(rel, size):
    for rx, dec, why in RULES:
        if re.search(rx, rel):
            return "EXCLUDE", why
    if "/" not in rel:
        return ("GIT", "root file") if rel in ROOT_FILES else ("EXCLUDE", "not a project file")
    if not rel.startswith(G_ROOTS):
        return "EXCLUDE", "outside the project folders"
    if re.search("|".join(LFS_PATTERNS), rel) or size >= LFS_THRESHOLD:
        return "LFS", ">= 50 MiB or required pickle (GitHub warns at 50 MiB, blocks at 100 MiB)"
    return "GIT", "source, document, small dataset or evaluation artifact"


def skip_dir(d):
    return d in {".venv", ".git", "node_modules", "__pycache__"}


rows, excl = [], defaultdict(lambda: [0, 0])
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if not skip_dir(d) and not (Path(dp).relative_to(ROOT).as_posix() == "docs/baseline" and d == "capture_2026-10-20") and not Path(dp).relative_to(ROOT).as_posix().startswith(("data/backups", "data/supervised/pytest_tmp"))]
    for f in fn:
        p = Path(dp) / f
        try:
            s = p.stat().st_size
        except OSError:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(("data/supervised/phase4/p434/", "data/supervised/phase4/p437/out/")):
            continue
        dec, why = decide(rel, s)
        rows.append((rel, s, dec, why))
        if dec == "EXCLUDE":
            excl[why][0] += 1
            excl[why][1] += s
with open(HERE / "proposed_manifest.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["path", "bytes", "decision", "rule"])
    w.writerows(rows)
with open(HERE / "exclusions_summary.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["reason", "files", "bytes"])
    for k, (n, b) in sorted(excl.items(), key=lambda x: -x[1][1]):
        w.writerow([k, n, b])
tot = defaultdict(lambda: [0, 0])
for rel, s, dec, why in rows:
    tot[dec][0] += 1
    tot[dec][1] += s
for d, (n, b) in tot.items():
    print(f"{d:8s} {n:6d} files {b / 1e6:9.1f} MB")
# upload estimate: deflate every GIT file (binary and already-compressed kinds counted as stored)
est = 0
for rel, s, dec, why in rows:
    if dec != "GIT":
        continue
    if rel.lower().endswith((".png", ".jpg", ".pdf", ".zip", ".woff2", ".gz")):
        est += s
        continue
    c = zlib.compressobj(6)
    n = 0
    with open(ROOT / rel, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            n += len(c.compress(chunk))
    est += n + len(c.flush())
print(f"GIT objects (compressed estimate): {est / 1e6:.1f} MB")
lfs = [(r[0], r[1]) for r in rows if r[2] == "LFS"]
print("LFS files:")
for p, s in sorted(lfs, key=lambda x: -x[1]):
    print(f"  {s / MIB:8.1f} MiB  {p}")
print(f"LFS total {sum(s for _, s in lfs) / MIB:.1f} MiB")
