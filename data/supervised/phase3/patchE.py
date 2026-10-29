p = "app/seasonsim/m2_protocol.py"
s = open(p, encoding="utf-8").read()

s = s.replace('scen = {"T0_model_exactly_true": 1.0, "T1_true_spread_80pct_of_model": 0.8, "T2_true_spread_60pct_of_model": 0.6}',
              'scen = {"T0_model_exactly_true": 1.0, "T1_true_spread_80pct_of_model": 0.8, "T2_true_spread_60pct_of_model": 0.6, "T3_true_spread_40pct_of_model": 0.4}')

# pooled protocol P3
s = s.replace('def run(reps: int = 400, seed: int = 21) -> dict:', '''def pooled_protocol(per_league: dict, leagues: list, tol: np.ndarray, level: float = 0.90) -> dict:
    """P3 (proposed primary): pooled equivalence + per-league screen. per_league[lg] = (dev, se)."""
    inv = np.array([1.0 / per_league[lg][1] ** 2 for lg in leagues])
    dev = np.array([per_league[lg][0] for lg in leagues])
    pooled = (inv * dev).sum(axis=0) / inv.sum(axis=0)
    pooled_se = 1.0 / np.sqrt(inv.sum(axis=0))
    z = norm.ppf(1 - (1 - level) / 2)
    pooled_ok = bool(((np.abs(pooled) + z * pooled_se) <= tol).all())               # 90% CI of the pooled deviation lies inside the practical margin (two one-sided tests)
    z_holm = norm.ppf(1 - 0.05 / (4 * len(leagues)) / 2)
    flagged = [lg for lg in leagues if ((np.abs(per_league[lg][0]) / per_league[lg][1] > z_holm) & (np.abs(per_league[lg][0]) > tol)).any()]
    return dict(pooled_equivalence=pooled_ok, no_league_flagged=not flagged, accepted=pooled_ok and not flagged, flagged=flagged)


def run(reps: int = 400, seed: int = 21) -> dict:''')

s = s.replace('''        result["scenarios"][sname] = dict(true_bias_of_the_model_vs_truth=bias, acceptance_probability=table)''', '''        tol = np.array([TOL_ORIG[k] for k in KEYS])
        p3 = {"all_five_leagues": [], "bundesliga_and_la_liga": []}
        for r in range(reps):
            per = {lg: acc[lg][r] for lg in B.LEAGUES}
            p3["all_five_leagues"].append(pooled_protocol(per, list(B.LEAGUES), tol)["accepted"])
            p3["bundesliga_and_la_liga"].append(pooled_protocol(per, ["BUNDESLIGA", "LALIGA"], tol)["accepted"])
        table["P3_pooled_equivalence_plus_league_screen (tolerances 0.10 goals / 0.05 share as practical margins)"] = {k: round(float(np.mean(v)), 3) for k, v in p3.items()}
        result["scenarios"][sname] = dict(true_bias_of_the_model_vs_truth=bias, acceptance_probability=table)''')
s = s.replace('''            print("  ", d, {n: x["all_five"] for n, x in t.items()}, "| BL", {n: x["per_league"]["BUNDESLIGA"] for n, x in t.items()})''', '''            if d.startswith("P3"):
                print("  ", d[:40], t)
            else:
                print("  ", d, {n: x["all_five"] for n, x in t.items()})''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
