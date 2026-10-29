"""Parse {{Football box}} style templates from Wikipedia wikitext into match rows (no guessing)."""
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
BOX_START = re.compile(r"\{\{\s*(?:#invoke:\s*)?football\s*box(?:\s*collapsible)?\s*(?:\|\s*main)?\s*(?=[|\n])", re.I)
HEAD = re.compile(r"^(={2,5})\s*(.+?)\s*\1\s*$")
DASH = r"[–—−-]"


def balanced(text, start):
    depth, i, n = 0, start, len(text)
    while i < n - 1:
        two = text[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
            continue
        if two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return text[start:i]
            continue
        i += 1
    return None


def split_params(block):
    inner = block[2:-2]
    parts, buf, br, cu = [], [], 0, 0
    i = 0
    while i < len(inner):
        two = inner[i:i + 2]
        if two == "[[":
            br += 1
            buf.append(two)
            i += 2
            continue
        if two == "]]":
            br -= 1
            buf.append(two)
            i += 2
            continue
        if two == "{{":
            cu += 1
            buf.append(two)
            i += 2
            continue
        if two == "}}":
            cu -= 1
            buf.append(two)
            i += 2
            continue
        ch = inner[i]
        if ch == "|" and br == 0 and cu == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    out = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def clean(s):
    s = re.sub(r"<ref[^>]*?/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    return s


def parse_date(v):
    v = clean(v)
    m = re.search(r"start date(?: and age)?\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", v, re.I)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    v2 = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", v)
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", v2)
    if m and m.group(2).lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", v2)
    if m and m.group(1).lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat()
    return None


def parse_team(v):
    v = clean(v)
    code = None
    m = re.search(r"(?:fbaicon|flagicon|flag|fb)\s*\|\s*([A-Za-z]{2,4})\b", v)
    if m:
        code = m.group(1).upper()
    bold = "'''" in v
    v2 = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v2 = re.sub(r"\{\{[^{}]*\}\}", "", v2)
    link = re.search(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", v2)
    tier = re.search(r"\((\d)\)", v2)
    if link:
        target, disp = link.group(1).strip(), (link.group(2) or link.group(1)).strip()
    else:
        t = re.sub(r"'''|''", "", v2)
        t = re.sub(r"\(\d\)", "", t).strip()
        target, disp = None, t
    return dict(display=re.sub(r"'''|''", "", disp).strip(), target=target, code=code, bold=bold,
                tier=int(tier.group(1)) if tier else None)


def parse_goals(v):
    """Return list of (base_minute, plus, tag) from {{goal|..}} templates."""
    out = []
    for m in re.finditer(r"\{\{\s*goal\s*\|([^{}]*)\}\}", clean(v), re.I):
        for part in m.group(1).split("|"):
            part = part.strip()
            mm = re.match(r"^(\d{1,3})(?:\+(\d{1,2}))?$", part)
            if mm:
                out.append([int(mm.group(1)), int(mm.group(2) or 0), ""])
            elif part.lower().startswith(("o.g", "og", "pen")) and out:
                out[-1][2] = part.lower()
            elif part.lower().startswith(("o.g", "og", "pen")):
                continue
    return out


def parse_page(text, defaults=None):
    lines = text.split("\n")
    # heading index by char offset
    heads, off = [], 0
    for ln in lines:
        m = HEAD.match(ln)
        if m:
            heads.append((off, len(m.group(1)), re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", clean(m.group(2))).strip()))
        off += len(ln) + 1
    rows = []
    for m in BOX_START.finditer(text):
        blk = balanced(text, m.start())
        if not blk:
            continue
        p = split_params(blk)
        stack = {}
        for o, lvl, name in heads:
            if o < m.start():
                stack = {k: v for k, v in stack.items() if k < lvl}
                stack[lvl] = name
        path = " > ".join(v for _, v in sorted(stack.items()))
        t1, t2 = parse_team(p.get("team1", "")), parse_team(p.get("team2", ""))
        sc_raw = clean(p.get("score", "")).strip()
        sm = re.search(rf"(\d+)\s*{DASH}\s*(\d+)", re.sub(r"\[\[[^\]]*\]\]", "", sc_raw))
        g1, g2 = parse_goals(p.get("goals1", "")), parse_goals(p.get("goals2", ""))
        pen = re.search(rf"(\d+)\s*{DASH}\s*(\d+)", clean(p.get("penaltyscore", "")))
        rows.append(dict(
            offset=m.start(), stage_path=path, date=parse_date(p.get("date", "")), time_raw=clean(p.get("time", ""))[:60],
            t1_display=t1["display"], t1_target=t1["target"], t1_code=t1["code"], t1_tier=t1["tier"],
            t2_display=t2["display"], t2_target=t2["target"], t2_code=t2["code"], t2_tier=t2["tier"],
            score_raw=sc_raw, s1=int(sm.group(1)) if sm else None, s2=int(sm.group(2)) if sm else None,
            aet_flag=(p.get("aet", "").strip().lower() in ("yes", "y", "true", "1")),
            pen1=int(pen.group(1)) if pen else None, pen2=int(pen.group(2)) if pen else None,
            goals1=g1, goals2=g2, stadium=re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", clean(p.get("stadium", "")))[:80],
            report_url=(re.search(r"https?://[^\s|\]}]+", clean(p.get("report", ""))) or [None])[0] if re.search(r"https?://", clean(p.get("report", ""))) else None))
    return rows
