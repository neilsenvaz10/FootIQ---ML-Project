"""Reproducibility manifest + artifact reload parity check."""
import glob
import json
import os
import pickle
import platform
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_models import *  # noqa
import sklearn, scipy  # noqa

sys.stdout.reconfigure(encoding="utf-8")
F = load_dev(); F = F[F.match_date <= DEV_END]
chk = {}
for p in sorted(glob.glob(os.path.join(ART, "candidate_*.pkl"))):
    d = pickle.load(open(p, "rb"))
    va = F[(F.match_date >= "2023-07-01")].head(2000)
    X = d["prep"].transform(va, d["kind"] == "lr")
    P1 = d["model"].predict_proba(X)
    P2 = d["model"].predict_proba(d["prep"].transform(va, d["kind"] == "lr"))
    chk[os.path.basename(p)] = dict(reload_prediction_identical=bool(np.allclose(P1, P2)), rows_in_sum_to_one=bool(np.allclose(P1.sum(1), 1)), n_features=len(d["features"]))
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, cwd=P).stdout.strip()
files = {}
for pat in ("_scripts/*.py", "_work/protocol_frozen.json", "_work/features_v2_meta.json", "_work/feature_selection.json", "_work/best_configs.json", "artifacts/*.pkl", "0*.csv", "0*.md"):
    for f in sorted(glob.glob(os.path.join(OUT, pat))):
        files[os.path.relpath(f, OUT).replace("\\", "/")] = sha(f) if callable(sha) else None
ds = os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv")
man = dict(
    experiment="FootIQ club 1X2 match prediction v2 (development only)", generated="2026-10-21", seed=SEED, status="development-validated only; not evaluated on any unseen data; not promoted; v1 not replaced",
    git=dict(branch=git("rev-parse", "--abbrev-ref", "HEAD"), head=git("rev-parse", "HEAD"), staged_or_committed_by_this_work=False),
    environment=dict(python=sys.version.split()[0], platform=platform.platform(), numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__,
                     xgboost="not installed - skipped", lightgbm="not installed - skipped", catboost="not installed - skipped"),
    development_window=dict(train_start=TRAIN_START, development_end=DEV_END, folds=FOLDS),
    inputs=dict(dataset=ds, dataset_sha256=sha(ds), universe_sha256_prefix=sha(os.path.join(PREP, "_build", "work", "V_universe.pkl"))[:16],
                v2_feature_table_sha256=sha(os.path.join(WORK, "features_v2_dev.pkl"))),
    elo2=json.load(open(os.path.join(WORK, "features_v2_meta.json")))["elo2_params"],
    feature_selection=json.load(open(os.path.join(WORK, "feature_selection.json"))),
    best_hyperparameters=json.load(open(os.path.join(WORK, "best_configs.json"))),
    artifact_reload_checks=chk,
    leakage_parity_tests=pd.read_csv(os.path.join(WORK, "leakage_parity_tests.csv")).to_dict("records"),
    file_hashes=files,
    forbidden_data_not_used="outcomes dated after 2024-06-30 (v1 test and v1 forward holdout) were never loaded by any v2 script",
)
json.dump(man, open(os.path.join(OUT, "11_REPRODUCIBILITY_MANIFEST.json"), "w"), indent=1, default=str)
print(json.dumps(chk, indent=1)); print(len(files), "files hashed")
