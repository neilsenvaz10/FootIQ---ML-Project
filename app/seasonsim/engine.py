"""Monte Carlo season engine: sample every remaining fixture, rebuild the table, rank with the league's official tie-break procedure, aggregate.

Pure NumPy, seeded (same seed + same inputs + same rule profile => identical output). No model code runs here: the per-fixture score distributions
(`pmf`, shape [F, K, K], goals 0..K-1 for home x away) are produced beforehand by `scoreline.py` from the frozen models' probabilities.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import rules

K = 10                                           # goals per team are capped at K-1 (a stated limit of the scoreline model)


@dataclass
class SeasonInput:
    teams: list                                  # entity ids, index = team number
    names: list
    played_home: np.ndarray                      # int indices
    played_away: np.ndarray
    played_hg: np.ndarray
    played_ag: np.ndarray
    fix_home: np.ndarray
    fix_away: np.ndarray
    pmf: np.ndarray                              # [F, K, K], rows sum to 1
    fix_ids: list = field(default_factory=list)


@dataclass
class SimResult:
    n: int
    seed: int
    pos: Optional[np.ndarray]                    # [N, T] final position 1..T of each team (None when ranking was skipped)
    points: np.ndarray
    gd: np.ndarray
    terminal_events: dict                         # counts, see _rank_all
    gf: Optional[np.ndarray] = None


def _sample_scores(pmf: np.ndarray, n: int, rng: np.random.Generator):
    F = pmf.shape[0]
    cdf = np.cumsum(pmf.reshape(F, -1), axis=1)
    cdf[:, -1] = 1.0
    sh = np.empty((n, F), dtype=np.int8)
    sa = np.empty((n, F), dtype=np.int8)
    u = rng.random((n, F))
    for f in range(F):
        idx = np.searchsorted(cdf[f], u[:, f], side="right")
        np.minimum(idx, K * K - 1, out=idx)
        sh[:, f], sa[:, f] = idx // K, idx % K
    return sh, sa


def validate_input(inp: SeasonInput) -> None:
    T = len(inp.teams)
    F = len(inp.fix_home)
    if inp.pmf.shape != (F, K, K):
        raise ValueError(f"pmf shape {inp.pmf.shape} != {(F, K, K)}")
    if F and not np.allclose(inp.pmf.reshape(F, -1).sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("every fixture's score distribution must sum to 1")
    for a in (inp.played_home, inp.played_away, inp.fix_home, inp.fix_away):
        if len(a) and (a.min() < 0 or a.max() >= T):
            raise ValueError("team index out of range")


class _Lookup:
    """Result of the match (home i, away j): played (fixed) or simulated (index into the score arrays)."""

    def __init__(self, inp: SeasonInput):
        T = len(inp.teams)
        self.T = T
        self.played = {}
        self.fixture = {}
        for h, a, hg, ag in zip(inp.played_home, inp.played_away, inp.played_hg, inp.played_ag):
            self.played[int(h) * T + int(a)] = (int(hg), int(ag))
        for f, (h, a) in enumerate(zip(inp.fix_home, inp.fix_away)):
            self.fixture[int(h) * T + int(a)] = f

    def goals(self, s: int, i: int, j: int, sh, sa):
        """(goals of home i, goals of away j) of the match i-v-j in simulation s, or None if that match does not exist."""
        k = i * self.T + j
        if k in self.played:
            return self.played[k]
        f = self.fixture.get(k)
        return None if f is None else (int(sh[s, f]), int(sa[s, f]))


def _criterion_value(c: str, t: int, base: list, s: int, lk: _Lookup, sh, sa, tot) -> int:
    gf, ga, away_goals = tot
    if c == "goal_difference":
        return int(gf[s, t] - ga[s, t])
    if c == "goals_scored":
        return int(gf[s, t])
    if c == "away_goals_total":
        return int(away_goals[s, t])
    pts = gd = ag = 0
    for u in base:
        if u == t:
            continue
        for home, away in ((t, u), (u, t)):
            r = lk.goals(s, home, away, sh, sa)
            if r is None:
                continue
            mine, theirs = (r[0], r[1]) if home == t else (r[1], r[0])
            pts += 3 if mine > theirs else 1 if mine == theirs else 0
            gd += mine - theirs
            if away == t:
                ag += mine
    return {"h2h_points": pts, "h2h_goal_difference": gd, "h2h_away_goals": ag}[c]


def _resolve(group: list, profile: dict, s: int, lk, sh, sa, tot, events: dict, start_pos: int, crit_from: int) -> list:
    """Order the clubs of a tied group, best first, with the profile's criteria (sequential refinement). Clubs that no supported criterion separates stay
    UNRESOLVED: they keep a stable order for bookkeeping only and are recorded in events['terminal'] as (first position, size, kind, members); no random or coin-flip
    decision is ever made (decision D6)."""
    kind = "two_clubs" if len(group) == 2 else "multi_clubs"
    crit = profile["criteria"][kind][crit_from:]
    scope = profile.get("h2h_scope", "current_group")
    subgroups = [list(group)]
    used_h2h = False
    unavailable_hit = False
    for c in crit:
        if all(len(g) == 1 for g in subgroups):
            break
        if c in rules.UNAVAILABLE:
            unavailable_hit = unavailable_hit or any(len(g) > 1 for g in subgroups)
            continue
        new = []
        for g in subgroups:
            if len(g) == 1:
                new.append(g)
                continue
            base = group if scope == "original_group" else g
            vals = {t: _criterion_value(c, t, base, s, lk, sh, sa, tot) for t in g}
            if c.startswith("h2h"):
                used_h2h = True
            for v in sorted(set(vals.values()), reverse=True):
                new.append([t for t in g if vals[t] == v])
        subgroups = new
    out, pos = [], start_pos
    for g in subgroups:
        if len(g) > 1:                                              # final decider (play-off / neutral match / lots / fair play without data): NOT simulated
            events["terminal"].append((pos, len(g), "unavailable_criterion" if unavailable_hit else "terminal", [int(t) for t in g]))
        out += g
        pos += len(g)
    if used_h2h and len(group) > 2:
        events["multi_h2h"] += 1
    return out


def _prefix_len(profile: dict) -> int:
    a, b = profile["criteria"]["two_clubs"], profile["criteria"]["multi_clubs"]
    overall = {"goal_difference", "goals_scored", "away_goals_total"}
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n] and a[n] in overall:
        n += 1
    return n


def _rank_all(points, gf, ga, away_goals, sh, sa, inp: SeasonInput, profile: dict) -> tuple:
    N, T = points.shape
    L = _prefix_len(profile)
    names = profile["criteria"]["two_clubs"][:L]
    cols = [points]
    for c in names:
        cols.append({"goal_difference": gf - ga, "goals_scored": gf, "away_goals_total": away_goals}[c])
    key = np.zeros((N, T), dtype=np.int64)
    for col in cols:
        key = key * 4096 + (col.astype(np.int64) + 2048)             # every term is far inside +-2048
    order = np.argsort(-key, axis=1, kind="stable")
    sk = np.take_along_axis(key, order, axis=1)
    tie_pairs = sk[:, 1:] == sk[:, :-1]
    lk = _Lookup(inp)
    tot = (gf, ga, away_goals)
    events = dict(terminal=[], multi_h2h=0)
    per_sim_terminal = []
    sims_with_ties = np.nonzero(tie_pairs.any(axis=1))[0]
    for s in sims_with_ties:
        ev = dict(terminal=[], multi_h2h=0)
        row, skr = order[s], sk[s]
        i = 0
        new_row = list(row)
        while i < T:
            j = i
            while j + 1 < T and skr[j + 1] == skr[i]:
                j += 1
            if j > i:
                new_row[i:j + 1] = _resolve([int(t) for t in row[i:j + 1]], profile, int(s), lk, sh, sa, tot, ev, i + 1, L)
            i = j + 1
        order[s] = new_row
        if ev["terminal"] or ev["multi_h2h"]:
            per_sim_terminal.append((int(s), ev))
    pos = np.empty((N, T), dtype=np.int16)
    np.put_along_axis(pos, order, np.arange(1, T + 1, dtype=np.int16)[None, :].repeat(N, axis=0), axis=1)
    return pos, per_sim_terminal, len(sims_with_ties)


def simulate(inp: SeasonInput, profile: dict, n: int = 10000, seed: int = 20261025, rank: bool = True) -> SimResult:
    """n seasons from the real table plus the sampled remaining fixtures. `profile` must come from rules.get_profile (verified and implemented).
    rank=False skips the league ranking (used only by scoreline diagnostics that need points and goals, not positions)."""
    validate_input(inp)
    T, F = len(inp.teams), len(inp.fix_home)
    rng_s = np.random.default_rng([seed, 0])
    base_pts, base_gf, base_ga, base_aw = (np.zeros(T, dtype=np.int64) for _ in range(4))
    w, d = profile["points"]["win"], profile["points"]["draw"]
    for h, a, hg, ag in zip(inp.played_home, inp.played_away, inp.played_hg, inp.played_ag):
        base_pts[h] += w if hg > ag else d if hg == ag else 0
        base_pts[a] += w if ag > hg else d if hg == ag else 0
        base_gf[h] += hg; base_ga[h] += ag; base_gf[a] += ag; base_ga[a] += hg; base_aw[a] += ag
    if F:
        sh, sa = _sample_scores(inp.pmf, n, rng_s)
        hp = np.where(sh > sa, w, np.where(sh == sa, d, 0)).astype(np.int64)
        ap = np.where(sa > sh, w, np.where(sh == sa, d, 0)).astype(np.int64)
        Hm = np.zeros((F, T), dtype=np.int64); Am = np.zeros((F, T), dtype=np.int64)
        Hm[np.arange(F), inp.fix_home] = 1
        Am[np.arange(F), inp.fix_away] = 1
        points = base_pts + hp @ Hm + ap @ Am
        gf = base_gf + sh.astype(np.int64) @ Hm + sa.astype(np.int64) @ Am
        ga = base_ga + sa.astype(np.int64) @ Hm + sh.astype(np.int64) @ Am
        away_goals = base_aw + sa.astype(np.int64) @ Am
    else:
        sh = sa = np.zeros((n, 0), dtype=np.int8)
        points, gf, ga, away_goals = (np.repeat(x[None, :], n, axis=0) for x in (base_pts, base_gf, base_ga, base_aw))
    if not rank:
        return SimResult(n=n, seed=seed, pos=None, points=points, gd=gf - ga, gf=gf, terminal_events=dict(per_sim=[], sims_with_points_prefix_ties=0))
    pos, term, n_tied = _rank_all(points, gf, ga, away_goals, sh, sa, inp, profile)
    return SimResult(n=n, seed=seed, pos=pos, points=points, gd=gf - ga, gf=gf, terminal_events=dict(per_sim=term, sims_with_points_prefix_ties=int(n_tied)))


def _band_bounds(res: SimResult, lo_pos: int, hi_pos: int) -> tuple:
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
