"""Phase 4.20: document the Champions League and the team filter in docs/mini-project/API_REFERENCE.md (record of exactly what changed)."""
from pathlib import Path

p = Path(__file__).resolve().parents[4] / "docs" / "mini-project" / "API_REFERENCE.md"
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


rep("### `GET /api/matches[?comp=&season=&matchday=&status=&limit=&cursor=&order=]` (Matches hub; five domestic leagues)",
    "### `GET /api/matches[?comp=&season=&matchday=&status=&team=&limit=&cursor=&order=]` (Matches hub; five domestic leagues and the Champions League)")
rep("Parameters: `comp` one of the five leagues (default all);", "Parameters: `comp` one of the five leagues or `UCL` (default all six); `team` a club identifier from `facets.teams` (needs `comp`; restricts rows and counts to that club's matches);")
rep("scope {competitions[], seasons {KEY: season}, matchday, status, order, limit},", "scope {competitions[], seasons {KEY: season}, matchday, status, order, limit, team},")
rep("timing {phase, ambiguous, note}, eligibility {eligible, predictable, reliability, flags} | null, saved_forecast_runs} ],", "timing {phase, ambiguous, note}, eligibility {eligible, predictable, reliability, flags} | null, saved_forecast_runs, validation_badge} ],")
rep("facets {seasons[], matchdays[]},", "facets {seasons[], matchdays[], teams[ {entity, name} ] (one league-season only, else [])},")
s = s.replace("* **Statuses** are effective ones,", """* **Champions League (Phase 4.20).** `UCL` rows are listed like the leagues, with three differences: their `matchday_no` is read from the stage label (`Matches > Matchday 3` is matchday 3, so the filter and facet work although the store holds no number); `eligibility` is `null` (the eligibility rules belong to the gameweek page, which is domestic-only; there is no gameweek for the Champions League); and `validation_badge` is `Not validated (indicative only)`, which a client must show next to any prediction link. Its `freshness` entry has no approved source (`historical_only` in `/api/data-freshness`): it changes only through approved imports (`app/store/uefa_import.py`).
* **Statuses** are effective ones,""", 1)
p.write_text(s, encoding="utf-8")
print("api doc patched")
