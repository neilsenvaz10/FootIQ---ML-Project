"""Generate 10_DATASET_DESCRIPTION.md and RAW_SOURCES_MANIFEST.csv from the finished CSV files."""
import hashlib
import os
import subprocess

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "_raw_sources")
ENC = "utf-8-sig"


def rd(fn):
    return pd.read_csv(os.path.join(ROOT, fn), low_memory=False, encoding=ENC)


def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return "\n".join(out)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    summ = rd("12_DATASET_SUMMARY.csv")
    comp = rd("07_Competitions.csv")
    qa = pd.read_csv(os.path.join(ROOT, "QA_Reports", "QA_Validation_Checks.csv"), encoding=ENC)
    d1, d2, d3 = rd("01_Historical_International_Matches.csv"), rd("02_Historical_Club_Matches.csv"), rd("03_Recent_Match_Results.csv")
    d5, d9 = rd("05_Player_Match_Statistics.csv"), rd("09_Upcoming_Fixtures.csv")
    gen = summ[summ.status == "generated"]
    files_tbl = gen[["dataset_file", "records", "earliest_date", "latest_date"]]

    club = comp[comp.record_scope == "club"]
    focus_ids = ["england:1-premierleague", "espana:1-liga", "deutschland:1-bundesliga", "italy:1-seriea", "europe/france:fr1",
                 "england:facup", "england:eflcup", "espana:cup", "deutschland:cup", "italy:cup", "europe/france:frcup",
                 "champions-league:cl", "champions-league:el", "champions-league:conf", "club-worldcup:clubworldcup",
                 "south-america:copal", "south-america:copas", "world/north-america:concacafcl", "world/africa:cafcl",
                 "world/north-america:mls"]
    foc = comp[comp.competition_id.isin(focus_ids)].set_index("competition_id").loc[
        [i for i in focus_ids if i in set(comp.competition_id)]].reset_index()
    foc = foc[["competition_name", "first_season", "last_season", "n_seasons", "n_scored", "latest_scored_match_date"]]
    intl_cat = d1.groupby("competition_category").agg(matches=("match_id", "size"), first=("match_date", "min"),
                                                      last=("match_date", "max")).reset_index()
    sb = pd.read_csv(os.path.join(HERE, "work", "sb_matches.csv"), low_memory=False)
    sbc = sb.groupby(["competition_name", "competition_gender"]).agg(
        seasons=("season_name", lambda s: ", ".join(sorted(set(s)))), matches=("sb_match_id", "nunique")).reset_index()
    sbc["seasons"] = sbc.seasons.str.slice(0, 70)
    ofp5 = d5[d5.source_dataset.str.startswith("openfootball")]
    ofc = ofp5.groupby(["competition_name", "season"]).agg(player_match_rows=("player_match_id", "size"),
                                                         matches=("match_id", "nunique")).reset_index()
    latest_club = d3[d3.record_scope == "club"].match_date.max()
    latest_intl = d3[d3.record_scope == "international"].match_date.max()
    stale = comp[(comp.record_scope == "club") & (comp.last_season.astype(str).str[:4].isin(["2025", "2026"])) &
                 (comp.n_matches > comp.n_scored)]
    stale_n = len(stale)
    checks_failed = qa[~qa.passed]
    sbn = d5[d5.source_dataset.str.startswith("Stats")]
    n_female = int((sbn.competition_gender.astype(str) == "female").sum())

    md = f"""# FootIQ Dataset Submission - Dataset Description

Prepared 2026-10-20 (extraction date). Scope: data collection, verification, cleaning and export only. No application code, models, databases or git operations were touched. The Milestone 1 baseline files were read but never modified.

## 1. What is in this package

{md_table(files_tbl)}

Additional files: `14_StatsBomb_Match_Index.csv` (supplementary, referenced by 05), `QA_Reports/` (validation checks and the records excluded or flagged), `RAW_SOURCES_MANIFEST.csv` (commits and checksums of downloaded raw sources), `_build/` (the Python scripts that produced everything - re-runnable).
The raw downloads live in `_raw_sources/` next to the cleaned CSVs (not included in the ZIP because of size; the manifest lists exact repository commits).

### Not generated (reported unavailable - nothing was fabricated)

* UEFA Super Cup, domestic super cups and the FIFA Intercontinental Cup: no authorised open source containing them was found. The Club World Cup (2000, 2005-2023, 2025) is the only global club competition present.
* Historical player statistics (shots, passes, tackles, interceptions...) for Premier League, La Liga, Bundesliga, Serie A and Ligue 1: no authorised open source. Event-level statistics exist only for the StatsBomb open-data subset below.
* Paid APIs and sites that prohibit automated use were not used (see `13_SOURCE_COVERAGE_MATRIX.csv`).

## 2. Definitions used across files

* **Historical** = completed matches dated on or before 2026-06-02 (the last scored date of the Milestone 1 baseline). **Recent** = completed matches 2026-06-03 to 2026-10-20 (file 03). The two never overlap.
* **Latest dates of the sources (not the same as 2026-10-20):** international source latest completed match **{latest_intl}**; club sources latest completed match **{latest_club}** (many competitions end earlier - see `latest_scored_match_date` in 07). Results after those dates are not in the sources (the latest openfootball commits, e.g. England on 2026-10-15, contain no later results).
* **Completed vs unscored:** an international record always has a score (the upstream file has no unscored rows). Club records without a result, cancelled/postponed matches and scheduled matches are never in 01/02/03; fixtures dated after 2026-06-02 are in `09_Upcoming_Fixtures.csv` ({len(d9)} rows; `fixture_status` says upcoming vs past-dated-without-result), earlier unscored club records are in `QA_Reports/QA_Club_Records_Not_Scored_Or_Nonstandard.csv`.
* **Score semantics.** International (01/03): score includes extra time and excludes penalties; penalty shootout winner is a separate column; regulation vs extra time cannot be separated. Club (02/03): `*_goals_regulation`, `*_goals_after_extra_time`, `*_penalties` are separate columns; `decided_in` is regulation / extra_time / penalties; `final_match_winner_side` is the winner of that single match (penalties > extra time > regulation) and is **not** two-legged-tie advancement, which the sources do not provide and which was not inferred.
* **Identifiers.** Source IDs are preserved where they exist (StatsBomb IDs, row/line numbers of every record). Where the sources have no IDs, team and player IDs are keys scoped to the source (`INT|name`, `ENG|Arsenal FC`, `OFP|team|name`). Teams/players that merely share a name are **not** merged; `name_match_key_hint` and `same_name_key_as_other_team_ids` in 06 only flag candidates for later manual resolution.
* Files are UTF-8 with BOM (opens correctly in Excel); dates are ISO-8601.

## 3. Coverage actually delivered

### 3.1 International football (01 + 03)

{md_table(intl_cat)}

* 01: {len(d1):,} matches 1872-11-30 to 2026-06-02; 03 adds {int((d3.record_scope == 'international').sum()):,} matches 2026-06-03 to {latest_intl}.
* {int(d1.decided_by_penalty_shootout.sum())} historical matches have a recorded penalty shootout.
* The refreshed upstream file supersedes the local baseline snapshot: all 72 matches that were unscored in the baseline now have scores (World Cup 2026 group games from 2026-06-11), two further scores changed (Tahiti v New Caledonia, 1974-02-17), and the `China PR` -> `China` rename accounts for most of the 725 baseline-only keys. `in_local_baseline` shows which rows exist in the baseline.

### 3.2 Club football (02 + 03 + 09)

{len(d2):,} historical club matches from {d2.competition_id.nunique()} competitions in {club.country_or_region.nunique()} countries/regions (`07_Competitions.csv`). Key competitions:

{md_table(foc)}

* Seasons shown are the seasons that exist in the open source, **not** the full history of the competition. For example the five major leagues are only present from the 2010s (England from 1992-93), and the domestic cups only from about 2018-19 to 2020-21 (Coupe de France: 2024-25 only). Earlier seasons are not included.
* {stale_n} competition-seasons for 2025-26/2026-27 contain scheduled matches without results in the source (the open repositories lag, especially in lower tiers); those are in `QA_Reports/` and `09_Upcoming_Fixtures.csv`.
* "Worldwide" coverage is **not** claimed: coverage is whatever the CC0 openfootball repositories contain (Europe is strongest; Africa, Asia, Oceania and the Americas are partial; many countries have only a few recent seasons).

### 3.3 Player data (04, 05, 08)

* **StatsBomb Open Data** (event-level, {sbn.match_id.nunique():,} matches, {len(sbn):,} player-match rows, including {n_female:,} rows from women's competitions - filter on `competition_gender`):

{md_table(sbc)}

* **openfootball lineups (appearances, estimated minutes, goals, own goals, penalty goals, cards only; all other metric columns intentionally blank):**

{md_table(ofc)}

* 08 combines match-lineup memberships with squad lists (Club World Cup squads, selected 2014-15 / 2023-24 league squads, Euro 2021/2024 and Copa America 2021/2024 squads).
* Player identity limitation: StatsBomb players have source IDs that persist across teams; openfootball players do not, so the same person can appear several times (`id_scope` column). Nothing was merged by name alone.
* Minutes for openfootball rows are estimates (substitution and red-card minutes inside a 90-minute frame); StatsBomb minutes are derived from lineup position intervals.

## 4. Processing and cleaning rules

1. Raw files are kept unmodified in `_raw_sources/`; every output row carries `source_file` and a line/row reference (club rows also keep the original `source_text`).
2. Dates were parsed from partial strings (no year) using the weekday printed in the source to select the correct year; a season file whose folder name disagreed with its title (Belgium folder 2021-22 holding 2020/21) was relabelled from the title and logged.
3. Column names, date format and outcome codes (H/D/A, home/away/draw) are standardised across files; competition names are standardised for the main competitions and otherwise taken from the source title.
4. Duplicates, invalid scores, half-time/full-time inconsistencies, date ranges and referential integrity (every ID in 05/08 exists in 04/06) were checked - see section 5 and the data dictionary (`11_DATA_DICTIONARY.csv`, {rd('11_DATA_DICTIONARY.csv').shape[0]} documented columns).
5. Missing values are left blank, never filled with 0 or inferred. Where a value is derivable with certainty (a 0-0 score after extra time implies 0-0 in regulation) it is derived and nothing else is.

## 5. Verification results

{md_table(qa[['dataset', 'check', 'passed', 'detail']])}

Failed rows above are informational flags on retained source data, not silent drops: {len(checks_failed)} flagged check(s) - {'; '.join(checks_failed.check.tolist())}. Per-dataset record counts, date ranges, missing-value statistics, duplicate statistics, source URLs, extraction date and limitations are in `12_DATASET_SUMMARY.csv`; source coverage and licence status are in `13_SOURCE_COVERAGE_MATRIX.csv`.

## 6. Licensing and permitted use

| Source | Licence evidence | Analytics / ML use |
|---|---|---|
| martj42/international_results | CC0-1.0 (GitHub licence metadata) | **Confirmed** |
| openfootball repositories | CC0 1.0 Universal (LICENSE.md in each cloned repository, checked) | **Confirmed** |
| StatsBomb Open Data | README: free for research and analysis, credit StatsBomb and use their logo if you publish | **Limited / partly unverified**: research and educational use with attribution is stated; commercial use and ML-model redistribution are not confirmed (LICENSE.pdf could not be machine-read in this session) |
| Football-Data.co.uk | Site text: private use only, not data-training products using bots/scrapers/AI | **Prohibited - not used** |
| FBref, Opta, Transfermarkt, paid APIs | Not reviewed / paid | **Not used** |

If StatsBomb-derived rows are published or shown in a report, credit **StatsBomb**. Check the licence terms again before any commercial use.

## 7. Known limitations (summary)

* Source gaps: see section 1 and 3; the club sources stop at {latest_club} and the international source at {latest_intl}; no results exist in the sources for 2026-10-07 to 2026-10-20.
* Regulation/extra-time split is unavailable for internationals and for {int(((d2.decided_in == 'extra_time') & d2.home_goals_regulation.isna()).sum()):,} historical club extra-time matches whose bracket gives only one value.
* {int(((d2.penalties_played == 'yes') & (d2.extra_time_played == 'unknown')).sum())} penalty-decided club matches do not state whether extra time was played.
* Team/player entity resolution across sources is intentionally not performed.
* Women's competitions appear only in the StatsBomb subset; the international source states men's full internationals only; the openfootball files carry no gender label, men's competitions are assumed from the competition names and no women's competition was identified, but this was not exhaustively verified.
* Cross-validation against an independent provider was not possible (no second authorised source); internal consistency checks were run instead (for example 99% of 2025-26 lineup goal attributions reconcile exactly with the recorded scores).

## 8. Reproducibility

Run in this order from the project root with the existing virtual environment (no extra packages required): `_build/build_club_matches.py`, `_build/build_players_openfootball.py`, `_build/build_players_statsbomb.py`, `_build/assemble_matches.py`, `_build/assemble_players.py`, `_build/validate_and_document.py`, `_build/write_description.py`. Source URLs and download date (2026-10-20) are in `13_SOURCE_COVERAGE_MATRIX.csv` and `RAW_SOURCES_MANIFEST.csv`.
"""
    with open(os.path.join(ROOT, "10_DATASET_DESCRIPTION.md"), "w", encoding="utf-8") as f:
        f.write(md)

    # raw manifest
    rows = []
    for d in sorted(os.listdir(RAW)):
        p = os.path.join(RAW, d)
        if os.path.isdir(os.path.join(p, ".git")):
            try:
                c = subprocess.check_output(["git", "-C", p, "log", "-1", "--format=%H|%cs"], text=True).strip()
                url = subprocess.check_output(["git", "-C", p, "remote", "get-url", "origin"], text=True).strip()
            except Exception:
                c, url = "", ""
            n = sum(len(fs) for _, _, fs in os.walk(p))
            rows.append(dict(raw_source=d, kind="git clone --depth 1", url=url, commit_and_date=c, files=n,
                             download_date="2026-10-20", sha256_note="commit hash identifies content"))
    mj = os.path.join(RAW, "martj42_refresh")
    for f in sorted(os.listdir(mj)):
        if f.endswith(".csv"):
            rows.append(dict(raw_source=f"martj42_refresh/{f}", kind="HTTP download",
                             url="https://raw.githubusercontent.com/martj42/international_results/master/" + f,
                             commit_and_date="", files=1, download_date="2026-10-20", sha256_note=sha256(os.path.join(mj, f))))
    pd.DataFrame(rows).to_csv(os.path.join(ROOT, "RAW_SOURCES_MANIFEST.csv"), index=False, encoding=ENC)
    print("description written;", len(md), "chars; manifest rows", len(rows))


if __name__ == "__main__":
    main()
