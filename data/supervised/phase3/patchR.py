p = "app/seasonsim/m4_margin_impact.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''def base_inputs(key: str):''', '''def coupled_sampler(pmf: np.ndarray, n: int, rng: np.random.Generator):
    """Draw the win/draw/loss outcome first and the score second, with two separate streams of uniform numbers, so that two score distributions with the SAME outcome probabilities produce
    identical outcomes (identical points) and differ only in the scores (goal difference, goals scored)."""
    F = pmf.shape[0]
    K = pmf.shape[1]
    G = np.arange(K)
    masks = [(G[:, None] > G[None, :]), (G[:, None] == G[None, :]), (G[:, None] < G[None, :])]
    u1, u2 = rng.random((n, F)), rng.random((n, F))
    sh = np.empty((n, F), dtype=np.int8)
    sa = np.empty((n, F), dtype=np.int8)
    for f in range(F):
        marg = np.array([pmf[f][m].sum() for m in masks])
        ocdf = np.cumsum(marg / marg.sum())
        ocdf[-1] = 1.0
        o = np.minimum(np.searchsorted(ocdf, u1[:, f], side="right"), 2)
        for k, m in enumerate(masks):
            sel = np.where(o == k)[0]
            if not len(sel):
                continue
            cond = (pmf[f] * m).reshape(-1)
            cdf = np.cumsum(cond / cond.sum())
            cdf[-1] = 1.0
            idx = np.minimum(np.searchsorted(cdf, u2[sel, f], side="right"), K * K - 1)
            sh[sel, f], sa[sel, f] = idx // K, idx % K
    return sh, sa


def base_inputs(key: str):''', 1)
s = s.replace('''def run(n: int = 6000, seed: int = 17) -> dict:
    out = {}''', '''def run(n: int = 6000, seed: int = 17) -> dict:
    out = {}
    original = engine._sample_scores
    engine._sample_scores = coupled_sampler                                    # restored in the finally below''')
s = s.replace('''        out[key] = res
    return out''', '''        out[key] = res
    engine._sample_scores = original
    return out''')
s = s.replace('''            same_positions = (ref.pos == r2.pos).all(axis=1).mean()''', '''            same_positions = (ref.pos == r2.pos).all(axis=1).mean()
            moved = (ref.pos != r2.pos).sum(axis=1)''')
s = s.replace('''share_of_seasons_with_any_position_change=round(float(1 - same_positions), 3),''', '''share_of_seasons_with_any_position_change=round(float(1 - same_positions), 3), mean_clubs_changing_position=round(float(moved.mean()), 3),
                            points_identical_in_every_season=bool((ref.points == r2.points).all()),''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
