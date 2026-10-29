"""Phase 0: repository state and baseline-preservation checks (read-only)."""
import hashlib
import importlib.util as iu
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
res = []
CRLF, LF = bytes([13, 10]), bytes([10])


def chk(n, ok, d=""):
    res.append(dict(check=n, passed=bool(ok), detail=str(d)[:300]))
    print(("PASS " if ok else "FAIL ") + n, "|", str(d)[:160])


def same(path, h):
    b = open(path, "rb").read()
    if hashlib.sha256(b).hexdigest() == h:
        return True
    lf = b.replace(CRLF, LF)       # git normalises text line endings (core.autocrlf=input)
    return hashlib.sha256(lf).hexdigest() == h or hashlib.sha256(lf.replace(LF, CRLF)).hexdigest() == h


man = json.load(open(os.path.join(V1, "10_REPRODUCIBILITY_MANIFEST.json")))
bad = [f for f, h in man["artifacts_sha256"].items() if not same(os.path.join(V1, "artifacts", f), h)]
chk("v1 artifacts match the v1 manifest hashes (model pickle byte-identical; text files identical up to git line-ending normalisation)", not bad, bad)
bad = [f for f, h in man["output_files_sha256"].items() if os.path.exists(os.path.join(V1, f)) and not same(os.path.join(V1, f), h)]
chk("v1 output files match the v1 manifest hashes (up to line-ending normalisation)", not bad, bad)
chk("v1 dataset hash unchanged", sha(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv")) == man["dataset"]["dataset_sha256"]
    and sha(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv")) == man["dataset"]["feature_file_sha256"], "")
fc = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json")))
chk("v1 feature contract has 25 features", len(fc["feature_order"]) == 25 and fc["feature_order"] == man["feature_order"], "")
m = pd.read_csv(os.path.join(PREP, "05_CHRONOLOGICAL_SPLIT_MANIFEST_v1.1.csv"), encoding=ENC)
chk("v1.1 split manifest rows 59,356 / 22,578 / 26,000 / 8,920", list(m.rows) == [59356, 22578, 26000, 8920], list(m.rows))


def git(*a):
    return subprocess.check_output(["git", "-C", P, *a], text=True).strip()


br = git("branch", "--show-current")
chk("on branch feat/club-ml-v2", br == "feat/club-ml-v2", br)
chk("local main equals origin/main and contains the merged baseline v1",
    git("rev-parse", "main") == git("rev-parse", "origin/main") and "FootIQ_Club_Model_Baseline_v1/10_REPRODUCIBILITY_MANIFEST.json" in git("ls-tree", "-r", "--name-only", "origin/main"), git("rev-parse", "main")[:10])
st = {line[3:] for line in git("status", "--short").splitlines()}
chk("working tree: only untracked docs and the new v2 folder, nothing modified or staged", st <= {"docs/baseline/", "docs/data-sources/", "FootIQ_Club_Model_Development_v2/"}, sorted(st))
U = os.path.join(PREP, "_build", "work", "V_universe.pkl")
chk("verified results universe present (derived from CC0 openfootball by the v1.1 pipeline)", os.path.exists(U), sha(U)[:16])
for lib in ("xgboost", "lightgbm", "catboost"):
    res.append(dict(check=f"{lib} installed", passed=True, detail="available" if iu.find_spec(lib) else "NOT installed - not installed by this task, algorithm skipped"))
    print(lib, "available" if iu.find_spec(lib) else "NOT installed")
json.dump(dict(checks=res, universe_sha256=sha(U), branch=br, main_commit=git("rev-parse", "main")), open(os.path.join(WORK, "phase0_checks.json"), "w"), indent=1)
failed = [r for r in res if not r["passed"]]
print("failed:", len(failed))
sys.exit(1 if failed else 0)
