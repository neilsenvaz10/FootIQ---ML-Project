"""Validation of the position bounds (pointbounds.py) against the REAL tie-break engine (engine._rank_all), offline. Used by tests/test_pointbounds_exhaustive.py and, as a script, to write
data/supervised/phase3/m5_bounds_validation.json for the integration report.

  1. Exhaustive small leagues: for every win / draw / loss pattern of the unplayed matches (3^F) and EVERY score completion with at most G goals per team, the real engine ranks the table;
     the positions it produces (an unresolved tie contributes every position of its block) must lie inside [best, worst] of the bounds. Soundness is a hard requirement; tightness
     (how often best and worst equal the extremes the engine reached) is reported. The engine is run under every reading of the rule text that it can express (head-to-head criteria over
     the original tied group or over the clubs still tied), because the bounds claim to hold under all of them.
  2. Realistic scale: the real Bundesliga and La Liga 2026-27 state (private read-only access), random win / draw / loss patterns and random consistent scores; same check.
Soundness means "the bounds never exclude a position the engine can produce"; it does not mean the bounds are exact (they are conservative by design).
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import engine, pointbounds, rules  # noqa: E402
from seasonsim.engine import K, SeasonInput  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"


def readings(key: str) -> dict:
    """The real profile plus the other reading of the head-to-head scope that the engine can express."""
    p = rules.get_profile(key, "2026-27")
    other = "original_group" if p.get("h2h_scope", "current_group") == "current_group" else "current_group"
    return {f"as in the profile ({p.get('h2h_scope', 'current_group')})": p, f"head-to-head over the {other.replace('_', ' ')}": dict(p, h2h_scope=other)}


def make(names, played, fixtures) -> SeasonInput:
    idx = {n: i for i, n in enumerate(names)}
    return SeasonInput(teams=list(names), names=list(names), played_home=np.array([idx[m[0]] for m in played], dtype=int), played_away=np.array([idx[m[1]] for m in played], dtype=int),
                       played_hg=np.array([m[2] for m in played], dtype=int), played_ag=np.array([m[3] for m in played], dtype=int),
                       fix_home=np.array([idx[f[0]] for f in fixtures], dtype=int), fix_away=np.array([idx[f[1]] for f in fixtures], dtype=int), pmf=None)


def engine_positions(inp: SeasonInput, profile: dict, sh: np.ndarray, sa: np.ndarray):
    """Positions from the real tie-break engine for complete score sets sh, sa of shape [N, F] (same aggregation as engine.simulate, then engine._rank_all)."""
    T, F = len(inp.teams), len(inp.fix_home)
    w, d = profile["points"]["win"], profile["points"]["draw"]
    bp, bgf, bga, baw = (np.zeros(T, dtype=np.int64) for _ in range(4))
    for h, a, hg, ag in zip(inp.played_home, inp.played_away, inp.played_hg, inp.played_ag):
        bp[h] += w if hg > ag else d if hg == ag else 0
        bp[a] += w if ag > hg else d if hg == ag else 0
        bgf[h] += hg; bga[h] += ag; bgf[a] += ag; bga[a] += hg; baw[a] += ag
    Hm = np.zeros((F, T), dtype=np.int64); Am = np.zeros((F, T), dtype=np.int64)
    Hm[np.arange(F), inp.fix_home] = 1
    Am[np.arange(F), inp.fix_away] = 1
    h64, a64 = sh.astype(np.int64), sa.astype(np.int64)
    hp = np.where(sh > sa, w, np.where(sh == sa, d, 0)).astype(np.int64)
    ap = np.where(sa > sh, w, np.where(sh == sa, d, 0)).astype(np.int64)
    points = bp + hp @ Hm + ap @ Am
    gf = bgf + h64 @ Hm + a64 @ Am
    ga = bga + a64 @ Hm + h64 @ Am
    aw = baw + a64 @ Am
    pos, term, _ = engine._rank_all(points, gf, ga, aw, sh, sa, inp, profile)
    return pos, term


def reachable_sets(pos: np.ndarray, term: list, rows=None) -> list:
    """Positions each club takes over the given engine rankings; an unresolved tie contributes every position of its block."""
    T = pos.shape[1]
    seen = [set(np.unique(pos[:, t]).tolist()) for t in range(T)]
    for _s, ev in term:
        for start, size, _k, members in ev["terminal"]:
            for t in members:
                seen[t].update(range(start, start + size))
    return seen


def score_options(code: int, G: int) -> list:
    return [(h, a) for h in range(G + 1) for a in range(G + 1) if (h > a and code == 0) or (h == a and code == 1) or (h < a and code == 2)]


def exhaustive_case(inp: SeasonInput, key: str, G: int = 3) -> dict:
    """All 3^F win / draw / loss patterns x all score completions up to G goals, against every reading of the rules."""
    F, T = len(inp.fix_home), len(inp.teams)
    prof = rules.get_profile(key, "2026-27")
    vectors = list(itertools.product((0, 1, 2), repeat=F))
    b = pointbounds.position_bounds(inp, prof, np.array(vectors, dtype=int).reshape(len(vectors), F))
    naive = pointbounds.position_bounds(inp, prof, np.array(vectors, dtype=int).reshape(len(vectors), F), use_known_information=False)
    legacy = pointbounds.position_bounds(inp, dict(prof, bounds_multi_club_prefix=None), np.array(vectors, dtype=int).reshape(len(vectors), F))   # the prototype without the reading-independent prefix
    out = dict(vectors=len(vectors), completions=0, club_checks=0, violations=0, naive_violations=0, tight=0, tight_checks=0, by_reading={}, tie_groups_of_two=0, tie_groups_of_three_or_more=0, legacy_violations=0, unresolved_blocks_in_engine=0)
    for row in b.points:
        for size in np.unique(row, return_counts=True)[1]:
            out["tie_groups_of_two"] += int(size == 2)
            out["tie_groups_of_three_or_more"] += int(size >= 3)
    for rname, rprof in readings(key).items():
        viol = checks = leg = 0
        for v, vec in enumerate(vectors):
            combos = np.array(list(itertools.product(*[score_options(c, G) for c in vec])), dtype=np.int16).reshape(-1, F, 2)
            if rname.startswith("as in"):
                out["completions"] += len(combos)
            pos, term = engine_positions(inp, rprof, combos[:, :, 0], combos[:, :, 1])
            seen = reachable_sets(pos, term)
            if rname.startswith("as in"):
                out["unresolved_blocks_in_engine"] += sum(len(ev["terminal"]) for _s, ev in term)
            for t in range(T):
                lo, hi = min(seen[t]), max(seen[t])
                checks += 1
                if not (b.best[v, t] <= lo and b.worst[v, t] >= hi):
                    viol += 1
                if not (naive.best[v, t] <= lo and naive.worst[v, t] >= hi):
                    out["naive_violations"] += 1
                if not (legacy.best[v, t] <= lo and legacy.worst[v, t] >= hi):
                    out["legacy_violations"] += 1
                    leg += 1
                if rname.startswith("as in"):
                    out["tight_checks"] += 1
                    out["tight"] += int(b.best[v, t] == lo and b.worst[v, t] == hi)
        out["by_reading"][rname] = dict(club_checks=checks, violations=viol, legacy_prototype_violations=leg)
        out["club_checks"] += checks
        out["violations"] += viol
    return out


def random_league(rng: np.random.Generator, T: int, F: int, gmax: int = 2):
    names = [f"C{i}" for i in range(T)]
    pairs = [(a, b) for a in names for b in names if a != b]
    rng.shuffle(pairs)
    played = []
    for a, b in pairs[F:]:
        hg = int(rng.integers(0, gmax + 1))
        ag = hg if rng.random() < 0.4 else int(rng.integers(0, gmax + 1))              # more draws than a uniform draw: more ties
        played.append((a, b, hg, ag))
    return names, played, pairs[:F]


def realistic_state(key: str, conn):
    """Real 2026-27 state (played results and remaining fixtures) as a SeasonInput, without any probability model."""
    from seasonsim import eligibility, service

    rows = service._season_rows(conn, key, "2026-27")
    played = [r for r in rows if r["status"] in eligibility.COMPLETED and r["hg"] is not None]
    pid = {r["record_id"] for r in played}
    rem = [r for r in rows if r["record_id"] not in pid]
    teams = sorted({r["h"] for r in rows} | {r["a"] for r in rows})
    idx = {t: i for i, t in enumerate(teams)}
    return SeasonInput(teams=teams, names=teams, played_home=np.array([idx[r["h"]] for r in played], dtype=int), played_away=np.array([idx[r["a"]] for r in played], dtype=int),
                       played_hg=np.array([int(r["hg"]) for r in played], dtype=int), played_ag=np.array([int(r["ag"]) for r in played], dtype=int),
                       fix_home=np.array([idx[r["h"]] for r in rem], dtype=int), fix_away=np.array([idx[r["a"]] for r in rem], dtype=int), pmf=None)


def realistic_check(inp: SeasonInput, key: str, n: int = 1500, seed: int = 3) -> dict:
    """Random win / draw / loss patterns with random consistent scores on the real state; the engine's positions must lie inside the bounds."""
    rng = np.random.default_rng(seed)
    F, T = len(inp.fix_home), len(inp.teams)
    oc = rng.choice(3, size=(n, F), p=[0.44, 0.25, 0.31])
    base = rng.poisson(0.9, size=(n, F))
    extra = 1 + rng.poisson(0.8, size=(n, F))
    lo_goals = np.where(oc == 1, rng.poisson(1.1, size=(n, F)), base)
    sh = np.where(oc == 0, lo_goals + extra, np.where(oc == 1, lo_goals, lo_goals)).astype(np.int16)
    sa = np.where(oc == 2, lo_goals + extra, np.where(oc == 1, lo_goals, lo_goals)).astype(np.int16)
    sh, sa = np.minimum(sh, K - 1), np.minimum(sa, K - 1)
    assert ((sh > sa) == (oc == 0)).all() and ((sh == sa) == (oc == 1)).all() and ((sh < sa) == (oc == 2)).all()
    prof = rules.get_profile(key, "2026-27")
    b = pointbounds.position_bounds(inp, prof, oc)
    res = dict(simulations=n, club_checks=0, violations=0, unresolved_blocks_checked=0, by_reading={})
    for rname, rprof in readings(key).items():
        pos, term = engine_positions(inp, rprof, sh, sa)
        viol = 0
        inside = (b.best <= pos) & (pos <= b.worst)
        viol += int((~inside).sum())
        for s, ev in term:                                                   # an unresolved block can be filled in any order: the whole block must be inside the bounds
            for start, size, _k, members in ev["terminal"]:
                res["unresolved_blocks_checked"] += 1 if rname.startswith("as in") else 0
                for t in members:
                    viol += int(not (b.best[s, t] <= start and b.worst[s, t] >= start + size - 1))
        res["by_reading"][rname] = dict(club_checks=int(n * T), violations=viol)
        res["club_checks"] += int(n * T)
        res["violations"] += viol
    res["share_of_clubs_with_exact_position_known"] = float((b.best == b.worst).mean())
    return res


