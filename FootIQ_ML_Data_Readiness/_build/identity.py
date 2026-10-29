"""Club identity resolution using the curated openfootball/clubs alias tables (CC0).

A source team name is resolved only if its normalised text EXACTLY equals the canonical name or a listed alias
of exactly one club in the same country. No similarity scoring is used anywhere in this module.
"""
import os
import re
import sys
import unicodedata
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW  # noqa

CODE2FOLDER = {
    "ENG": "england", "ESP": "spain", "GER": "germany", "ITA": "italy", "FRA": "france", "POR": "portugal",
    "NED": "netherlands", "BEL": "belgium", "TUR": "turkey", "GRE": "greece", "UKR": "ukraine", "CZE": "czech-republic",
    "AUT": "austria", "SUI": "switzerland", "SCO": "scotland", "RUS": "russia", "DEN": "denmark", "CYP": "cyprus",
    "NOR": "norway", "SRB": "serbia", "POL": "poland", "SWE": "sweden", "CRO": "croatia", "BUL": "bulgaria",
    "ROU": "romania", "AZE": "azerbaijan", "SVN": "slovenia", "HUN": "hungary", "SVK": "slovakia", "MDA": "moldova",
    "BLR": "belarus", "ARM": "armenia", "IRL": "ireland", "FIN": "finland", "ISL": "iceland", "BIH": "bosnia-n-herzegovina",
    "LVA": "latvija", "KOS": "kosovo", "EST": "estonia", "NIR": "northern-ireland", "LTU": "lithuania",
    "FRO": "faroe-islands", "GIB": "gibraltar", "ALB": "albania", "WAL": "wales", "MLT": "malta", "MNE": "montenegro",
    "GEO": "georgia", "AND": "andorra", "LUX": "luxembourg", "MKD": "macedonia", "SMR": "san-marino", "MCO": "monaco",
    "LIE": "liechtenstein", "ISR": "israel", "KAZ": "kazakhstan"}
FOLDER2CODE = {v: k for k, v in CODE2FOLDER.items()}
# openfootball domestic namespaces -> clubs-repo country folder
NS2FOLDER = {"england": "england", "espana": "spain", "deutschland": "germany", "italy": "italy", "austria": "austria",
             "belgium": "belgium"}


def ident_key(s):
    """Case/accent/punctuation-insensitive key. Deliberately does NOT drop words such as FC/CF/AFC."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\[[a-z]{2}\]", " ", s)
    s = s.replace("&", " and ").replace(".", "").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def slug(s):
    return ident_key(s).replace(" ", "-")


def load_clubs():
    """Return (index, canon) ; index[folder][key] -> set(canonical_id); canon[canonical_id] -> dict."""
    root = os.path.join(RAW, "clubs")
    dirs = []
    for region in ("europe", "middle-east", "asia"):
        rb = os.path.join(root, region)
        for folder in sorted(os.listdir(rb)):
            if os.path.isdir(os.path.join(rb, folder)) and (region == "europe" or folder in ("israel", "kazakhstan")):
                dirs.append((region, folder))
    index = defaultdict(lambda: defaultdict(set))
    canon = {}
    for region, folder in dirs:
        d = os.path.join(root, region, folder)
        code = FOLDER2CODE.get(folder, folder.upper()[:3])
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".clubs.txt"):
                continue
            cur = None
            for ln, line in enumerate(open(os.path.join(d, fn), encoding="utf-8"), 1):
                raw = line.rstrip("\n")
                s = raw.strip()
                if not s or s.startswith(("#", "=")):
                    continue
                if s.startswith("|"):
                    if cur is None:
                        continue
                    body = re.sub(r"#.*$", "", s)
                    for a in body.split("|"):
                        a = re.sub(r"\[[a-z]{2}\]", "", a).strip()
                        if a:
                            index[folder][ident_key(a)].add(cur)
                    continue
                name = re.sub(r"#.*$", "", s)
                reserve = bool(re.match(r"^[ivx]+\)\s*", name))
                name = re.sub(r"^[ivx]+\)\s*", "", name)
                name = name.split(",")[0].strip()
                name = re.sub(r"\[[a-z]{2}\]", "", name).strip()
                if not name:
                    continue
                cid = f"CLUB:{code}:{slug(name)}"
                canon[cid] = dict(canonical_name=name, country_code=code, folder=folder, reserve_team=reserve,
                                  source_file=f"clubs/{region}/{folder}/{fn}", source_line=ln)
                cur = cid
                index[folder][ident_key(name)].add(cid)
    return index, canon


# clubs that play in a neighbouring country's league pyramid (explicit, not similarity based)
FALLBACK_FOLDERS = {"france": ["monaco"], "england": ["wales"], "wales": ["england"], "switzerland": ["liechtenstein"],
                    "scotland": [], "germany": [], "italy": ["san-marino"]}


def resolve(index, folder, name):
    """-> (canonical_id or None, status). status in {resolved_exact_alias, ambiguous_multiple_clubs, no_alias_match, no_country}"""
    if not folder:
        return None, "no_country"
    c = set(index.get(folder, {}).get(ident_key(name), set()))
    if not c:
        for fb in FALLBACK_FOLDERS.get(folder, []):
            c |= index.get(fb, {}).get(ident_key(name), set())
    if len(c) == 1:
        return next(iter(c)), "resolved_exact_alias"
    if len(c) > 1:
        return None, "ambiguous_multiple_clubs"
    return None, "no_alias_match"
