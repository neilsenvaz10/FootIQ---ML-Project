"""Read views over the store. They rebuild exactly the frames the app and the frozen model code already use, so the rest of the system does not change."""
import pandas as pd

import config as C

DASHBOARD_COLUMNS = ["competition_key", "competition", "group", "season", "stage", "date", "home", "away", "home_entity_id", "away_entity_id", "home_goals", "away_goals", "home_source_name",
                     "away_source_name", "score_basis", "outcome", "outcome_basis", "shootout_winner", "neutral", "source", "licence"]
COMP = C.ALL_BY_KEY                                  # name/group lookups for every stored row, archived competitions included


def dashboard_matches(conn) -> pd.DataFrame:
    """Completed matches of every stored competition (the application filters to its six) in the same shape and order as data/miniproject/matches.csv."""
    df = pd.read_sql_query(
        "SELECT m.*, t1.display_name AS home_display, t2.display_name AS away_display FROM matches m "
        "LEFT JOIN teams t1 ON t1.entity_id = m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id = m.away_entity_id "
        "WHERE m.competition_key IS NOT NULL AND m.status IN ('completed','awarded') AND m.home_goals_final IS NOT NULL ORDER BY m.src_order", conn)
    club = df.kind == "club"
    out = pd.DataFrame({
        "competition_key": df.competition_key, "competition": df.competition_key.map(lambda k: COMP[k]["name"]), "group": df.competition_key.map(lambda k: COMP[k]["group"]),
        "season": df.season.astype(str), "stage": df.stage.fillna(""), "date": df.match_date,
        "home": df.home_display.where(club & df.home_display.notna(), df.home_name), "away": df.away_display.where(club & df.away_display.notna(), df.away_name),
        "home_entity_id": df.home_entity_id.fillna(""), "away_entity_id": df.away_entity_id.fillna(""), "home_goals": df.home_goals_final.astype("int64"), "away_goals": df.away_goals_final.astype("int64"),
        "home_source_name": df.home_name.where(club, ""), "away_source_name": df.away_name.where(club, ""),
        "score_basis": df.apply(lambda r: "final score excluding penalties" if r.kind == "club" else ("recorded score (knockouts: after extra time)" if r.season == "2026" and r.competition_key == "WC" and r.source_system != "martj42/international_results" else "recorded score (may include extra time)"), axis=1),
        "outcome": df.outcome.fillna(""),
        "outcome_basis": df.apply(lambda r: f"90 min ({r.label_90_status})" if r.kind == "club" else ("recorded score; 90-min result not separable for knockouts" if r.season == "2026" and r.competition_key == "WC" and r.source_system != "martj42/international_results" else "recorded score; 90-min result not separable"), axis=1),
        "shootout_winner": df.shootout_winner.fillna(""), "neutral": df.neutral.fillna(""), "source": df.source_system.fillna(""), "licence": df.licence.fillna("")})
    out["_k"] = out.competition_key
    out = out.sort_values(["competition_key", "date", "home"], kind="mergesort").reset_index(drop=True)
    return out.drop(columns="_k")[DASHBOARD_COLUMNS]


def model_universe(conn) -> pd.DataFrame:
    """The model universe in the layout of the frozen V_universe.pkl (only the columns the inference code reads).
    Completed results only; rows are ordered by record_id, which the state machines do not depend on (they sort by date and record_id)."""
    df = pd.read_sql_query(
        "SELECT record_id, match_date, model_home_entity AS home_entity_id, model_away_entity AS away_entity_id, home_name AS home_team_name, away_name AS away_team_name, competition_id, season AS season_corrected, tier, competition_type, "
        "regular AS regular_round_robin_stage, rated, home_goals_90 AS gh, away_goals_90 AS ga FROM matches WHERE in_universe=1 AND status IN ('completed','awarded','abandoned') ORDER BY record_id", conn)
    df["dt"] = pd.to_datetime(df.match_date)
    df["regular_round_robin_stage"] = df.regular_round_robin_stage.astype(bool)
    df["rated"] = df.rated.astype(bool)
    df["match_date"] = df.dt
    df["gh"], df["ga"] = df.gh.astype(float), df.ga.astype(float)      # same dtype as the frozen pickle
    return df


def freshness(conn) -> list[dict]:
    """Per competition: newest completed result, newest scheduled fixture, matches still awaiting a result, and the last sync that touched it."""
    rows = []
    for key in [c["key"] for c in C.COMPETITIONS]:
        r = conn.execute(
            "SELECT MAX(CASE WHEN status IN ('completed','awarded') THEN match_date END) AS latest_result, "
            "SUM(status='awaiting_result') AS awaiting, SUM(status='scheduled') AS scheduled, MAX(CASE WHEN status='scheduled' THEN match_date END) AS last_fixture, "
            "MIN(CASE WHEN status='awaiting_result' THEN match_date END) AS oldest_awaiting FROM matches WHERE competition_key=?", (key,)).fetchone()
        rows.append(dict(competition_key=key, latest_result=r["latest_result"], awaiting_result=int(r["awaiting"] or 0), scheduled=int(r["scheduled"] or 0), last_fixture=r["last_fixture"], oldest_awaiting=r["oldest_awaiting"]))
    return rows
