"""Parser for the openfootball 'Football.TXT' match format (CC0 sources).

Only what the source text states is extracted. Anything that cannot be parsed
is returned as an issue row instead of being guessed.
"""
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
DOW = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"

RE_TITLE = re.compile(r"^=\s*(.+?)\s*$")
RE_STAGE = re.compile(r"^\s*[▪»]\s*(.+?)\s*$")
RE_DATE = re.compile(
    rf"^\s*\[?(?:{DOW}[a-z]*[,/ ]\s*)?([A-Z][a-z]{{2}})[a-z]*[ /.](\d{{1,2}})(?:[ ,/.]+(\d{{4}}))?\]?\s*$")
RE_DATE_ALT = re.compile(  # "Sat 17 Aug 2024" / "17 Aug"
    rf"^\s*\[?(?:{DOW}[a-z]*[,/ ]\s*)?(\d{{1,2}})[ /.]([A-Z][a-z]{{2}})[a-z]*(?:[ ,/.]+(\d{{4}}))?\]?\s*$")
RE_DATE_DOT = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.(?:(\d{4}))?\s*$")
RE_TIME = re.compile(r"^(\d{1,2})[:.](\d{2})\s+")
RE_SCORE = re.compile(r"(?<!\S)(\d+)-(\d+)(?!\S)")
RE_PEN = re.compile(r"(\d+)-(\d+)\s+pen\.")
RE_AET = re.compile(r"(\d+)-(\d+)\s+a\.e\.t\.")
RE_PAREN = re.compile(r"\(([^()]*)\)")
RE_TEAMCODE = re.compile(r"^(.*?)\s+\(([A-Z]{2,4})\)$")


RE_BRACKET = re.compile(r"\[([^\]]+)\]")
_SC = r"\d+-\d+(?:\s+(?:\d+-\d+\s+)?(?:pen\.|a\.e\.t\.))*(?:\s*\([^)]*\))?"
RE_MID = re.compile(rf"^(.+?)\s+({_SC})\s+(\S.*?)$")
RE_MIDFIX = re.compile(r"^(.+?)\s{2,}-\s{2,}(\S.*?)$")


def _resolve_date(mon, day, yr, prev, title, season_start_year, issues, ln, line):
    cands = []
    if yr:
        years = [int(yr)]
    else:
        base = None
        if prev is not None:
            base = prev.year
        else:
            ym = re.search(r"(\d{4})(/\d{2,4})?\s*(?:\$|\W|$)", title or "")
            if ym:
                base = int(ym.group(1))
                if ym.group(2) and mon <= 6:
                    base += 1
            elif season_start_year:
                base = season_start_year
        years = [base - 1, base, base + 1] if base else []
    for y in years:
        try:
            cands.append(date(y, mon, day))
        except ValueError:
            pass
    if not cands:
        issues.append((ln, "bad_date", line.strip()))
        return None
    dm = re.search(rf"({DOW})", line)
    if dm and not yr:
        wk = [d for d in cands if d.strftime("%a") == dm.group(1)]
        if wk:
            cands = wk
    if yr:
        return cands[0]
    ref = prev if prev is not None else date(years[1], 7, 1)
    return min(cands, key=lambda d: abs((d - ref).days))


def _int(x):
    return int(x) if x is not None else None


def parse_result(rest):
    """Return dict of score fields from the text after team 2, or None if no score."""
    rest = rest.strip()
    out = dict(main=None, ft=None, aet=None, pen=None, ht=None, note=None, status="scored")
    if not rest:
        out["status"] = "unscored"
        return out
    # strip trailing venue / note ("@ Stadium") but keep as note
    pens = RE_PEN.search(rest)
    aet = RE_AET.search(rest)
    paren_vals = []
    pm = RE_PAREN.search(rest)
    if pm:
        for part in pm.group(1).split(","):
            sm = RE_SCORE.search(part.strip())
            if sm:
                paren_vals.append((int(sm.group(1)), int(sm.group(2))))
    body = RE_PAREN.sub("", rest)
    if pens:
        out["pen"] = (int(pens.group(1)), int(pens.group(2)))
    if aet:
        out["aet"] = (int(aet.group(1)), int(aet.group(2)))
    first = RE_SCORE.search(body)
    if not first:
        # e.g. "w/o", "awd", "abd.", "postponed"
        out["status"] = "no_score_token"
        out["note"] = rest
        return out
    main = (int(first.group(1)), int(first.group(2)))
    out["main"] = main
    if pens and aet:
        # "5-4 pen. 0-0 a.e.t. (0-0)": paren = (regulation, HT) or (HT)
        if len(paren_vals) >= 2:
            out["ft"], out["ht"] = paren_vals[0], paren_vals[1]
        elif len(paren_vals) == 1:
            out["ht"] = paren_vals[0]
            if out["aet"] == (0, 0):
                out["ft"] = (0, 0)  # derivable: ET score 0-0 implies regulation 0-0
    elif pens:
        if len(paren_vals) >= 2:
            out["ft"], out["ht"] = paren_vals[0], paren_vals[1]
        elif len(paren_vals) == 1:
            out["ht"] = paren_vals[0]
    elif aet:
        if len(paren_vals) >= 2:
            out["ft"], out["ht"] = paren_vals[0], paren_vals[1]
        elif len(paren_vals) == 1:
            out["ht"] = paren_vals[0]
            if out["aet"] == (0, 0):
                out["ft"] = (0, 0)
    else:
        out["ft"] = main
        if paren_vals:
            out["ht"] = paren_vals[0]
    leftover = RE_SCORE.sub("", RE_PEN.sub("", RE_AET.sub("", body)))
    leftover = re.sub(r"\ba\.e\.t\.|\bpen\.", "", leftover).strip(" ,;")
    if leftover:
        out["note"] = leftover
    return out


