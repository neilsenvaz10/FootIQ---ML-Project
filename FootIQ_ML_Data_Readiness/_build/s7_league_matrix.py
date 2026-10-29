"""Wikipedia round-robin result matrices (undated!) for 2025-26 leagues whose openfootball season is incomplete.
Matrix results have NO match dates: they are used for completeness verification and exported as undated records only."""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
import identity as I  # noqa
from wiki_fetch import fetch  # noqa

D = "–"
LEAGUES = [  # competition_id, country folder, page title, regular-phase teams expected rounds note
    ("europe/scotland:sco1", "scotland", f"2025{D}26 Scottish Premiership"),
    ("espana:2-liga2", "spain", f"2025{D}26 Segunda División"),
    ("deutschland:2-bundesliga2", "germany", f"2025{D}26 2. Bundesliga"),
    ("deutschland:3-liga3", "germany", f"2025{D}26 3. Liga"),
    ("europe/france:fr2", "france", f"2025{D}26 Ligue 2"),
    ("england:3-league1", "england", f"2025{D}26 EFL League One"),
    ("england:4-league2", "england", f"2025{D}26 EFL League Two"),
    ("england:5-nationalleague", "england", f"2025{D}26 National League"),
    ("europe/turkey:tr1", "turkey", f"2025{D}26 Süper Lig"),
    ("belgium:be1", "belgium", f"2025{D}26 Belgian Pro League"),
    ("europe/greece:gr1", "greece", f"2025{D}26 Super League Greece"),
    ("austria:2-liga1", "austria", f"2025{D}26 2. Liga (Austria)"),
    ("italy:2-serieb", "italy", f"2025{D}26 Serie B"),
]
SC = re.compile(r"(\d+)\s*[–−—-]\s*(\d+)")


def parse_matrix(w):
    names = {}
    for m in re.finditer(r"\|\s*name_([^\s=]+)\s*=\s*([^\n]+)", w):
        v = m.group(2)
        lk = re.search(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", v)
        names[m.group(1)] = (lk.group(1).strip(), (lk.group(2) or lk.group(1)).strip()) if lk else (None, re.sub(r"[{}|]|nowrap", "", v).strip())
    res = {}
    for m in re.finditer(r"\|\s*match_([^\s_=]+)_([^\s=]+)\s*=\s*([^\n|]*)", w):
        sc = SC.search(re.sub(r"\[\[[^\]|]*\|", "", m.group(3)))
        res[(m.group(1), m.group(2))] = (int(sc.group(1)), int(sc.group(2))) if sc else None
    return names, res


def main():
    index, canon = I.load_clubs()
    U = pd.read_pickle(os.path.join(WORK, "U_of.pkl"))
    rows, summ = [], []
    for cid, folder, title in LEAGUES:
        r = fetch(title)
        if r.get("missing"):
            summ.append(dict(competition_id=cid, page=title, status="page_missing"))
            continue
        names, res = parse_matrix(r["wikitext"])
        ent = {}
        for ab, (tgt, disp) in names.items():
            cands = {I.resolve(index, folder, x)[0] for x in (tgt, disp) if x}
            cands.discard(None)
            ent[ab] = (next(iter(cands)) if len(cands) == 1 else None, tgt or disp)
        base = U[(U.competition_id == cid) & (U.season == "2025-26")]
        baseA = {(a, b): (h, w_) for a, b, h, w_, st in zip(base.home_entity_id, base.away_entity_id, base.final_excl_pens_home,
                                                          base.final_excl_pens_away, base.match_status) if st == "completed"}
        n_ok = n_conf = n_new = n_unmapped = 0
        tmp = []
        for (a, b), sc in res.items():
            if sc is None or a not in ent or b not in ent:
                continue
            ea, eb = ent[a][0], ent[b][0]
            if not ea or not eb:
                n_unmapped += 1
                continue
            if (ea, eb) in baseA:
                if tuple(baseA[(ea, eb)]) == sc:
                    n_ok += 1
                else:
                    n_conf += 1
                continue
            n_new += 1
            tmp.append(dict(competition_id=cid, season="2025-26", home_entity_id=ea, away_entity_id=eb,
                             home_team_name=ent[a][1], away_team_name=ent[b][1], final_home=sc[0], final_away=sc[1],
                             match_date=None, date_status="UNKNOWN_matrix_has_no_dates", page_title=r["title"],
                             page_revid=r["revid"], page_revision_timestamp=r["timestamp"], page_url=r["url"],
                             retrieved=r["retrieved"], license="CC BY-SA 4.0"))
        used = n_conf == 0
        if used:
            rows.extend(tmp)
        n_scored = sum(1 for v in res.values() if v)
        summ.append(dict(competition_id=cid, page=r["title"], status="parsed", teams=len(names), matrix_scored_cells=n_scored,
                         agree_with_openfootball=n_ok, conflict_with_openfootball=n_conf, new_undated_results=n_new,
                         unmapped_team_cells=n_unmapped, matrix_used=used, note=('' if used else 'REJECTED: matrix disagrees with openfootball on overlapping cells; undated fills not exported'), openfootball_completed=len(baseA)))
    pd.DataFrame(rows).to_csv(os.path.join(WORK, "league_matrix_undated.csv"), index=False, encoding="utf-8")
    s = pd.DataFrame(summ)
    s.to_csv(os.path.join(WORK, "league_matrix_summary.csv"), index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(s.to_string())


if __name__ == "__main__":
    main()
