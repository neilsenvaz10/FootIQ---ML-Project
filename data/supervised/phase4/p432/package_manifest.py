"""Phase 4.32: submission package manifest. Read-only on the project. Modes:
  package_manifest.py estimate                 -> writes submission_manifest.csv (path, tier, bytes) and prints raw size per tier plus a measured deflate estimate (nothing written to disk besides the csv)
  package_manifest.py build <dest> [tiers]     -> copies the listed tiers into <dest> (a NEW folder outside the project; refuses a non-empty folder). Originals are never modified.
Tiers: T1 runtime (needed to run), T2 data engineering and datasets, T3 models and evaluation, T4 documentation, T5 tests, T6 dataset submission zip.
Exclusions (never packaged): .venv, node_modules, dist, .git, caches, pytest folders, scratch, logs, backups, rehearsal copies, the raw StatsBomb clone, secrets (config/contact.local, .env), baseline capture copies."""
import csv
import fnmatch
import os
import shutil
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SKIP_DIRS = {".venv", "node_modules", "dist", ".git", "__pycache__", ".pytest_cache", "pytest_tmp", "scratch", "logs", "backups", "provider_cache", "pytest-of-DELL"}
SKIP_FILES = {"contact.local", ".env", ".DS_Store", "Thumbs.db"}
SKIP_SUFFIX = (".pyc", ".log", ".key", ".pem", ".sqlite-wal", ".sqlite-shm", ".p428before")


def walk(rel, keep=lambda p: True):
    base = ROOT / rel
    if base.is_file():
        yield base
        return
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f in SKIP_FILES or f.endswith(SKIP_SUFFIX):
                continue
            p = Path(dp) / f
            if keep(p):
                yield p


def small(limit):
    return lambda p: p.stat().st_size <= limit


MODEL_FILES = ["FootIQ_Club_Model_Baseline_v1/04_TEST_METRICS.csv", "FootIQ_Club_Model_Baseline_v1/05_FORWARD_HOLDOUT_METRICS.csv", "FootIQ_Club_Model_Baseline_v1/06a_LEAGUE_WISE_METRICS.csv"]
RUNTIME_FILES = [  # the 23 files the running application opens (Phase 4.25 runtime footprint) besides app/, config/ and the database
    "FootIQ_Club_Model_Development_v2/08_LEAGUE_GROUP_PERFORMANCE.csv", "FootIQ_Club_Model_Development_v2/_work/features_v2_meta.json", "FootIQ_ML_Data_Readiness/01_COMPETITION_SEASON_COVERAGE_MATRIX.csv",
    "FootIQ_ML_Training_Preparation/feature_contract_v1.1.json", "data/model_artifacts/v27/live_match_model.pkl"]


