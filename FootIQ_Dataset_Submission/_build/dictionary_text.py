"""Column descriptions and per-dataset metadata used by validate_and_document.py."""

SRC_MARTJ = "https://github.com/martj42/international_results"
SRC_OF = "https://github.com/openfootball (england, espana, deutschland, italy, champions-league, europe, club-worldcup, austria, belgium, south-america, world)"
SRC_SB = "https://github.com/statsbomb/open-data"

DATASETS = {
    "01": dict(date_col="match_date", comp_col="competition_id", country_col="country", season_col=None,
               key=["match_date", "home_team", "away_team"], sources=SRC_MARTJ,
               legal="CONFIRMED: CC0-1.0 public-domain dedication (analytics and ML permitted).",
               limits="Men's full internationals only. Score includes extra time and excludes penalty shootouts; regulation vs extra-time cannot be separated. Historic team names are kept as published (e.g. Czechoslovakia, Yugoslavia, Zaire); former_names mapping is in 06_Teams.csv, teams are not merged. Cut-off 2026-06-02 mirrors the Milestone 1 baseline; later matches are in 03. Upstream differs from the local baseline snapshot (see in_local_baseline)."),
    "02": dict(date_col="match_date", comp_col="competition_id", country_col="competition_country", season_col="season",
               key=["competition_id", "season", "match_date", "home_team_id", "away_team_id", "stage"], sources=SRC_OF,
               legal="CONFIRMED: openfootball repositories carry CC0 1.0 Universal (LICENSE.md checked per repository).",
               limits="Coverage differs per competition/season (see 07_Competitions.csv). England 1888-present, Spain from 2012-13, Germany from 2010-11, Italy from 2013-14, Champions League/Europa/Conference from 2011-12, France from 2014-15, many other countries only from the 2010s; top-5 league seasons before those years are NOT included. 2025-26 season files for several leagues and lower tiers are incomplete (scheduled matches without results are listed in QA_Reports). Kick-off times are local times as published. Penalty-only results do not always state whether extra time was played (extra_time_played=unknown). Two-legged tie aggregates and knockout advancement are not provided by the source and are not derived."),
    "03": dict(date_col="match_date", comp_col="competition_id", country_col="competition_country", season_col="season",
               key=["match_id"], sources=SRC_MARTJ + " ; " + SRC_OF,
               legal="CONFIRMED: CC0 for both sources.",
               limits="Window 2026-06-03 to 2026-10-20 (day after the baseline cut-off to extraction date). Latest international match in source is 2026-10-06; latest club result per competition is in 07_Competitions.csv (latest_scored_match_date) - many competitions end earlier. International rows have only an extra-time-inclusive score; club rows follow the 02 score semantics. Unfinished/unscored matches are in 09."),
    "04": dict(date_col="last_seen_date", comp_col=None, country_col="nationality", season_col=None,
               key=["player_id"], sources=SRC_SB + " ; " + SRC_OF,
               legal="StatsBomb: research use with attribution (commercial/other use NOT confirmed). openfootball: CC0.",
               limits="No single global player identity: StatsBomb players use the source player ID; openfootball lineup and squad players only have name-based keys scoped to team (and season/squad), so the same real person appears under several IDs and common names are NOT merged. Nationality/position/birth data exist only where the source lists them; birth_text is a year or date string as published. No market value, height, or club-career history."),
    "05": dict(date_col="match_date", comp_col="competition_name", country_col=None, season_col="season",
               key=["match_id", "player_id", "team_id"], sources=SRC_SB + " ; " + SRC_OF,
               legal="Mixed: StatsBomb rows = research/educational use with attribution; openfootball rows = CC0. Treat the whole file as research use unless source rows are filtered.",
               limits="Event-based metrics (shots, passes, tackles, xG...) exist ONLY for StatsBomb open-data competitions (selected men's and women's seasons, e.g. La Liga 2004-2020 Messi seasons, Premier League 2015-16, World Cups, Euros, Champions League finals). openfootball rows cover appearances, estimated minutes, goals and cards only for 2025-26 PL/La Liga/Bundesliga/Serie A/Ligue 1/Austrian Bundesliga and Club World Cup 2000-2025; their stat columns are intentionally blank, not zero. No stats exist for the other competitions."),
    "06": dict(date_col="last_match_date", comp_col=None, country_col="team_country_code", season_col=None,
               key=["team_id"], sources=SRC_MARTJ + " ; " + SRC_OF + " ; " + SRC_SB,
               legal="CC0 sources; StatsBomb team names are research-use.",
               limits="Team IDs are source-scoped: exact name within the source/country namespace. The same real club can have several IDs (different name spellings or sources); same_name_key_as_other_team_ids / name_match_key_hint flag candidates for later manual entity resolution but no merge was performed. No stadium/city/founding data attached."),
    "07": dict(date_col="last_match_date", comp_col="competition_id", country_col="country_or_region", season_col="last_season",
               key=["competition_id"], sources=SRC_MARTJ + " ; " + SRC_OF + " ; " + SRC_SB,
               legal="CC0 sources; StatsBomb competitions are research-use.",
               limits="One row per competition across all seasons; competition_name standardised for major competitions, otherwise taken from the source file title. Competition IDs are source-scoped (a league renamed by the source keeps the same ID only if the file code is stable)."),
    "08": dict(date_col="last_match_date", comp_col="competition_or_event", country_col=None, season_col="season",
               key=["player_id", "team_id", "competition_or_event", "season", "membership_basis"], sources=SRC_SB + " ; " + SRC_OF,
               legal="StatsBomb: research use with attribution. openfootball: CC0.",
               limits="Memberships are evidenced either by appearing in a match lineup (dates and counts known) or by being listed in a published squad (no match dates). Club-career histories across seasons are not reconstructed; the same person under different keys is not linked."),
    "09": dict(date_col="match_date", comp_col="competition_id", country_col="competition_country", season_col="season",
               key=["match_id"], sources=SRC_OF,
               legal="CONFIRMED: CC0.",
               limits="Club fixtures only; the international source has no unscored fixtures after 2026-10-06. fixture_status 'past_date_no_result_in_source' marks scheduled matches dated after 2026-06-02 up to 2026-10-20 that the source has no result for (not necessarily unplayed). Postponed fixtures keep their original date."),
    "14": dict(date_col="match_date", comp_col="competition_name", country_col="competition_country", season_col="season_name",
               key=["match_id"], sources=SRC_SB,
               legal="Research use with attribution (StatsBomb README); commercial use not confirmed.",
               limits="Supplementary index of the 3,961 StatsBomb matches referenced by 05 (SB:M... match IDs). Includes women's and youth competitions - see competition_gender / competition_youth."),
}

