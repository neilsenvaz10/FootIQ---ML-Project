"""Artifact manifest: every file that influences a prediction is hashed (text files with normalised line endings, binaries raw).
The approval file binds the sha256 of the whole manifest, so a change to a model, preprocessing, Elo parameter, feature contract, feature code, adapter or this logger after approval is detected."""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                                   # hardened_logger_r2_draft
V2 = os.path.dirname(ROOT)                                     # FootIQ_Club_Model_Development_v2
P = os.path.dirname(V2)                                        # D:\Foot IQ
PREP = os.path.join(P, "FootIQ_ML_Training_Preparation")
V1 = os.path.join(P, "FootIQ_Club_Model_Baseline_v1")
TEXT_SUFFIX = (".json", ".py", ".md", ".csv", ".txt")


def canonical_paths():
    j = os.path.join
    d = {
        "model_v2_pickle": j(V2, "final_refit_v2_r1", "artifacts", "club_v2_lr_final_candidate.pkl"),
        "model_v2_feature_contract": j(V2, "final_refit_v2_r1", "artifacts", "feature_contract_v2_final.json"),
        "model_v2_coefficients": j(V2, "final_refit_v2_r1", "artifacts", "model_coefficients.json"),
        "model_v2_frozen_record": j(V2, "final_refit_v2_r1", "artifacts", "FROZEN.json"),
        "model_matched_v1_pickle": j(V2, "matched_v1_prospective_r1", "artifacts", "matched_v1_lr_refit.pkl"),
        "model_matched_v1_preprocessing": j(V2, "matched_v1_prospective_r1", "artifacts", "matched_v1_preprocessing.json"),
        "model_matched_v1_coefficients": j(V2, "matched_v1_prospective_r1", "artifacts", "matched_v1_coefficients.json"),
        "model_matched_v1_frozen_record": j(V2, "matched_v1_prospective_r1", "artifacts", "MATCHED_V1_FROZEN.json"),
        "model_v1_original_pickle": j(V1, "artifacts", "multinomial_logreg.pkl"),
        "model_v1_original_preprocessing": j(V1, "artifacts", "preprocessing_train_fitted.json"),
        "model_v1_original_coefficients": j(V1, "artifacts", "multinomial_logreg_coefficients.json"),
        "model_v1_elo_parameters": j(V1, "artifacts", "baseline_parameters.json"),
        "model_v1_frozen_record": j(V1, "artifacts", "FROZEN.json"),
        "feature_contract_v1": j(PREP, "feature_contract_v1.1.json"),
        "preprocessing_spec_v1": j(PREP, "preprocessing_spec_v1.1.json"),
        "elo2_parameters_and_meta": j(V2, "_work", "features_v2_meta.json"),
        "eligibility_exclusions": j(V2, "matched_v1_prospective_r1", "eligibility_exclusions_r1.json"),
        "universe": j(PREP, "_build", "work", "V_universe.pkl"),
        "code_v2_features": j(V2, "_scripts", "v2_features.py"),
        "code_v2_models": j(V2, "_scripts", "v2_models.py"),
        "code_v2_common": j(V2, "_scripts", "v2_common.py"),
        "code_v1_feature_contract": j(PREP, "_build", "feature_contract.py"),
        "code_d11_features_and_v1_scoring": j(V2, "_scripts", "d11_prospective_logger.py"),
        "code_e4_model_loading": j(V2, "_scripts", "e4_prospective_logger.py"),
        "code_adapter_openligadb": j(V2, "source_adapters_r1", "footiq_sources", "openligadb.py"),
        "code_adapter_common": j(V2, "source_adapters_r1", "footiq_sources", "common.py"),
        "code_adapter_identity": j(V2, "source_adapters_r1", "footiq_sources", "identity.py"),
        "code_adapter_reconcile": j(V2, "source_adapters_r1", "footiq_sources", "reconcile.py"),
    }
    for f in sorted(os.listdir(HERE)):
        if f.endswith(".py"):
            d["code_hardened_" + f[:-3]] = j(HERE, f)
    return d


_CACHE = {}


def digest_file(path: str) -> str:
    st = os.stat(path)
    key = (path, st.st_mtime_ns, st.st_size)
    if key in _CACHE:
        return _CACHE[key]
    with open(path, "rb") as fh:
        b = fh.read()
    if path.lower().endswith(TEXT_SUFFIX):
        b = b.replace(b"\r\n", b"\n")
    h = hashlib.sha256(b).hexdigest()
    _CACHE[key] = h
    return h


def manifest(paths=None) -> dict:
    paths = paths or canonical_paths()
    return {k: digest_file(p) for k, p in sorted(paths.items())}


def manifest_sha(m: dict) -> str:
    return hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()


def verify(expected: dict, paths=None) -> list:
    """Returns the list of mismatches (empty = intact). Missing files and unexpected extra entries count."""
    cur = {}
    problems = []
    for k, p in sorted((paths or canonical_paths()).items()):
        try:
            cur[k] = digest_file(p)
        except OSError:
            problems.append(f"{k}: file missing")
    for k, h in expected.items():
        if k not in cur:
            problems.append(f"{k}: not present") if not any(x.startswith(k + ":") for x in problems) else None
        elif cur[k] != h:
            problems.append(f"{k}: hash differs")
    for k in cur:
        if k not in expected:
            problems.append(f"{k}: not in expected manifest")
    return problems


PIN_PATH = os.path.join(ROOT, "pinned_artifact_manifest.json")


def write_pin(path=PIN_PATH):
    m = manifest()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(manifest=m, manifest_sha256=manifest_sha(m), note="DRAFT pin for regression/shadow use; official use binds the manifest sha256 inside the owner's approval file"), fh, indent=1)
    return m


def load_pin(path=PIN_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["manifest"]
