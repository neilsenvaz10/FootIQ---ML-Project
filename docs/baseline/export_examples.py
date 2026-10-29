"""Capture full-precision reference packets from the isolated original artifact."""
from pathlib import Path
import csv
import hashlib
import json
import pickle
import sys

base = Path(__file__).parent.resolve()
capture = base / "capture_2026-10-20"
root = capture / "isolated_execution/run1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(root / "scripts"))
import numpy as np
import build_live_predictions_v27 as predictor
import build_confidence_gate_v28 as gate

model_path = root / "data/model_artifacts/v27/live_match_model.pkl"
with model_path.open("rb") as f:
    artifact = pickle.load(f)
features = predictor.build_live_feature_rows()
first = predictor.predict_models(artifact, features)
second = predictor.predict_models(artifact, features)
prob_rows, pick_rows, comparison_rows = predictor.build_prediction_tables(artifact, features, first)
repeats = {name: bool(np.array_equal(values, second[name])) for name, values in first.items()}
checks = {name: {"finite": bool(np.isfinite(values).all()), "in_range": bool(((values >= 0) & (values <= 1)).all()),
                 "max_sum_error": float(abs(values.sum(axis=1)-1).max())} for name, values in first.items()}

def read(rel):
    with (root/rel).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

gate_rows = {r["fixture_key"]:r for r in read("data/processed/v28_live_public_picks.csv")}
elo = {r["team"]:r for r in read("data/processed/team_elo_latest.csv")}
form = {r["team"]:r for r in read("data/processed/team_recent_form_latest.csv")}
examples = []
for i, f in enumerate(features):
    examples.append({"fixture_key": f["fixture_key"], "input_feature_row": f,
        "source_elo_rows": {team:elo.get(team) for team in [f["home_team"],f["away_team"]]},
        "source_form_rows": {team:form.get(team) for team in [f["home_team"],f["away_team"]]},
        "component_probabilities_home_draw_away": {name:values[i].tolist() for name,values in first.items()},
        "exported_probability_row": prob_rows[i], "v27_public_row": pick_rows[i], "v28_public_row":gate_rows[f["fixture_key"]],
        "cutoffs": {"artifact_training_date_max":artifact["training_date_max"],
                    "home_last_match_date":form.get(f["home_team"],{}).get("last_match_date"),
                    "away_last_match_date":form.get(f["away_team"],{}).get("last_match_date"),
                    "fixture_date":f["date"],
                    "availability_cutoff": "Not proven: historical snapshot retrieval/known-at timestamps are not complete. This is a reconstruction of archived inputs, not a new pre-kickoff forecast."}})
result = {"model_version":artifact["version"], "model_sha256":hashlib.sha256(model_path.read_bytes()).hexdigest(),
          "artifact_trained_at_utc":artifact["trained_at_utc"], "ensemble_weights":artifact["ensemble_weights"],
          "temperatures":artifact["temperatures"], "pass_rules":artifact["pass_rules"], "label_order":artifact["labels"],
          "full_precision_repeat_equal":repeats, "probability_checks":checks,
          "comparison_policy":{"full_precision_absolute_tolerance":1e-12,"legacy_csv_rounding":5,"same_environment_exact_csv_hashes_required":True},
          "examples":examples}
with (capture/"prediction_examples.json").open("x",encoding="utf-8") as out:
    json.dump(result,out,ensure_ascii=False,indent=2,allow_nan=False)
    out.write("\n")
print(json.dumps({"fixtures":len(examples),"full_precision_repeat_equal":repeats,"probability_checks":checks},indent=2))
assert all(repeats.values())
assert all(v["finite"] and v["in_range"] and v["max_sum_error"]<1e-12 for v in checks.values())
