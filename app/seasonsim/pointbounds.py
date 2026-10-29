"""Rigorous lower and upper bounds for league-position probabilities from POINTS-ONLY simulations (used by the experimental points-only mode for the Bundesliga and La Liga).

What is simulated: only win / draw / loss of every remaining fixture (frozen club v1 probabilities), exactly as in the points-only mode. No score is generated, no coin is flipped.

What is computed per simulated season and per club: the BEST and the WORST position the club could finish in under the league's official tie-break procedure, over EVERY set of
scores that is consistent with (a) the known completed results and (b) the simulated win / draw / loss pattern. Clubs level on points form a tie group; inside it, a club Y is
"definitely above" a club X only if the tie-break criteria, evaluated as intervals, force it:
  * a win adds a goal margin of at least +1 (any positive integer), a draw adds exactly 0, a loss adds at most -1;
  * so goal difference, goals scored, head-to-head goal difference, ... are intervals that become exact when the club has nothing left to play;
  * points-based head-to-head criteria are exact (outcomes are simulated);
  * criteria are compared in the league's order; a criterion decides only if the intervals are strictly separated; the next one is consulted only if both values are exactly
    equal; anything else is NOT definite (the order is unresolved, no coin).
best  = (first position of the tie group) + (clubs definitely above)         -> the club cannot finish higher
worst = (last position of the tie group)  - (clubs definitely below)          -> the club cannot finish lower
Probabilities (over the simulations):
  guaranteed = P(best >= band start and worst <= band end)      the band is reached whatever the unknown scores are          (lower bound)
  possible   = P(worst >= band start and best <= band end)      the band is reachable for some consistent scores             (upper bound)
  unresolved = possible - guaranteed
Rigour: both bounds are valid OUTER bounds (guaranteed is never too high, possible is never too low) for every tie-break outcome compatible with the information; they use only pairwise
"definitely above" facts, so they can be wider than the exact set of reachable positions (conservative), never narrower. They do not remove model error (the win/draw/loss probabilities are
the frozen model's) or Monte Carlo error (standard errors are returned).
Rule readings: a tie among THREE OR MORE clubs is decided here only by the first `bounds_multi_club_prefix` criteria of the league's multi-club list (declared in the rule profile). Those are
the criteria whose application to a group is not open to interpretation (Bundesliga: overall goal difference, goals scored; La Liga: points in the matches among the tied clubs). Everything
the rule text leaves open (what happens to a pair that is still level after a mini-table, how head-to-head criteria work for three clubs) stays unresolved, so the bounds hold under every
reading of the text. For exactly two clubs the full two-club list is used.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import rules
from .engine import SeasonInput

INF = float("inf")
H2H = {"h2h_points", "h2h_goal_difference", "h2h_away_goals"}
BAND_NAMES = ("title", "top4", "relegation", "relegation_playoff")


def draw_outcomes(probs: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Same random stream and rule as pointsonly.simulate_points: 0 home win, 1 draw, 2 away win. Shape [n, F]."""
    p = np.clip(np.asarray(probs, dtype=float), 0.0, None)
    p = p / p.sum(axis=1, keepdims=True)
    cdf = np.cumsum(p, axis=1)
    cdf[:, -1] = 1.0
    u = np.random.default_rng([seed, 2]).random((n, len(p)))
    return (u[:, :, None] > cdf[None, :, :2]).sum(axis=2)


@dataclass
class Bounds:
    best: np.ndarray            # [N, T] best (smallest) possible position, 1-based
    worst: np.ndarray           # [N, T] worst (largest) possible position
    points: np.ndarray          # [N, T]
    stats: dict


