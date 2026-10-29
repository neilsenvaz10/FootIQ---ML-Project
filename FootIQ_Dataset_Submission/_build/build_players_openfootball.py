"""Extract player-level records from the openfootball '-full' match files and squad files (CC0).

Outputs (in _build/work): of_full_matches.csv, of_player_match.csv, of_goal_events.csv, of_squads.csv,
of_players_issues.csv
Nothing is invented: a value is exported only if the source text states it or it is a documented
arithmetic derivation (minutes estimate).
"""
import os
import re
import sys
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import footballtxt as ft  # noqa: E402
import build_club_matches as bcm  # noqa: E402

ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "_raw_sources")
WORK = os.path.join(HERE, "work")

RE_HDR = re.compile(
    r"^\s*(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s+)?([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?"
    r"(?:\s+(\d{1,2}:\d{2}))?\s+UTC([+-]\d+(?::\d+)?)\s*(?:@\s*(.*?))?\s*$")
RE_ATT = re.compile(r",\s*Att:\s*([\d,.]+)\s*$")
RE_LINEUP = re.compile(r"^(?P<team>[^\s#▪][^:]{0,60}):\s+(?P<rest>\S.*)$")
RE_MIN = r"(\d+(?:\+\d+)?)"
RE_CARD = re.compile(r"\[(Y/R|Y|R)\s+" + RE_MIN + r"'\]")
RE_SUB = re.compile(r"\(" + RE_MIN + r"'\s+(.*)\)\s*$")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def minute_val(m):
    return int(str(m).split("+")[0]) if m is not None else None


def split_top(s):
    out, buf, depth, i = [], [], 0, 0
    while i < len(s):
        ch = s[i]
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if depth == 0 and ch == ",":
            out.append("".join(buf))
            buf = []
        elif depth == 0 and s[i:i + 3] == " - ":
            out.append("".join(buf))
            buf = []
            i += 3
            continue
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


def parse_person(txt):
    """'NAME [c] [Y 51']' -> dict(name, captain, cards[list of (type,minute)])"""
    cards = [(m.group(1), m.group(2)) for m in RE_CARD.finditer(txt)]
    captain = "[c]" in txt
    name = RE_CARD.sub("", txt).replace("[c]", "").strip()
    return dict(name=name, captain=captain, cards=cards)


def parse_lineup(rest):
    players = []
    for k, ent in enumerate(split_top(rest)):
        sub = None
        sm = RE_SUB.search(ent)
        if sm:
            sub = parse_person(sm.group(2))
            sub["minute"] = sm.group(1)
            ent = ent[:sm.start()].strip()
        p = parse_person(ent)
        p["sub"] = sub
        players.append(p)
    return players


RE_GOAL_TOKEN = re.compile(r"^(?:(?P<name>.*?)\s+)?(?P<min>\d+(?:\+\d+)?)'(?:\((?P<kind>p|og)\))?$")


def parse_goal_group(seg):
    goals, last = [], None
    for part in [p.strip() for p in seg.split(",") if p.strip()]:
        m = RE_GOAL_TOKEN.match(part)
        if not m:
            goals.append(dict(name=None, minute=None, kind=None, raw=part, ok=False))
            continue
        name = m.group("name") or last
        last = name
        goals.append(dict(name=name, minute=m.group("min"), kind=m.group("kind") or "",
                          raw=part, ok=name is not None))
    return goals


def parse_goals(raw, hs, as_):
    """Return (home_goals, away_goals, status). The two sides are separated by ';'."""
    raw = raw.strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1]
    if ";" in raw:
        a, b = raw.split(";", 1)
        return parse_goal_group(a), parse_goal_group(b), "two_sides"
    g = parse_goal_group(raw)
    if hs == 0 and as_ and as_ > 0:
        return [], g, "inferred_away_only_from_score"
    if as_ == 0 and hs and hs > 0:
        return g, [], "inferred_home_only_from_score"
    return [], [], "ambiguous_side_not_assigned"


