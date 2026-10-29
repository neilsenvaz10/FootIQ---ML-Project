"""FootIQ club v2 - leakage-safe football feature engine (state machine).

Contract: for a calendar day D, features of every fixture of D are computed from the state built from matches dated < D;
only afterwards the state absorbs the results of D. The same code is meant for training and (later) inference.
All goal-based quantities are derived from previous ACTUAL scores (90-minute results); they are NOT event-data xG.
Unknown history is NaN, never 0.
"""
import bisect
import math
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from scipy.stats import poisson

K1, HA1 = 20.0, 60.0          # v1 Elo (kept for continuity and the v1 baselines)
SHRINK_LEAGUE = 300.0         # prior weight (matches) for league-level statistics
SHRINK_TEAM_HA = 8.0          # prior weight (matches) for team home/away effects
ATT_PRIOR = 4.0               # prior weight (matches) for attack / defence ratios
DECAY_FORM, DECAY_GOALS = 0.85, 0.92


def gd_mult(gd):
    gd = abs(gd)
    return 1.0 if gd <= 1 else (1.5 if gd == 2 else (11.0 + gd) / 8.0)


class Elo2:
    """Tunable Elo with season-transition regression towards the league mean (league = competition id)."""

    def __init__(self, K, HA, R, init=1500.0):
        self.K, self.HA, self.R, self.init = K, HA, R, init
        self.elo, self.last_cs = {}, {}
        self.active = defaultdict(dict)

    def league_mean(self, comp, d, window=400):
        ents = [e for e, ld in self.active[comp].items() if d - ld <= window]
        if len(ents) < 6:
            return None
        return sum(self.elo.get(e, self.init) for e in ents) / len(ents)

    def eff(self, e, comp, season, lm):
        base = self.elo.get(e, self.init)
        if self.R > 0 and lm is not None and self.last_cs.get((e, comp), season) != season:
            return base + self.R * (lm - base)
        return base

    def update(self, h, a, comp, season, d, eh, ea, gh, ga):
        p = 1.0 / (1.0 + 10.0 ** (-((eh + self.HA) - ea) / 400.0))
        s = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
        delta = self.K * gd_mult(gh - ga) * (s - p)
        self.elo[h], self.elo[a] = eh + delta, ea - delta
        for e in (h, a):
            self.last_cs[(e, comp)] = season
            self.active[comp][e] = d


def _mean(x):
    return float(np.mean(x)) if len(x) else np.nan


def _wmean(vals, decay):
    if not len(vals):
        return np.nan
    w = decay ** np.arange(len(vals) - 1, -1, -1)       # most recent last -> weight 1
    return float(np.dot(w, vals) / w.sum())


