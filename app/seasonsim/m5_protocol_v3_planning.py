"""Planning numbers for Protocol v3 (offline). Synthetic samples drawn from the evaluation matches' own expected distributions, plus the PRE-MATCH history depth of the confirmation set CA.

Nothing here evaluates a scoreline method on any real result: no outcome of any CA or CB match is read, the original benchmark and its files are not touched, and the revised protocol is
not run on CA or CB.

  A  Algebra: matches needed for 90% power per statistic with (i) the one-sided z used in Protocol v2 and (ii) the correct two one-sided tests (TOST) z, and the joint four-statistic requirement.
  B  Simulated power of the full decision rule (all four statistics must pass) for ONE method, as the number of matches grows, for the three candidate margin pairs.
  C  Simulated power under Holm over THREE methods: worst case (one correct method, two clearly wrong, so the correct one must pass at alpha/3) and best case (all three nearly right),
     compared with the sequence proposed in Protocol v2.
  D  Pre-match history depth of the CA matches (no outcome read): how many CA matches have two clubs with at least T earlier matches in the model history.
Seeds are fixed; `python app/seasonsim/m5_protocol_v3_planning.py` reproduces the JSON exactly.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import norm

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import m2_protocol as P  # noqa: E402
from seasonsim import m4_protocol_review as R  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
ALPHA = 0.05
MARGINS = {"0.10 / 0.05": np.array([0.10, 0.10, 0.05, 0.05]), "0.15 / 0.075": np.array([0.15, 0.15, 0.075, 0.075]), "0.20 / 0.10": np.array([0.20, 0.20, 0.10, 0.10])}
GRID = (500, 686, 800, 1000, 1158, 1300, 1464, 1600, 1800, 2000, 2200, 2400, 2606, 3000, 3300, 3800, 4321, 5000)


def part_a() -> dict:
    c = json.loads((OUT / "m2_confirmation_planning.json").read_text(encoding="utf-8"))["standard_error_times_sqrt_n"]
    z_v2 = norm.ppf(0.95) + norm.ppf(0.90)                       # what Protocol v2 used: one-sided power formula
    z_tost = norm.ppf(0.95) + norm.ppf(0.95)                     # two one-sided tests at 5%, true difference zero: power = 2 Phi(delta/se - z) - 1, so 90% needs z(0.95) + z(0.95)
    per_stat = 0.90 ** (1 / 4)                                   # all four must pass: if they were independent each needs 97.4% power (an upper bound on the matches needed, correlation lowers it)
    z_joint = norm.ppf(0.95) + norm.ppf(1 - (1 - per_stat) / 2)
    out = dict(z_v2=round(float(z_v2), 3), z_tost=round(float(z_tost), 3), z_joint_independent_upper_bound=round(float(z_joint), 3), factor_tost_over_v2=round(float((z_tost / z_v2) ** 2), 3),
               factor_joint_over_v2=round(float((z_joint / z_v2) ** 2), 3), se_times_sqrt_n=c, margins={})
    for name, d in MARGINS.items():
        need = lambda z: {k: int(np.ceil((z * c[k] / d[i]) ** 2)) for i, k in enumerate(P.KEYS)}
        out["margins"][name] = {label: dict(by_statistic=n, binding=max(n.values())) for label, n in (("v2_one_sided_z", need(z_v2)), ("tost_z_one_statistic", need(z_tost)), ("joint_independent_upper_bound", need(z_joint)))}
    return out


def interpolate(curve: dict, level: float):
    ns = sorted(int(k) for k in curve)
    for a, b in zip(ns, ns[1:]):
        pa, pb = curve[str(a)], curve[str(b)]
        if pa < level <= pb:
            return int(round(a + (level - pa) / (pb - pa) * (b - a)))
    return None if curve[str(ns[-1])] < level else ns[0]


def part_b(ev, pm, reps: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for name, d in MARGINS.items():
        curve = {}
        for n in GRID:
            acc = 0
            for _ in range(reps):
                idx = rng.integers(0, len(ev), n)
                est, se = P.sample_actual(pm["S1"][idx], rng)
                acc += R.tost_p(P.model_vec(pm["S1"][idx]) - est, se, d) <= ALPHA
            curve[str(n)] = round(acc / reps, 3)
        out[name] = dict(power=curve, n_for_80pct=interpolate(curve, 0.80), n_for_90pct=interpolate(curve, 0.90))
    return out


def part_c(ev, pm, reps: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    truth = pm["S1"]
    out = {}
    for name, d in MARGINS.items():
        curve = {}
        for n in GRID:
            worst = best = seq = single = 0
            for _ in range(reps):
                idx = rng.integers(0, len(ev), n)
                est, se = P.sample_actual(truth[idx], rng)
                p1 = R.tost_p(P.model_vec(pm["S1"][idx]) - est, se, d)
                p2 = R.tost_p(P.model_vec(pm["S2"][idx]) - est, se, d)
                p3 = R.tost_p(P.model_vec(pm["S3"][idx]) - est, se, d)
                single += p1 <= ALPHA
                worst += p1 <= ALPHA / 3                                                  # Holm over three methods when only S1 is correct: the smallest p-value is compared with alpha/3
                best += min(p1, p2, p3) <= ALPHA / 3                                      # all three nearly right: the best of three at alpha/3
                seq += (p1 <= ALPHA) or (p2 <= ALPHA) or (p3 <= ALPHA)                    # the sequence proposed in Protocol v2 (each at alpha)
            curve[str(n)] = dict(single_method_alpha=round(single / reps, 3), holm_worst_case_one_correct_method=round(worst / reps, 3), holm_best_case_three_nearly_right=round(best / reps, 3),
                                 sequence_as_in_v2=round(seq / reps, 3))
        out[name] = dict(power=curve, n_for_80pct_holm_worst=interpolate({k: v["holm_worst_case_one_correct_method"] for k, v in curve.items()}, 0.80),
                         n_for_90pct_holm_worst=interpolate({k: v["holm_worst_case_one_correct_method"] for k, v in curve.items()}, 0.90),
                         n_for_90pct_holm_best=interpolate({k: v["holm_best_case_three_nearly_right"] for k, v in curve.items()}, 0.90))
    return out


def part_d() -> dict:
    """History depth of CA matches from PRE-MATCH information only (the number of earlier matches of each club in the model history). No outcome is read."""
    import predict
    from seasonsim import m4_ca_audit as A

    lg, V, tiers = predict._club_runtime()
    manifest = json.loads((OUT / "ca_manifest.json").read_text(encoding="utf-8"))
    x = A.ca_rows(V)[["record_id", "competition_id", "dt", "home_entity_id", "away_entity_id"]]                    # no result column is selected
    long = np.concatenate([V[["home_entity_id", "dt"]].values, V[["away_entity_id", "dt"]].values])
    import pandas as pd

    hist = pd.DataFrame(long, columns=["club", "dt"]).sort_values("dt")
    hist["k"] = hist.groupby("club").cumcount()
    first_k = hist.groupby(["club", "dt"]).k.min()                                  # earlier matches strictly before that date
    depth = lambda club, dt: first_k.get((club, dt), np.nan)
    dh = np.array([depth(c, d) for c, d in zip(x.home_entity_id, x.dt)], dtype=float)
    da = np.array([depth(c, d) for c, d in zip(x.away_entity_id, x.dt)], dtype=float)
    m = np.nanmin(np.vstack([dh, da]), axis=0)
    ca1 = x.competition_id.isin(manifest["ca1_leagues"]).values
    out = dict(ca_matches=int(len(x)), ca1_matches=int(ca1.sum()), definition="earlier matches of the club in the model history (any competition) strictly before the match date; both clubs must reach the threshold", thresholds={})
    for t in (0, 30, 60, 100, 150, 200, 300):
        out["thresholds"][str(t)] = dict(ca=int((m >= t).sum()), ca1=int(((m >= t) & ca1).sum()), ca1_share=round(float(((m >= t) & ca1).sum() / ca1.sum()), 3))
    tmask = V[(V.dt >= A.START) & (V.dt <= A.END) & V.competition_id.isin(["deutschland:1-bundesliga", "espana:1-liga"])]
    th = np.nanmin(np.vstack([np.array([depth(c, d) for c, d in zip(tmask.home_entity_id, tmask.dt)], dtype=float), np.array([depth(c, d) for c, d in zip(tmask.away_entity_id, tmask.dt)], dtype=float)]), axis=0)
    out["target_leagues_for_comparison"] = dict(matches=int(len(tmask)), median_min_depth=float(np.nanmedian(th)), p10_min_depth=float(np.nanpercentile(th, 10)))
    out["ca1_min_depth_percentiles"] = {str(q): float(np.nanpercentile(m[ca1], q)) for q in (10, 25, 50, 75, 90)}
    return out


def main(reps_b: int = 500, reps_c: int = 500, seed: int = 41) -> dict:
    t0 = time.time()
    ev, pm, _ = R.template()
    res = dict(settings=dict(reps_power=reps_b, reps_holm=reps_c, seed=seed, grid=list(GRID), margins={k: v.tolist() for k, v in MARGINS.items()}, alpha=ALPHA))
    res["A_formula"] = part_a()
    res["B_single_method_power"] = part_b(ev, pm, reps_b, seed)
    res["C_holm_over_three_methods_power"] = part_c(ev, pm, reps_c, seed + 1)
    res["D_ca_history_depth_pre_match_only"] = part_d()
    res["seconds"] = round(time.time() - t0, 1)
    return res


if __name__ == "__main__":
    r = main()
    (OUT / "m5_protocol_v3_planning.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k in ("A_formula",)}, indent=1))
    for k in ("B_single_method_power",):
        print({m: (v["n_for_80pct"], v["n_for_90pct"]) for m, v in r[k].items()})
    print({m: (v["n_for_80pct_holm_worst"], v["n_for_90pct_holm_worst"], v["n_for_90pct_holm_best"]) for m, v in r["C_holm_over_three_methods_power"].items()})
    print(json.dumps(r["D_ca_history_depth_pre_match_only"], indent=1))
    print("seconds", r["seconds"])
