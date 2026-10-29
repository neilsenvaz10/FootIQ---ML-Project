"""OFFLINE RESEARCH PROTOTYPE (not wired into the API or UI, disabled in production): dynamic-strength points simulation with an Elo-in-the-loop update.

Idea. The frozen club v1 model is multinomial logistic regression on standardised features, three of which carry a club's strength: home_elo, away_elo and elo_diff. Because the model is
linear in those features, the effect on a fixture's win/draw/loss log-odds of a change `d_home` in the home club's Elo and `d_away` in the away club's Elo is exactly
    delta_logit_k = (coef_k,home_elo / sd_home_elo + coef_k,elo_diff / sd_elo_diff) * d_home + (coef_k,away_elo / sd_away_elo - coef_k,elo_diff / sd_elo_diff) * d_away
with the frozen coefficients and the frozen training standard deviations READ from the artifact files (never written, never refitted).
Simulation. Fixtures are processed in date order (all fixtures of one date are drawn before any of that date's results is applied). In each simulated season every club carries an Elo offset
since the cut-off, starting at 0. A fixture's cut-off probabilities p0 (computed once, outside the loop, by the frozen model) are tilted by the offsets of its two clubs; the outcome is drawn with
the SAME uniform numbers the static simulation uses; the two offsets are then updated with the v1 Elo rule (K, home advantage and the expected-score formula of `feature_contract.py`;
the goal-margin multiplier needs scores, so it is 1 here). Optional random drift: every club's offset also receives a normal shock with standard deviation tau * sqrt(weeks) between dates.
Parameters: kappa scales the Elo update (0 = no feedback), tau the weekly drift (0 = none), tilt scales the sensitivity of probabilities to the offsets (1 = the frozen coefficients exactly),
ha / k override the Elo constants for sensitivity analysis. With kappa = 0 and tau = 0 the result equals the static points-only simulation exactly.
What it cannot do: it moves only the Elo channel of the frozen model (form windows such as points per game over the last 5 matches also react in reality), and it needs no score.
"""
import json
import sys
from pathlib import Path

import numpy as np

import config as C

ART = C.ROOT / "FootIQ_Club_Model_Baseline_v1" / "artifacts"
PREP_BUILD = C.ROOT / "FootIQ_ML_Training_Preparation" / "_build"


def elo_constants() -> tuple:
    """(K, home advantage) of the v1 Elo state, read from the project's feature contract (fallback to the documented 20 / 60)."""
    try:
        if str(PREP_BUILD) not in sys.path:
            sys.path.insert(0, str(PREP_BUILD))
        import feature_contract as fc

        return float(fc.K), float(fc.HOME_ADV)
    except Exception:  # noqa: BLE001
        return 20.0, 60.0


def tilt_slopes() -> dict:
    """Log-odds change per Elo point for (home club, away club) and each outcome (H, D, A), from the frozen coefficients. Read-only."""
    coef = json.loads((ART / "multinomial_logreg_coefficients.json").read_text(encoding="utf-8"))
    prep = json.loads((ART / "preprocessing_train_fitted.json").read_text(encoding="utf-8"))
    cols, w, sd = coef["input_columns"], np.array(coef["coef"], dtype=float), prep["std_train"]
    assert coef["classes_order"] == ["H", "D", "A"]
    g = lambda name: w[:, cols.index(name)] / sd[name]  # noqa: E731
    return dict(home=g("home_elo") + g("elo_diff"), away=g("away_elo") - g("elo_diff"))


def simulate_dynamic(base_points: np.ndarray, fix_home: np.ndarray, fix_away: np.ndarray, dates: np.ndarray, probs: np.ndarray, elo0: np.ndarray, n: int, seed: int,
                     kappa: float = 1.0, tau: float = 0.0, tilt: float = 1.0, k: float = None, ha: float = None) -> np.ndarray:
    """Final points [n, T]. `dates`: integer day numbers of the fixtures; `elo0`: every club's v1 Elo at the cut-off."""
    T, F = len(base_points), len(fix_home)
    pts = np.repeat(np.asarray(base_points, dtype=np.int64)[None, :], n, axis=0)
    if F == 0:
        return pts
    K0, HA0 = elo_constants()
    K_, HA_ = (K0 if k is None else k), (HA0 if ha is None else ha)
    sl = tilt_slopes()
    sh, sa = sl["home"] * tilt, sl["away"] * tilt
    p = np.clip(np.asarray(probs, dtype=float), 1e-12, None)
    p = p / p.sum(axis=1, keepdims=True)
    cdf0 = np.cumsum(p, axis=1)
    cdf0[:, -1] = 1.0
    u = np.random.default_rng([seed, 2]).random((n, F))                       # the static simulation's uniform numbers: identical streams make runs comparable
    drift = np.random.default_rng([seed, 3])
    logp = np.log(p)
    off = np.zeros((n, T))
    elo0 = np.nan_to_num(np.asarray(elo0, dtype=float), nan=1500.0)
    order = np.lexsort((np.arange(F), dates))
    last_date = dates[order[0]]
    i = 0
    static = kappa == 0.0 and tau == 0.0
    while i < F:
        d = dates[order[i]]
        j = i
        while j < F and dates[order[j]] == d:
            j += 1
        if tau > 0 and d > last_date:
            off += drift.normal(0.0, tau * np.sqrt((d - last_date) / 7.0), size=off.shape)
        last_date = d
        updates = []
        for f in order[i:j]:
            h, a = fix_home[f], fix_away[f]
            if static:
                cdf = cdf0[f][None, :]
            else:
                logit = logp[f][None, :] + off[:, [h]] * sh[None, :] + off[:, [a]] * sa[None, :]
                logit -= logit.max(axis=1, keepdims=True)
                e = np.exp(logit)
                cdf = np.cumsum(e / e.sum(axis=1, keepdims=True), axis=1)
                cdf[:, -1] = 1.0
            outcome = (u[:, [f]] > cdf[:, :2]).sum(axis=1)
            pts[:, h] += np.where(outcome == 0, 3, np.where(outcome == 1, 1, 0))
            pts[:, a] += np.where(outcome == 2, 3, np.where(outcome == 1, 1, 0))
            if not static and kappa:
                exp_h = 1.0 / (1.0 + 10.0 ** (-(((elo0[h] + off[:, h]) + HA_) - (elo0[a] + off[:, a])) / 400.0))
                s = np.where(outcome == 0, 1.0, np.where(outcome == 1, 0.5, 0.0))
                updates.append((h, a, kappa * K_ * (s - exp_h)))
        for h, a, delta in updates:                                              # results of a date are applied after every fixture of that date has been drawn
            off[:, h] += delta
            off[:, a] -= delta
        i = j
    return pts
