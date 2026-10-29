"""Assemble datasets 01, 02, 03, 06, 07, 09 from the raw sources (no fabricated values).

Run: .venv\\Scripts\\python.exe -I FootIQ_Dataset_Submission\\_build\\assemble_matches.py
"""
import os
import re
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.dirname(ROOT)
RAW = os.path.join(ROOT, "_raw_sources")
WORK = os.path.join(HERE, "work")
OUT = ROOT
EXTRACTION_DATE = "2026-10-20"
CUTOFF_HISTORICAL = "2026-06-02"   # last scored date of the Milestone 1 baseline dataset
TODAY = "2026-10-20"
ENC = "utf-8-sig"

MARTJ = "https://github.com/martj42/international_results"
OPENF = "https://github.com/openfootball"


def slug(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def name_key(s):
    """Hint-only matching key (NOT an identity assertion)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|afc|sc|ac|ssc|sv|fk|cd|ud)\b|[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------ international
def build_international():
    base = os.path.join(RAW, "martj42_refresh")
    res = pd.read_csv(os.path.join(base, "results.csv"))
    sh = pd.read_csv(os.path.join(base, "shootouts.csv"))
    fn = pd.read_csv(os.path.join(base, "former_names.csv"))
    res["source_row_number"] = res.index + 2  # header is row 1
    n0 = len(res)
    sh = sh.rename(columns={"winner": "penalty_shootout_winner", "first_shooter": "penalty_shootout_first_shooter"})
    sh_dups = int(sh.duplicated(["date", "home_team", "away_team"]).sum())
    sh = sh.drop_duplicates(["date", "home_team", "away_team"], keep="first")
    df = res.merge(sh, on=["date", "home_team", "away_team"], how="left", validate="m:1")
    assert len(df) == n0
    # baseline comparison (local Milestone 1 raw file); China PR was renamed China upstream
    old = pd.read_csv(os.path.join(PROJECT, "data", "raw", "international_results", "results.csv"))
    fix = lambda s: s.replace({"China PR": "China"})  # noqa: E731
    old_keys = set(zip(old.date, fix(old.home_team), fix(old.away_team)))
    df["in_local_baseline"] = [(d, h, a) in old_keys for d, h, a in zip(df.date, fix(df.home_team), fix(df.away_team))]

    t = df["tournament"]
    cat = pd.Series("other_international_tournament", index=df.index)
    cat[t.str.contains("qualification", case=False)] = "qualification"
    cat[t.eq("FIFA World Cup qualification")] = "world_cup_qualification"
    cat[t.eq("FIFA World Cup")] = "world_cup_finals"
    cat[t.eq("Friendly")] = "friendly"
    cat[t.str.contains("Nations League", case=False) & ~t.str.contains("qualification", case=False)] = "nations_league"
    cont = ["UEFA Euro", "Copa Am", "African Cup of Nations", "AFC Asian Cup", "Gold Cup", "Oceania Nations Cup",
            "CONCACAF Championship", "Confederations Cup", "Arab Cup", "Gulf Cup", "AFF Championship", "SAFF",
            "CECAFA", "COSAFA", "WAFF", "EAFF", "Pacific Games", "Island Games", "African Nations Championship"]
    pat = "|".join(cont)
    cat[t.str.contains(pat, case=False) & ~t.str.contains("qualification", case=False) & cat.eq("other_international_tournament")] = "continental_or_regional_tournament"
    df["competition_category"] = cat
    df["competition_id"] = "INTL:" + t.map(slug)
    df["home_team_id"] = "INT|" + df.home_team
    df["away_team_id"] = "INT|" + df.away_team
    hs, as_ = df.home_score.astype("Int64"), df.away_score.astype("Int64")
    df["home_score_incl_extra_time"] = hs
    df["away_score_incl_extra_time"] = as_
    df["result_incl_extra_time"] = [("H" if a > b else ("A" if a < b else "D")) if pd.notna(a) and pd.notna(b) else ""
                                    for a, b in zip(hs, as_)]
    df["decided_by_penalty_shootout"] = df.penalty_shootout_winner.notna()
    df["neutral_venue"] = df.neutral.astype(str).str.upper().map({"TRUE": True, "FALSE": False})
    df["match_id"] = ["INTL:" + d + ":" + slug(h) + ":" + slug(a) + ":r" + str(r)
                      for d, h, a, r in zip(df.date, df.home_team, df.away_team, df.source_row_number)]
    df["match_date"] = df["date"]
    df["scored"] = hs.notna() & as_.notna()
    df["source_name"] = "martj42/international_results (CC0-1.0)"
    df["source_url"] = MARTJ
    df["source_file"] = "results.csv + shootouts.csv"
    df["source_extraction_date"] = EXTRACTION_DATE
    df["score_basis"] = "full-time score including extra time, excluding penalty shootout; regulation/extra-time split not provided"
    cols = ["match_id", "match_date", "home_team_id", "home_team", "away_team_id", "away_team",
            "home_score_incl_extra_time", "away_score_incl_extra_time", "result_incl_extra_time",
            "decided_by_penalty_shootout", "penalty_shootout_winner", "penalty_shootout_first_shooter",
            "tournament", "competition_id", "competition_category", "city", "country", "neutral_venue",
            "score_basis", "in_local_baseline", "source_name", "source_url", "source_file", "source_row_number",
            "source_extraction_date"]
    stats = dict(n_source_rows=n0, shootout_duplicate_keys_dropped=sh_dups,
                 shootouts_unmatched=int(len(sh) - df.penalty_shootout_winner.notna().sum()),
                 unscored_rows=int((~df.scored).sum()))
    hist = df[df.scored & (df.match_date <= CUTOFF_HISTORICAL)][cols]
    recent = df[df.scored & (df.match_date > CUTOFF_HISTORICAL)]
    unscored = df[~df.scored]
    return hist, recent, unscored, fn, stats, df


# ------------------------------------------------------------------ club
CLUB_COLS = ["match_id", "match_date", "kickoff_time_local", "competition_id", "competition_name", "competition_type",
             "tier", "competition_country", "season", "stage", "group", "knockout_or_cup_round", "home_team_id",
             "home_team", "home_team_country_code", "away_team_id", "away_team", "away_team_country_code",
             "home_goals_regulation", "away_goals_regulation", "home_goals_after_extra_time",
             "away_goals_after_extra_time", "home_penalties", "away_penalties", "home_goals_halftime",
             "away_goals_halftime", "extra_time_played", "penalties_played", "result_regulation", "decided_in",
             "final_match_winner_side", "match_status", "status_note", "source_name", "source_repo",
             "source_repo_commit", "source_file", "source_line", "source_text"]


def load_club():
    d = pd.read_csv(os.path.join(WORK, "club_matches_all.csv"), low_memory=False, keep_default_na=False,
                    na_values=[""])
    for c in ["tier", "home_goals_regulation", "away_goals_regulation", "home_goals_after_extra_time",
              "away_goals_after_extra_time", "home_penalties", "away_penalties", "home_goals_halftime",
              "away_goals_halftime"]:
        d[c] = d[c].astype("Int64")
    return d


def main():
    hist_i, recent_i, unscored_i, former, istats, int_all = build_international()
    club = load_club()
    club["has_score"] = club.home_goals_regulation.notna() | club.home_goals_after_extra_time.notna() \
        | club.home_penalties.notna() | club.final_match_winner_side.ne("") & club.final_match_winner_side.notna()
    # main score is stored in regulation unless AET/pen; guard for single-paren AET rows where regulation is unknown
    scored_status = club.match_status.isin(["completed", "awarded", "abandoned"]) & club.final_match_winner_side.notna()
    club["is_scored"] = scored_status
    club["match_date_dt"] = pd.to_datetime(club.match_date)
    hist_c = club[club.is_scored & (club.match_date <= CUTOFF_HISTORICAL)]
    recent_c = club[club.is_scored & (club.match_date > CUTOFF_HISTORICAL) & (club.match_date <= TODAY)]
    future_scored = club[club.is_scored & (club.match_date > TODAY)]
    fixtures_c = club[(club.match_status.isin(["unscored", "postponed"])) &
                      (club.match_date > CUTOFF_HISTORICAL)]
    fixtures_c = fixtures_c.assign(fixture_status=[
        "upcoming" if d > TODAY else "past_date_no_result_in_source" for d in fixtures_c.match_date])
    qa_nonstandard = club[~club.is_scored & ~club.index.isin(fixtures_c.index)]
    hist_unscored = club[(club.match_status.isin(["unscored", "postponed"])) & (club.match_date <= CUTOFF_HISTORICAL)]
    print("club scored hist/recent/future_scored:", len(hist_c), len(recent_c), len(future_scored))
    print("fixtures:", len(fixtures_c), " other non-scored:", len(qa_nonstandard), " hist unscored:", len(hist_unscored))

    # 01
    hist_i.to_csv(os.path.join(OUT, "01_Historical_International_Matches.csv"), index=False, encoding=ENC)
    # 02
    hist_c[CLUB_COLS].to_csv(os.path.join(OUT, "02_Historical_Club_Matches.csv"), index=False, encoding=ENC)

    # 03: union schema
    ic = recent_i.copy()
    ic["record_scope"] = "international"
    ic["competition_name"] = ic.tournament
    ic["competition_type"] = ic.competition_category
    ic["season"] = ic.match_date.str[:4]
    ic["competition_country"] = ic.country
    ic["final_match_winner_side"] = ic.result_incl_extra_time.map({"H": "home", "A": "away", "D": "draw"})
    # a shootout winner decides the tie; record it explicitly without inventing a score
    sw = [("home" if w == h else ("away" if w == a else "")) if isinstance(w, str) else ""
          for w, h, a in zip(ic.penalty_shootout_winner, ic.home_team, ic.away_team)]
    ic["penalty_shootout_winner_side"] = sw
    ic.loc[ic.penalty_shootout_winner_side.ne(""), "final_match_winner_side"] = ic.penalty_shootout_winner_side
    ic["decided_in"] = ["penalties" if p else "not_distinguished_regulation_or_extra_time"
                        for p in ic.decided_by_penalty_shootout]
    ic["match_status"] = "completed"
    cc = recent_c.copy()
    cc["record_scope"] = "club"
    cc["competition_name"] = cc.competition_name
    cc["home_score_incl_extra_time"] = pd.NA
    cc["away_score_incl_extra_time"] = pd.NA
    rec_cols = ["record_scope", "match_id", "match_date", "competition_id", "competition_name", "competition_type",
                "competition_country", "season", "stage", "home_team_id", "home_team", "away_team_id", "away_team",
                "home_goals_regulation", "away_goals_regulation", "home_score_incl_extra_time",
                "away_score_incl_extra_time", "home_goals_after_extra_time", "away_goals_after_extra_time",
                "home_penalties", "away_penalties", "penalty_shootout_winner_side", "extra_time_played",
                "result_regulation", "decided_in", "final_match_winner_side", "match_status", "source_name",
                "source_url", "source_file", "source_line_or_row", "source_extraction_date"]
    for df_, kind in ((ic, "intl"), (cc, "club")):
        df_["source_extraction_date"] = EXTRACTION_DATE
    ic["source_line_or_row"] = ic.source_row_number
    cc["source_line_or_row"] = cc.source_line
    cc["source_url"] = OPENF + "/" + cc.source_repo
    cc["penalty_shootout_winner_side"] = [("home" if (h or 0) > (a or 0) else "away") if pd.notna(h) else ""
                                          for h, a in zip(cc.home_penalties, cc.away_penalties)]
    for c in rec_cols:
        for df_ in (ic, cc):
            if c not in df_.columns:
                df_[c] = pd.NA
    recent = pd.concat([ic[rec_cols], cc[rec_cols]], ignore_index=True).sort_values(["match_date", "record_scope", "match_id"])
    recent.to_csv(os.path.join(OUT, "03_Recent_Match_Results.csv"), index=False, encoding=ENC)

    # 09
    fx = fixtures_c.copy()
    fx_cols = ["match_id", "match_date", "kickoff_time_local", "fixture_status", "match_status", "competition_id",
               "competition_name", "competition_type", "competition_country", "season", "stage", "home_team_id",
               "home_team", "away_team_id", "away_team", "source_name", "source_repo", "source_repo_commit",
               "source_file", "source_line", "status_note"]
    fx[fx_cols].sort_values(["match_date", "competition_id"]).to_csv(
        os.path.join(OUT, "09_Upcoming_Fixtures.csv"), index=False, encoding=ENC)

    # QA extras
    qa_dir = os.path.join(OUT, "QA_Reports")
    os.makedirs(qa_dir, exist_ok=True)
    pd.concat([qa_nonstandard, hist_unscored])[CLUB_COLS].to_csv(
        os.path.join(qa_dir, "QA_Club_Records_Not_Scored_Or_Nonstandard.csv"), index=False, encoding=ENC)
    future_scored[CLUB_COLS].to_csv(os.path.join(qa_dir, "QA_Club_Scored_After_20261020.csv"), index=False, encoding=ENC)

    # 06 Teams
    parts = []
    allc = club[club.is_scored | club.match_status.isin(["unscored", "postponed"])]
    for side in ("home", "away"):
        x = allc[[f"{side}_team_id", f"{side}_team", f"{side}_team_country_code", "competition_id",
                  "competition_country", "competition_type", "match_date", "source_repo"]].copy()
        x.columns = ["team_id", "team_name", "team_country_code", "competition_id", "competition_country",
                     "competition_type", "match_date", "source_repo"]
        parts.append(x)
    ca = pd.concat(parts)
    ca_played = ca
    g = ca_played.groupby("team_id")
    tc = g.agg(team_name=("team_name", lambda s: s.mode().iat[0]),
               team_name_variants_in_source=("team_name", lambda s: "; ".join(sorted(set(s))[:5])),
               team_country_code=("team_country_code", lambda s: next((v for v in s if isinstance(v, str) and v), "")),
               competition_countries=("competition_country", lambda s: "; ".join(sorted(set(s))[:6])),
               n_competitions=("competition_id", "nunique"),
               first_match_date=("match_date", "min"), last_match_date=("match_date", "max"),
               n_match_records=("match_date", "size"),
               source_repos=("source_repo", lambda s: "; ".join(sorted(set(s))))).reset_index()
    tc["team_type"] = "club"
    tc["former_names"] = ""
    tc["source_name"] = "openfootball (CC0 / public domain)"
    tc["source_url"] = OPENF
    # national teams
    ia = pd.concat([int_all[["home_team", "match_date"]].rename(columns={"home_team": "team_name"}),
                    int_all[["away_team", "match_date"]].rename(columns={"away_team": "team_name"})])
    gi = ia.groupby("team_name").agg(first_match_date=("match_date", "min"), last_match_date=("match_date", "max"),
                                     n_match_records=("match_date", "size")).reset_index()
    gi["team_id"] = "INT|" + gi.team_name
    gi["team_name_variants_in_source"] = gi.team_name
    gi["team_country_code"] = ""
    gi["competition_countries"] = ""
    gi["n_competitions"] = gi.team_name.map(
        pd.concat([int_all[["home_team", "tournament"]].rename(columns={"home_team": "t"}),
                   int_all[["away_team", "tournament"]].rename(columns={"away_team": "t"})]).groupby("t").tournament.nunique())
    gi["team_type"] = "national"
    fmap = former.groupby("current")["former"].apply(lambda s: "; ".join(s)).to_dict()
    gi["former_names"] = gi.team_name.map(fmap).fillna("")
    gi["source_repos"] = "martj42/international_results"
    gi["source_name"] = "martj42/international_results (CC0-1.0)"
    gi["source_url"] = MARTJ
    teams = pd.concat([gi, tc], ignore_index=True)
    teams["name_match_key_hint"] = teams.team_name.map(name_key)
    dupkey = teams.groupby("name_match_key_hint").team_id.transform("nunique")
    teams["same_name_key_as_other_team_ids"] = (dupkey > 1)
    teams = teams[["team_id", "team_name", "team_type", "team_country_code", "former_names",
                   "team_name_variants_in_source", "competition_countries", "n_competitions", "first_match_date",
                   "last_match_date", "n_match_records", "name_match_key_hint", "same_name_key_as_other_team_ids",
                   "source_repos", "source_name", "source_url"]]
    teams.to_csv(os.path.join(OUT, "06_Teams.csv"), index=False, encoding=ENC)

    # 07 Competitions
    ci = int_all.groupby(["competition_id", "tournament", "competition_category"]).agg(
        first_match_date=("match_date", "min"), last_match_date=("match_date", "max"),
        n_matches=("match_date", "size"),
        n_seasons=("match_date", lambda s: s.str[:4].nunique())).reset_index()
    ci["competition_name"] = ci.tournament
    ci["record_scope"] = "international"
    ci["competition_type"] = ci.competition_category
    ci["country_or_region"] = "FIFA national teams"
    ci["tier"] = pd.NA
    ci["first_season"] = ci.first_match_date.str[:4]
    ci["last_season"] = ci.last_match_date.str[:4]
    ci["source_name"] = "martj42/international_results (CC0-1.0)"
    ci["source_url"] = MARTJ
    cm = club[club.is_scored | club.match_status.isin(["unscored", "postponed"])].copy()
    cm["scored_date"] = cm.match_date.where(cm.is_scored, "")
    cc2 = cm.groupby(["competition_id"]).agg(
        competition_name=("competition_name", lambda s: s.mode().iat[0]),
        competition_name_variants=("competition_name_source", lambda s: "; ".join(sorted(set(map(str, s)))[:4])),
        competition_type=("competition_type", "first"), tier=("tier", "first"),
        country_or_region=("competition_country", "first"),
        first_match_date=("match_date", "min"), last_match_date=("match_date", "max"),
        n_matches=("match_date", "size"), n_seasons=("season", "nunique"),
        n_scored=("is_scored", "sum"), latest_scored_match_date=("scored_date", "max"),
        first_season=("season", "min"), last_season=("season", "max"),
        source_name=("source_name", "first"), source_repo=("source_repo", "first")).reset_index()
    cc2["latest_scored_match_date"] = cc2.latest_scored_match_date.replace("", pd.NA)
    cc2["record_scope"] = "club"
    cc2["source_url"] = OPENF + "/" + cc2.source_repo
    cc2["tournament"] = cc2.competition_name
    cc2["competition_category"] = cc2.competition_type
    ci["competition_name_variants"] = ""
    ci["n_scored"] = ci.n_matches
    ci["latest_scored_match_date"] = ci.last_match_date
    comp = pd.concat([ci, cc2], ignore_index=True)
    comp = comp[["competition_id", "competition_name", "competition_name_variants", "record_scope",
                 "competition_type", "tier", "country_or_region", "first_season", "last_season", "n_seasons",
                 "first_match_date", "last_match_date", "n_matches", "n_scored", "latest_scored_match_date",
                 "source_name", "source_url"]]
    comp.to_csv(os.path.join(OUT, "07_Competitions.csv"), index=False, encoding=ENC)
    pd.Series(istats).to_csv(os.path.join(WORK, "international_stats.csv"), header=False)
    print(istats)
    print("01:", len(hist_i), "02:", len(hist_c), "03:", len(recent), "06:", len(teams), "07:", len(comp), "09:", len(fx))


if __name__ == "__main__":
    main()
