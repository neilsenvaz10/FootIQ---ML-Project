"""Parse openfootball (CC0) Football.TXT files into one club-match table.

Run:  .venv\\Scripts\\python.exe -I FootIQ_Dataset_Submission\\_build\\build_club_matches.py
Writes intermediate files to FootIQ_Dataset_Submission/_build/work/.
"""
import os
import re
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import footballtxt as ft  # noqa: E402

ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "_raw_sources")
WORK = os.path.join(HERE, "work")
os.makedirs(WORK, exist_ok=True)

# ---- registry -------------------------------------------------------------------
CC = {"england": "ENG", "espana": "ESP", "deutschland": "GER", "italy": "ITA",
      "france": "FRA", "austria": "AUT", "belgium": "BEL"}
COUNTRY_NAME = {"england": "England", "espana": "Spain", "deutschland": "Germany", "italy": "Italy",
                "austria": "Austria", "belgium": "Belgium"}
STD = {  # (namespace, code) -> (standard name, type, tier)
    ("england", "1-premierleague"): ("English Premier League", "domestic_league", 1),
    ("england", "1-footballleague"): ("English Football League (top tier, 1888-1892)", "domestic_league", 1),
    ("england", "2-championship"): ("English Championship (tier 2)", "domestic_league", 2),
    ("england", "2-division1"): ("English Championship (tier 2)", "domestic_league", 2),
    ("england", "3-league1"): ("English League One (tier 3)", "domestic_league", 3),
    ("england", "3-division2"): ("English League One (tier 3)", "domestic_league", 3),
    ("england", "4-league2"): ("English League Two (tier 4)", "domestic_league", 4),
    ("england", "4-division3"): ("English League Two (tier 4)", "domestic_league", 4),
    ("england", "5-nationalleague"): ("English National League (tier 5)", "domestic_league", 5),
    ("england", "facup"): ("FA Cup", "domestic_cup", None),
    ("england", "eflcup"): ("EFL Cup (League Cup)", "league_cup", None),
    ("espana", "1-liga"): ("Spanish La Liga", "domestic_league", 1),
    ("espana", "2-liga2"): ("Spanish Segunda Division", "domestic_league", 2),
    ("espana", "cup"): ("Copa del Rey", "domestic_cup", None),
    ("deutschland", "1-bundesliga"): ("German Bundesliga", "domestic_league", 1),
    ("deutschland", "2-bundesliga2"): ("German 2. Bundesliga", "domestic_league", 2),
    ("deutschland", "3-liga3"): ("German 3. Liga", "domestic_league", 3),
    ("deutschland", "cup"): ("DFB-Pokal", "domestic_cup", None),
    ("italy", "1-seriea"): ("Italian Serie A", "domestic_league", 1),
    ("italy", "2-serieb"): ("Italian Serie B", "domestic_league", 2),
    ("italy", "cup"): ("Coppa Italia", "domestic_cup", None),
    ("austria", "1-bundesliga"): ("Austrian Bundesliga", "domestic_league", 1),
    ("austria", "2-liga1"): ("Austrian 2. Liga (tier 2)", "domestic_league", 2),
    ("austria", "2-liga2"): ("Austrian 2. Liga (tier 2)", "domestic_league", 2),
    ("austria", "3-regionalliga-ost"): ("Austrian Regionalliga Ost (tier 3)", "domestic_league", 3),
    ("austria", "3-regionalliga-mitte"): ("Austrian Regionalliga Mitte (tier 3)", "domestic_league", 3),
    ("austria", "cup"): ("Austrian Cup", "domestic_cup", None),
    ("belgium", "be1"): ("Belgian First Division A", "domestic_league", 1),
    ("belgium", "becup"): ("Belgian Cup", "domestic_cup", None),
    ("champions-league", "cl"): ("UEFA Champions League", "continental_club", None),
    ("champions-league", "clq"): ("UEFA Champions League (qualifying)", "continental_club", None),
    ("champions-league", "el"): ("UEFA Europa League", "continental_club", None),
    ("champions-league", "elq"): ("UEFA Europa League (qualifying)", "continental_club", None),
    ("champions-league", "conf"): ("UEFA Conference League", "continental_club", None),
    ("champions-league", "confq"): ("UEFA Conference League (qualifying)", "continental_club", None),
    ("club-worldcup", "clubworldcup"): ("FIFA Club World Cup", "global_club", None),
    ("south-america", "copal"): ("Copa Libertadores", "continental_club", None),
    ("south-america", "copas"): ("Copa Sudamericana", "continental_club", None),
    ("world", "concacafcl"): ("CONCACAF Champions Cup/League", "continental_club", None),
    ("world", "cafcl"): ("CAF Champions League", "continental_club", None),
    ("world", "mls"): ("Major League Soccer", "domestic_league", 1),
    ("world", "afl"): ("African Football League", "continental_club", None),
}
SKIP_PARTS = ("rsssf", "squads", "austriasoccer.at", "attic", "openliga", "players", ".git", "more",
              "statsbomb_open_data", "martj42_refresh", "clubs")
