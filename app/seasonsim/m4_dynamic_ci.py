"""Paired cluster-bootstrap intervals for the static versus dynamic comparison on the EVALUATION seasons (rows written by m4_dynamic_eval.py). Clusters are league-season blocks
(all three cut-offs of one league and season together), because the same teams appear at every cut-off of a season."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "data" / "supervised" / "phase3"


def main(reps: int = 4000, seed: int = 5) -> dict:
    a = pd.read_pickle(OUT / "dyn_eval_rows_static.pkl").reset_index(drop=True)
    b = pd.read_pickle(OUT / "dyn_eval_rows_chosen.pkl").reset_index(drop=True)
    assert (a[["season", "cutoff", "league", "y"]].values == b[["season", "cutoff", "league", "y"]].values).all()
    d = pd.DataFrame(dict(block=a.season + "|" + a.league, d_crps=b.crps - a.crps, d_cov=b.cov80.astype(float) - a.cov80.astype(float), d_z=b.z.abs() - a.z.abs()))
    blocks = {k: g for k, g in d.groupby("block")}
    keys = list(blocks)
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(reps):
        pick = rng.choice(len(keys), len(keys))
        x = pd.concat([blocks[keys[i]] for i in pick])
        boot.append((x.d_crps.mean(), x.d_cov.mean()))
    boot = np.array(boot)
    res = dict(blocks=len(keys), team_cutoffs=int(len(d)), mean_crps_change=float(d.d_crps.mean()), crps_change_95ci=[float(np.percentile(boot[:, 0], 2.5)), float(np.percentile(boot[:, 0], 97.5))],
               share_of_bootstrap_with_better_crps=float((boot[:, 0] < 0).mean()), mean_coverage_change=float(d.d_cov.mean()), coverage_change_95ci=[float(np.percentile(boot[:, 1], 2.5)), float(np.percentile(boot[:, 1], 97.5))],
               blocks_where_dynamic_has_better_crps=int(sum(blocks[k].d_crps.mean() < 0 for k in keys)))
    (OUT / "dyn_ci.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