def main(small_cases: int = 80, G: int = 3, seed: int = 5) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    report = dict(settings=dict(G=G, seed=seed), exhaustive={}, realistic={})
    for key in ("BUNDESLIGA", "LALIGA"):
        tot = dict(cases=0, vectors=0, completions=0, club_checks=0, violations=0, naive_violations=0, tight=0, tight_checks=0, tie_groups_of_two=0, tie_groups_of_three_or_more=0, legacy_violations=0, unresolved_blocks_in_engine=0)
        for i in range(small_cases):
            T, F = (4, 4) if i % 3 else (5, 3)
            names, played, fx = random_league(rng, T, F, gmax=1 if i % 2 else 2)
            r = exhaustive_case(make(names, played, fx), key, G)
            tot["cases"] += 1
            for k in ("vectors", "completions", "club_checks", "violations", "naive_violations", "tight", "tight_checks", "tie_groups_of_two", "tie_groups_of_three_or_more", "legacy_violations", "unresolved_blocks_in_engine"):
                tot[k] += r[k]
        tot["share_exactly_tight"] = tot["tight"] / tot["tight_checks"]
        report["exhaustive"][key] = tot
    from store import db as store_db

    conn = store_db.connect(readonly=True)
    try:
        for key in ("BUNDESLIGA", "LALIGA"):
            report["realistic"][key] = realistic_check(realistic_state(key, conn), key)
    finally:
        conn.close()
    report["seconds"] = round(time.time() - t0, 1)
    report["total_violations"] = sum(v["violations"] for v in report["exhaustive"].values()) + sum(v["violations"] for v in report["realistic"].values())
    return report


if __name__ == "__main__":
    rep = main()
    (OUT / "m5_bounds_validation.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep, indent=1))
