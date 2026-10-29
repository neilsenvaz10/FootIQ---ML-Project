"""Phase 4.19 step 1: READ-ONLY audit of the Champions League data in the production store (opened mode=ro) and the local staging file.
Writes ucl_audit.json and ucl_coverage_by_season.csv next to this script. Nothing in the project is modified; no network."""
import csv
import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DB = ROOT / "data" / "footiq.sqlite"
MATRIX = ROOT / "FootIQ_ML_Data_Readiness" / "01_COMPETITION_SEASON_COVERAGE_MATRIX.csv"
STAGING = ROOT / "data" / "supervised" / "phase4" / "p417" / "uefa_2026_27_staging.csv"
LEAGUE_PHASE = re.compile(r"^(League\b|Matches\s*>\s*Matchday)", re.I)

c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
m = pd.read_sql_query("SELECT * FROM matches WHERE competition_key='UCL'", c)
teams = pd.read_sql_query("SELECT entity_id, display_name FROM teams", c)
known = set(teams.entity_id)
mx = pd.read_csv(MATRIX)
mx = mx[mx.competition_id == "champions-league:cl"].set_index("season")

out = {"database": str(DB.relative_to(ROOT)), "rows": int(len(m)), "seasons": {}}
rows = []
for season, d in m.groupby("season"):
    done = d[d.status.isin(["completed", "awarded"]) & d.home_goals_final.notna()]
    expected = int(mx.loc[season, "expected_matches"]) if season in mx.index and pd.notna(mx.loc[season, "expected_matches"]) else (189 if season == "2026-27" else None)
    lp = d[d.stage.fillna("").map(lambda s: bool(LEAGUE_PHASE.match(s)) and not re.search(r"play-?off|knockout|round of|final", s, re.I))]
    lp_expected = 144 if season >= "2024-25" else None
    teams_lp = set(lp.home_entity_id) | set(lp.away_entity_id)
    dup = d.duplicated(["season", "match_date", "home_entity_id", "away_entity_id"], keep=False)
    dup_pair_stage = d.duplicated(["season", "stage", "home_entity_id", "away_entity_id"], keep=False)
    y0 = int(season[:4])
    out_of_window = d[(d.match_date < f"{y0}-07-01") | (d.match_date > f"{y0 + 1}-08-31")]
    bad_score = done[(done.home_goals_final < 0) | (done.away_goals_final < 0) | (done.home_goals_final > 15) | (done.away_goals_final > 15)]
    missing_ent = d[d.home_entity_id.isna() | d.away_entity_id.isna() | (d.home_entity_id == "") | (d.away_entity_id == "")]
    unknown_ent = d[~d.home_entity_id.isin(known) | ~d.away_entity_id.isin(known)]
    same_team = d[d.home_entity_id == d.away_entity_id]
    missing_score = d[d.status.isin(["completed", "awarded"]) & (d.home_goals_final.isna() | d.away_goals_final.isna())]
    # outcome column vs score (final score excluding penalties; knockout extra time can legitimately differ from the 90-minute outcome, so only league-stage and group rows are compared)
    comparable = done[done.outcome.notna() & (done.label_90_status == "confirmed")]
    wrong_outcome = comparable[comparable.apply(lambda r: ("H" if r.home_goals_final > r.away_goals_final else "A" if r.home_goals_final < r.away_goals_final else "D") != r.outcome and r.home_goals_90 == r.home_goals_final, axis=1)]
    per_team = {t: int(((lp.home_entity_id == t) | (lp.away_entity_id == t)).sum()) for t in teams_lp}
    rec = dict(season=season, rows=int(len(d)), expected=expected, completed=int(len(done)), not_completed=int(len(d) - len(done)), missing_vs_expected=(expected - len(d)) if expected else None,
               first_date=d.match_date.min(), last_date=d.match_date.max(), sources=sorted(d.source_system.dropna().unique().tolist()), licences=sorted(d.licence.dropna().unique().tolist()),
               in_model_universe=int(d.in_universe.sum()), league_phase_rows=int(len(lp)), league_phase_expected=lp_expected, league_phase_teams=len(teams_lp),
               teams_with_wrong_league_match_count=sorted(t for t, n in per_team.items() if lp_expected and n != 8),
               duplicate_same_day_pair=int(dup.sum()), duplicate_same_stage_pair=int(dup_pair_stage.sum()), dates_outside_season_window=int(len(out_of_window)), implausible_scores=int(len(bad_score)),
               completed_without_score=int(len(missing_score)), missing_team_identifier=int(len(missing_ent)), team_identifier_not_in_teams_table=int(len(unknown_ent)), home_equals_away=int(len(same_team)), outcome_disagrees_with_score=int(len(wrong_outcome)))
    out["seasons"][season] = rec
    rows.append(rec)

# the seasons that are the same team in two spellings: display names per entity id across the competition
names = m.groupby("home_entity_id").home_name.nunique()
out["entities"] = dict(distinct_entity_ids=int(len(set(m.home_entity_id) | set(m.away_entity_id))), entities_with_several_source_spellings=int((names > 1).sum()), example_spellings={e: sorted(m[m.home_entity_id == e].home_name.unique().tolist())[:4] for e in names[names > 1].index[:5]})

# 2026-27: what the store has vs the local staging file (36 results, 108 scheduled fixtures)
cur = m[m.season == "2026-27"]
st = pd.read_csv(STAGING, encoding="utf-8-sig")
st = st[st.competition_key == "UCL"]
key = lambda df, h, a: set(zip(df[h], df[a]))
store_pairs = key(cur, "home_entity_id", "away_entity_id")
st["in_store"] = [(h, a) in store_pairs for h, a in zip(st.home_entity, st.away_entity)]
by_md = st.groupby("matchday").agg(fixtures=("home", "size"), played_in_staging=("status", lambda s: int((s == "played").sum())), in_store=("in_store", "sum"), first=("date", "min"), last=("date", "max")).reset_index()
out["season_2026_27"] = dict(expected_league_phase=144, in_store=int(len(cur)), completed_in_store=int(cur.status.isin(["completed"]).sum()), scheduled_in_store=int((cur.status == "scheduled").sum()),
                             staging_rows=int(len(st)), staging_played=int((st.status == "played").sum()), staging_scheduled=int((st.status == "scheduled").sum()),
                             missing_from_store=int((~st.in_store).sum()), by_matchday=by_md.to_dict(orient="records"),
                             knockout_phase="45 knockout-phase matches (16 play-off, 16 round of 16, 8 quarter-final, 4 semi-final, 1 final): pairings are not drawn until the league phase ends, so no source holds them",
                             expected_total_competition=189)
miss = st[~st.in_store][["matchday", "date", "home", "away", "home_entity", "away_entity", "status", "home_goals", "away_goals"]]
miss.to_csv(HERE / "ucl_2026_27_missing_from_store.csv", index=False, encoding="utf-8-sig")
with open(HERE / "ucl_coverage_by_season.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    for r in rows:
        w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
(HERE / "ucl_audit.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps({s: {k: v for k, v in r.items() if k not in ("sources", "licences")} for s, r in out["seasons"].items()}, indent=0, default=str)[:6000])
print(json.dumps(out["season_2026_27"], indent=0, default=str)[:2500])
print(out["entities"])
