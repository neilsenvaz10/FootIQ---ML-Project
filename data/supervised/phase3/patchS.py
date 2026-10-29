p = "app/seasonsim/m4_margin_impact.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''def band_values(summary: dict) -> dict:''', '''def late_season_inputs(key: str, cutoff: str, season: str = "2025-26"):
    """A late-season state of a COMPLETED season (pre-match probabilities and expected goals of the matches still to be played at `cutoff`), for the sensitivity experiment only."""
    import pandas as pd

    m = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    m = m[(m.league == key) & (m.season == season)]
    c = pd.Timestamp(cutoff)
    played, rem = m[m.dt < c], m[m.dt >= c]
    teams = sorted(set(m.home) | set(m.away))
    idx = {t: i for i, t in enumerate(teams)}
    pmf, _ = scoreline.build_pmf("S1", rem[["p1_H", "p1_D", "p1_A"]].values, rem.lam_h.values, rem.lam_a.values, key)
    return SeasonInput(teams=teams, names=teams, played_home=played.home.map(idx).values.astype(int), played_away=played.away.map(idx).values.astype(int), played_hg=played.hg.values.astype(int),
                       played_ag=played.ag.values.astype(int), fix_home=rem.home.map(idx).values.astype(int), fix_away=rem.away.map(idx).values.astype(int), pmf=pmf), len(rem)


def band_values(summary: dict) -> dict:''', 1)
s = s.replace('''def run(n: int = 6000, seed: int = 17) -> dict:
    out = {}''', '''def distort_table(inp, profile, n: int, seed: int) -> list:
    ref = engine.simulate(inp, profile, n, seed)
    sref = engine.summarize(ref, inp, profile)
    bref = band_values(sref)
    res = []
    for label, make in (("winners +1 goal, probability 0.15 (margin bias about +0.15)", lambda p: R.inflate(p, 0.15)), ("winners +1 goal, probability 0.30", lambda p: R.inflate(p, 0.30)), ("big wins shrink, probability 0.30 (margin bias about -0.18)", lambda p: R.deflate(p, 0.30))):
        pmf2 = make(inp.pmf)
        inp2 = SeasonInput(**{**inp.__dict__, "pmf": pmf2})
        r2 = engine.simulate(inp2, profile, n, seed)
        s2 = engine.summarize(r2, inp2, profile)
        b2 = band_values(s2)
        ch = {}
        for name in ("title", "top4", "relegation"):
            d = {sref["teams"][i]["entity_id"]: bref[name][i] for i in range(len(sref["teams"]))}
            d2 = {s2["teams"][i]["entity_id"]: b2[name][i] for i in range(len(s2["teams"]))}
            ch[name] = round(max(abs(d[k] - d2[k]) for k in d if not (np.isnan(d[k]) or np.isnan(d2[k]))), 4)
        res.append(dict(distortion=label, bias_margin_home_win=round(B.model_stats(pmf2)["mean_margin_home_win"] - B.model_stats(inp.pmf)["mean_margin_home_win"], 3), max_change_title=ch["title"], max_change_top4=ch["top4"],
                        max_change_relegation=ch["relegation"], share_of_seasons_with_any_position_change=round(float((ref.pos != r2.pos).any(axis=1).mean()), 3), mean_clubs_changing_position=round(float((ref.pos != r2.pos).sum(axis=1).mean()), 3)))
    return res


def run_late(n: int = 6000, seed: int = 17) -> dict:
    out = {}
    original = engine._sample_scores
    engine._sample_scores = coupled_sampler
    try:
        for key, cutoffs in (("BUNDESLIGA", ("2026-04-10", "2026-05-01")), ("LALIGA", ("2026-04-18", "2026-05-09"))):
            for c in cutoffs:
                inp, left = late_season_inputs(key, c)
                out[f"{key} {c} ({left} matches left)"] = distort_table(inp, rules.get_profile(key, "2026-27"), n, seed)
    finally:
        engine._sample_scores = original
    return out


def run(n: int = 6000, seed: int = 17) -> dict:
    out = {}''', 1)
s = s.replace('''if __name__ == "__main__":
    r = run()
    (OUT / "m4_margin_impact.json").write_text(json.dumps(r, indent=1), encoding="utf-8")''', '''if __name__ == "__main__":
    r = run()
    r["late_season_states_2025_26_completed_season"] = run_late()
    (OUT / "m4_margin_impact.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    for k, rows in r["late_season_states_2025_26_completed_season"].items():
        print(k)
        for x in rows:
            print("  ", x)''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
