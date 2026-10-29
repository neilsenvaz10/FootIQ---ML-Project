"""FootIQ club 90-minute 1X2 - SINGLE FEATURE CONTRACT (v1.1).

The same code path builds training rows and (later) live rows:
    state = ClubState(); for each calendar day D in order:
        rows = [state.features(home, away, D) for each fixture on D]      # uses only matches dated < D
        state.apply_day(D, results_of_day)                                # then, and only then, learn the day's results
No snapshot tables ("latest.csv"), no capped counters, no defaults: unknown history is NaN.
"""
import math
from collections import defaultdict

import numpy as np
import pandas as pd

CONTRACT_VERSION = "v1.1"
K, HOME_ADV, ELO_INIT = 20.0, 60.0, 1500.0

# order is part of the contract
FEATURE_ORDER = [
    "home_elo", "away_elo", "elo_diff",
    "home_n_prior", "away_n_prior",
    "home_ppg5", "away_ppg5", "home_ppg10", "away_ppg10",
    "home_gf5", "home_ga5", "away_gf5", "away_ga5",
    "home_gf10", "home_ga10", "away_gf10", "away_ga10",
    "home_venue_ppg5", "away_venue_ppg5",
    "ppg5_diff", "gd5_diff",
    "home_days_rest", "away_days_rest", "rest_diff",
    "league_tier",
]
# metadata produced by the same call (never model inputs)
META_ORDER = ["latest_info_date", "pair_connected_asof"]


def gd_mult(gd):
    gd = abs(gd)
    return 1.0 if gd <= 1 else (1.5 if gd == 2 else (11.0 + gd) / 8.0)


class ClubState:
    def __init__(self):
        self.elo = defaultdict(lambda: ELO_INIT)
        self.hist = defaultdict(list)       # entity -> [(date, points, gf, ga, was_home)] of RATED (confirmed 90-minute) results
        self.last_played = {}               # entity -> date of the latest completed match of ANY kind (rest days)
        self.parent = {}

    # ---- union-find over the rated-results graph (as-of connectivity of Elo)
    def _find(self, x):
        while self.parent.setdefault(x, x) != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def connected(self, a, b):
        return a in self.parent and b in self.parent and self._find(a) == self._find(b)

    def features(self, home, away, date, tier):
        """date: pandas.Timestamp (calendar day of the fixture). Uses only state learnt from days < date."""
        f = {}
        info = []
        for side, e in (("home", home), ("away", away)):
            h = self.hist[e] if e in self.hist else []
            f[f"{side}_elo"] = self.elo[e] if e in self.elo else ELO_INIT
            f[f"{side}_n_prior"] = len(h)
            for w in (5, 10):
                x = h[-w:]
                f[f"{side}_ppg{w}"] = float(np.mean([i[1] for i in x])) if x else np.nan
                f[f"{side}_gf{w}"] = float(np.mean([i[2] for i in x])) if x else np.nan
                f[f"{side}_ga{w}"] = float(np.mean([i[3] for i in x])) if x else np.nan
            v = [i for i in h if i[4] == (side == "home")][-5:]
            f[f"{side}_venue_ppg5"] = float(np.mean([i[1] for i in v])) if v else np.nan
            lp = self.last_played.get(e)
            f[f"{side}_days_rest"] = float((date - lp).days) if lp is not None else np.nan
            if lp is not None:
                info.append(lp)
            if h:
                info.append(h[-1][0])
        f["elo_diff"] = f["home_elo"] - f["away_elo"]
        f["ppg5_diff"] = f["home_ppg5"] - f["away_ppg5"] if not (math.isnan(f["home_ppg5"]) or math.isnan(f["away_ppg5"])) else np.nan
        hg = f["home_gf5"] - f["home_ga5"]
        ag = f["away_gf5"] - f["away_ga5"]
        f["gd5_diff"] = hg - ag if not (math.isnan(hg) or math.isnan(ag)) else np.nan
        f["rest_diff"] = f["home_days_rest"] - f["away_days_rest"] if not (math.isnan(f["home_days_rest"]) or math.isnan(f["away_days_rest"])) else np.nan
        f["league_tier"] = float(tier) if tier is not None and not pd.isna(tier) else np.nan
        f["latest_info_date"] = max(info) if info else pd.NaT
        f["pair_connected_asof"] = self.connected(home, away)
        return f

    def apply_day(self, date, matches):
        """matches: iterable of dict(home, away, completed(bool), rated(bool), gh, ga). Order inside a day is irrelevant for features."""
        for m in matches:
            if m["completed"]:
                for e in (m["home"], m["away"]):
                    if e not in self.last_played or self.last_played[e] < date:
                        self.last_played[e] = date
        for m in matches:
            if not m["rated"]:
                continue
            h, a, gh, ga = m["home"], m["away"], m["gh"], m["ga"]
            eh, ea = self.elo[h], self.elo[a]
            exp_h = 1.0 / (1.0 + 10.0 ** (-((eh + HOME_ADV) - ea) / 400.0))
            s = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
            delta = K * gd_mult(gh - ga) * (s - exp_h)
            self.elo[h], self.elo[a] = eh + delta, ea - delta
            self.hist[h].append((date, 3 if gh > ga else (1 if gh == ga else 0), gh, ga, True))
            self.hist[a].append((date, 3 if ga > gh else (1 if gh == ga else 0), ga, gh, False))
            ra, rb = self._find(h), self._find(a)
            if ra != rb:
                self.parent[ra] = rb


def build_features(df):
    """df columns: record_id, dt(Timestamp), home, away, tier, completed, rated, gh, ga, want_features(bool).
    Returns DataFrame of features for rows with want_features, in chronological order."""
    st = ClubState()
    out = []
    for dt, g in df.sort_values(["dt", "record_id"], kind="mergesort").groupby("dt", sort=True):
        for r in g.itertuples():
            if r.want_features:
                f = st.features(r.home, r.away, dt, r.tier)
                f["record_id"] = r.record_id
                out.append(f)
        st.apply_day(dt, [dict(home=r.home, away=r.away, completed=r.completed, rated=r.rated, gh=r.gh, ga=r.ga) for r in g.itertuples()])
    return pd.DataFrame(out)