C = {}


def add(desc, *cols):
    for c in cols:
        C[c] = desc


add("Dataset-unique match identifier. 01: INTL:date:home:away:source row. 02/03/09 club: competition_id:season:L<line number in source file>. SB:M<id> = StatsBomb match ID.", "match_id")
add("Match date (ISO YYYY-MM-DD) as published; local calendar date for club matches.", "match_date")
add("Team identifier scoped to its source: INT|name (national team name as published), <country code>|name (club), SB:T<StatsBomb team ID>. Same text in different sources is NOT guaranteed to be the same entity.", "team_id", "home_team_id", "away_team_id")
add("Team name exactly as written in the source (country-code suffix removed for clubs).", "home_team", "away_team", "team_name")
add("Home team score at full time including extra time, excluding penalty shootout (international source semantics).", "home_score_incl_extra_time")
add("Away team score at full time including extra time, excluding penalty shootout (international source semantics).", "away_score_incl_extra_time")
add("Result from the score including extra time: H home win, D draw, A away win.", "result_incl_extra_time")
add("True if the source lists a penalty shootout for this match.", "decided_by_penalty_shootout")
add("Winner of the penalty shootout as published (team name).", "penalty_shootout_winner")
add("Team that took the first penalty as published.", "penalty_shootout_first_shooter")
add("Tournament name exactly as published by the source.", "tournament")
add("Source-scoped competition identifier (INTL:<slug>, <repo>:<file code>, SB:C<id>).", "competition_id")
add("FootIQ category derived from tournament text: world_cup_finals, world_cup_qualification, qualification, nations_league, friendly, continental_or_regional_tournament, other_international_tournament.", "competition_category")
add("City of the venue as published.", "city")
add("Country where the match was played as published (international data).", "country")
add("True when the match was played at a neutral venue (source flag).", "neutral_venue")
add("Text explaining what the score columns mean for this source.", "score_basis")
add("True if the same (date, home, away) match exists in the local Milestone 1 baseline file data/raw/international_results/results.csv after mapping 'China PR' to 'China'.", "in_local_baseline")
add("Name of the upstream data source.", "source_name")
add("URL of the upstream source repository.", "source_url")
add("Source file(s) the record came from (relative path inside _raw_sources or upstream repo).", "source_file")
add("1-based row number in the upstream results.csv (header = row 1).", "source_row_number")
add("Date the data was downloaded/extracted for this package.", "source_extraction_date")
add("Clock time of kick-off in local time as published (no timezone conversion).", "kickoff_time_local")
add("Competition name (standardised for major competitions; otherwise source title without season).", "competition_name")
add("Competition type: domestic_league, domestic_cup, league_cup, continental_club, global_club (club data); world_cup_finals etc. (international); international_tournament / domestic_or_club_competition (StatsBomb).", "competition_type")
add("League tier (1 = top flight) where derivable from the file code; blank for cups.", "tier")
add("Country or confederation of the competition as derived from the source path (UEFA (Europe), CONMEBOL (South America), FIFA (World) for continental/global).", "competition_country")
add("Season label (e.g. 2024-25 or 2025). Taken from the file title when it disagrees with the folder name.", "season")
add("Stage/round text exactly as published (e.g. 'Matchday 12', 'Round 3', 'Quarterfinals').", "stage")
add("Group label if the source gives one.", "group")
add("True when the stage text suggests a cup/knockout/qualifying round (regex on stage text; heuristic).", "knockout_or_cup_round")
add("UEFA/FIFA style 3-letter country code printed after the club name in continental files, otherwise blank.", "home_team_country_code", "away_team_country_code")
add("Home goals in regulation time (90 min) when the source states or implies it; blank if not determinable (e.g. extra-time match with only one bracket value).", "home_goals_regulation")
add("Away goals in regulation time (90 min) when stated/implied; blank if not determinable.", "away_goals_regulation")
add("Home goals after extra time (only when extra time was played).", "home_goals_after_extra_time")
add("Away goals after extra time (only when extra time was played).", "away_goals_after_extra_time")
add("Home penalty shootout score.", "home_penalties")
add("Away penalty shootout score.", "away_penalties")
add("Home goals at half time when published.", "home_goals_halftime")
add("Away goals at half time when published.", "away_goals_halftime")
add("yes / no / unknown. unknown = decided on penalties but the source does not say whether extra time was played.", "extra_time_played")
add("yes if a shootout is recorded, no for scored matches without one.", "penalties_played")
add("Result after regulation time: H home win, D draw, A away win; blank if regulation score unknown.", "result_regulation")
add("How the match was decided: regulation, extra_time, penalties (club) or penalties / not_distinguished_regulation_or_extra_time (international).", "decided_in")
add("Winner of THIS match after all recorded phases (penalties > extra time > regulation): home, away, draw. This is the single-match outcome, NOT two-legged-tie advancement.", "final_match_winner_side")
add("completed, awarded, abandoned (scored), unscored, postponed or cancelled as flagged in the source text.", "match_status")
add("Free-text note from the source line (e.g. reason for award).", "status_note")
add("openfootball repository the file came from.", "source_repo")
add("Git commit (hash|commit date) of the cloned repository at download.", "source_repo_commit")
add("1-based line number of the match in the source file.", "source_line")
add("The original text line from the source file, kept for audit.", "source_text")
add("'international' or 'club'.", "record_scope")
add("Penalty shootout winner as home/away side (03).", "penalty_shootout_winner_side")
add("Row number in the source (international) or line number (club) - see source_file.", "source_line_or_row")
add("Player identifier. SB:P<id> is the native StatsBomb ID. OFP|<team_id>|<name> and SQD|... are derived keys scoped to team (and squad); they are NOT global identities.", "player_id")
add("Original ID in the source system (StatsBomb player_id).", "source_player_id")
add("Scope/quality of player_id: source_native_id_StatsBomb, derived_team_scoped_name_key, derived_squad_scoped_key.", "id_scope")
add("Player name as written in the source (may differ in casing/accents between sources).", "player_name")
add("Nickname from StatsBomb lineups when present.", "player_nickname")
add("Country of the player as given by StatsBomb lineups, or nationality code printed in squad files.", "nationality")
add("Nationality code in parentheses after the name in squad files (blank if absent).", "nationality_code_if_listed")
add("Most frequent first position (StatsBomb) or squad position code (GK/DF/MF/FW).", "position_primary")
add("Birth year/date text exactly as published in squad files; blank otherwise.", "birth_text")
add("Gender of the competition(s) where seen, from StatsBomb; openfootball sections are men's but the source does not state it.", "gender_context")
add("Earliest date the player is seen in a match record.", "first_seen_date")
add("Latest date the player is seen in a match record.", "last_seen_date")
add("Number of distinct matches with a lineup appearance.", "n_match_appearance_records")
add("Number of squad-list rows for the player key.", "n_squad_list_records")
add("Number of distinct teams the key is seen with.", "n_teams")
add("Dataset the record came from.", "source_dataset")
add("Row identifier for the player-match record.", "player_match_id")
add("True if match_id exists in 02 or 03 (openfootball rows linked to a match record).", "match_in_02_or_03")
add("StatsBomb competition gender (male/female) or note for openfootball.", "competition_gender")
add("Opponent team name.", "opponent_team_name")
add("True if in the starting XI.", "started")
add("Position played (StatsBomb first position); blank for openfootball.", "position")
add("True if captain ([c] in openfootball lineups).", "captain")
add("Minute (as published) the player came on; blank for starters.", "substituted_in_minute")
add("Minute (as published) the player was replaced; blank if not replaced.", "substituted_out_minute")
add("Minutes played. StatsBomb: from lineup position intervals. openfootball: ESTIMATE from substitution/red-card minutes (see minutes_basis).", "minutes_played")
add("How minutes_played was obtained.", "minutes_basis")
add("Goals scored (excluding own goals and shootout kicks).", "goals")
add("Assists as defined by StatsBomb (pass.goal_assist). Blank for openfootball.", "assists")
add("Own goals scored by the player.", "own_goals")
add("Goals scored from penalties.", "penalty_goals")
add("Shots excluding shootout kicks (StatsBomb).", "shots")
add("Shots with outcome Goal, Saved or Saved to Post (StatsBomb).", "shots_on_target")
add("Sum of StatsBomb statsbomb_xg of the player's shots.", "xg")
add("Pass attempts (StatsBomb).", "passes")
add("Passes without an outcome flag, i.e. completed (StatsBomb).", "passes_completed")
add("Passes flagged shot_assist (StatsBomb).", "key_passes")
add("Passes flagged cross.", "crosses")
add("Duels of type Tackle.", "tackles")
add("Tackles with outcome Won / Success In Play / Success Out.", "tackles_won")
add("Interception events.", "interceptions")
add("Clearance events.", "clearances")
add("Block events.", "blocks")
add("Ball Recovery events not flagged as failures.", "ball_recoveries")
add("Dribble attempts.", "dribbles")
add("Dribbles with outcome Complete.", "dribbles_completed")
add("Foul Committed events.", "fouls_committed")
add("Foul Won events.", "fouls_won")
add("Pressure events.", "pressures")
add("All Duel events.", "duels")
add("Duels with outcome Won / Success.", "duels_won")
add("Dispossessed events.", "dispossessed")
add("Miscontrol events.", "miscontrols")
add("Carry events.", "carries")
add("Offside events.", "offsides")
add("Goalkeeper saves (Shot Saved variants).", "gk_saves")
add("Goalkeeper Goal Conceded events.", "gk_goals_conceded")
add("Yellow cards (incl. second yellow) from lineup/lineup-text.", "yellow_cards")
add("Red cards (incl. second yellow dismissals).", "red_cards")
add("event_level_full (StatsBomb events), lineup_only (StatsBomb without events), appearance_goals_cards_only (openfootball).", "stats_coverage")
add("Pointer to the source file/line the record was derived from.", "source_reference")
add("player or team type of the membership: national or club. For team table: club or national.", "team_type")
add("Alternative former names of the national team (former_names.csv, current name -> former names).", "former_names")
add("All distinct spellings seen in the source (up to 5).", "team_name_variants_in_source")
add("Countries of the competitions the team appears in (up to 6).", "competition_countries")
add("Number of distinct competitions the team appears in.", "n_competitions")
add("First match date for the team in this package.", "first_match_date")
add("Last match date for the team in this package.", "last_match_date")
add("Number of match records mentioning the team.", "n_match_records")
add("Lower-cased, punctuation/club-form-stripped name. A HINT for manual entity resolution only; not an identity assertion.", "name_match_key_hint")
add("True when another team_id shares the same name_match_key_hint (candidate duplicate across sources); no merge applied.", "same_name_key_as_other_team_ids")
add("Source repositories contributing the team.", "source_repos")
add("Alternative spellings of the competition name in source titles.", "competition_name_variants")
add("International/club/StatsBomb subset scope of the competition.", "competition_scope")
add("Country or region of the competition.", "country_or_region")
add("First season covered.", "first_season")
add("Last season covered.", "last_season")
add("Number of distinct seasons.", "n_seasons")
add("Number of match records (scored + unscored) for the competition.", "n_matches")
add("Number of scored match records.", "n_scored")
add("Latest match date with a recorded score in the source.", "latest_scored_match_date")
add("Row identifier for the membership.", "membership_id")
add("Reminder of how reliable player_id is as an identity.", "id_scope_note")
add("Competition (or squad event) name.", "competition_or_event")
add("appeared_in_match_lineup or listed_in_published_squad.", "membership_basis")
add("Number of matches with a lineup appearance.", "n_matches")
add("Sum of minutes_played (blank for squad lists).", "minutes_total")
add("Shirt number from squad files.", "shirt_number")
add("Position code from squad files.", "position_text")
add("Caps recorded before the event (national-team squad files).", "caps_before_event")
add("Last column of the squad row (previous/current club as printed, interpretation depends on file type).", "listed_club_text")
add("fixture status: upcoming (dated after 2026-10-20) or past_date_no_result_in_source.", "fixture_status")
add("StatsBomb match ID.", "sb_match_id")
add("Kick-off time from StatsBomb.", "kick_off")
add("StatsBomb competition ID.", "sb_competition_id")
add("StatsBomb season ID.", "sb_season_id")
add("StatsBomb season name.", "season_name")
add("StatsBomb youth competition flag.", "competition_youth")
add("StatsBomb international competition flag.", "competition_international")
add("Home score from StatsBomb match metadata.", "home_score")
add("Away score from StatsBomb match metadata.", "away_score")
add("Match week from StatsBomb.", "match_week")
add("Stadium name from StatsBomb.", "stadium")
add("StatsBomb data version.", "data_version")
add("Whether lineup and event files were available for this match.", "lineup_event_files_status")

DICT = C

C["team_country_code"] = "Country code printed after the club name in continental competition files (e.g. ENG); blank when the source gives none."
