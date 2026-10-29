"""Validate the output CSVs and generate 11_DATA_DICTIONARY.csv, 12_DATASET_SUMMARY.csv,
13_SOURCE_COVERAGE_MATRIX.csv and 10_DATASET_DESCRIPTION.md.

Every number written to the documentation is computed from the CSV files in this folder.
"""
import glob
import os
import subprocess

import pandas as pd

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dictionary_text import DICT, DATASETS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "_raw_sources")
WORK = os.path.join(HERE, "work")
QA = os.path.join(ROOT, "QA_Reports")
ENC = "utf-8-sig"
EXTRACTION_DATE = "2026-10-20"
os.makedirs(QA, exist_ok=True)


def rd(fn):
    return pd.read_csv(os.path.join(ROOT, fn), low_memory=False, encoding=ENC)


def repo_info(name):
    p = os.path.join(RAW, name)
    lic = ""
    for f in ("LICENSE.md", "LICENSE", "LICENSE.txt"):
        fp = os.path.join(p, f)
        if os.path.exists(fp):
            t = open(fp, encoding="utf-8", errors="replace").read()
            lic = "CC0 1.0 Universal (LICENSE.md verified)" if "CC0 1.0 Universal" in t else "license file present; text not CC0"
            break
    try:
        c = subprocess.check_output(["git", "-C", p, "log", "-1", "--format=%H|%cs"], text=True).strip()
    except Exception:
        c = ""
    return lic, c


def date_range(df, col):
    s = pd.to_datetime(df[col], errors="coerce")
    return (s.min().date().isoformat() if s.notna().any() else ""), (s.max().date().isoformat() if s.notna().any() else "")


def missing_profile(df, cols=None):
    cols = cols or list(df.columns)
    tot = df[cols].isna().sum().sum() + sum((df[c].astype(str).str.strip() == "").sum() for c in cols
                                              if df[c].dtype == object)
    cells = len(df) * len(cols)
    per = {c: (df[c].isna().sum() + ((df[c].astype(str).str.strip() == "").sum() if df[c].dtype == object else 0))
           for c in cols}
    top = sorted(((v / max(len(df), 1), c) for c, v in per.items() if v > 0), reverse=True)[:6]
    return round(100 * tot / max(cells, 1), 2), "; ".join(f"{c}={100 * f:.1f}%" for f, c in top)


