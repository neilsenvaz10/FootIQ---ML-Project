"""Name matching helpers shared by the Phase 4.20 staging scripts (copied from stage_leagues.py)."""
import difflib
import re
import unicodedata

ALIAS = {
    "slavia praha": "sk slavia prague",
    "inter milan": "internazionale milano", "internazionale": "internazionale milano",
    "athletic bilbao": "athletic club", "racing de santander": "real racing club de santander", "racing santander": "real racing club de santander",  # football-data.co.uk short names -> a form the fuzzy matcher can reach
    "man city": "manchester city", "man united": "manchester united", "nott m forest": "nottingham forest", "spurs": "tottenham", "wolves": "wolverhampton", "newcastle": "newcastle united",
    "leeds": "leeds united", "west ham": "west ham united", "brighton": "brighton hove albion", "inter": "internazionale", "milan": "ac milan", "paris sg": "paris saint germain",
    "st etienne": "saint etienne", "ein frankfurt": "eintracht frankfurt", "m gladbach": "borussia monchengladbach", "mainz": "mainz 05", "fc koln": "koln", "ath madrid": "atletico madrid",
    "ath bilbao": "athletic club", "sociedad": "real sociedad", "betis": "real betis", "vallecano": "rayo vallecano", "celta": "celta vigo", "espanol": "espanyol", "leverkusen": "bayer leverkusen",
    "dortmund": "borussia dortmund", "stuttgart": "vfb stuttgart", "hoffenheim": "tsg hoffenheim", "bayern munich": "bayern munchen", "werder bremen": "werder bremen", "heidenheim": "heidenheim",
    "hamburg": "hamburger sv", "lyon": "olympique lyonnais", "marseille": "olympique de marseille", "monaco": "as monaco", "lille": "lille osc", "nice": "ogc nice", "rennes": "stade rennais",
    "brest": "stade brestois", "lens": "rc lens", "strasbourg": "rc strasbourg", "toulouse": "toulouse fc", "nantes": "fc nantes", "lorient": "fc lorient", "paris fc": "paris fc", "metz": "fc metz"}
STOP = {"fc", "cf", "afc", "ac", "as", "sc", "ssc", "sv", "bv", "tsg", "vfb", "vfl", "rb", "rc", "us", "ss", "ud", "cd", "rcd", "calcio", "de", "the", "1", "fsv", "sg", "osc", "ogc", "fk", "1899", "1909", "1907", "1913", "1946", "04", "05", "96", "98"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = " ".join(s.split())
    return ALIAS.get(s, s)


def core(s):
    return "".join(t for t in norm(s).split() if t not in STOP)


def alike(a, b):
    ca, cb = core(a), core(b)
    return ca == cb or (len(ca) >= 4 and len(cb) >= 4 and (ca in cb or cb in ca)) or difflib.SequenceMatcher(None, ca, cb).ratio() >= 0.82


def resolve(ent_name: dict, label: str):
    """Entity whose name matches `label`: a unique exact core match wins; otherwise a unique fuzzy match; otherwise None (ambiguous or unknown)."""
    exact = [e for e, n in ent_name.items() if core(n) == core(label)]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None
    fuzzy = [e for e, n in ent_name.items() if alike(n, label)]
    return fuzzy[0] if len(fuzzy) == 1 else None
