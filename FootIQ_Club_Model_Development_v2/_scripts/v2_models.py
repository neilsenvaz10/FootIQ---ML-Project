"""Shared modelling utilities for the v2 development experiments (no test / holdout data is ever loaded here)."""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa

LOGN = ["home_n_prior", "away_n_prior", "league_n_prior", "home_comp_n_prior", "away_comp_n_prior"]


def load_dev():
    F = pd.read_pickle(os.path.join(WORK, "features_v2_dev.pkl"))
    F1 = pd.read_pickle(os.path.join(WORK, "features_v1_dev.pkl")).set_index("record_id")
    v1cols = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json")))["feature_order"]
    F = F.join(F1[v1cols].add_prefix("v1__"), how="left")
    return add_derived(F)


def add_derived(F):
    """Deterministic derived columns used by the model (same code for training and inference)."""
    F = F.copy()
    for c in LOGN:
        if c in F:
            F[c + "_log"] = np.log1p(F[c])
    F["home_info_gap"] = F["d"] - F["home_info_date"]
    return F


GROUPS = {
    "elo_v1": ["elo1_diff"],
    "elo2": ["elo2_diff"],
    "elo_plus": ["home_elo2_rel", "away_elo2_rel", "elo2_mom5_diff", "home_n_prior_log", "away_n_prior_log", "home_new_to_comp", "away_new_to_comp"],
    "home_adv": ["league_ha_gd", "league_home_win", "league_ha_recent_minus_long", "team_ha_diff", "home_team_ha", "away_team_ha"],
    "form": ["home_ppg3", "away_ppg3", "home_ppg5", "away_ppg5", "home_ppg10", "away_ppg10", "ppg5_diff", "ppg10_diff", "wppg10_diff", "home_form_mom", "away_form_mom", "perf10_diff",
             "gd5_diff", "home_venue_ppg5", "away_venue_ppg5"],
    "goal": ["home_att", "home_dfn", "away_att", "away_dfn", "lambda_home", "lambda_away", "exp_goal_diff", "poisson_pH", "poisson_pD", "poisson_pA", "home_gf5", "home_ga5", "away_gf5", "away_ga5"],
    "league": ["league_tier", "league_draw", "league_goals_pm", "days_into_season", "league_n_prior_log", "home_comp_n_prior_log", "away_comp_n_prior_log"],
    "rest": ["home_days_rest", "away_days_rest", "rest_diff", "home_n_known_7", "away_n_known_7", "home_n_known_14", "away_n_known_14", "home_n_known_30", "away_n_known_30",
             "congestion30_diff", "home_cup_recorded_365", "away_cup_recorded_365"],
}
V1_FEATS = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json")))["feature_order"]
GROUPS["v1_all25"] = ["v1__" + c for c in V1_FEATS]


class Prep:
    """Median imputation + missing indicators + standardisation, fitted on the training window only."""

    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, X):
        X = X[self.cols]
        self.med = X.median()
        self.med = self.med.fillna(0.0)
        self.ind = [c for c in self.cols if X[c].isna().any()]
        Xi = X.fillna(self.med)
        self.mu, self.sd = Xi.mean(), Xi.std(ddof=0).replace(0, 1.0)
        return self

    def transform(self, X, scale=True):
        X = X[self.cols]
        ind = np.column_stack([X[c].isna().astype(float).values for c in self.ind]) if self.ind else np.zeros((len(X), 0))
        Xi = X.fillna(self.med)
        Z = ((Xi - self.mu) / self.sd).values if scale else Xi.values
        return np.hstack([Z, ind])


class OrdLogit:
    def fit(self, d, y):
        def nll(t):
            P = self._p(t, d)
            return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1)).mean()
        self.t = minimize(nll, [1.0, -0.5, 0.0], method="L-BFGS-B").x
        return self

    @staticmethod
    def _p(t, d):
        b, c1, ld = t
        z = b * np.asarray(d) / 100.0
        pA = expit(c1 - z); pAD = expit(c1 + np.exp(ld) - z)
        return np.column_stack([1 - pAD, pAD - pA, pA])

    def predict_proba(self, d):
        return self._p(self.t, d)


def make_model(kind, **hp):
    if kind == "lr":
        return LogisticRegression(solver="lbfgs", max_iter=3000, random_state=SEED, **hp)
    if kind == "rf":
        return RandomForestClassifier(random_state=SEED, n_jobs=6, **hp)
    if kind == "hgb":
        return HistGradientBoostingClassifier(random_state=SEED, early_stopping=False, **hp)
    raise ValueError(kind)


def fit_predict(kind, hp, cols, tr, va, scale=None):
    """Fit on tr (DataFrame with column y), predict va. Preprocessing fitted on tr only."""
    scale = (kind == "lr") if scale is None else scale
    pp = Prep(cols).fit(tr)
    Xtr, Xva = pp.transform(tr, scale), pp.transform(va, scale)
    m = make_model(kind, **hp).fit(Xtr, tr.y.astype(int).values)
    return m, pp, m.predict_proba(Xva)


def fold_frames(F, fold):
    tr = F[F.match_date <= fold["train_end"]]
    va = F[(F.match_date >= fold["val_start"]) & (F.match_date <= fold["val_end"])]
    return tr, va


def fold_eval(F, kind, hp, cols, rows="dev_primary"):
    """Returns list of per-fold metric dicts and the stacked out-of-sample predictions (record_id indexed)."""
    res, preds = [], []
    for f in FOLDS:
        tr, va = fold_frames(F, f)
        _, _, P = fit_predict(kind, hp, cols, tr, va)
        msk = va[rows].values
        m = metrics(va.y.values[msk].astype(int), P[msk])
        res.append(dict(fold=f["fold"], **m))
        pr = pd.DataFrame(P[msk], index=va.index[msk], columns=["pH", "pD", "pA"])
        pr["fold"] = f["fold"]
        preds.append(pr)
    return res, pd.concat(preds)


class VecScale:
    def fit(self, P, y):
        self.m = LogisticRegression(C=10.0, max_iter=2000).fit(np.log(np.clip(P, 1e-6, 1)), y)
        return self

    def predict_proba(self, P):
        return self.m.predict_proba(np.log(np.clip(P, 1e-6, 1)))