class _Ctx:
    def __init__(self, inp: SeasonInput, profile: dict, oc: np.ndarray, use_information: bool):
        self.inp, self.profile, self.oc, self.use = inp, profile, oc, use_information
        T, F = len(inp.teams), len(inp.fix_home)
        self.T, self.F = T, F
        self.gd0, self.gf0, self.ag0 = (np.zeros(T, dtype=np.int64) for _ in range(3))
        self.played = {}
        for h, a, hg, ag in zip(inp.played_home, inp.played_away, inp.played_hg, inp.played_ag):
            self.played[(int(h), int(a))] = (int(hg), int(ag))
            self.gd0[h] += hg - ag; self.gd0[a] += ag - hg
            self.gf0[h] += hg; self.gf0[a] += ag
            self.ag0[a] += ag
        self.fixture = {(int(h), int(a)): f for f, (h, a) in enumerate(zip(inp.fix_home, inp.fix_away))}
        Hm = np.zeros((F, T), dtype=np.int64); Am = np.zeros((F, T), dtype=np.int64)
        if F:
            Hm[np.arange(F), inp.fix_home] = 1
            Am[np.arange(F), inp.fix_away] = 1
        hw, dr, aw = (oc == 0).astype(np.int64), (oc == 1).astype(np.int64), (oc == 2).astype(np.int64)
        self.W = hw @ Hm + aw @ Am                      # remaining wins per club per simulation
        self.D = dr @ (Hm + Am)
        self.L = aw @ Hm + hw @ Am
        self.Wa = aw @ Am                               # remaining wins played away
        self.n_away = Am.sum(axis=0)                    # remaining away fixtures per club (same in every simulation)
        base = np.zeros(T, dtype=np.int64)
        w, d = profile["points"]["win"], profile["points"]["draw"]
        for h, a, hg, ag in zip(inp.played_home, inp.played_away, inp.played_hg, inp.played_ag):
            base[h] += w if hg > ag else d if hg == ag else 0
            base[a] += w if ag > hg else d if hg == ag else 0
        self.points = base + (hw @ Hm) * w + (aw @ Am) * w + dr @ (Hm + Am) * d
        prefix = profile.get("bounds_multi_club_prefix")
        self.multi = list(profile["criteria"]["multi_clubs"] if prefix is None else profile["criteria"]["multi_clubs"][:int(prefix)])

    # ------------------------------------------------------------------------------------------------ intervals
    def _match(self, s: int, x: int, y: int):
        """Match of home x v away y: ('known', hg, ag) | ('out', code) | None (absent)."""
        k = (x, y)
        if k in self.played:
            return ("known",) + self.played[k]
        f = self.fixture.get(k)
        return None if f is None else ("out", int(self.oc[s, f]))

    def interval(self, c: str, x: int, S: list, s: int) -> tuple:
        if c == "goal_difference":
            lo = -INF if self.L[s, x] > 0 else self.gd0[x] + self.W[s, x]
            hi = INF if self.W[s, x] > 0 else self.gd0[x] - self.L[s, x]
            return (lo, hi)
        if c == "goals_scored":
            r = self.W[s, x] + self.D[s, x] + self.L[s, x]
            return (self.gf0[x] + self.W[s, x], INF if r > 0 else self.gf0[x])
        if c == "away_goals_total":
            return (self.ag0[x] + self.Wa[s, x], INF if self.n_away[x] > 0 else self.ag0[x])
        pts_lo = pts_hi = gd_lo = gd_hi = ag_lo = ag_hi = 0
        for y in S:
            if y == x:
                continue
            for home, away in ((x, y), (y, x)):
                m = self._match(s, home, away)
                if m is None:
                    continue
                if m[0] == "known":
                    mine, theirs = (m[1], m[2]) if home == x else (m[2], m[1])
                    pts_lo += 3 if mine > theirs else 1 if mine == theirs else 0
                    gd_lo += mine - theirs; gd_hi += mine - theirs
                    if away == x:
                        ag_lo += mine; ag_hi += mine
                else:
                    code = m[1]
                    won = (code == 0 and home == x) or (code == 2 and away == x)
                    lost = (code == 2 and home == x) or (code == 0 and away == x)
                    pts_lo += 3 if won else 1 if code == 1 else 0
                    if won:
                        gd_lo += 1; gd_hi += INF
                    elif lost:
                        gd_lo += -INF; gd_hi += -1
                    if away == x:
                        ag_lo += 1 if won else 0; ag_hi += INF
        if c == "h2h_points":
            return (pts_lo, pts_lo)
        if c == "h2h_goal_difference":
            return (gd_lo, gd_hi)
        if c == "h2h_away_goals":
            return (ag_lo, ag_hi)
        return (-INF, INF)                                               # fair play and anything unknown: no information

    def relation(self, x: int, y: int, S: list, s: int) -> int:
        """+1 x definitely above y, -1 y definitely above x, 0 not decided by the known information."""
        if not self.use:
            return 0
        pair = len(S) == 2
        scope = self.profile.get("h2h_scope", "current_group")
        for c in (self.profile["criteria"]["two_clubs"] if pair else self.multi):
            if c in H2H and not pair and scope != "original_group":
                return 0
            ix, iy = self.interval(c, x, S, s), self.interval(c, y, S, s)
            if ix[0] > iy[1]:
                return 1
            if ix[1] < iy[0]:
                return -1
            if ix[0] == ix[1] == iy[0] == iy[1]:
                continue
            return 0
        return 0


