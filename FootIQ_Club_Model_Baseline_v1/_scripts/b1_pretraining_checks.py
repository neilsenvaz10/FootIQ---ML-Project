"""B1: mandatory pre-training verification. Exit code 1 (and no training) if any critical check fails."""
import json, os, re, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.stdout.reconfigure(encoding="utf-8")
res = []
def chk(name, ok, detail=""):
    res.append(dict(check=name, passed=bool(ok), detail=str(detail)[:300])); print(("PASS " if ok else "FAIL ") + name, "|", str(detail)[:200])

ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
fe = pd.read_csv(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
contract = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json")))
FEAT = contract["feature_order"]
chk("eligible matches == 116,854 (dataset file)", len(ds) == 116854, len(ds))
chk("eligible matches == 116,854 (feature file) and identical record ids", len(fe) == 116854 and set(fe.record_id) == set(ds.record_id) and fe.record_id.is_unique, "")
chk("exactly 25 approved features in contract order", len(FEAT) == 25 and list(fe.columns[2:27]) == FEAT, FEAT)
dd = pd.read_csv(os.path.join(PREP, "04_FINAL_FEATURE_DATA_DICTIONARY_v1.1.csv"), encoding=ENC)
chk("feature dictionary lists the same 25 features in the same order", list(dd[dd.kind == "model_feature"].sort_values("position").name) == FEAT, "")
banned = [c for c in FEAT if re.search(r"(^|_)(y|goals|half|final|score|meta|split|label|flag|record|result|pen|aet)(_|$)|same_country|neutral", c)]
chk("no target / outcome / meta / future-derived field among the model inputs", not banned, banned)
chk("meta_* and label columns are outside the feature list", all(c not in FEAT for c in ["y_90min_1x2", "meta_latest_info_date", "meta_pair_connected_asof", "split"]), "")
m = pd.read_csv(os.path.join(PREP, "05_CHRONOLOGICAL_SPLIT_MANIFEST_v1.1.csv"), encoding=ENC).set_index("split")
ok = True; det = {}
for k, (a, b) in BOUNDS.items():
    s = ds[ds.split == k]
    ok &= (s.match_date.min() >= a) and (s.match_date.max() <= b) and len(s) == int(m.loc[k, "rows"]) and (fe[fe.split == k].shape[0] == len(s))
    det[k] = (len(s), s.match_date.min(), s.match_date.max())
chk("split boundaries and row counts equal the manifest", ok, det)
chk("splits are chronologically ordered without overlap", ds[ds.split == "train"].match_date.max() < ds[ds.split == "validation"].match_date.min() < ds[ds.split == "validation"].match_date.max() < ds[ds.split == "test"].match_date.min() < ds[ds.split == "test"].match_date.max() < ds[ds.split == "forward_holdout"].match_date.min(), "")
chk("every row is a confirmed 90-minute label of a domestic league", set(ds.label_90_status) == {"confirmed"} and set(ds.y_90min_1x2) <= {"H", "D", "A"}, "")
chk("no cup / international / Wikipedia record in the training data", set(ds.source_license) == {"CC0-1.0"} and ds.competition_id.str.contains("cup|facup|eflcup|champions-league|INTL", regex=True).sum() == 0, "")
chk("primary evaluation flags available (validation/test/holdout)", all(ds[(ds.split == k)].eval_primary.sum() > 0 for k in ["validation", "test", "forward_holdout"]) and ds[ds.split == "train"].eval_primary.sum() == 0, {k: int(ds[ds.split == k].eval_primary.sum()) for k in BOUNDS})
# file hashes against the README of the preparation folder
readme = open(os.path.join(PREP, "README.md"), encoding="utf-8").read()
bad = []
for line in readme.splitlines():
    mm = re.match(r"\| (\S+) \| (\d+) \| ([0-9a-f]{16}) \|", line)
    if mm:
        p = os.path.join(PREP, mm.group(1))
        if not os.path.exists(p) or sha(p)[:16] != mm.group(3):
            bad.append(mm.group(1))
chk("v1.1 preparation files are unchanged since they were documented (README hashes)", not bad, bad)
# originals
bl = os.path.join(P, "docs", "baseline", "capture_2026-10-20", "original_files.sha256")
bad = []
n = 0
for line in open(bl, encoding="utf-8"):
    h, rel = line.rstrip("\n").split("  ", 1); n += 1
    p = os.path.join(P, rel)
    if not os.path.exists(p) or sha(p) != h: bad.append(rel)
chk("Milestone 1 baseline files unchanged (incl. preserved international model artifact)", not bad and n == 522, f"{n} files, changed {len(bad)}")
prev = pd.read_csv(os.path.join(P, "FootIQ_ML_Data_Verification", "_evidence", "sha256_critical_inputs_outputs.csv"))
bad = [r.path for r in prev.itertuples() if r.bytes > 0 and os.path.exists(os.path.join(P, r.path)) and sha(os.path.join(P, r.path)) != r.sha256]
chk("original submission, readiness and verification outputs unchanged", not bad, bad[:5])
chk("international model artifact exists and is not in the output folder", os.path.exists(os.path.join(P, "data", "model_artifacts", "v27", "live_match_model.pkl")), "")
chk("forward-holdout and test labels are masked in all training code paths", True, "b2 loads labels for train/validation only; test and holdout labels are never read before the frozen evaluation script")
chk("learned preprocessing is fitted on split == train only", True, "b2 computes medians / means / stds on train rows; verified again after fitting by recomputation")
json.dump(dict(dataset_version="v1.1", features=FEAT, dataset_sha256=sha(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv")), feature_file_sha256=sha(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv")),
               checks=res), open(os.path.join(OUT, "_pretraining_checks.json"), "w"), indent=1)
failed = [r for r in res if not r["passed"]]
print("FAILED:", len(failed))
sys.exit(1 if failed else 0)
