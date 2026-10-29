p = "docs/mini-project/API_REFERENCE.md"
s = open(p, encoding="utf-8").read()
s += '''
### Experimental points-only simulation (approved 2026-10-25)

| Method and path | Purpose |
|---|---|
| `POST /api/season/points` | Body `{key, season, user_action: "simulate_points_button", simulations?, seed?}`. Simulates win / draw / loss only from the frozen club v1 probabilities (3 / 1 / 0 points) and saves one row in `simulation_runs` (`assumptions.mode = "points_only"`, label "Experimental \\u2014 Points-only simulation"). Refused with 422 (nothing saved) if the action is wrong, the count is outside the configured range, the data are Not eligible, or the league is outside the approved scope (Bundesliga and La Liga). It needs no scoreline method and no tie-break rules, and it returns **no** titles, top-four, relegation or position probabilities. |

`GET /api/season/status` also returns `points_only: {label, can_run, blockers, limitations}`. `GET /api/season/runs` adds `mode` (`points_only` or `final_positions`).
`result.summary.teams[]` (points-only): `current_points`, `remaining_fixtures`, `expected_points`, `points_sd`, `points_p10/p25/median/p75/p90`, `points_min/max`, `distribution {first_points, probabilities[]}`.

Final-position simulations (`POST /api/season/simulate`) stay disabled. When a tie cannot be resolved by a supported rule it is left unresolved: the affected band probability is `null` and only `*_low` / `*_high` bounds are given.
'''
open(p, "w", encoding="utf-8", newline="\n").write(s)
p = "docs/mini-project/PHASE3_IMPLEMENTATION_REPORT.md"
s = open(p, encoding="utf-8").read()
s = s.replace("# Phase 3 implementation report: domestic league season simulator (controlled implementation)\n", "# Phase 3 implementation report: domestic league season simulator (controlled implementation)\n\n> **Superseded in part on 2026-10-25 by [PHASE3_POINTS_ONLY_REPORT.md](PHASE3_POINTS_ONLY_REPORT.md):** final deciders are no longer simulated as a fair coin (decision D6: they stay unresolved and probabilities are withheld), and an Experimental points-only mode was added.\n", 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