class V2State:
    def __init__(self, elo2_params):
        self.e1 = {}
        self.elo2 = Elo2(*elo2_params)
        self.hist = defaultdict(list)       # rated results: (ord, pts, gf, ga, was_home, perf, gf_rel, ga_rel, elo2_after)
        self.played = defaultdict(list)     # ordinals of all completed matches (any competition)
        self.cups = defaultdict(list)       # ordinals of completed non-league matches (cups / continental)
        self.compn = defaultdict(int)       # (entity, comp) -> completed matches in that competition
        self.cs_first = {}                  # (comp, season) -> first ordinal date seen
        self.lg = defaultdict(lambda: dict(n=0, hg=0, ag=0, dr=0, hw=0, recent=deque(maxlen=380)))
        self.g = dict(n=0, hg=0.0, ag=0.0, dr=0, hw=0)
        self._day = None
        self._lm = {}

    # ---- helpers (day-level caches keep the result independent of the order of same-day matches)
    def _lm2(self, comp, d):
        if self._day != d:
            self._day, self._lm = d, {}
        if comp not in self._lm:
            self._lm[comp] = self.elo2.league_mean(comp, d)
        return self._lm[comp]

    def league_stats(self, comp):
        L, G = self.lg[comp], self.g
        n, K = L["n"], SHRINK_LEAGUE
        gn = max(G["n"], 1)
        gd0 = (G["hg"] - G["ag"]) / gn if G["n"] else 0.3
        hw0 = G["hw"] / gn if G["n"] else 0.45
        dr0 = G["dr"] / gn if G["n"] else 0.26
        hg0 = G["hg"] / gn if G["n"] else 1.5
        ag0 = G["ag"] / gn if G["n"] else 1.2
        out = dict(ha_gd=(L["hg"] - L["ag"] + K * gd0) / (n + K), home_win=(L["hw"] + K * hw0) / (n + K), draw=(L["dr"] + K * dr0) / (n + K),
                   hmean=(L["hg"] + K * hg0) / (n + K), amean=(L["ag"] + K * ag0) / (n + K), n=n)
        out["goals_pm"] = out["hmean"] + out["amean"]
        rec = L["recent"]
        out["ha_gd_recent"] = (sum(x[0] - x[1] for x in rec) + K * out["ha_gd"]) / (len(rec) + K)
        out["home_ppg"] = 3 * out["home_win"] + out["draw"]
        out["away_ppg"] = 3 * (1 - out["home_win"] - out["draw"]) + out["draw"]
        return out

    def side(self, e, comp, season, d, is_home, lgs, lm):
        h = self.hist[e] if e in self.hist else []
        f = {}
        n = len(h)
        f["n_prior"] = n
        e2 = self.elo2.eff(e, comp, season, lm)
        f["elo1"] = self.e1.get(e, 1500.0)
        f["elo2"] = e2
        f["elo2_rel"] = (e2 - lm) if lm is not None else np.nan
        pts = [x[1] for x in h]
        gf = [x[2] for x in h]
        ga = [x[3] for x in h]
        for w in (3, 5, 10):
            f[f"ppg{w}"] = _mean(pts[-w:])
            f[f"gf{w}"] = _mean(gf[-w:])
            f[f"ga{w}"] = _mean(ga[-w:])
        f["gd5"] = f["gf5"] - f["ga5"] if n else np.nan
        f["gd10"] = f["gf10"] - f["ga10"] if n else np.nan
        f["wppg10"] = _wmean(pts[-10:], DECAY_FORM)
        f["form_mom"] = f["ppg3"] - f["ppg10"] if n else np.nan
        f["perf10"] = _mean([x[5] for x in h[-10:]])
        vh = [x for x in h if x[4] == is_home][-5:]
        f["venue_ppg5"] = _mean([x[1] for x in vh])
        f["elo2_mom5"] = (e2 - h[-5][8]) if n >= 5 else np.nan
        # attack / defence relative to league level (previous actual scores only)
        last = h[-20:]
        if last:
            w = DECAY_GOALS ** np.arange(len(last) - 1, -1, -1)
            f["att"] = float((np.dot(w, [x[6] for x in last]) + ATT_PRIOR) / (w.sum() + ATT_PRIOR))
            f["dfn"] = float((np.dot(w, [x[7] for x in last]) + ATT_PRIOR) / (w.sum() + ATT_PRIOR))
        else:
            f["att"] = f["dfn"] = np.nan
        # team-specific home / away effect (shrunk)
        hp = [x[1] for x in h if x[4]][-15:]
        ap = [x[1] for x in h if not x[4]][-15:]
        k = SHRINK_TEAM_HA
        f["team_ha"] = (sum(hp) + k * lgs["home_ppg"]) / (len(hp) + k) - (sum(ap) + k * lgs["away_ppg"]) / (len(ap) + k)
        # rest / congestion on KNOWN matches only
        pl = self.played[e] if e in self.played else []
        f["days_rest"] = float(d - pl[-1]) if pl else np.nan
        i_hi = bisect.bisect_left(pl, d)           # matches dated < d (strictly earlier days)
        for w in (7, 14, 30):
            f[f"n_known_{w}"] = i_hi - bisect.bisect_left(pl, d - w)
        cu = self.cups[e] if e in self.cups else []
        i0, i1 = bisect.bisect_left(cu, d - 365), bisect.bisect_left(cu, d)
        f["cup_recorded_365"] = 1.0 if i1 > i0 else 0.0
        f["comp_n_prior"] = self.compn.get((e, comp), 0)
        ds_ = ([pl[-1]] if pl else []) + ([h[-1][0]] if h else [])
        f["info_date"] = float(max(ds_)) if ds_ else np.nan
        return f

    def features(self, h, a, comp, season, d, tier):
        lgs = self.league_stats(comp)
        lm = self._lm2(comp, d)
        H, A = self.side(h, comp, season, d, True, lgs, lm), self.side(a, comp, season, d, False, lgs, lm)
        f = {"d": d}
        for k, v in H.items():
            f[f"home_{k}"] = v
        for k, v in A.items():
            f[f"away_{k}"] = v
        f["elo1_diff"] = H["elo1"] - A["elo1"]
        f["elo2_diff"] = H["elo2"] - A["elo2"]
        for w in ("ppg5", "ppg10", "wppg10", "gd5", "perf10"):
            f[f"{w}_diff"] = H[w] - A[w]
        f["rest_diff"] = H["days_rest"] - A["days_rest"]
        f["congestion30_diff"] = H["n_known_30"] - A["n_known_30"]
        f["team_ha_diff"] = H["team_ha"] - A["team_ha"]
        f["elo2_mom5_diff"] = H["elo2_mom5"] - A["elo2_mom5"]
        for k in ("ha_gd", "home_win", "draw", "goals_pm", "ha_gd_recent"):
            f[f"league_{k}"] = lgs[k]
        f["league_ha_recent_minus_long"] = lgs["ha_gd_recent"] - lgs["ha_gd"]
        f["league_n_prior"] = lgs["n"]
        fm = self.cs_first.get((comp, season))
        f["days_into_season"] = float(d - fm) if fm is not None else 0.0
        f["league_tier"] = float(tier) if tier is not None and not pd.isna(tier) else np.nan
        f["home_new_to_comp"] = 1.0 if H["comp_n_prior"] == 0 else 0.0
        f["away_new_to_comp"] = 1.0 if A["comp_n_prior"] == 0 else 0.0
        f["lambda_home"] = lgs["hmean"] * H["att"] * A["dfn"] if not (math.isnan(H["att"]) or math.isnan(A["dfn"])) else np.nan
        f["lambda_away"] = lgs["amean"] * A["att"] * H["dfn"] if not (math.isnan(A["att"]) or math.isnan(H["dfn"])) else np.nan
        return f

    def apply_day(self, d, matches):
        """matches: list of dict(h,a,comp,season,ctype,regular,rated,gh,ga). Day-level pre-state is snapshotted first."""
        pre = []
        for m in matches:
            lm = self._lm2(m["comp"], d)
            if m["rated"]:
                lgs = self.league_stats(m["comp"])
                pre.append((self.e1.get(m["h"], 1500.0), self.e1.get(m["a"], 1500.0), self.elo2.eff(m["h"], m["comp"], m["season"], lm), self.elo2.eff(m["a"], m["comp"], m["season"], lm),
                            lgs["goals_pm"] / 2.0))
            else:
                pre.append(None)
        for m, p in zip(matches, pre):
            h, a, comp, season = m["h"], m["a"], m["comp"], m["season"]
            for e in (h, a):
                self.played[e].append(d)
                if m["ctype"] != "domestic_league":
                    self.cups[e].append(d)
                self.compn[(e, comp)] += 1
            if (comp, season) not in self.cs_first:
                self.cs_first[(comp, season)] = d
            if not m["rated"]:
                continue
            # defect fix (final-refit pre-check): entities playing twice on one day must see the first match's rating change (as in the v1 contract);
            # using the day-start snapshot silently discarded it. Features of fixtures still use day-start state only.
            avg = p[4]
            e1h, e1a = self.e1.get(h, 1500.0), self.e1.get(a, 1500.0)
            e2h, e2a = self.elo2.eff(h, comp, season, self._lm2(comp, d)), self.elo2.eff(a, comp, season, self._lm2(comp, d))
            gh, ga = m["gh"], m["ga"]
            exp = 1.0 / (1.0 + 10.0 ** (-((e1h + HA1) - e1a) / 400.0))
            s = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
            delta = K1 * gd_mult(gh - ga) * (s - exp)
            self.e1[h], self.e1[a] = e1h + delta, e1a - delta
            self.elo2.update(h, a, comp, season, d, e2h, e2a, gh, ga)
            av = max(avg, 0.3)
            self.hist[h].append((d, 3 if gh > ga else (1 if gh == ga else 0), gh, ga, True, s - exp, gh / av, ga / av, self.elo2.elo[h]))
            self.hist[a].append((d, 3 if ga > gh else (1 if gh == ga else 0), ga, gh, False, (1 - s) - (1 - exp), ga / av, gh / av, self.elo2.elo[a]))
            if m["ctype"] == "domestic_league" and m["regular"]:
                L = self.lg[comp]
                L["n"] += 1; L["hg"] += gh; L["ag"] += ga; L["dr"] += int(gh == ga); L["hw"] += int(gh > ga)
                L["recent"].append((gh, ga))
                G = self.g
                G["n"] += 1; G["hg"] += gh; G["ag"] += ga; G["dr"] += int(gh == ga); G["hw"] += int(gh > ga)


