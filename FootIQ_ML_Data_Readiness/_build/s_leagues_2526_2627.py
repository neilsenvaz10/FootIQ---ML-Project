"""All domestic-league matches for 2025-26 and 2026-27 (cut-off: before 2026-10-01) from the original submission data."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

CUT = "2026-10-01"
OUTD = os.path.join(OUT, "leagues_2025-26_2026-27")
os.makedirs(OUTD, exist_ok=True)
d = pd.read_csv(os.path.join(SUBWORK, "club_matches_all.csv"), low_memory=False, keep_default_na=False, na_values=[""])
d["season"] = d.season.astype(str)
lg = d[(d.competition_type == "domestic_league") & d.season.isin(["2025-26", "2026-27", "2025", "2026"])].copy()
lg["completed"] = lg.match_status.isin(["completed", "awarded", "abandoned"]) & lg.final_match_winner_side.notna()
lg["before_cutoff"] = lg.match_date < CUT
done = lg[lg.completed & lg.before_cutoff].copy()
rest = lg[~(lg.completed & lg.before_cutoff)].copy()
rest["why_not_in_results"] = [
    ("scheduled_on_or_after_2026-10-01" if not b else (s if s != "completed" else "other"))
    for b, s in zip(rest.before_cutoff, rest.match_status)]
rest.loc[(rest.match_status == "unscored") & rest.before_cutoff, "why_not_in_results"] = "date_before_cutoff_but_no_result_in_source"
cols = ["match_id", "match_date", "kickoff_time_local", "competition_id", "competition_name", "competition_country", "tier",
        "season", "stage", "home_team_id", "home_team", "away_team_id", "away_team", "home_goals_regulation",
        "away_goals_regulation", "home_goals_halftime", "away_goals_halftime", "result_regulation", "match_status",
        "status_note", "source_repo", "source_repo_commit", "source_file", "source_line"]
done.sort_values(["competition_country", "competition_id", "match_date"])[cols].to_csv(
    os.path.join(OUTD, "league_results_2025-26_2026-27_before_2026-10-01.csv"), index=False, encoding=ENC)
rest.sort_values(["competition_id", "match_date"])[cols + ["why_not_in_results"]].to_csv(
    os.path.join(OUTD, "league_records_without_result_or_after_cutoff.csv"), index=False, encoding=ENC)
rows = []
for (cid, s), g in lg.groupby(["competition_id", "season"]):
    c = g[g.completed & g.before_cutoff]
    teams = set(g.home_team_id) | set(g.away_team_id)
    n = len(teams)
    pairs = set(zip(c.home_team_id, c.away_team_id))
    rows.append(dict(competition_id=cid, competition_name=g.competition_name.iloc[0], country=g.competition_country.iloc[0],
                     tier=g.tier.iloc[0], season=s, teams=n, records_in_source=len(g), completed_before_cutoff=len(c),
                     unscored_before_cutoff=int(((g.match_status == "unscored") & g.before_cutoff).sum()),
                     scheduled_after_cutoff=int((~g.before_cutoff).sum()),
                     cancelled=int((g.match_status == "cancelled").sum()), postponed=int((g.match_status == "postponed").sum()),
                     abandoned=int((g.match_status == "abandoned").sum()),
                     double_round_robin_size=n * (n - 1), ordered_pair_coverage=round(len(pairs) / (n * (n - 1)), 3) if n > 1 else None,
                     latest_completed_date=c.match_date.max() if len(c) else None, first_date=g.match_date.min(),
                     status=("complete_season" if len(c) == len(g) - int((g.match_status == "cancelled").sum()) and len(c) > 0 and not (~g.before_cutoff).any()
                             else ("in_progress" if len(c) > 0 else "no_results_in_source"))))
cov = pd.DataFrame(rows).sort_values(["country", "tier", "season"])
cov.to_csv(os.path.join(OUTD, "league_coverage_by_competition_season.csv"), index=False, encoding=ENC)
pd.set_option("display.width", 250)
print(len(done), "results;", len(rest), "other records;", cov.competition_id.nunique(), "leagues;", len(cov), "league-seasons")
print(cov.status.value_counts().to_string())
print(cov[cov.competition_id.isin(["england:1-premierleague", "espana:1-liga", "deutschland:1-bundesliga", "italy:1-seriea", "europe/france:fr1"])][
    ["competition_name", "season", "teams", "records_in_source", "completed_before_cutoff", "scheduled_after_cutoff", "latest_completed_date", "status"]].to_string())
