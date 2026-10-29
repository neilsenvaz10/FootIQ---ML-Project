p = "app/seasonsim/m4_protocol_review.py"
s = open(p, encoding="utf-8").read()

s = s.replace("def template():", '''def deflate(pmf: np.ndarray, q: float) -> np.ndarray:
    """Opposite distortion: with probability q the winner of a win by two or more goals scores one goal fewer (winning margins shrink, one-goal wins become more common)."""
    G = np.arange(B.K)
    big_h = (G[:, None] - G[None, :]) >= 2
    big_a = (G[None, :] - G[:, None]) >= 2
    mh, ma = pmf * big_h[None], pmf * big_a[None]
    out = pmf.copy()
    moved_h = mh * q
    moved_a = ma * q
    out -= moved_h + moved_a
    out[:, :-1, :] += moved_h[:, 1:, :]                         # mass at (h, a) -> (h - 1, a)
    out[:, :, :-1] += moved_a[:, :, 1:]                         # mass at (h, a) -> (h, a - 1)
    return out


def solve_q(pm_truth: np.ndarray, distort, target: float = 1.0) -> float:
    """Distortion probability for which the model `pm_truth` sits exactly at `target` times the margin (largest of the four |bias| / margin)."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        r = float(np.max(np.abs(population_bias(pm_truth, distort(pm_truth, mid))) / DELTA))
        lo, hi = (mid, hi) if r < target else (lo, mid)
    return (lo + hi) / 2


def opposite_direction_demo(ev, pm, reps: int, rng) -> dict:
    """Two WRONG methods on opposite sides of the truth, each exactly on the margin boundary: M_a = S1 with margins too small, M_b = S1 with margins too large (truth = S1 inflated or deflated halfway)."""
    q_i = solve_q(pm["S1"], inflate)
    q_d = solve_q(pm["S1"], deflate)
    truth = pm["S1"]
    ma, mb = deflate(truth, q_d), inflate(truth, q_i)                       # methods that are wrong in opposite directions by exactly the margin
    ordered = [("Ma", ma), ("Mb", mb)]
    res = {}
    for n in (1158, 2606, 4321):
        cnt = dict(sequence_as_proposed=0, holm=0, bonferroni=0, each=dict(Ma=0, Mb=0))
        for _ in range(reps):
            idx = rng.integers(0, len(ev), n)
            est, se = P.sample_actual(truth[idx], rng)
            ps = {name: tost_p(P.model_vec(arr[idx]) - est, se) for name, arr in ordered}
            cnt["each"]["Ma"] += ps["Ma"] <= ALPHA
            cnt["each"]["Mb"] += ps["Mb"] <= ALPHA
            cnt["sequence_as_proposed"] += (ps["Ma"] <= ALPHA) or (ps["Mb"] <= ALPHA)
            order = sorted(ps, key=ps.get)
            cnt["holm"] += ps[order[0]] <= ALPHA / 2
            cnt["bonferroni"] += (ps["Ma"] <= ALPHA / 2) or (ps["Mb"] <= ALPHA / 2)
        res[str(n)] = dict(false_acceptance_each_method_alone=dict(Ma=round(cnt["each"]["Ma"] / reps, 3), Mb=round(cnt["each"]["Mb"] / reps, 3)), sequence_as_proposed=round(cnt["sequence_as_proposed"] / reps, 3),
                           holm_over_methods=round(cnt["holm"] / reps, 3), bonferroni_over_methods=round(cnt["bonferroni"] / reps, 3))
    return dict(deflation_probability=round(q_d, 3), inflation_probability=round(q_i, 3), bias_vs_margin_ratio=dict(Ma=round(float(np.max(np.abs(population_bias(ma, truth)) / DELTA)), 3), Mb=round(float(np.max(np.abs(population_bias(mb, truth)) / DELTA)), 3)),
                results_by_sample_size=res)


def power_curve(ev, pm, rng, reps: int) -> dict:
    """Probability that the TRUE model (truth = S1, method S1) is accepted at level alpha, versus the number of matches, at the three candidate margins."""
    out = {}
    for name, d in {"0.10 / 0.05": np.array([0.10, 0.10, 0.05, 0.05]), "0.15 / 0.075": DELTA, "0.20 / 0.10": np.array([0.20, 0.20, 0.10, 0.10])}.items():
        row = {}
        for n in (686, 1158, 1464, 1800, 2200, 2606, 3300, 4321):
            acc = 0
            for _ in range(reps):
                idx = rng.integers(0, len(ev), n)
                est, se = P.sample_actual(pm["S1"][idx], rng)
                acc += tost_p(P.model_vec(pm["S1"][idx]) - est, se, d) <= ALPHA
            row[str(n)] = round(acc / reps, 3)
        out[name] = row
    return out


def template():''', 1)
s = s.replace('''    out["holm_league_screen_false_flags_when_S1_is_exactly_right"]''', '''    out["opposite_direction_demo"] = opposite_direction_demo(ev, pm, 1500, rng)
    out["power_curve_correct_model_single_method_alpha_0.05"] = power_curve(ev, pm, rng, 500)
    out["holm_league_screen_false_flags_when_S1_is_exactly_right"]''', 1)
s = s.replace('    print(json.dumps({k: r[k] for k in r if k.startswith("holm")}, indent=1))', '    print(json.dumps({k: r[k] for k in r if k.startswith(("holm", "opposite", "power"))}, indent=1))')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
