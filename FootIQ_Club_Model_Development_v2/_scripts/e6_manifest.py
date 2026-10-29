import json, os, sys, platform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
import sklearn, scipy  # noqa
NEW = os.path.join(OUT, "matched_v1_prospective_r1")
files = {}
for root, _, fs in os.walk(NEW):
    for f in sorted(fs):
        p = os.path.join(root, f)
        if f == "11_REPRODUCIBILITY_MANIFEST.json":
            continue
        files[os.path.relpath(p, NEW).replace("\\", "/")] = sha(p)
code = {f: sha(os.path.join(OUT, "_scripts", f)) for f in sorted(os.listdir(os.path.join(OUT, "_scripts"))) if f.endswith(".py")}
fr = json.load(open(os.path.join(OUT, "final_refit_v2_r1", "artifacts", "FROZEN.json")))
mv = json.load(open(os.path.join(NEW, "artifacts", "MATCHED_V1_FROZEN.json")))
frozen_ok = sha(os.path.join(OUT, "final_refit_v2_r1", "artifacts", "club_v2_lr_final_candidate.pkl")) == "55c1e4c53bcfefd39d5e90a1ce60a75bc697668f7894e425305bdc9a65b3e56c"
man = dict(version="matched_v1_prospective_r1", generated="2026-10-21", frozen_v2_pickle_sha256_unchanged=frozen_ok, matched_v1=mv, frozen_v2_artifacts=fr["artifact_sha256"],
           files_sha256=files, scripts_sha256=code, environment=dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__, platform=platform.platform()),
           run_order=["e1_integrity_and_identity.py", "e2_matched_v1_refit.py (refuses to rerun)", "e3_ingest_results.py selftest | plan", "e5_logging_validation.py (uses e4_prospective_logger.py)", "e6_manifest.py"],
           official_logging="not started; OFFICIAL_LOGGING_APPROVED.json absent", git_note="no commits made; code identified by script hashes")
json.dump(man, open(os.path.join(NEW, "11_REPRODUCIBILITY_MANIFEST.json"), "w"), indent=1)
print(len(files), "files hashed; frozen v2 unchanged:", frozen_ok)
