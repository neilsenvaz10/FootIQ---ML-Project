p = "app/seasonsim/m4_protocol_review.py"
s = open(p, encoding="utf-8").read()

# replace the spread family by a margin-inflation family (spread saturates below the margin, so it can never produce a truth outside it)
a = s.index("    spread = {}")
b = s.index("    return ev, pm, spread")
s = s[:a] + '''    spread = {q: inflate(pm["S1"], q) for q in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40)}
''' + s[b:]
s = s.replace("def template():", '''def inflate(pmf: np.ndarray, q: float) -> np.ndarray:
    """Truth in which, with probability q, the winner of a decisive match scores one more goal: every mean winning margin rises by about q and one-goal wins become rarer."""
    G = np.arange(B.K)
    home, away = (G[:, None] > G[None, :]), (G[:, None] < G[None, :])
    sh = np.zeros_like(pmf)
    src_h = pmf * home[None]
    src_a = pmf * away[None]
    sh[:, 1:, :] += src_h[:, :-1, :]
    sh[:, -1, :] += src_h[:, -1, :]
    sh[:, :, 1:] += src_a[:, :, :-1]
    sh[:, :, -1] += src_a[:, :, -1]
    sh += pmf * (~(home | away))[None]
    return (1 - q) * pmf + q * sh


def template():''', 1)
s = s.replace('''    pts = [(1.0, population_bias(pm["S1"], pm["S1"]))] + [(k, population_bias(pm["S1"], v)) for k, v in sorted(spread.items(), reverse=True)]''', '''    pts = [(0.0, population_bias(pm["S1"], pm["S1"]))] + [(k, population_bias(pm["S1"], v)) for k, v in sorted(spread.items())]''')
s = s.replace('''spread_bias_table=[dict(spread_factor=k, worst_bias_over_margin=round(r, 2)) for k, r in ratios]''', '''inflation_bias_table=[dict(inflation_probability=k, S1_worst_bias_over_margin=round(r, 2)) for k, r in ratios]''')
s = s.replace('''    k_b = min(spread, key=lambda k: abs(dict(ratios)[k] - 1.0))                          # the tabulated spread closest to the margin boundary
    scenarios = {"truth = S1 (S1 exactly right)": pm["S1"], "truth = S3 (S3 exactly right)": pm["S3"], f"truth = S1 spread {k_b} (S1 near the margin boundary)": spread[k_b], "truth = S1 spread 0.2 (every method far outside the margin)": spread[0.2]}''', '''    k_b = min(spread, key=lambda k: abs(dict(ratios)[k] - 1.0))                          # the tabulated inflation closest to the margin boundary for S1
    scenarios = {"truth = S1 (S1 exactly right)": pm["S1"], "truth = S3 (S3 exactly right)": pm["S3"], f"truth = winners score +1 goal with probability {k_b} (S1 on the margin boundary)": spread[k_b],
                 "truth = winners score +1 goal with probability 0.40 (every method far outside the margin)": spread[0.40]}''')
s = s.replace('print(json.dumps(r["spread_bias_table"]))', 'print(json.dumps(r["inflation_bias_table"]))')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
