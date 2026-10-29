"""Assemble datasets 04, 05, 08 (+ supplementary 14 StatsBomb match index) and extend 06/07.

Run after assemble_matches.py, build_players_openfootball.py and build_players_statsbomb.py.
"""
import os
import re
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(HERE, "work")
OUT = ROOT
ENC = "utf-8-sig"
EXTRACTION_DATE = "2026-10-20"
SB_URL = "https://github.com/statsbomb/open-data"
OF_URL = "https://github.com/openfootball"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def rd(name, **kw):
    return pd.read_csv(os.path.join(WORK, name), low_memory=False, **kw)


STAT_COLS = ["goals", "assists", "own_goals", "penalty_goals", "shots", "shots_on_target", "xg", "passes",
             "passes_completed", "key_passes", "crosses", "tackles", "tackles_won", "interceptions", "clearances",
             "blocks", "ball_recoveries", "dribbles", "dribbles_completed", "fouls_committed", "fouls_won",
             "pressures", "duels", "duels_won", "dispossessed", "miscontrols", "carries", "offsides", "gk_saves",
             "gk_goals_conceded", "yellow_cards", "red_cards"]


def main():
    sbm = rd("sb_matches.csv")
    sbp = rd("sb_player_match.csv")
    ofp = rd("of_player_match.csv")
    ofm = rd("of_full_matches.csv")
    sq = rd("of_squads.csv")
    club = rd("club_matches_all.csv", keep_default_na=False, na_values=[""])
    matches_in_02_03 = set(club.match_id)

    # ------------------------------------------------------------ StatsBomb player-match
    sbp = sbp.merge(sbm[["sb_match_id", "match_date", "competition_name", "season_name", "competition_gender",
                         "competition_international", "stage", "home_team", "away_team", "sb_home_team_id",
                         "sb_away_team_id", "lineup_event_files_status", "source_file"]]
                    .rename(columns={"source_file": "sb_match_meta_file"}), on="sb_match_id", how="left")
    sb = pd.DataFrame(index=sbp.index)
    sb["source_dataset"] = "StatsBomb Open Data"
    sb["match_id"] = "SB:M" + sbp.sb_match_id.astype(str)
    sb["match_in_02_or_03"] = False
    sb["match_date"] = sbp.match_date
    sb["competition_name"] = sbp.competition_name
    sb["competition_gender"] = sbp.competition_gender
    sb["season"] = sbp.season_name
    sb["stage"] = sbp.stage
    sb["player_id"] = "SB:P" + sbp.sb_player_id.astype(str)
    sb["source_player_id"] = sbp.sb_player_id.astype(str)
    sb["player_name"] = sbp.player_name
    sb["team_id"] = "SB:T" + sbp.sb_team_id.astype(str)
    sb["team_name"] = sbp.team_name
    sb["opponent_team_name"] = [a if t == h else h for t, h, a in zip(sbp.team_name, sbp.home_team, sbp.away_team)]
    sb["started"] = sbp.started
    sb["position"] = sbp.first_position
    sb["captain"] = pd.NA
    sb["substituted_in_minute"] = pd.NA
    sb["substituted_out_minute"] = pd.NA
    sb["minutes_played"] = sbp.minutes_played
    sb["minutes_basis"] = "derived from StatsBomb lineup position intervals (from/to match clock); end of match = last non-shootout event"
    has_events = sbp.lineup_event_files_status.eq("ok")
    for c in STAT_COLS:
        if c in sbp.columns:
            col = sbp[c].astype(float)
            sb[c] = col.where(has_events)
        else:
            sb[c] = pd.NA
    sb["yellow_cards"] = sbp.yellow_cards  # from lineup file (independent of events)
    sb["red_cards"] = sbp.red_cards
    sb["stats_coverage"] = ["event_level_full" if h else "lineup_only" for h in has_events]
    sb["source_url"] = SB_URL
    sb["source_reference"] = sbp.sb_match_meta_file

    # ------------------------------------------------------------ openfootball lineups
    ofp["link_ok"] = ofp.link_status.astype(str).str.startswith("linked")
    of = pd.DataFrame(index=ofp.index)
    of["source_dataset"] = "openfootball match files (CC0)"
    of["match_id"] = ofp.match_id
    of["match_in_02_or_03"] = ofp.match_id.isin(matches_in_02_03)
    of["match_date"] = ofp.match_date
    cname = club.drop_duplicates("competition_id").set_index("competition_id").competition_name
    of["competition_name"] = ofp.competition_id.map(cname)
    of["competition_gender"] = "unlabelled in source (men's competition assumed from competition name)"
    of["season"] = ofp.season.astype(str)
    of["stage"] = pd.NA
    of["player_id"] = ofp.player_key
    of["source_player_id"] = pd.NA
    of["player_name"] = ofp.player_name_source
    of["team_id"] = ofp.team_id
    of["team_name"] = ofp.team_name
    # opponent from the match record
    opp = {}
    for r in ofm.itertuples():
        opp[(r.match_id, "home")] = r.away_team_source
        opp[(r.match_id, "away")] = r.home_team_source
    of["opponent_team_name"] = [opp.get((m, s)) for m, s in zip(ofp.match_id, ofp.side)]
    of["started"] = ofp.role.eq("starter")
    of["position"] = pd.NA
    of["captain"] = ofp.captain
    of["substituted_in_minute"] = ofp.substituted_in_minute
    of["substituted_out_minute"] = ofp.substituted_out_minute
    of["minutes_played"] = ofp.minutes_played_est_90min_frame
    of["minutes_basis"] = ofp.minutes_basis
    for c in STAT_COLS:
        of[c] = pd.NA
    for c in ("goals", "own_goals", "penalty_goals", "yellow_cards", "red_cards"):
        of[c] = ofp[c]
    of["stats_coverage"] = "appearance_goals_cards_only"
    of["source_url"] = OF_URL
    of["source_reference"] = ofp.source_file + ":L" + ofp.source_line.astype(str)

    pm = pd.concat([sb, of], ignore_index=True)
    pm.insert(0, "player_match_id", [f"PM{i:07d}" for i in range(1, len(pm) + 1)])
    pm["source_extraction_date"] = EXTRACTION_DATE
    pm = pm.sort_values(["match_date", "match_id", "team_id", "started"], ascending=[True, True, True, False])
    pm.to_csv(os.path.join(OUT, "05_Player_Match_Statistics.csv"), index=False, encoding=ENC)
    print("05 rows", len(pm), pm.source_dataset.value_counts().to_dict())

    # ------------------------------------------------------------ memberships
    mem = []
    g = pm.groupby(["player_id", "team_id", "competition_name", "season"], dropna=False)
    agg = g.agg(player_name=("player_name", "first"), team_name=("team_name", "first"),
                first_match_date=("match_date", "min"), last_match_date=("match_date", "max"),
                n_matches=("match_id", "nunique"), minutes_total=("minutes_played", "sum"),
                source_dataset=("source_dataset", "first"), gender=("competition_gender", "first")).reset_index()
    comp_intl = sbm.drop_duplicates(["competition_name", "season_name"]).set_index(
        ["competition_name", "season_name"]).competition_international
    team_kind = []
    for r in agg.itertuples():
        if r.source_dataset.startswith("StatsBomb"):
            v = comp_intl.get((r.competition_name, r.season))
            team_kind.append("national" if v is True or str(v) == "True" else "club")
        elif r.competition_name == "FIFA Club World Cup":
            team_kind.append("club")
        else:
            team_kind.append("club")
    agg["team_type"] = team_kind
    agg["membership_basis"] = "appeared_in_match_lineup"
    agg["shirt_number"] = pd.NA
    agg["position_text"] = pd.NA
    agg["caps_before_event"] = pd.NA
    agg["listed_club_text"] = pd.NA
    agg["source_url"] = agg.source_dataset.map(lambda s: SB_URL if s.startswith("Stats") else OF_URL)
    agg["source_reference"] = agg.source_dataset
    agg = agg.rename(columns={"competition_name": "competition_or_event"})
    # squad lists
    sq = sq.copy()
    sq["heading"] = sq.squad_heading.fillna(sq.squad_title)
    names = []
    comp_ev = []
    seasons = []
    team_names = []
    for r in sq.itertuples():
        h = str(r.heading)
        title = str(r.squad_title) if isinstance(r.squad_title, str) else ""
        if " - " in h and not r.squad_source_file.endswith("-squads.txt"):
            tn, ev = h.split(" - ", 1)
        elif r.squad_source_file.endswith("-squads.txt"):
            tn, ev = h, title
        else:
            tn, ev = h, title
        m = re.search(r"(\d{4}(?:/\d{2,4})?)\s*$", ev or title)
        team_names.append(re.sub(r"\s+", " ", tn).strip())
        comp_ev.append(ev or title)
        seasons.append(m.group(1) if m else "")
    sq["team_name"] = team_names
    sq["competition_or_event"] = comp_ev
    sq["season"] = seasons
    sq["team_type"] = ["national" if ("/euro/" in "/" + f or "copa-america" in f) else "club"
                       for f in sq.squad_source_file]
    sq["team_id"] = "SQD|" + sq.squad_source_file.str.replace(r"/[^/]+$", "", regex=True) + "|" + sq.team_name
    # file-level group for club world cup: many teams in one file -> include team name only (already)
    sq["player_id"] = ("SQD|" + sq.team_id.str[4:] + "|" + sq.competition_or_event + "|" + sq.player_name_source.map(norm)
                       + "|" + sq.birth_text.fillna("").astype(str))
    sqm = pd.DataFrame(dict(
        player_id=sq.player_id, team_id=sq.team_id, competition_or_event=sq.competition_or_event, season=sq.season,
        player_name=sq.player_name_source, team_name=sq.team_name, first_match_date=pd.NA, last_match_date=pd.NA,
        n_matches=pd.NA, minutes_total=pd.NA, source_dataset="openfootball squad files (CC0)", gender=pd.NA,
        team_type=sq.team_type, membership_basis="listed_in_published_squad", shirt_number=sq.shirt_number,
        position_text=sq.position_code, caps_before_event=sq.caps_before_event,
        listed_club_text=sq.listed_club_text, source_url=OF_URL,
        source_reference=sq.squad_source_file + ":L" + sq.source_line.astype(str)))
    memb = pd.concat([agg, sqm], ignore_index=True)
    memb.insert(0, "membership_id", [f"MB{i:07d}" for i in range(1, len(memb) + 1)])
    memb["id_scope_note"] = memb.player_id.map(lambda x: "source_native_player_id" if x.startswith("SB:")
                                               else "derived_team_scoped_key_not_a_global_identity")
    memb["source_extraction_date"] = EXTRACTION_DATE
    memb = memb[["membership_id", "player_id", "player_name", "id_scope_note", "team_id", "team_name", "team_type",
                 "competition_or_event", "season", "membership_basis", "first_match_date", "last_match_date",
                 "n_matches", "minutes_total", "shirt_number", "position_text", "caps_before_event",
                 "listed_club_text", "source_dataset", "source_url", "source_reference", "source_extraction_date"]]
    memb.to_csv(os.path.join(OUT, "08_Player_Team_Memberships.csv"), index=False, encoding=ENC)
    print("08 rows", len(memb))

    # ------------------------------------------------------------ players
    parts = []
    s1 = sbp.groupby("sb_player_id").agg(
        player_name=("player_name", "first"), player_nickname=("player_nickname", "first"),
        nationality=("country_name", lambda s: s.dropna().mode().iat[0] if s.notna().any() else ""),
        position_primary=("first_position", lambda s: s.dropna().mode().iat[0] if s.notna().any() else ""),
        first_seen_date=("match_date", "min"), last_seen_date=("match_date", "max"),
        n_match_appearance_records=("sb_match_id", "nunique"), n_teams=("sb_team_id", "nunique"),
        gender_context=("competition_gender", lambda s: "; ".join(sorted(set(map(str, s.dropna())))))).reset_index()
    s1["player_id"] = "SB:P" + s1.sb_player_id.astype(str)
    s1["source_player_id"] = s1.sb_player_id.astype(str)
    s1["id_scope"] = "source_native_id_StatsBomb"
    s1["birth_text"] = ""
    s1["source_dataset"] = "StatsBomb Open Data"
    s1["source_url"] = SB_URL
    s1["nationality_code_if_listed"] = ""
    parts.append(s1.drop(columns=["sb_player_id"]))
    o1 = ofp.groupby("player_key").agg(
        player_name=("player_name_source", lambda s: s.mode().iat[0]),
        first_seen_date=("match_date", "min"), last_seen_date=("match_date", "max"),
        n_match_appearance_records=("match_id", "nunique"), n_teams=("team_id", "nunique")).reset_index()
    o1["player_id"] = o1.player_key
    o1["player_nickname"] = ""
    o1["nationality"] = ""
    o1["position_primary"] = ""
    o1["gender_context"] = "unlabelled in source (men's competition assumed from competition name)"
    o1["source_player_id"] = ""
    o1["id_scope"] = "derived_team_scoped_name_key"
    o1["birth_text"] = ""
    o1["source_dataset"] = "openfootball match files (CC0)"
    o1["source_url"] = OF_URL
    o1["nationality_code_if_listed"] = ""
    parts.append(o1.drop(columns=["player_key"]))
    s2 = pd.DataFrame(dict(
        player_id=sq.player_id, player_name=sq.player_name_source, player_nickname="",
        nationality=sq.nationality_code_if_listed, nationality_code_if_listed=sq.nationality_code_if_listed,
        position_primary=sq.position_code, first_seen_date=pd.NA, last_seen_date=pd.NA,
        n_match_appearance_records=0, n_teams=1, gender_context="unlabelled in source (assumed men's from section)",
        source_player_id="", id_scope="derived_squad_scoped_key", birth_text=sq.birth_text.fillna(""),
        source_dataset="openfootball squad files (CC0)", source_url=OF_URL))
    s2 = s2.drop_duplicates("player_id")
    parts.append(s2)
    pl = pd.concat(parts, ignore_index=True)
    pl["n_squad_list_records"] = pl.player_id.map(sq.groupby("player_id").size()).fillna(0).astype(int)
    pl["source_extraction_date"] = EXTRACTION_DATE
    pl = pl[["player_id", "source_player_id", "id_scope", "player_name", "player_nickname", "nationality",
             "nationality_code_if_listed", "position_primary", "birth_text", "gender_context", "first_seen_date",
             "last_seen_date", "n_match_appearance_records", "n_squad_list_records", "n_teams", "source_dataset",
             "source_url", "source_extraction_date"]]
    pl.to_csv(os.path.join(OUT, "04_Football_Players.csv"), index=False, encoding=ENC)
    print("04 rows", len(pl), pl.id_scope.value_counts().to_dict())

    # ------------------------------------------------------------ supplementary 14: StatsBomb match index
    mi = sbm.copy()
    mi["match_id"] = "SB:M" + mi.sb_match_id.astype(str)
    mi["home_team_id"] = "SB:T" + mi.sb_home_team_id.astype(str)
    mi["away_team_id"] = "SB:T" + mi.sb_away_team_id.astype(str)
    mi["source_url"] = SB_URL
    mi["source_extraction_date"] = EXTRACTION_DATE
    mi = mi[["match_id", "sb_match_id", "match_date", "kick_off", "sb_competition_id", "competition_name",
             "competition_country", "competition_gender", "competition_youth", "competition_international",
             "sb_season_id", "season_name", "stage", "home_team_id", "home_team", "away_team_id", "away_team",
             "home_score", "away_score", "match_status", "match_week", "stadium", "data_version",
             "lineup_event_files_status", "source_file", "source_url", "source_extraction_date"]]
    mi.to_csv(os.path.join(OUT, "14_StatsBomb_Match_Index.csv"), index=False, encoding=ENC)
    print("14 rows", len(mi))

    # ------------------------------------------------------------ extend 06 and 07
    teams = pd.read_csv(os.path.join(OUT, "06_Teams.csv"), low_memory=False, encoding=ENC)
    sbt = pd.concat([
        sbm[["sb_home_team_id", "home_team", "match_date", "competition_international"]].set_axis(
            ["tid", "tname", "match_date", "intl"], axis=1),
        sbm[["sb_away_team_id", "away_team", "match_date", "competition_international"]].set_axis(
            ["tid", "tname", "match_date", "intl"], axis=1)])
    gt = sbt.groupby("tid").agg(team_name=("tname", "first"), first_match_date=("match_date", "min"),
                                last_match_date=("match_date", "max"), n_match_records=("match_date", "size"),
                                intl=("intl", "max")).reset_index()
    gt["team_id"] = "SB:T" + gt.tid.astype(str)
    gt["team_type"] = ["national" if bool(x) else "club" for x in gt.intl]
    gt["source_repos"] = "statsbomb/open-data"
    gt["source_name"] = "StatsBomb Open Data"
    gt["source_url"] = SB_URL
    for c in teams.columns:
        if c not in gt.columns:
            gt[c] = pd.NA
    gt["name_match_key_hint"] = gt.team_name.map(lambda s: re.sub(r"\s+", " ", re.sub(
        r"\b(fc|cf|afc|sc|ac|ssc|sv|fk|cd|ud)\b|[^a-z0-9 ]", " ", norm(s))).strip())
    teams = teams[~teams.team_id.str.startswith("SB:T")]
    teams = pd.concat([teams, gt[teams.columns]], ignore_index=True)
    dupkey = teams.groupby("name_match_key_hint").team_id.transform("nunique")
    teams["same_name_key_as_other_team_ids"] = dupkey > 1
    teams.to_csv(os.path.join(OUT, "06_Teams.csv"), index=False, encoding=ENC)
    print("06 rows", len(teams))

    comp = pd.read_csv(os.path.join(OUT, "07_Competitions.csv"), low_memory=False, encoding=ENC)
    comp = comp[~comp.competition_id.astype(str).str.startswith("SB:")]
    cs = sbm.groupby(["sb_competition_id", "competition_name", "competition_country", "competition_gender",
                      "competition_international"]).agg(
        first_season=("season_name", "min"), last_season=("season_name", "max"), n_seasons=("sb_season_id", "nunique"),
        first_match_date=("match_date", "min"), last_match_date=("match_date", "max"),
        n_matches=("sb_match_id", "nunique")).reset_index()
    cs["competition_id"] = "SB:C" + cs.sb_competition_id.astype(str)
    cs["competition_name_variants"] = "gender=" + cs.competition_gender.astype(str)
    cs["record_scope"] = ["international (StatsBomb event-data subset)" if bool(x) else "club (StatsBomb event-data subset)"
                          for x in cs.competition_international]
    cs["competition_type"] = ["international_tournament" if bool(x) else "domestic_or_club_competition"
                              for x in cs.competition_international]
    cs["tier"] = pd.NA
    cs["country_or_region"] = cs.competition_country
    cs["n_scored"] = cs.n_matches
    cs["latest_scored_match_date"] = cs.last_match_date
    cs["source_name"] = "StatsBomb Open Data"
    cs["source_url"] = SB_URL
    comp = pd.concat([comp, cs[comp.columns]], ignore_index=True)
    comp.to_csv(os.path.join(OUT, "07_Competitions.csv"), index=False, encoding=ENC)
    print("07 rows", len(comp))


if __name__ == "__main__":
    main()
