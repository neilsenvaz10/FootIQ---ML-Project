"""World Cup simulation: thin wrapper around the EXISTING simulators in scripts/ (no new model, nothing written to disk).

mode "current"        -> scripts/simulate_live_tournament_v213.py: v2.3 team-power Monte Carlo with completed 2026 results locked.
                         The repo holds the archived end-of-tournament state, so almost everything is locked to real results.
mode "pre_tournament" -> scripts/build_worldcup_model_v23.py run_tournament_v23: the same engine with NO results locked
                         (the static pre-tournament model that the repo's own v2.3 report is based on).
Neither is the v2.7 match model. Must run with `python -X utf8` on Windows. Seeded: the same seed gives the same output.
"""
import sys
import threading
import time

import config as C

SCRIPTS = C.ROOT / "scripts"
DEFAULT_SIMS = 5000
MAX_SIMS = 50000   # the simulators' own default
MODES = ("current", "pre_tournament")
_LOCK = threading.Lock()     # the simulators use module-level config and the global `random` state


class SimulationError(RuntimeError):
    pass


def _norm(row: dict, rank_key: str) -> dict:
    out = {"rank": row[rank_key]}
    for k in ("team", "group", "qualify_knockout_pct", "round_of_16_pct", "quarter_final_pct", "semi_final_pct", "final_pct", "champion_pct"):
        out[k] = row.get(k)
    return out


def run(simulations: int = DEFAULT_SIMS, seed: int | None = None, mode: str = "current") -> dict:
    if not sys.flags.utf8_mode:
        raise SimulationError("start Python with `-X utf8` (the existing simulator reads CSVs with the Windows default encoding otherwise)")
    if mode not in MODES:
        raise SimulationError(f"mode must be one of {MODES}")
    simulations = max(100, min(int(simulations), MAX_SIMS))
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_worldcup_model_v23 as v23
    import simulate_live_tournament_v213 as sim

    with _LOCK:
        t = time.time()
        if mode == "current":
            cfg = sim.V213_CONFIG
            old = (cfg["simulations"], cfg["seed"])
            cfg["simulations"] = simulations
            if seed is not None:
                cfg["seed"] = int(seed)
            used_seed = cfg["seed"]
            try:
                rows, metadata, group_tables, _ = sim.run_live_tournament()
            finally:
                cfg["simulations"], cfg["seed"] = old
            odds = [_norm(r, "live_title_rank") for r in rows]
            engine = cfg["base_engine"]
            groups = {g: [{k: t_[k] for k in ("team", "played", "points", "goal_diff", "goals_for") if k in t_} for t_ in tab] for g, tab in group_tables.items()}
            note = ("Archived 2026 tournament state held in the repo: all completed results are locked, so only the remaining matches are simulated "
                    "and most percentages are 0 or 100. Not live odds.")
        else:
            cfg = v23.V23_CONFIG
            old = (cfg["simulations"], cfg["seed"])
            cfg["simulations"] = simulations
            if seed is not None:
                cfg["seed"] = int(seed)
            used_seed = cfg["seed"]
            try:
                powers = v23.build_team_power_v23()
                fixtures = sim.read_csv(sim.PROCESSED / "worldcup_2026_matches.csv")
                rows = v23.run_tournament_v23(powers, fixtures)
            finally:
                cfg["simulations"], cfg["seed"] = old
            odds = [_norm(r, "title_rank") for r in rows]
            engine, groups = "v2.3 team power + v2.3 group/knockout Monte Carlo (no results locked)", None
            metadata = dict(actual_group_results_locked=0, actual_knockout_results_locked=0, simulations=simulations)
            note = "Pre-tournament view: no real results are used, so this is what the model said before the 2026 World Cup started."
    return dict(mode=mode, simulations=simulations, seed=used_seed, seconds=round(time.time() - t, 1), engine=engine, note=note,
                metadata=metadata, title_odds=odds, group_tables=groups)