def poisson_probs(lh, la, maxg=10):
    lh, la = np.asarray(lh, float), np.asarray(la, float)
    g = np.arange(maxg + 1)
    ph = poisson.pmf(g[None, :], lh[:, None])
    pa = poisson.pmf(g[None, :], la[:, None])
    joint = ph[:, :, None] * pa[:, None, :]
    iu = np.triu_indices(maxg + 1, 1)
    il = np.tril_indices(maxg + 1, -1)
    pd_ = np.einsum("nii->n", joint)
    pH = joint[:, il[0], il[1]].sum(1)
    pA = joint[:, iu[0], iu[1]].sum(1)
    tot = pH + pd_ + pA
    return pH / tot, pd_ / tot, pA / tot


def build(df, want, elo2_params):
    """df: columns record_id, dt, h, a, comp, season, tier, ctype, regular, rated, gh, ga (one row per completed match, any competition).
    want: set of record_ids for which features are produced. Returns DataFrame indexed by record_id."""
    st = V2State(elo2_params)
    out = []
    for dt, g in df.sort_values(["dt", "record_id"], kind="mergesort").groupby("dt", sort=True):
        d = dt.toordinal()
        rows = list(g.itertuples())
        for r in rows:
            if r.record_id in want:
                f = st.features(r.h, r.a, r.comp, r.season, d, r.tier)
                f["record_id"] = r.record_id
                out.append(f)
        # rows flagged is_fixture (inference mode) receive features but never update the state
        st.apply_day(d, [dict(h=r.h, a=r.a, comp=r.comp, season=r.season, ctype=r.ctype, regular=r.regular, rated=r.rated, gh=r.gh, ga=r.ga) for r in rows
                         if not getattr(r, "is_fixture", False)])
    F = pd.DataFrame(out).set_index("record_id")
    pH, pD, pA = poisson_probs(F.lambda_home.fillna(1.4).values, F.lambda_away.fillna(1.1).values)
    nanrow = F.lambda_home.isna() | F.lambda_away.isna()
    F["poisson_pH"], F["poisson_pD"], F["poisson_pA"] = np.where(nanrow, np.nan, pH), np.where(nanrow, np.nan, pD), np.where(nanrow, np.nan, pA)
    F["exp_goal_diff"] = F.lambda_home - F.lambda_away
    return F