def parse_full(text, season_start, rel):
    title = None
    stage = None
    cur = None
    issues, matches = [], []
    lines = text.splitlines()
    cur_date = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("=") and title is None:
            title = line.lstrip("= ").strip()
            continue
        sm = ft.RE_STAGE.match(line)
        if sm and not line.startswith("    "):
            stage = sm.group(1)
            continue
        hm = RE_HDR.match(line)
        if hm and hm.group(5) is not None or (hm and " v " not in line):
            dow, mon, day, yr, tm, tz, venue = hm.groups()
            att = None
            if venue:
                am = RE_ATT.search(venue)
                if am:
                    att = int(re.sub(r"[,.]", "", am.group(1)))
                    venue = venue[:am.start()].strip()
            cur_date = ft._resolve_date(ft.MONTHS[mon], int(day), yr, cur_date, title, season_start, issues, i, line)
            cur = dict(line_no=i, date=cur_date.isoformat() if cur_date else None, kickoff=tm or "", tz="UTC" + tz,
                       venue=venue or "", attendance=att, stage=stage, lineups={}, extra_cards=[], goals_raw="")
            matches.append(cur)
            continue
        if cur is None:
            continue
        if " v " in line and "team1" not in cur and line.startswith("  "):
            body = line.strip()
            t1, right = re.split(r"\s+v\s+", body, maxsplit=1)
            sc = re.search(r"(?<=\s)(\d+-\d+)(?=\s|$)", right)
            if sc:
                t2, rest = right[:sc.start()].strip(), right[sc.start():]
            else:
                t2, rest = right.strip(), ""
            cur.update(team1=t1.strip(), team2=t2, res=ft.parse_result(rest), match_line=line.strip())
            continue
        mm = re.match(r"^\s{2}(.+?)\s{2,}(\d+-\d+)\s{2,}(.+?)(?:\s+\((\d+)-(\d+) pen\))?\s*$", line)
        if mm and "team1" not in cur and " v " not in line:
            sc = tuple(int(x) for x in mm.group(2).split("-"))
            res = dict(main=sc, ft=None, aet=None, pen=(int(mm.group(4)), int(mm.group(5))) if mm.group(4) else None,
                       ht=None, note=None, flag=None, status="scored")
            cur.update(team1=mm.group(1).strip(), team2=mm.group(3).strip(), res=res, match_line=line.strip())
            continue
        if line.strip().startswith("(") and "team1" in cur and not cur["lineups"]:
            g = line.strip()
            while g.count("(") > g.count(")") and i < len(lines):
                g += " " + lines[i].strip()
                i += 1
            cur["goals_raw"] = (cur["goals_raw"] + " " + g).strip()
            continue
        ym = re.match(r"^\s+(Yellow-Red|Yellow|Red|Yellow/Red|Second yellow):\s*(.*)$", line)
        if ym:
            txt = ym.group(2)
            while i < len(lines) and lines[i].startswith("      ") and not lines[i].strip().startswith(("Yellow", "Red")):
                txt += " " + lines[i].strip()
                i += 1
            for tok in split_top(txt):
                mm = re.match(r"^(.*?)\s+" + RE_MIN + r"'$", tok.strip())
                if mm:
                    cur["extra_cards"].append((ym.group(1), mm.group(1).strip(), mm.group(2)))
            continue
        lm = RE_LINEUP.match(line)
        if lm and lm.group("team") not in ("Refs", "Penalties") and not line.startswith(" "):
            team, rest = lm.group("team").strip(), lm.group("rest")
            while i < len(lines) and lines[i].startswith("      ") and lines[i].strip() \
                    and not re.match(r"^\s+(Yellow-Red|Yellow|Red|Yellow/Red|Second yellow):", lines[i]):
                rest += " " + lines[i].strip()
                i += 1
            cur["lineups"][team] = rest
            continue
        if line.startswith(("Refs:", "Penalties:")) or line.strip().startswith(("Refs:", "Referee")):
            continue
        issues.append((i, "unparsed_line", line.strip()[:200]))
    return title, matches, issues