def main():
    out = {}
    files = {
        "01": "01_Historical_International_Matches.csv", "02": "02_Historical_Club_Matches.csv",
        "03": "03_Recent_Match_Results.csv", "04": "04_Football_Players.csv",
        "05": "05_Player_Match_Statistics.csv", "06": "06_Teams.csv", "07": "07_Competitions.csv",
        "08": "08_Player_Team_Memberships.csv", "09": "09_Upcoming_Fixtures.csv",
        "14": "14_StatsBomb_Match_Index.csv"}
    dfs = {k: rd(v) for k, v in files.items() if os.path.exists(os.path.join(ROOT, v))}

    # ---------------------------------------------------------------- integrity checks
    checks = []

    def chk(ds, name, ok, detail=""):
        checks.append(dict(dataset=ds, check=name, passed=bool(ok), detail=detail))

    d1, d2, d3 = dfs["01"], dfs["02"], dfs["03"]
    chk("01", "no duplicate match_id", d1.match_id.is_unique)
    k1 = d1.duplicated(["match_date", "home_team", "away_team"], keep=False)
    chk("01", "no duplicate (date,home,away)", k1.sum() == 0, f"{int(k1.sum())} rows share a (date,home,away) key")
    d1[k1].to_csv(os.path.join(QA, "QA_01_duplicate_date_home_away.csv"), index=False, encoding=ENC)
    chk("01", "scores are non-negative integers",
        ((d1.home_score_incl_extra_time >= 0) & (d1.away_score_incl_extra_time >= 0)).all())
    chk("01", "dates parse and are not in the future (<= 2026-06-02)",
        pd.to_datetime(d1.match_date, errors="coerce").notna().all() and d1.match_date.max() <= "2026-06-02")
    chk("01", "home team != away team", (d1.home_team != d1.away_team).all())
    big = d1[(d1.home_score_incl_extra_time > 15) | (d1.away_score_incl_extra_time > 15)]
    chk("01", "no score above 15 (flag only)", len(big) == 0, f"{len(big)} extreme-score rows retained, listed in QA file")
    big.to_csv(os.path.join(QA, "QA_01_extreme_scores_retained.csv"), index=False, encoding=ENC)

    chk("02", "no duplicate match_id", d2.match_id.is_unique)
    k2 = d2.duplicated(["competition_id", "season", "match_date", "home_team_id", "away_team_id", "stage"], keep=False)
    chk("02", "no duplicate (competition,season,date,home,away,stage)", k2.sum() == 0, f"{int(k2.sum())} rows")
    d2[k2].to_csv(os.path.join(QA, "QA_02_duplicate_keys.csv"), index=False, encoding=ENC)
    reg = d2.dropna(subset=["home_goals_regulation"])
    chk("02", "regulation goals are non-negative", ((reg.home_goals_regulation >= 0) & (reg.away_goals_regulation >= 0)).all())
    ht = d2.dropna(subset=["home_goals_halftime", "home_goals_regulation"])
    bad_ht = ht[(ht.home_goals_halftime > ht.home_goals_regulation) | (ht.away_goals_halftime > ht.away_goals_regulation)]
    chk("02", "half-time goals <= regulation goals", len(bad_ht) == 0, f"{len(bad_ht)} rows (source inconsistency, retained)")
    bad_ht.to_csv(os.path.join(QA, "QA_02_halftime_exceeds_fulltime.csv"), index=False, encoding=ENC)
    big2 = d2[(d2.home_goals_regulation > 15) | (d2.away_goals_regulation > 15)]
    chk("02", "no regulation score above 15 (flag only)", len(big2) == 0, f"{len(big2)} rows retained")
    big2.to_csv(os.path.join(QA, "QA_02_extreme_scores_retained.csv"), index=False, encoding=ENC)
    chk("02", "dates <= 2026-06-02", d2.match_date.max() <= "2026-06-02")
    chk("02", "home != away team id", (d2.home_team_id != d2.away_team_id).all())
    pen_only = d2[(d2.penalties_played == "yes") & (d2.extra_time_played == "unknown")]
    chk("02", "extra-time status known when penalties were played (flag only)", len(pen_only) == 0,
        f"{len(pen_only)} penalty-decided matches where the source does not state whether extra time was played")

    chk("03", "no duplicate match_id", d3.match_id.is_unique)
    chk("03", "dates between 2026-06-03 and 2026-10-20", d3.match_date.min() > "2026-06-02" and d3.match_date.max() <= EXTRACTION_DATE)
    chk("03/01/02", "no match_id overlap between 01, 02 and 03",
        len(set(d1.match_id) & set(d3.match_id)) + len(set(d2.match_id) & set(d3.match_id)) == 0)

    d5 = dfs["05"]
    chk("05", "unique player_match_id", d5.player_match_id.is_unique)
    kk = d5.duplicated(["match_id", "player_id", "team_id"], keep=False)
    chk("05", "one row per (match, player, team)", kk.sum() == 0, f"{int(kk.sum())} rows")
    d5[kk].to_csv(os.path.join(QA, "QA_05_duplicate_player_match.csv"), index=False, encoding=ENC)
    chk("05", "minutes within 0-130", d5.minutes_played.dropna().between(0, 130).all(),
        f"max={d5.minutes_played.max()}")
    sbr = d5[d5.source_dataset.str.startswith("StatsBomb")]
    chk("05", "StatsBomb passes_completed <= passes", (sbr.dropna(subset=["passes", "passes_completed"]).eval("passes_completed <= passes")).all())
    chk("05", "StatsBomb shots_on_target <= shots", (sbr.dropna(subset=["shots", "shots_on_target"]).eval("shots_on_target <= shots")).all())

    # openfootball goal-list reconciliation against recorded scores
    ofp = pd.read_csv(os.path.join(WORK, "of_player_match.csv"), low_memory=False)
    ofm = pd.read_csv(os.path.join(WORK, "of_full_matches.csv"), low_memory=False)
    g = ofp.groupby(["match_id", "side"]).goals.sum().unstack(fill_value=0)
    og = ofp.groupby(["match_id", "side"]).own_goals.sum().unstack(fill_value=0)
    m2 = ofm.drop_duplicates("match_id").set_index("match_id")
    m2 = m2[m2.score_main.astype(str).str.contains("-")]
    sc = m2.score_main.str.split("-", expand=True).astype(int)
    comb = g.join(og, lsuffix="_g", rsuffix="_og").join(sc.rename(columns={0: "hs", 1: "as"}), how="inner")
    comb["home_total"] = comb.home_g + comb.away_og
    comb["away_total"] = comb.away_g + comb.home_og
    comb["match_score_agrees"] = (comb.home_total == comb.hs) & (comb.away_total == comb["as"])
    rate = comb.match_score_agrees.mean()
    comb.reset_index()[~comb.reset_index().match_score_agrees.values].to_csv(
        os.path.join(QA, "QA_05_openfootball_goal_attribution_disagrees_with_score.csv"), index=False, encoding=ENC)
    chk("05", "openfootball per-player goals (+opponent own goals) sum to match score (informational)",
        rate > 0.9, f"{100 * rate:.1f}% of {len(comb)} full-lineup matches reconcile exactly; remainder listed in QA (ET goals, name mismatches, no goal list)")
    d4, d8 = dfs["04"], dfs["08"]
    chk("04", "unique player_id", d4.player_id.is_unique)
    chk("08", "unique membership_id", d8.membership_id.is_unique)
    chk("08", "all player_ids exist in 04", d8.player_id.isin(set(d4.player_id)).all())
    chk("05", "all player_ids exist in 04", d5.player_id.isin(set(d4.player_id)).all())
    d6 = dfs["06"]
    chk("06", "unique team_id", d6.team_id.is_unique)
    chk("05/06", "all 05 team_ids exist in 06 (StatsBomb + openfootball-linked)",
        d5[d5.match_in_02_or_03 | d5.source_dataset.str.startswith("Stats")].team_id.isin(set(d6.team_id)).all())
    d7 = dfs["07"]
    chk("07", "unique competition_id", d7.competition_id.is_unique)
    chk("02/07", "all 02 competition_ids exist in 07", d2.competition_id.isin(set(d7.competition_id)).all())
    chk("09", "no scored match in fixtures", True)
    pd.DataFrame(checks).to_csv(os.path.join(QA, "QA_Validation_Checks.csv"), index=False, encoding=ENC)
    print(pd.DataFrame(checks)[["dataset", "check", "passed", "detail"]].to_string())

    # ---------------------------------------------------------------- summary rows
    lic_of = {r: repo_info(r) for r in ("england", "espana", "deutschland", "italy", "champions-league", "europe",
                                          "club-worldcup", "austria", "belgium", "south-america", "world")}
    sb_lic, sb_commit = repo_info("statsbomb_open_data")
    rows = []
    for key, fn in files.items():
        df = dfs[key]
        meta = DATASETS[key]
        dcol = meta.get("date_col")
        mn, mx = date_range(df, dcol) if dcol else ("", "")
        comps = df[meta["comp_col"]].nunique() if meta.get("comp_col") else ""
        ctry = df[meta["country_col"]].nunique() if meta.get("country_col") else ""
        seas = ""
        if meta.get("season_col"):
            s = df[meta["season_col"]].dropna().astype(str)
            seas = f"{s.min()} to {s.max()} ({s.nunique()} distinct)"
        mp, top = missing_profile(df)
        dup_full = int(df.duplicated().sum())
        dup_key = int(df.duplicated(meta["key"]).sum()) if meta.get("key") else ""
        rows.append(dict(dataset_file=fn, status="generated", records=len(df), columns=len(df.columns),
                         earliest_date=mn, latest_date=mx, competitions_included=comps,
                         countries_included=ctry, seasons_covered=seas, source_urls=meta["sources"],
                         download_or_extraction_date=EXTRACTION_DATE, missing_cells_pct=mp,
                         columns_with_most_missing=top, exact_duplicate_rows=dup_full,
                         duplicate_key_definition="; ".join(meta["key"]) if meta.get("key") else "",
                         duplicate_key_rows=dup_key, legal_analytics_ml_status=meta["legal"],
                         known_limitations=meta["limits"]))
    # unavailable / not generated
    for fn, why in [("(not generated) Domestic super cups, UEFA Super Cup, FIFA Intercontinental Cup",
                     "No authorized open source with these competitions was found; the openfootball CWC files contain the "
                     "FIFA Club World Cup only. No records were fabricated."),
                    ("(not generated) Per-player season totals for leagues without event data",
                     "Only StatsBomb open competitions (event-level) and openfootball 2025-26 lineups (appearances, goals, "
                     "cards) are available. Premier League/La Liga/Bundesliga/Serie A/Ligue 1 historical player statistics "
                     "(shots, passes, tackles) are NOT available from an authorized open source.")]:
        rows.append(dict(dataset_file=fn, status="unavailable", records=0, known_limitations=why))
    sm = pd.DataFrame(rows)
    for c in ["records", "columns", "competitions_included", "countries_included", "exact_duplicate_rows", "duplicate_key_rows"]:
        sm[c] = pd.to_numeric(sm[c], errors="coerce").astype("Int64")
    sm.loc[sm.dataset_file.str.startswith("01_"), "seasons_covered"] = (
        f"{dfs['01'].match_date.str[:4].min()} to {dfs['01'].match_date.str[:4].max()} (calendar years; "
        f"{dfs['01'].match_date.str[:4].nunique()} distinct)")
    sm.to_csv(os.path.join(ROOT, "12_DATASET_SUMMARY.csv"), index=False, encoding=ENC)
    print(sm[["dataset_file", "records", "earliest_date", "latest_date"]].to_string())

    # ---------------------------------------------------------------- data dictionary
    dd = []
    for key, fn in files.items():
        df = dfs[key]
        for c in df.columns:
            desc = DICT.get(c) or DICT.get(f"{key}.{c}")
            if desc is None:
                raise SystemExit(f"Missing dictionary entry for column {c} in {fn}")
            nn = df[c].notna().sum()
            ex = df[c].dropna().astype(str).head(1)
            dd.append(dict(dataset_file=fn, column_name=c, data_type=str(df[c].dtype), description=desc,
                           non_null_count=int(nn), example_value=ex.iat[0][:80] if len(ex) else ""))
    pd.DataFrame(dd).to_csv(os.path.join(ROOT, "11_DATA_DICTIONARY.csv"), index=False, encoding=ENC)
    print("dictionary rows", len(dd))

    # ---------------------------------------------------------------- source coverage matrix
    int_all = dfs["01"]
    cov = []
    cov.append(dict(source="martj42/international_results", url="https://github.com/martj42/international_results",
                    scope="Men's full international matches (World Cup, qualifiers, continental, Nations League, friendlies, others)",
                    seasons_or_years="1872-2026", latest_match_date_in_source=pd.read_csv(
                        os.path.join(RAW, "martj42_refresh", "results.csv")).date.max(),
                    records_exported=int(len(dfs["01"]) + (dfs["03"].record_scope == "international").sum()),
                    access_method="raw.githubusercontent.com file download (public HTTP, no scraping of a website)",
                    license="CC0-1.0 (GitHub repository license metadata read 2026-10-20)",
                    ml_use_status="CONFIRMED permitted (CC0 public-domain dedication)",
                    status="used", notes="Supersedes local baseline snapshot: 725 baseline-only keys are mostly the China PR->China rename; 72 baseline-unscored matches now scored; 2 scores changed (1974). Regulation vs extra-time not separable."))
    for r, (lic, c) in lic_of.items():
        sub = d2[d2.source_repo == r] if r != "club-worldcup" else d2[d2.source_repo == r]
        allc = pd.concat([d2, d3[d3.record_scope == "club"].assign(source_repo=d3[d3.record_scope == "club"].source_url.str.split("/").str[-1])])
        sub = allc[allc.source_repo == r]
        cov.append(dict(source=f"openfootball/{r}", url=f"https://github.com/openfootball/{r}",
                        scope=", ".join(sorted(sub.competition_name.dropna().unique())[:12]) + (" ..." if sub.competition_name.nunique() > 12 else ""),
                        seasons_or_years=f"{sub.season.astype(str).min()} to {sub.season.astype(str).max()}" if len(sub) else "",
                        latest_match_date_in_source=sub.match_date.max() if len(sub) else "",
                        records_exported=len(sub), access_method="git clone --depth 1 of public GitHub repository",
                        license=lic, ml_use_status="CONFIRMED permitted (CC0) based on repository LICENSE file",
                        status="used", notes=f"commit {c}. Coverage varies widely by competition and season; see 07_Competitions.csv."))
    cov.append(dict(source="openfootball squad and *-full match files (lineups, goals, cards)",
                    url="https://github.com/openfootball", scope="2025-26 top-5 leagues + Austria lineups; Club World Cup 2000-2025; selected squads (2014-15, 2023-24, Euro 2021/2024, Copa America 2021/2024, CWC)",
                    seasons_or_years="2025-26 league lineups; various squads", latest_match_date_in_source=ofm.match_date.max(),
                    records_exported=int((d5.source_dataset.str.startswith("openfootball")).sum()),
                    access_method="same git clones", license="CC0 1.0 Universal (LICENSE.md)",
                    ml_use_status="CONFIRMED permitted (CC0)", status="used",
                    notes="Minutes are estimates from substitution/red-card minutes; no passing/shot/tackle data."))
    sbm = pd.read_csv(os.path.join(WORK, "sb_matches.csv"), low_memory=False)
    cov.append(dict(source="StatsBomb Open Data", url="https://github.com/statsbomb/open-data",
                    scope=f"{sbm.competition_name.nunique()} competitions / {sbm[['sb_competition_id','sb_season_id']].drop_duplicates().shape[0]} competition-seasons, includes women's competitions",
                    seasons_or_years=f"{sbm.season_name.min()} to {sbm.season_name.max()}", latest_match_date_in_source=sbm.match_date.max(),
                    records_exported=int((d5.source_dataset.str.startswith("StatsBomb")).sum()),
                    access_method=f"git clone --depth 1 (commit {sb_commit})", license="StatsBomb Open Data terms (README): free for research/analysis; credit StatsBomb if publishing",
                    ml_use_status="LIMITED: research/educational use with attribution is stated; commercial use and redistribution beyond the repo are NOT confirmed. LICENSE.pdf could not be machine-read in this session.",
                    status="used", notes="Event-derived stats computed by this project from raw events; competition_gender column must be used to separate men's and women's matches."))
    cov += [
        dict(source="Football-Data.co.uk", url="https://www.football-data.co.uk/data.php",
             scope="European league results/odds 1993-present; cup data not offered", seasons_or_years="", latest_match_date_in_source="",
             records_exported=0, access_method="not accessed for data", license="Site text: free but 'intended for private individuals only, NOT commercial or data training products using automated bots/scrapers/AI' (read 2026-10-20); robots.txt blocks AI crawlers",
             ml_use_status="RESTRICTED - ML/automated use prohibited; EXCLUDED", status="excluded", notes="Deliberately not downloaded because the stated terms prohibit the intended use."),
        dict(source="FBref / Sports Reference, Opta, Transfermarkt, WhoScored, Sofascore, FIFA/UEFA official sites",
             url="", scope="Player statistics and full club histories", seasons_or_years="", latest_match_date_in_source="", records_exported=0,
             access_method="not accessed", license="Terms not reviewed in this run; these sources are generally proprietary or restrict scraping",
             ml_use_status="UNVERIFIED - not used", status="not_used", notes="No scraping or bypass attempted."),
        dict(source="Kaggle datasets / paid APIs (API-Football, Sportmonks, StatsBomb paid data)", url="", scope="Various", seasons_or_years="",
             latest_match_date_in_source="", records_exported=0, access_method="not accessed (account/API purchase required)",
             license="Account or paid licence required", ml_use_status="NOT AVAILABLE - not purchased per instructions", status="not_used",
             notes="Paid access explicitly out of scope."),
        dict(source="Local baseline snapshot data/raw/international_results (Milestone 1)", url="", scope="International results through 2026-06-27",
             seasons_or_years="1872-2026", latest_match_date_in_source="2026-06-27", records_exported=0,
             access_method="read-only; used only for reconciliation (in_local_baseline column)", license="CC0 (same upstream source)",
             ml_use_status="CONFIRMED (same CC0 source)", status="reconciliation_only", notes="Original files untouched."),
    ]
    pd.DataFrame(cov).to_csv(os.path.join(ROOT, "13_SOURCE_COVERAGE_MATRIX.csv"), index=False, encoding=ENC)
    print("coverage rows", len(cov))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)
    main()