def parse_text(text, season_start_year=None):
    """Yield (matches, issues). season_start_year seeds the year when dates lack one."""
    matches, issues = [], []
    title = None
    stage = None
    group = None
    cur_date = None
    goal_open = False
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if goal_open and matches:
            matches[-1]["goals_raw"] += " " + line.strip()
            goal_open = matches[-1]["goals_raw"].count("(") > matches[-1]["goals_raw"].count(")")
            continue
        if line.strip().startswith("(") and matches and "goals_raw" not in matches[-1] \
                and matches[-1]["line_no"] >= ln - 12:
            matches[-1]["goals_raw"] = line.strip()
            goal_open = line.count("(") > line.count(")")
            continue
        m = RE_TITLE.match(line)
        if m and not line.startswith("  "):
            title = m.group(1)
            continue
        m = RE_STAGE.match(line)
        if m:
            s = m.group(1)
            if line.lstrip().startswith("»"):
                group = s
            else:
                stage, group = s, None
            continue
        # date line
        mon = None
        dd = RE_DATE_DOT.match(line)
        if dd and 1 <= int(dd.group(2)) <= 12:
            mon, day, yr = int(dd.group(2)), int(dd.group(1)), dd.group(3)
            cur_date = _resolve_date(mon, day, yr, cur_date, title, season_start_year, issues, ln, line)
            continue
        dm = RE_DATE.match(line)
        if dm and dm.group(1) in MONTHS:
            mon, day, yr = MONTHS[dm.group(1)], int(dm.group(2)), dm.group(3)
        else:
            dm2 = RE_DATE_ALT.match(line)
            if dm2 and dm2.group(2) in MONTHS:
                mon, day, yr = MONTHS[dm2.group(2)], int(dm2.group(1)), dm2.group(3)
        if mon is not None and " v " not in line:
            cur_date = _resolve_date(mon, day, yr, cur_date, title, season_start_year, issues, ln, line)
            continue
        body = line.strip()
        tm = RE_TIME.match(body)
        kick = None
        if tm and (" v " in body or RE_MID.match(body[tm.end():]) or RE_MIDFIX.match(body[tm.end():])):
            kick = f"{int(tm.group(1)):02d}:{tm.group(2)}"
            body = body[tm.end():]
        flags = RE_BRACKET.findall(body)
        body_nb = RE_BRACKET.sub("", body).rstrip()
        t1 = t2 = None
        rest = ""
        if " v " in body_nb:
            t1, right = re.split(r"\s+v\s+", body_nb, maxsplit=1)
            right = right.strip()
            sc = re.search(r"(?<=\s)(\d+-\d+)(?=\s|$)", right)
            sm = re.search(r"\s{2,}(?=\S)", right)
            if sc is not None:
                t2, rest = right[:sc.start()].strip(), right[sc.start():]
            elif sm:
                t2, rest = right[:sm.start()].strip(), right[sm.end():]
            else:
                t2 = right
        else:
            mm = RE_MID.match(body_nb)
            if mm:
                t1, rest, t2 = mm.group(1), mm.group(2), mm.group(3)
            else:
                mf = RE_MIDFIX.match(body_nb)
                if mf:
                    t1, t2 = mf.group(1), mf.group(2)
        if t1 is not None and t2:
            res = parse_result(rest)
            if flags:
                res["note"] = "; ".join(flags)
                res["flag"] = flags[0].strip().lower()
            matches.append(dict(line_no=ln, date=cur_date.isoformat() if cur_date else None,
                                kickoff_local=kick, stage=stage, group=group,
                                team1=t1.strip(), team2=t2.strip(), res=res, raw_line=line.strip()))
            if cur_date is None:
                issues.append((ln, "match_without_date", line.strip()))
            continue
        issues.append((ln, "unparsed_line", line.strip()))
    return title, matches, issues


def split_team(name):
    """('Name (ENG)') -> ('Name', 'ENG'); otherwise (name, None). No merging performed."""
    m = RE_TEAMCODE.match(name)
    if m:
        return m.group(1).strip(), m.group(2)
    return name.strip(), None