def entries():
    out = []
    add = lambda tier, paths: out.extend((tier, p) for p in paths)
    # T1 runtime
    add("T1", walk("app"))
    add("T1", walk("config"))
    add("T1", [p for p in walk("frontend") if p.relative_to(ROOT / "frontend").parts[0] in ("src", "index.html", "package.json", "package-lock.json", "vite.config.js", "README.md")])
    add("T1", [ROOT / "data" / "footiq.sqlite"])
    add("T1", walk("FootIQ_Club_Model_Baseline_v1/artifacts"))
    add("T1", walk("FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts"))
    add("T1", [ROOT / f for f in MODEL_FILES + RUNTIME_FILES])
    # project code the prediction runtime imports (found by the clean-install test): the feature and model modules
    add("T1", walk("FootIQ_Club_Model_Development_v2/_scripts"))
    add("T1", walk("FootIQ_Club_Model_Development_v2/source_adapters_r1/footiq_sources"))
    add("T1", walk("FootIQ_Club_Model_Development_v2/source_adapters_r1/config"))
    add("T1", [ROOT / "FootIQ_Club_Model_Development_v2/source_adapters_r1/MANIFEST.json"])
    add("T1", [p for p in (ROOT / "FootIQ_ML_Training_Preparation" / "_build").iterdir() if p.is_file() and p.suffix == ".py"])
    add("T1", [ROOT / f for f in ("requirements-share.txt", ".env.example", "README.md", "pytest.ini", ".gitignore", ".gitattributes")])
    # T2 data engineering pipeline and datasets
    add("T2", walk("scripts"))
    add("T2", [ROOT / "FootIQ_ML_Data_Readiness" / "04d_COMBINED_CLUB_MATCHES_v1.0.csv"])
    add("T2", walk("data/supervised/phase4", small(2_000_000)))
    add("T2", walk("data/snapshots"))
    add("T2", [p for p in walk("FootIQ_Club_Model_Development_v2/source_adapters_r1") if "pilot" not in p.relative_to(ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1").parts[:1]])
    # T3 models and evaluation
    add("T3", walk("FootIQ_Club_Model_Baseline_v1"))
    add("T3", walk("FootIQ_Club_Model_Development_v2/final_refit_v2_r1"))
    add("T3", [p for p in (ROOT / "FootIQ_Club_Model_Development_v2").iterdir() if p.is_file()])
    add("T3", [p for p in (ROOT / "FootIQ_ML_Training_Preparation").iterdir() if p.is_file() and p.stat().st_size < 5_000_000])
    add("T3", [p for p in walk("FootIQ_ML_Data_Verification") if p.suffix in (".md", ".csv", ".json") and p.stat().st_size < 5_000_000])
    add("T3", walk("outputs"))
    # T4 documentation
    add("T4", walk("docs/mini-project"))
    add("T4", walk("docs/architecture"))
    add("T4", walk("docs/data-sources"))
    add("T4", [ROOT / f for f in ("PROJECT.md", "README_SHARE.md", "SHARE_MANIFEST.sha256", "World_Cup_Prediction_Model_Sources_and_Provenance.pdf", "World_Cup_Prediction_Model_Project_Journey.pdf")])
    # T5 tests (backend tests, frontend tests, the few data files tests read)
    add("T5", walk("tests"))
    add("T5", walk("data/miniproject"))
    add("T5", walk("frontend/tests"))
    add("T5", [p for p in walk("data/supervised/phase3") if p.name in ("m2b_report.json", "m2_s4_tuning.json", "m2_rule_power.json", "m2_matches.pkl", "m2_distribution_report.json")])
    add("T5", [p for p in walk("data/supervised/phase4/p417")])
    # T6 dataset submission package (already a zip)
    add("T6", [ROOT / "FootIQ_Dataset_Submission.zip"])
    seen, res = set(), []
    for t, p in out:
        if p.exists() and p not in seen:
            seen.add(p)
            res.append((t, p))
    return res


def deflate_size(p):
    c = zlib.compressobj(6)
    n = 0
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            n += len(c.compress(chunk))
    return n + len(c.flush())


if __name__ == "__main__":
    mode = sys.argv[1]
    ents = entries()
    if mode == "estimate":
        rows, tier = [], {}
        for t, p in ents:
            b = p.stat().st_size
            rows.append((p.relative_to(ROOT).as_posix(), t, b))
            tier[t] = tier.get(t, [0, 0, 0])
            tier[t][0] += 1
            tier[t][1] += b
        with open(HERE / "submission_manifest.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["path", "tier", "bytes"])
            w.writerows(rows)
        tot_raw = tot_z = 0
        for t in sorted(tier):
            z = 0
            for tt, p in ents:
                if tt == t:
                    z += p.stat().st_size if p.suffix.lower() in (".zip", ".png", ".jpg", ".pdf") else deflate_size(p)
            tier[t][2] = z
            tot_raw += tier[t][1]
            tot_z += z
            print(f"{t}: {tier[t][0]:6d} files  raw {tier[t][1] / 1e6:8.1f} MB  zip estimate {z / 1e6:8.1f} MB")
        print(f"TOTAL: {len(rows)} files  raw {tot_raw / 1e6:.1f} MB  zip estimate {tot_z / 1e6:.1f} MB")
        big = sorted(rows, key=lambda r: -r[2])[:12]
        print("largest files:")
        for r in big:
            print(f"  {r[2] / 1e6:8.1f} MB  {r[1]}  {r[0]}")
    elif mode == "build":
        dest = Path(sys.argv[2]).resolve()
        tiers = set((sys.argv[3] if len(sys.argv) > 3 else "T1,T2,T3,T4,T5,T6").split(","))
        if ROOT in dest.parents or dest == ROOT:
            sys.exit("STOP: the destination must be outside the project")
        if dest.exists() and any(dest.iterdir()):
            sys.exit("STOP: the destination is not empty")
        n = 0
        for t, p in ents:
            if t in tiers:
                target = dest / p.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
                n += 1
        reqs = [(ROOT / "requirements-share.txt").read_text(encoding="utf-8").strip(), (ROOT / "app" / "requirements.txt").read_text(encoding="utf-8").strip(), "scipy==1.17.1"]
        (dest / "requirements-final.txt").write_text(chr(10).join(reqs) + chr(10), encoding="utf-8")      # one file for a clean install; scipy is imported directly but was not named in the originals
        print(f"copied {n} files to {dest}")