def build_full():
    base = pd.read_csv(os.path.join(WORK, "club_matches_all.csv"), low_memory=False, keep_default_na=False,
                       na_values=[""])
    base["k1"] = base.home_team.map(norm)
    base["k2"] = base.away_team.map(norm)
    files = []
    for dp, dn, fn in os.walk(RAW):
        dn[:] = [d for d in dn if d not in (".git", "statsbomb_open_data", "martj42_refresh", "players")]
        for n in fn:
            if n.endswith("-full.txt"):
                files.append(os.path.relpath(os.path.join(dp, n), RAW).replace("\\", "/"))
    mrows, prows, grows, irows = [], [], [], []
    for rel in sorted(files):
        # derive the base-file path for registry lookup
        if rel.startswith("club-worldcup/more/"):
            yr = os.path.basename(rel)[:4]
            base_rel = f"club-worldcup/{yr}/clubworldcup.txt"
        else:
            base_rel = rel.replace("-full.txt", ".txt")
        info = bcm.describe(base_rel)
        if info is None:
            irows.append(dict(file=rel, line=0, kind="no_registry_entry", text=""))
            continue
        comp_id = f"{info['ns']}:{info['code']}"
        text = open(os.path.join(RAW, rel), encoding="utf-8").read()
        season = info["season"]
        title, matches, issues = parse_full(text, int(season[:4]), rel)
        tm = re.search(r"(\d{4})(?:/(\d{2,4}))?\s*$", title or "")
        if tm:
            t_season = tm.group(1) + ("-" + tm.group(2)[-2:] if tm.group(2) else "")
            if t_season != season:
                season = t_season
                title, matches, issues = parse_full(text, int(season[:4]), rel)
        for ln, kind, txt in issues:
            irows.append(dict(file=rel, line=ln, kind=kind, text=txt))
        sub = base[(base.competition_id == comp_id) & (base.season == season)]
        for m in matches:
            if "team1" not in m:
                irows.append(dict(file=rel, line=m["line_no"], kind="header_without_match_line", text=""))
                continue
            t1n, t1c = ft.split_team(m["team1"])
            t2n, t2c = ft.split_team(m["team2"])
            k1, k2 = norm(t1n), norm(t2n)
            cand = sub[(sub.match_date == m["date"])]
            hit = cand[(cand.k1.map(lambda x: x == k1 or x.startswith(k1) or k1.startswith(x)))
                       & (cand.k2.map(lambda x: x == k2 or x.startswith(k2) or k2.startswith(x)))]
            swapped = False
            if len(hit) == 0 and m["date"]:
                d0 = pd.Timestamp(m["date"])
                near = sub[(pd.to_datetime(sub.match_date) - d0).abs() <= pd.Timedelta(days=1)]
                cand = near
                hit = cand[(cand.k1.map(lambda x: x == k1 or x.startswith(k1) or k1.startswith(x)))
                           & (cand.k2.map(lambda x: x == k2 or x.startswith(k2) or k2.startswith(x)))]
            if len(hit) != 1:
                hit2 = cand[(cand.k1.map(lambda x: x == k2 or x.startswith(k2) or k2.startswith(x)))
                            & (cand.k2.map(lambda x: x == k1 or x.startswith(k1) or k1.startswith(x)))]
                if len(hit2) == 1:
                    hit, swapped = hit2, True
            fuzzy = False
            if len(hit) != 1 and len(cand) > 0:
                def jac(a, b):
                    sa, sb = set(a.split()) - {"fc", "sc", "cf", "de", "ac"}, set(b.split()) - {"fc", "sc", "cf", "de", "ac"}
                    return len(sa & sb) / max(len(sa | sb), 1)
                scored = []
                for ix, row in cand.iterrows():
                    fwd = min(jac(k1, row.k1), jac(k2, row.k2))
                    rev = min(jac(k1, row.k2), jac(k2, row.k1))
                    scored.append((max(fwd, rev), rev > fwd, ix))
                scored.sort(reverse=True)
                if scored and scored[0][0] >= 0.5 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
                    hit, swapped, fuzzy = cand.loc[[scored[0][2]]], scored[0][1], True
            if len(hit) == 1:
                link = "linked_to_base_match" + ("_home_away_order_differs" if swapped else "") \
                    + ("_fuzzy_team_name_same_date" if fuzzy else "")
                mid = hit.iloc[0].match_id
                if swapped:
                    home_id, away_id = hit.iloc[0].away_team_id, hit.iloc[0].home_team_id
                else:
                    home_id, away_id = hit.iloc[0].home_team_id, hit.iloc[0].away_team_id
            else:
                link = "no_unique_base_match"
                mid = f"{comp_id}:{season}:full:L{m['line_no']}"
                ns = bcm.CC.get(info["ns"], info["ns"])
                home_id, away_id = f"{t1c or ns}|{t1n}", f"{t2c or ns}|{t2n}"
            res = m["res"]
            main = res["main"]
            hs, as_ = (main if main else (None, None))
            hg, ag, gstat = parse_goals(m["goals_raw"], hs, as_) if m["goals_raw"] else ([], [], "no_goal_list")
            n_listed = len(hg) + len(ag)
            mrows.append(dict(match_id=mid, link_status=link, source_file=rel, source_line=m["line_no"],
                              competition_id=comp_id, season=season, match_date=m["date"],
                              kickoff_time=m["kickoff"], kickoff_tz=m["tz"], venue=m["venue"],
                              attendance=m["attendance"], home_team_source=t1n, away_team_source=t2n,
                              score_main=f"{hs}-{as_}" if main else "", goal_list_status=gstat,
                              goals_listed=n_listed))
            # lineups
            lineups = {k: parse_lineup(v) for k, v in m["lineups"].items()}
            sides = {}
            for tname, plist in lineups.items():
                kt = norm(re.sub(r"\(.*?\)", "", tname))
                if kt == k1 or kt.startswith(k1) or k1.startswith(kt):
                    sides[tname] = "home"
                elif kt == k2 or kt.startswith(k2) or k2.startswith(kt):
                    sides[tname] = "away"
                else:
                    sides[tname] = ""
                    irows.append(dict(file=rel, line=m["line_no"], kind="lineup_team_not_matched",
                                      text=f"{tname} vs {t1n} / {t2n}"))
            by_side = {"home": [], "away": []}
            for tname, plist in lineups.items():
                if sides[tname]:
                    by_side[sides[tname]] = plist
            goal_by_side = {"home": hg, "away": ag}
            match_has_et = bool(res["aet"] or res["pen"])
            for side, plist in by_side.items():
                team_id = home_id if side == "home" else away_id
                team_name = t1n if side == "home" else t2n
                own_goals = {"home": ag, "away": hg}[side]  # og listed under the benefiting side
                for pos, p in enumerate(plist):
                    entries = [(p, True)] + ([(p["sub"], False)] if p["sub"] else [])
                    for person, starter in entries:
                        nm = person["name"]
                        if not nm:
                            continue
                        cards = list(person["cards"])
                        for typ, nme, mn in m["extra_cards"]:
                            if norm(nme) == norm(nm) and not cards:
                                cards.append(("Y/R" if typ in ("Yellow-Red", "Yellow/Red", "Second yellow") else ("Y" if typ.startswith("Yellow") else "R"), mn))
                        y = [c for c in cards if c[0] == "Y"]
                        r = [c for c in cards if c[0] in ("R", "Y/R")]
                        # minutes estimate within a 90-minute frame
                        if starter:
                            out_min = minute_val(p["sub"]["minute"]) if p["sub"] else 90
                            in_min = 0
                        else:
                            in_min = minute_val(person["minute"])
                            out_min = 90
                        if r:
                            out_min = min(out_min, minute_val(r[0][1]))
                        mins = max(out_min - in_min, 0)
                        pk = norm(nm)
                        goals = [g for g in goal_by_side[side] if g["ok"] and norm(g["name"]) == pk and g["kind"] != "og"]
                        pens = [g for g in goals if g["kind"] == "p"]
                        ogs = [g for g in own_goals if g["ok"] and norm(g["name"]) == pk and g["kind"] == "og"]
                        prows.append(dict(
                            match_id=mid, link_status=link, competition_id=comp_id, season=season,
                            match_date=m["date"], team_id=team_id, team_name=team_name, side=side,
                            player_name_source=nm, player_key=f"OFP|{team_id}|{pk}",
                            lineup_order=pos + 1 if starter else None, role="starter" if starter else "substitute",
                            captain=person["captain"], substituted_in_minute=None if starter else person["minute"],
                            substituted_out_minute=(p["sub"]["minute"] if starter and p["sub"] else None),
                            minutes_played_est_90min_frame=mins,
                            minutes_basis="estimated from substitution/red-card minutes; 90 assumed otherwise; stoppage time ignored",
                            match_went_beyond_90=match_has_et,
                            goals=len(goals), penalty_goals=len(pens), own_goals=len(ogs),
                            yellow_cards=len(y), red_cards=len(r),
                            yellow_minutes=";".join(c[1] for c in y), red_minutes=";".join(c[1] for c in r),
                            source_file=rel, source_line=m["line_no"]))
            # goal events
            for side in ("home", "away"):
                for g in goal_by_side[side]:
                    if not g["ok"]:
                        continue
                    credited = home_id if side == "home" else away_id
                    grows.append(dict(match_id=mid, link_status=link, competition_id=comp_id, season=season,
                                      match_date=m["date"], credited_team_id=credited, side=side,
                                      player_name_source=g["name"], minute=g["minute"],
                                      goal_type={"": "open_play_or_unspecified", "p": "penalty",
                                                 "og": "own_goal"}[g["kind"]],
                                      list_side_basis=gstat, source_file=rel, source_line=m["line_no"]))
    pd.DataFrame(mrows).to_csv(os.path.join(WORK, "of_full_matches.csv"), index=False, encoding="utf-8")
    pd.DataFrame(prows).to_csv(os.path.join(WORK, "of_player_match.csv"), index=False, encoding="utf-8")
    pd.DataFrame(grows).to_csv(os.path.join(WORK, "of_goal_events.csv"), index=False, encoding="utf-8")
    return irows, len(mrows), len(prows), len(grows)