BE_ALLOWED = {"be1", "becup"}


def describe(rel):
    """Return registry info for a relative path, or None to skip."""
    parts = rel.replace("\\", "/").split("/")
    base = parts[-1]
    if not base.endswith(".txt") or base.endswith(("-full.txt", ".conf.txt")) or base.startswith("."):
        return None
    if any(p in SKIP_PARTS for p in parts[:-1]):
        return None
    top = parts[0]
    m = re.match(r"^(\d{4})(?:[-_](\d{2}))?[_-]?(.*)\.txt$", base)
    season_dir = next((p for p in parts[1:-1] if re.match(r"^\d{4}(-\d{2})?$", p)), None)
    if top in ("england", "espana", "deutschland", "italy", "austria", "belgium", "champions-league"):
        code = base[:-4]
        if top == "belgium" and code not in BE_ALLOWED:
            return None
        if top == "england" and "archive" in parts and parts[-1] != "1-footballleague.txt" \
                and not code.startswith(("1-", "2-", "3-", "4-", "5-")):
            return None
        season = season_dir
        std = STD.get((top, code))
        if not std and top != "champions-league" and (re.match(r"^\d-", code) or "cup" in code):
            dm = re.match(r"^(\d)-", code)
            std = (None, "domestic_cup" if "cup" in code else "domestic_league", int(dm.group(1)) if dm else None)
        if not std or not season:
            return None
        country = {"champions-league": "UEFA (Europe)"}.get(top, COUNTRY_NAME.get(top))
        return dict(ns=top, code=code, season=season, std=std, country=country)
    if top == "club-worldcup":
        if len(parts) == 3 and parts[2] == "clubworldcup.txt":
            return dict(ns=top, code="clubworldcup", season=parts[1], std=STD[(top, "clubworldcup")],
                        country="FIFA (World)")
        return None
    if m:  # europe/<country>/<season>_<code>.txt, south-america, world
        season = m.group(1) + (("-" + m.group(2)) if m.group(2) else "")
        code = m.group(3)
        if top == "europe" and len(parts) == 3:
            ctry = parts[1]
            kind = ("domestic_cup", None) if code.endswith("cup") else ("domestic_league", None)
            tm = re.search(r"(\d)", code)
            tier = int(tm.group(1)) if tm and not code.endswith("cup") else None
            return dict(ns="europe/" + ctry, code=code, season=season,
                        std=(None, kind[0], tier), country=ctry.replace("-", " ").title())
        if top == "south-america" and len(parts) == 3:
            ctry = parts[1]
            if ctry == "copa-libertadores":
                key = ("south-america", code)
                return dict(ns="south-america", code=code, season=season, std=STD[key],
                            country="CONMEBOL (South America)")
            kind = "domestic_cup" if code.endswith("cup") else "domestic_league"
            tm = re.search(r"(\d)", code)
            return dict(ns="south-america/" + ctry, code=code, season=season,
                        std=(None, kind, int(tm.group(1)) if tm and kind == "domestic_league" else None),
                        country=ctry.title())
        if top == "world" and len(parts) >= 4:
            key = ("world", code)
            region_country = parts[2] if len(parts) >= 5 else parts[1]
            if key in STD:
                return dict(ns="world/" + region_country, code=code, season=season, std=STD[key],
                            country=region_country.replace("-", " ").title())
            kind = "domestic_cup" if code.endswith("cup") else "domestic_league"
            tm = re.search(r"(\d)", code)
            return dict(ns="world/" + region_country, code=code, season=season,
                        std=(None, kind, int(tm.group(1)) if tm and kind == "domestic_league" else None),
                        country=region_country.replace("-", " ").title())
    return None


def git_commit(repo_dir):
    try:
        return subprocess.check_output(["git", "-C", repo_dir, "log", "-1", "--format=%H|%cs"],
                                       text=True).strip()
    except Exception:
        return ""


KNOCKOUT_RE = re.compile(r"(round|final|quarter|semi|playoff|play-off|knockout|last 16|1/\d+|replay|"
                         r"preliminary|qualifying|match 3rd|third place)", re.I)


