"""Scoreline models: from a fixture's home/draw/away probabilities (frozen club model) and expected goals (v2 feature generator) to a joint
distribution over (home goals, away goals), capped at K-1 goals per team.

  S1 conditional Poisson : outcome probabilities are the model's; given the outcome, the score is independent Poisson(lam_h, lam_a) restricted to that outcome.
  S2 outcome-matched     : independent Poisson whose lam_h, lam_a are solved so that P(home) and P(away) equal the model's; total goals are implied.
  S3 empirical bootstrap : given the outcome, the score is drawn from real historical scores of the same league and a similar strength gap (lam_h - lam_a),
                           using only matches before the cut-off.
All three return a pmf of shape [F, K, K] whose outcome marginals equal the model's probabilities (S2 up to its solver tolerance).
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import poisson

from .engine import K

GOALS = np.arange(K)
_HOME = (GOALS[:, None] > GOALS[None, :])
_DRAW = (GOALS[:, None] == GOALS[None, :])
_AWAY = (GOALS[:, None] < GOALS[None, :])
MASKS = (_HOME, _DRAW, _AWAY)


def _pois_vec(lam: np.ndarray) -> np.ndarray:
    return poisson.pmf(GOALS[None, :], np.asarray(lam)[:, None])                           # [F, K]


def _norm_probs(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-9, None)
    return p / p.sum(axis=1, keepdims=True)


def conditional_poisson(p: np.ndarray, lam_h: np.ndarray, lam_a: np.ndarray) -> np.ndarray:
    """S1."""
    p = _norm_probs(p)
    base = _pois_vec(lam_h)[:, :, None] * _pois_vec(lam_a)[:, None, :]                        # [F, K, K]
    out = np.zeros_like(base)
    for o, m in enumerate(MASKS):
        cond = base * m[None]
        s = cond.sum(axis=(1, 2), keepdims=True)
        cond = np.where(s > 0, cond / np.where(s > 0, s, 1), m[None] / m.sum())
        out += p[:, o][:, None, None] * cond
    return out


def outcome_matched(p: np.ndarray, lam0_h: np.ndarray, lam0_a: np.ndarray) -> tuple:
    """S2. Returns (pmf, converged mask). Bounded least squares in log space from several starts; a fixture is accepted only if both outcome
    probabilities are reproduced to 1e-6 with expected goals below 8, otherwise it is reported as not converged (the caller falls back to S1)."""
    p = _norm_probs(p)
    F = len(p)
    pmf = np.zeros((F, K, K))
    ok = np.zeros(F, dtype=bool)

    def res(x, target):
        g = poisson.pmf(GOALS, np.exp(x[0]))[:, None] * poisson.pmf(GOALS, np.exp(x[1]))[None, :]
        g = g / g.sum()
        return np.array([g[_HOME].sum() - target[0], g[_AWAY].sum() - target[2]])

    lo, hi = np.log(0.05), np.log(8.0)
    for f in range(F):
        first = [np.log(max(lam0_h[f], 0.2)) if np.isfinite(lam0_h[f]) else np.log(1.4), np.log(max(lam0_a[f], 0.2)) if np.isfinite(lam0_a[f]) else np.log(1.1)]
        best = None
        for x0 in (first, [np.log(1.5), np.log(1.2)], [np.log(0.6), np.log(0.6)], [np.log(3.0), np.log(0.6)], [np.log(0.6), np.log(3.0)]):
            sol = least_squares(res, np.clip(x0, lo, hi), args=(p[f],), bounds=([lo, lo], [hi, hi]), xtol=1e-12, ftol=1e-12, gtol=1e-12)
            r = np.abs(sol.fun).max()
            if best is None or r < best[0]:
                best = (r, sol.x)
            if r < 1e-8:
                break
        if best[0] < 1e-6:
            g = poisson.pmf(GOALS, np.exp(best[1][0]))[:, None] * poisson.pmf(GOALS, np.exp(best[1][1]))[None, :]
            pmf[f] = g / g.sum()
            ok[f] = True
    return pmf, ok


class Empirical:
    """S3: historical scores by league, outcome and strength-gap bin. Fit on matches before the cut-off only."""

    def __init__(self, n_bins: int = 6, alpha: float = 10.0, min_league_matches: int = 300):
        self.n_bins, self.alpha, self.min_league = n_bins, alpha, min_league_matches
        self.edges, self.tab, self.pooled = {}, {}, {}

    def fit(self, league, x, hg, ag) -> "Empirical":
        league, x, hg, ag = (np.asarray(v) for v in (league, x, hg, ag))
        good = np.isfinite(x)
        league, x, hg, ag = league[good], x[good], np.minimum(hg[good], K - 1).astype(int), np.minimum(ag[good], K - 1).astype(int)
        groups = {l: np.nonzero(league == l)[0] for l in np.unique(league)}
        groups["*"] = np.arange(len(x))
        for l, idx in groups.items():
            xs = x[idx]
            edges = np.unique(np.quantile(xs, np.linspace(0, 1, self.n_bins + 1)[1:-1]))
            b = np.searchsorted(edges, xs, side="right")
            self.edges[l] = edges
            pooled = np.zeros((3, K, K))
            tab = np.zeros((len(edges) + 1, 3, K, K))
            for i, j in enumerate(idx):
                o = 0 if hg[j] > ag[j] else 1 if hg[j] == ag[j] else 2
                tab[b[i], o, hg[j], ag[j]] += 1
                pooled[o, hg[j], ag[j]] += 1
            self.pooled[l] = pooled / np.maximum(pooled.sum(axis=(1, 2), keepdims=True), 1)
            self.tab[l] = tab
            self.pooled[l + "_n"] = len(idx)
        return self

    def pmf(self, league: str, x: np.ndarray, p: np.ndarray) -> np.ndarray:
        p = _norm_probs(p)
        key = league if (league in self.tab and self.pooled[league + "_n"] >= self.min_league) else "*"
        edges, tab, pooled = self.edges[key], self.tab[key], self.pooled[key]
        x = np.where(np.isfinite(x), x, np.nan)
        b = np.where(np.isnan(x), len(edges) // 2, np.searchsorted(edges, np.nan_to_num(x), side="right"))
        out = np.zeros((len(p), K, K))
        for o in range(3):
            c = tab[b, o]                                                               # [F, K, K]
            n = c.sum(axis=(1, 2), keepdims=True)
            cond = (c + self.alpha * pooled[o][None]) / (n + self.alpha)
            out += p[:, o][:, None, None] * cond
        return out


def build_pmf(method: str, p: np.ndarray, lam_h: np.ndarray, lam_a: np.ndarray, league: str, league_lams=(1.5, 1.2), empirical: Empirical = None) -> tuple:
    """Returns (pmf [F,K,K], info dict). Missing expected goals fall back to the league average and are counted, never hidden."""
    lam_h, lam_a = np.asarray(lam_h, dtype=float), np.asarray(lam_a, dtype=float)
    missing = int((~np.isfinite(lam_h) | ~np.isfinite(lam_a)).sum())
    lam_h = np.where(np.isfinite(lam_h), lam_h, league_lams[0])
    lam_a = np.where(np.isfinite(lam_a), lam_a, league_lams[1])
    if method == "S1":
        return conditional_poisson(p, lam_h, lam_a), dict(method="S1 conditional Poisson", fallback_fixtures=0, missing_expected_goals=missing)
    if method == "S2":
        pmf, ok = outcome_matched(p, lam_h, lam_a)
        if (~ok).any():
            pmf[~ok] = conditional_poisson(np.asarray(p)[~ok], lam_h[~ok], lam_a[~ok])
        return pmf, dict(method="S2 outcome-matched Poisson", fallback_fixtures=int((~ok).sum()), fallback_to="S1", missing_expected_goals=missing)
    if method == "S3":
        if empirical is None:
            raise ValueError("S3 needs a fitted Empirical model")
        return empirical.pmf(league, np.asarray(lam_h) - np.asarray(lam_a), p), dict(method="S3 empirical conditional bootstrap", fallback_fixtures=0, missing_expected_goals=missing)
    raise ValueError(f"unknown scoreline method {method}")


def outcome_marginals(pmf: np.ndarray) -> np.ndarray:
    return np.stack([pmf[:, m].sum(axis=1) for m in MASKS], axis=1)
