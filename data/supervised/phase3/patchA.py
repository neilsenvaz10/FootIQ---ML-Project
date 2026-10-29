p = "app/seasonsim/engine.py"
s = open(p, encoding="utf-8").read()

s = s.replace('def _resolve(group: list, profile: dict, s: int, lk, sh, sa, tot, rng, events: dict, start_pos: int, crit_from: int) -> list:\n    """Order the clubs of a tied group, best first, with the profile\'s criteria (sequential refinement). Returns the ordered list."""',
              'def _resolve(group: list, profile: dict, s: int, lk, sh, sa, tot, events: dict, start_pos: int, crit_from: int) -> list:\n    """Order the clubs of a tied group, best first, with the profile\'s criteria (sequential refinement). Clubs that no supported criterion separates stay\n    UNRESOLVED: they keep a stable order for bookkeeping only and are recorded in events[\'terminal\'] as (first position, size, kind, members); no random or coin-flip\n    decision is ever made (decision D6)."""')
s = s.replace('''        if len(g) > 1:                                              # terminal criterion (play-off / neutral match / lots / unspecified): random
            g = list(rng.permutation(g))
            events["terminal"].append((pos, len(g), "unavailable_criterion" if unavailable_hit else "terminal"))''',
              '''        if len(g) > 1:                                              # final decider (play-off / neutral match / lots / fair play without data): NOT simulated
            events["terminal"].append((pos, len(g), "unavailable_criterion" if unavailable_hit else "terminal", [int(t) for t in g]))''')
s = s.replace("def _rank_all(points, gf, ga, away_goals, sh, sa, inp: SeasonInput, profile: dict, rng) -> tuple:", "def _rank_all(points, gf, ga, away_goals, sh, sa, inp: SeasonInput, profile: dict) -> tuple:")
s = s.replace("_resolve([int(t) for t in row[i:j + 1]], profile, int(s), lk, sh, sa, tot, rng, ev, i + 1, L)", "_resolve([int(t) for t in row[i:j + 1]], profile, int(s), lk, sh, sa, tot, ev, i + 1, L)")
s = s.replace("    rng_t = np.random.default_rng([seed, 1])\n", "")
s = s.replace("_rank_all(points, gf, ga, away_goals, sh, sa, inp, profile, rng_t)", "_rank_all(points, gf, ga, away_goals, sh, sa, inp, profile)")

