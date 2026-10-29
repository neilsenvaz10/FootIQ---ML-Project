"""Are the acceptance rates stated in PHASE3_VALIDATION_REVIEW.md reproducible? Re-runs m2_protocol with the SAME seed (must match exactly) and with a DIFFERENT seed
(must agree within Monte Carlo error), and compares against the stored result file.
"""
import json
import sys
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import m2_protocol as P  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flatten(v, f"{prefix}{k}/"))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[f"{prefix}{k}"] = float(v)
    return out


def main() -> None:
    stored = json.loads((OUT / "m2_protocol.json").read_text(encoding="utf-8"))
    keys = ["scenarios"]
    same = P.run(reps=400, seed=21)
    other = P.run(reps=400, seed=22)
    fs, f1, f2 = flatten({k: stored[k] for k in keys}), flatten({k: same[k] for k in keys}), flatten({k: other[k] for k in keys})
    acc = [k for k in fs if "acceptance_probability" in k]
    same_diff = max(abs(fs[k] - f1[k]) for k in fs)
    d2 = np.array([abs(fs[k] - f2[k]) for k in acc])
    se = np.array([np.sqrt(max(fs[k] * (1 - fs[k]), 1e-4) / 400 * 2) for k in acc])                  # standard error of a difference of two runs of 400
    report = dict(stored_vs_same_seed_max_abs_difference=same_diff, identical_with_same_seed=bool(same_diff == 0.0), n_acceptance_rates_compared=len(acc),
                  different_seed_max_abs_difference=float(d2.max()), different_seed_mean_abs_difference=float(d2.mean()), share_within_2_standard_errors=float((d2 <= 2 * se).mean()),
                  largest_standardised_difference=float((d2 / se).max()))
    (OUT / "m4_reproducibility.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
