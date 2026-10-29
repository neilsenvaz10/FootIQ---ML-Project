import glob, json, os, sys, platform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
FD = os.path.join(OUT, "final_refit_v2_r1")
fr = json.load(open(os.path.join(FD, "artifacts", "FROZEN.json")))
files = {}
for root, _, fs in os.walk(FD):
    for f in sorted(fs):
        p = os.path.join(root, f)
        if f == "07_REPRODUCIBILITY_MANIFEST.json": continue
        files[os.path.relpath(p, FD).replace("\\", "/")] = sha(p)
code = {f: sha(os.path.join(OUT, "_scripts", f)) for f in sorted(os.listdir(os.path.join(OUT, "_scripts"))) if f.endswith(".py")}
v1 = {os.path.basename(p): sha(p) for p in sorted(glob.glob(os.path.join(V1, "artifacts", "*")))}
man = dict(version="v2-r1", generated="2026-10-21", frozen=fr, final_refit_files_sha256=files, scripts_sha256_at_manifest_time=code, v1_reference_artifacts_sha256=v1,
           world_cup_model_sha256=sha(os.path.join(P, "data", "model_artifacts", "v27", "live_match_model.pkl")),
           run_order=["d2b_rebuild_features.py", "d6_leakage_tests.py", "d9_postfix_reeval.py", "d10_final_refit.py", "d12_final_verification.py", "d11_prospective_logger.py --dry-run", "d13_final_manifest.py"],
           interpreter="D:/Foot IQ/.venv/Scripts/python.exe -I", platform=platform.platform(),
           note="d10 refuses to run once artifacts/FROZEN.json exists; a different configuration must be a new version directory")
json.dump(man, open(os.path.join(FD, "07_REPRODUCIBILITY_MANIFEST.json"), "w"), indent=1)
print(len(files), "files hashed")