# ------------------------------------------------------------------ goal events from base files
RE_SQ_HEAD = re.compile(r"^=+\s*(.+?)\s*$")
RE_SQ_ROW = re.compile(
    r"^\s*(?P<no>\d+|-)\s*,\s*(?P<name>[^,]+?)\s*,\s*(?P<pos>[A-Z?]{1,3})\s*,\s*(?P<mid>(?:\d+/\d+\s*,\s*)?)"
    r"(?:b\.\s*(?P<born>[\d/]+))?\s*(?:,\s*(?P<club>.*))?$")
RE_SQ_ROW2 = re.compile(r"^\s*(?P<no>\d+|-)\s{2,}(?P<name>.+?)\s{2,}(?P<pos>[A-Z]{2})\s+(?P<yr>\S*)\s*$")
RE_NAME_NAT = re.compile(r"^(?P<n>.*?)\s*\((?P<nat>[A-Z]{2,4})\)$")


def build_squads():
    rows, issues = [], []
    for dp, dn, fn in os.walk(RAW):
        dn[:] = [d for d in dn if d not in (".git", "statsbomb_open_data", "martj42_refresh", "players", "attic")]
        for n in sorted(fn):
            if not n.endswith(".txt"):
                continue
            rel = os.path.relpath(os.path.join(dp, n), RAW).replace("\\", "/")
            is_sq = "/squads/" in rel or n.endswith("-squads.txt")
            if not is_sq or rel.startswith("players/"):
                continue
            text = open(os.path.join(RAW, rel), encoding="utf-8").read()
            repo = rel.split("/")[0]
            team = None
            title = None
            for ln, line in enumerate(text.splitlines(), 1):
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if line.startswith("==") and not line.startswith("==="):  # team heading in CWC squads
                    team = re.sub(r"\s*#.*$", "", line.lstrip("= ")).strip()
                    continue
                hm = RE_SQ_HEAD.match(line)
                if hm and line.startswith("=") and not re.match(r"^=+$", line.strip()):
                    title = hm.group(1)
                    if not n.endswith("-squads.txt"):
                        team = title
                    continue
                if re.match(r"^=+$", line.strip()):
                    continue
                m = RE_SQ_ROW.match(line)
                m2 = RE_SQ_ROW2.match(line) if not m else None
                if m2:
                    nn = RE_NAME_NAT.match(m2.group("name").strip())
                    nm_, nat_ = (nn.group("n"), nn.group("nat")) if nn else (m2.group("name").strip(), "")
                    rows.append(dict(squad_source_file=rel, source_repo=repo, squad_heading=team, squad_title=title,
                                     shirt_number=m2.group("no") if m2.group("no") != "-" else "",
                                     player_name_source=nm_, nationality_code_if_listed=nat_,
                                     position_code=m2.group("pos"), caps_before_event="",
                                     international_goals_before_event="", birth_text="",
                                     listed_club_text="joined: " + (m2.group("yr") or ""), source_line=ln))
                    continue
                if not m:
                    issues.append(dict(file=rel, line=ln, kind="unparsed_squad_line", text=line.strip()[:160]))
                    continue
                nn = RE_NAME_NAT.match(m.group("name").strip())
                name, nat = (nn.group("n"), nn.group("nat")) if nn else (m.group("name").strip(), "")
                mid = (m.group("mid") or "").replace(",", "").strip()
                caps = goals = ""
                if mid:
                    caps, goals = mid.split("/")
                rows.append(dict(squad_source_file=rel, source_repo=repo, squad_heading=team, squad_title=title,
                                 shirt_number=m.group("no") if m.group("no") != "-" else "",
                                 player_name_source=name, nationality_code_if_listed=nat,
                                 position_code=m.group("pos"), caps_before_event=caps, international_goals_before_event=goals,
                                 birth_text=m.group("born") or "", listed_club_text=(m.group("club") or "").strip(),
                                 source_line=ln))
    pd.DataFrame(rows).to_csv(os.path.join(WORK, "of_squads.csv"), index=False, encoding="utf-8")
    return rows, issues


if __name__ == "__main__":
    irows, nm, npm, ng = build_full()
    rows, sissues = build_squads()
    pd.DataFrame(irows + sissues).to_csv(os.path.join(WORK, "of_players_issues.csv"), index=False, encoding="utf-8")
    print("full matches", nm, "player-match", npm, "goal events", ng, "squad rows", len(rows),
          "issues", len(irows) + len(sissues))
