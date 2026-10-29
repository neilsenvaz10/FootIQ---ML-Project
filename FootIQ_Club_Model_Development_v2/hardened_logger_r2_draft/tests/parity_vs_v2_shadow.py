import json, glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from helpers import *
V, VS, RES = universe()
recs, rej, S = engine.predict_core(V, [real_snap()], T0 + pd.Timedelta(minutes=45), RES, pin())
old = [json.loads(l) for l in open(glob.glob(os.path.join(artifacts.V2, "shadow_integration_r1", "shadow_log", "SHADOW", "shadow_batch_*.jsonl"))[0], encoding="utf-8")]
od = {r["fixture_id"]: r for r in old}
d = max(abs(r["probs"][m][c] - od[r["fixture_id"]]["probs"][m][c]) for r in recs for m in r["probs"] for c in "HDA")
same_elig = all(r["primary_eligible"] == od[r["fixture_id"]]["primary_eligible"] and r["eligibility_reasons"] == od[r["fixture_id"]]["eligibility_reasons"] for r in recs)
same_feat = all(r["v2_feature_sha256"] == od[r["fixture_id"]]["v2_feature_sha256"] for r in recs)
print(json.dumps(dict(fixtures_compared=len(recs), max_abs_probability_difference_vs_v2_shadow_batch=d, eligibility_identical=same_elig, v2_feature_hashes_identical=same_feat, eligible=sum(r["primary_eligible"] for r in recs), integrity_events=len(S.events))))