def position_bounds(inp: SeasonInput, profile: dict, outcomes: np.ndarray, use_known_information: bool = True) -> Bounds:
    """Best and worst possible position of every club in every simulated season (see the module docstring)."""
    ctx = _Ctx(inp, profile, outcomes, use_known_information)
    N, T = ctx.points.shape[0], ctx.T
    best = np.zeros((N, T), dtype=np.int16)
    worst = np.zeros((N, T), dtype=np.int16)
    order = np.argsort(-ctx.points, axis=1, kind="stable")
    sp = np.take_along_axis(ctx.points, order, axis=1)
    n_groups = n_decided = 0
    for s in range(N):
        i = 0
        while i < T:
            j = i
            while j + 1 < T and sp[s, j + 1] == sp[s, i]:
                j += 1
            S = [int(t) for t in order[s, i:j + 1]]
            if len(S) == 1:
                best[s, S[0]] = worst[s, S[0]] = i + 1
            else:
                n_groups += 1
                above = {x: 0 for x in S}
                below = {x: 0 for x in S}
                any_open = False
                for a_i in range(len(S)):
                    for b_i in range(a_i + 1, len(S)):
                        x, y = S[a_i], S[b_i]
                        r = ctx.relation(x, y, S, s)
                        if r == 1:
                            below[x] += 1; above[y] += 1
                        elif r == -1:
                            below[y] += 1; above[x] += 1
                        else:
                            any_open = True
                n_decided += 0 if any_open else 1
                for x in S:
                    best[s, x] = i + 1 + above[x]
                    worst[s, x] = j + 1 - below[x]
            i = j + 1
    return Bounds(best=best, worst=worst, points=ctx.points, stats=dict(tie_groups=n_groups, fully_decided_tie_groups=n_decided, simulations=N))


def band_counts(b: Bounds, lo: int, hi: int) -> tuple:
    """Per club: number of simulations in which the band lo..hi is guaranteed, and in which it is possible (integers, so guaranteed <= possible holds exactly)."""
    sure = ((b.best >= lo) & (b.worst <= hi)).sum(axis=0)
    poss = ((b.worst >= lo) & (b.best <= hi)).sum(axis=0)
    return sure, poss


def band_summary(b: Bounds, profile: dict, inp: SeasonInput, names: Optional[tuple] = None) -> dict:
    """Guaranteed / possible / unresolved probability per club and band, with Monte Carlo standard errors of the two bounds."""
    N, T = b.best.shape
    out = {}
    for name in (names or BAND_NAMES):
        pos = profile.get("bands", {}).get(name)
        if not pos:
            continue
        lo, hi = min(pos), max(pos)
        sure, poss = band_counts(b, lo, hi)
        gs, ps = sure / N, poss / N
        out[name] = dict(positions=[lo, hi], clubs=[dict(entity_id=inp.teams[t], club=inp.names[t], guaranteed=float(gs[t]), possible=float(ps[t]), unresolved=float((poss[t] - sure[t]) / N),
                                                         se_guaranteed=float(np.sqrt(gs[t] * (1 - gs[t]) / N)), se_possible=float(np.sqrt(ps[t] * (1 - ps[t]) / N))) for t in np.argsort(-ps, kind="stable")],
                         mean_unresolved=float(((poss - sure) / N).mean()), max_unresolved=float(((poss - sure) / N).max()))
    return out
