p = "app/seasonsim/m2_protocol.py"
s = open(p, encoding="utf-8").read()
s = s.replace('if __name__ == "__main__":', '''def scope_power(reps: int = 400, seed: int = 5) -> dict:
    """Operating characteristics of the proposed pooled protocol for a Bundesliga + La Liga scope at two choices of practical margin."""
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    ev, fit = df[df.dt >= B.SPLIT], df[df.dt < B.SPLIT]
    lam_mean = {l: (float(g.hg.mean()), float(g.ag.mean())) for l, g in fit.groupby("league")}
    rng = np.random.default_rng(seed)
    leagues = ["BUNDESLIGA", "LALIGA"]
    margins = {"margins 0.10 goals / 0.05 share": np.array([0.10, 0.10, 0.05, 0.05]), "margins 0.15 goals / 0.075 share": np.array([0.15, 0.15, 0.075, 0.075])}
    out = {"matches_in_scope": int(sum((ev.league == lg).sum() for lg in leagues))}
    for sname, k in {"model exactly true": 1.0, "true spread 80% of model (margin bias about 0.05)": 0.8, "true spread 60% of model (margin bias about 0.09)": 0.6, "true spread 40% of model (margin bias about 0.12)": 0.4}.items():
        truth, model = {}, {}
        for lg in leagues:
            e = ev[ev.league == lg]
            P = e[["p1_H", "p1_D", "p1_A"]].values
            model[lg] = scoreline.conditional_poisson(P, e.lam_h.values, e.lam_a.values)
            truth[lg] = scoreline.conditional_poisson(P, np.exp(k * np.log(e.lam_h.values) + (1 - k) * np.log(lam_mean[lg][0])), np.exp(k * np.log(e.lam_a.values) + (1 - k) * np.log(lam_mean[lg][1])))
        res = {m: [] for m in margins}
        for _ in range(reps):
            per = {}
            for lg in leagues:
                est, se = sample_actual(truth[lg], rng)
                per[lg] = (model_vec(model[lg]) - est, se)
            for m, tol in margins.items():
                res[m].append(pooled_protocol(per, leagues, tol)["accepted"])
        out[sname] = {m: round(float(np.mean(v)), 3) for m, v in res.items()}
    return out


if __name__ == "__main__":''', 1)
s = s.replace('    (OUT / "m2_protocol.json").write_text(json.dumps(r, indent=1), encoding="utf-8")', '    r["bundesliga_la_liga_scope"] = scope_power()\n    (OUT / "m2_protocol.json").write_text(json.dumps(r, indent=1), encoding="utf-8")\n    print(json.dumps(r["bundesliga_la_liga_scope"], indent=1))')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