i = s.index("def summarize(")
s = s[:i] + '''def _band_bounds(res: SimResult, lo_pos: int, hi_pos: int) -> tuple:
    """Per club: share of simulations in which it surely is in the band (low) and possibly is in the band (high). They differ only through unresolved ties."""
    inb = (res.pos >= lo_pos) & (res.pos <= hi_pos)
    low, high = inb.copy(), inb.copy()
    for s, ev in res.terminal_events["per_sim"]:
        for start, size, _kind, members in ev["terminal"]:
            k = max(0, min(start + size - 1, hi_pos) - max(start, lo_pos) + 1)
            for t in members:
                if k == 0:
                    low[s, t] = high[s, t] = False
                elif k == size:
                    low[s, t] = high[s, t] = True
                else:
                    low[s, t], high[s, t] = False, True
    return low.mean(axis=0), high.mean(axis=0)


def summarize(res: SimResult, inp: SeasonInput, profile: dict) -> dict:
    """Aggregate a ranked simulation. A band probability (title, top four, relegation) is reported only when no unresolved tie touches it: otherwise it is None
    and only the lower and upper bound are given. Exact-position probabilities exclude the simulations in which a club's position is unresolved."""
    N, T = res.pos.shape
    bands = profile.get("bands", {})
    unresolved = np.zeros((N, T), dtype=bool)
    for s, ev in res.terminal_events["per_sim"]:
        for _start, _size, _kind, members in ev["terminal"]:
            unresolved[s, members] = True
    posmat = np.zeros((T, T))
    for t in range(T):
        posmat[t] = np.bincount(res.pos[~unresolved[:, t], t] - 1, minlength=T) / N
    names = {"title": "p_title", "top4": "p_top4", "relegation": "p_relegation", "relegation_playoff": "p_relegation_playoff"}
    bounds = {k: _band_bounds(res, min(bands[k]), max(bands[k])) for k in names if bands.get(k)}
    ambiguous_bands = sorted(k for k, (lo, hi) in bounds.items() if not np.allclose(lo, hi))
    n_unres = sum(1 for _, ev in res.terminal_events["per_sim"] if ev["terminal"])
    teams = []
    for t in np.argsort(-res.points.mean(axis=0), kind="stable"):
        pts = res.points[:, t]
        row = dict(entity_id=inp.teams[t], name=inp.names[t], expected_points=float(pts.mean()), points_p10=float(np.percentile(pts, 10)), points_p90=float(np.percentile(pts, 90)),
                   expected_rank=None if unresolved[:, t].any() else float(res.pos[:, t].mean()), rank_p10=float(np.percentile(res.pos[:, t], 10)), rank_p90=float(np.percentile(res.pos[:, t], 90)),
                   expected_goal_difference=float(res.gd[:, t].mean()), position_probabilities=[float(x) for x in posmat[t]], position_unresolved_probability=float(unresolved[:, t].mean()))
        for k, name in names.items():
            if k in bounds:
                lo, hi = float(bounds[k][0][t]), float(bounds[k][1][t])
                row[name], row[name + "_low"], row[name + "_high"] = (lo if lo == hi else None), lo, hi
            else:
                row[name] = row[name + "_low"] = row[name + "_high"] = None
        teams.append(row)
    return dict(
        n=N, seed=res.seed, teams=teams, standard_error_max=float(0.5 / np.sqrt(N)),
        final_position_probabilities_supported=not ambiguous_bands and n_unres == 0, bands_with_unresolved_ties=ambiguous_bands,
        tie_resolution=dict(simulations_with_a_tie_after_the_overall_criteria=res.terminal_events["sims_with_points_prefix_ties"],
                            simulations_with_an_unresolved_tie=n_unres, share_with_an_unresolved_tie=n_unres / N,
                            simulations_with_a_multi_club_head_to_head=sum(1 for _, ev in res.terminal_events["per_sim"] if ev["multi_h2h"]),
                            note="Ties that no supported criterion separates (play-off, neutral-ground match, lots, fair play without card data) are left UNRESOLVED, never decided by a coin: "
                                 "the affected probabilities are withheld and only bounds are given."))
'''
open(p, "w", encoding="utf-8", newline="\n").write(s)

p = "config/season_rules.json"
s = open(p, encoding="utf-8").read()
s = s.replace('"resolved_by": "coin_flip_placeholder", "decision": "D6"', '"resolved_by": "unresolved_not_simulated", "decision": "D6 (approved 2026-10-25: never a coin)"')
s = s.replace("is not a result we can predict: it is simulated as a fair coin and its frequency is reported (decision D6 is unresolved).", "is not a result we can predict: such outcomes are left UNRESOLVED (decision D6) and the affected probabilities are withheld.")
s = s.replace("The neutral-ground match (final criterion) is simulated as a fair coin (decision D6 unresolved).", "The neutral-ground match (final criterion) is not simulated: such outcomes stay unresolved (decision D6).")
s = s.replace("Such ties are separated at random and reported.", "Such ties stay unresolved and are reported.")
s = s.replace("The play-off is simulated as a fair coin (decision D6 unresolved).", "The play-off is not simulated: such outcomes stay unresolved (decision D6).")
s = s.replace("When a tie reaches it, the clubs are separated at random and the frequency is reported.", "When a tie reaches it, the outcome stays unresolved and the frequency is reported.")
s = s.replace("the text was read from the Internet Archive copy of this exact URL, so it should be re-checked against the live federation page by you.",
              "the text was read from the Internet Archive capture of this exact URL taken 2026-07-14 11:27:22 UTC (origin last-modified 2026-06-30); a search index of the live URL confirms the same title and that art. 10 (tie-break) is on page 6. Rechecked 2026-10-25: the live URL still returns HTTP 403 to automated access. Please re-check it against the live federation page.")
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
