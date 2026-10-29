"""Offline comparison of the static points-only simulation and the dynamic (Elo-in-the-loop) prototype on historical cut-offs. Private data only; nothing is saved to any database.

Protocol (fixed in this docstring BEFORE the evaluation seasons were run):
  * Development seasons 2020-21 .. 2023-24 (v1 in-sample for the first three, validation for the last): the ONLY data used to choose parameters. Evaluation seasons 2024-25 and 2025-26
    (frozen v1 out-of-sample) are run once with the chosen configuration, after the choice is written to data/supervised/phase3/dyn_choice.json.
  * Candidate grid: kappa in {0, 0.5, 1, 1.5, 2} (Elo update scale), tau in {0, 6, 12} (weekly drift, Elo points); the other constants stay at the frozen v1 values (K 20, home advantage 60, tilt 1).
  * Rule: among configurations whose mean CRPS is not worse than static by more than 0.5%, take the one whose pooled 10-90% coverage is closest to 0.80; configurations within 0.01
    of the best count as tied and the simpler one wins (smaller kappa, then smaller tau).
  * Sensitivity (reporting only, never used for choice): K, home advantage, tilt and kappa varied around the chosen configuration on development AND evaluation seasons.
Metrics per team-cut-off: realised final points against the simulated distribution: 10-90, 25-75 and 5-95 interval coverage, CRPS, standardised error, probability-integral transform.
"""
import itertools
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import dynamic  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
N_SIMS, SEED = 2000, 2026
Z90 = 1.2816


def crps(samples: np.ndarray, y: float) -> float:
    x = np.sort(samples)
    n = len(x)
    term2 = (2.0 / n ** 2) * float(((2 * np.arange(1, n + 1) - n - 1) * x).sum())            # E|X - X'|
    return float(np.abs(x - y).mean() - 0.5 * term2)


def case_metrics(case: dict, cfg: dict, n: int = N_SIMS, seed: int = SEED, with_points: bool = False):
    fx = case["fixtures"]
    idx = {t: i for i, t in enumerate(case["teams"])}
    dates = np.array([pd.Timestamp(d).toordinal() for d in fx.dt])
    pts = dynamic.simulate_dynamic(case["base_points"], fx.h.map(idx).values.astype(int), fx.a.map(idx).values.astype(int), dates, fx[["p_H", "p_D", "p_A"]].values, case["elo"], n, seed, **cfg)
    rows = []
    rng = np.random.default_rng(seed + 7)
    for t in range(len(case["teams"])):
        has = ((fx.h.map(idx) == t) | (fx.a.map(idx) == t)).any()
        if not has:
            continue
        col, y = pts[:, t], float(case["real_points"][t])
        sd = col.std()
        p10, p25, p75, p90, p05, p95 = np.percentile(col, [10, 25, 75, 90, 5, 95])
        pit = (col < y).mean() + rng.random() * (col == y).mean()
        rows.append(dict(season=case["season"], cutoff=case["cutoff"], league=case["league"], role=case["role"], y=y, mean=col.mean(), sd=sd, z=(y - col.mean()) / max(sd, 1e-9), cov80=p10 <= y <= p90,
                         cov50=p25 <= y <= p75, cov90=p05 <= y <= p95, width80=p90 - p10, crps=crps(col, y), pit=pit))
    return (rows, pts) if with_points else rows


def evaluate(cases: list, cfg: dict) -> pd.DataFrame:
    out = []
    for c in cases:
        out += case_metrics(c, cfg)
    return pd.DataFrame(out)


def summary(df: pd.DataFrame) -> dict:
    return dict(n=int(len(df)), coverage_10_90=round(float(df.cov80.mean()), 3), coverage_25_75=round(float(df.cov50.mean()), 3), coverage_5_95=round(float(df.cov90.mean()), 3),
                crps=round(float(df.crps.mean()), 4), std_standardised_error=round(float(df.z.std()), 3), mean_error_points=round(float((df.y - df["mean"]).mean()), 3), mean_width_10_90=round(float(df.width80.mean()), 2),
                pit_deciles=[round(float(x), 3) for x in np.histogram(df.pit, bins=10, range=(0, 1))[0] / len(df)])


def by_cutoff(df: pd.DataFrame) -> dict:
    m = df.cutoff.str[5:7]
    return {name: dict(coverage_10_90=round(float(g.cov80.mean()), 3), std_standardised_error=round(float(g.z.std()), 3), crps=round(float(g.crps.mean()), 3)) for name, g in df.groupby(m.map({"11": "1 Nov", "01": "1 Jan", "03": "1 Mar"}))}


def choose(dev_cases: list) -> tuple:
    grid = [dict(kappa=k, tau=t) for k, t in itertools.product((0.0, 0.5, 1.0, 1.5, 2.0), (0.0, 6.0, 12.0))]
    res = []
    for cfg in grid:
        res.append((cfg, summary(evaluate(dev_cases, cfg))))
        print("dev", cfg, res[-1][1]["coverage_10_90"], res[-1][1]["crps"], flush=True)
    static = next(s for c, s in res if c["kappa"] == 0 and c["tau"] == 0)
    ok = [(c, s) for c, s in res if s["crps"] <= static["crps"] * 1.005]
    best = min(abs(s["coverage_10_90"] - 0.80) for _, s in ok)
    tied = [(c, s) for c, s in ok if abs(s["coverage_10_90"] - 0.80) <= best + 0.01]
    chosen = min(tied, key=lambda cs: (cs[0]["kappa"] > 0 and cs[0]["tau"] > 0, cs[0]["kappa"], cs[0]["tau"]))
    return chosen[0], res


def main() -> None:
    cases = pickle.load(open(OUT / "dyn_inputs.pkl", "rb"))
    dev = [c for c in cases if c["role"] == "development"]
    ev = [c for c in cases if c["role"] == "evaluation"]
    chosen, grid = choose(dev)
    (OUT / "dyn_choice.json").write_text(json.dumps(dict(chosen=chosen, grid=[dict(cfg=c, **s) for c, s in grid], rule="see module docstring", n_sims=N_SIMS, seed=SEED), indent=1), encoding="utf-8")
    print("CHOSEN on development data only:", chosen, flush=True)
    result = dict(chosen=chosen, development={}, evaluation={}, sensitivity={})
    sens = {"chosen": chosen, "static": dict(kappa=0.0, tau=0.0)}
    for k in (10.0, 30.0):
        sens[f"K={k:g}"] = dict(chosen, k=k)
    for h in (40.0, 80.0):
        sens[f"home advantage={h:g}"] = dict(chosen, ha=h)
    for g in (0.5, 1.5):
        sens[f"tilt x{g}"] = dict(chosen, tilt=g)
    for kk in (0.5, 2.0):
        sens[f"kappa={kk}"] = dict(chosen, kappa=kk)
    for name, cfg in sens.items():
        d_df, e_df = evaluate(dev, cfg), evaluate(ev, cfg)
        result["sensitivity"][name] = dict(cfg=cfg, development=summary(d_df), evaluation=summary(e_df))
        if name in ("chosen", "static"):
            result["development"][name], result["evaluation"][name] = dict(summary(d_df), by_cutoff=by_cutoff(d_df)), dict(summary(e_df), by_cutoff=by_cutoff(e_df), by_league={lg: summary(g) for lg, g in e_df.groupby("league")})
            e_df.to_pickle(OUT / f"dyn_eval_rows_{name}.pkl")
        print(name, "dev", result["sensitivity"][name]["development"]["coverage_10_90"], "eval", result["sensitivity"][name]["evaluation"]["coverage_10_90"], flush=True)
    (OUT / "dyn_eval.json").write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