def main():
    repo_commit = {}
    for d in os.listdir(RAW):
        p = os.path.join(RAW, d)
        if os.path.isdir(os.path.join(p, ".git")):
            repo_commit[d] = git_commit(p)
    rows, issue_rows, files_log = [], [], []
    for dp, dn, fn in os.walk(RAW):
        dn[:] = [d for d in dn if d not in (".git", "statsbomb_open_data", "martj42_refresh")]
        for n in sorted(fn):
            full = os.path.join(dp, n)
            rel = os.path.relpath(full, RAW).replace("\\", "/")
            info = describe(rel)
            if info is None:
                continue
            with open(full, "rb") as fh:
                raw = fh.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
                issue_rows.append(dict(file=rel, line=0, kind="utf8_decode_replacement", text=""))
            season_start = int(info["season"][:4])
            title, matches, issues = ft.parse_text(text, season_start)
            season = info["season"]
            tm = re.search(r"(\d{4})(?:/(\d{2,4}))?\s*$", title or "")
            if tm:
                t_season = tm.group(1) + ("-" + tm.group(2)[-2:] if tm.group(2) else "")
                if t_season != season:
                    issue_rows.append(dict(file=rel, line=1, kind="folder_season_mismatch_title_used",
                                           text=f"folder={season} title={title}"))
                    season = t_season
                    season_start = int(season[:4])
                    title, matches, issues = ft.parse_text(text, season_start)
            files_log.append(dict(file=rel, title=title, n_matches=len(matches), n_issues=len(issues)))
            for ln, kind, txt in issues:
                issue_rows.append(dict(file=rel, line=ln, kind=kind, text=txt))
            std_name, ctype, tier = info["std"]
            comp_title = re.sub(r"\s*\d{4}(/\d{2,4})?\s*$", "", title or "").strip() or None
            comp_name = std_name or comp_title or info["code"]
            comp_id = f"{info['ns']}:{info['code']}"
            repo = rel.split("/")[0]
            for m in matches:
                r = m["res"]
                t1, c1 = ft.split_team(m["team1"])
                t2, c2 = ft.split_team(m["team2"])
                dom_cc = CC.get(info["ns"].split("/")[-1] if info["ns"].startswith("europe/") else info["ns"])
                if info["ns"] == "europe/france":
                    dom_cc = "FRA"
                ns1 = c1 or dom_cc or info["ns"]
                ns2 = c2 or dom_cc or info["ns"]
                if info["ns"] == "club-worldcup" and not c1:
                    ns1 = "CWC"
                reg = r["ft"]
                aet = r["aet"]
                pen = r["pen"]
                main_s = r["main"]
                if r["status"] != "scored":
                    status = "unscored"
                else:
                    status = "completed"
                flag = (r.get("flag") or "").lower()
                for kw in ("cancelled", "awarded", "postponed", "abandoned"):
                    if flag.startswith(kw):
                        status = kw if not (kw == "abandoned" and r["status"] == "scored") else "abandoned"
                        break
                if pen:
                    et = "yes" if aet else "unknown"
                elif aet:
                    et = "yes"
                elif main_s:
                    et = "no"
                else:
                    et = ""
                final = pen or aet or main_s
                if final and final[0] != final[1]:
                    winner = "home" if final[0] > final[1] else "away"
                elif final:
                    winner = "draw"
                else:
                    winner = ""
                if reg:
                    res_reg = "H" if reg[0] > reg[1] else ("A" if reg[0] < reg[1] else "D")
                else:
                    res_reg = ""
                if pen:
                    decided = "penalties"
                elif aet:
                    decided = "extra_time"
                elif main_s:
                    decided = "regulation"
                else:
                    decided = ""
                stage = m["stage"] or ""
                rows.append(dict(
                    match_id=f"{comp_id}:{season}:L{m['line_no']}",
                    competition_id=comp_id, competition_name=comp_name, competition_name_source=comp_title,
                    competition_type=ctype, tier=tier, competition_country=info["country"],
                    season=season, stage=stage, group=m["group"] or "",
                    knockout_or_cup_round=bool(KNOCKOUT_RE.search(stage)) if ctype != "domestic_league"
                    or "playoff" in stage.lower() else False,
                    match_date=m["date"], kickoff_time_local=m["kickoff_local"] or "",
                    home_team_id=f"{ns1}|{t1}", home_team=t1, home_team_country_code=c1 or "",
                    away_team_id=f"{ns2}|{t2}", away_team=t2, away_team_country_code=c2 or "",
                    home_goals_regulation=reg[0] if reg else None, away_goals_regulation=reg[1] if reg else None,
                    home_goals_after_extra_time=aet[0] if aet else None,
                    away_goals_after_extra_time=aet[1] if aet else None,
                    home_penalties=pen[0] if pen else None, away_penalties=pen[1] if pen else None,
                    home_goals_halftime=r["ht"][0] if r["ht"] else None,
                    away_goals_halftime=r["ht"][1] if r["ht"] else None,
                    extra_time_played=et, penalties_played="yes" if pen else ("no" if main_s else ""),
                    result_regulation=res_reg, decided_in=decided, final_match_winner_side=winner,
                    match_status=status, status_note=r.get("note") or "",
                    source_name="openfootball (CC0 / public domain)", source_repo=repo,
                    source_repo_commit=repo_commit.get(repo, ""), source_file=rel, source_line=m["line_no"],
                    source_text=m["raw_line"]))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(WORK, "club_matches_all.csv"), index=False, encoding="utf-8")
    pd.DataFrame(issue_rows).to_csv(os.path.join(WORK, "club_parse_issues.csv"), index=False, encoding="utf-8")
    pd.DataFrame(files_log).to_csv(os.path.join(WORK, "club_files_log.csv"), index=False, encoding="utf-8")
    print(len(df), "matches;", len(issue_rows), "issues;", len(files_log), "files")


if __name__ == "__main__":
    main()
