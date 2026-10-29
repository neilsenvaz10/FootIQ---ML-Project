"""Parse all cached Wikipedia pages into wp_matches.csv with explicit 90-minute / extra-time evidence."""
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
import s2_fetch_wikipedia as s2  # noqa
import wp_parse  # noqa
from wiki_fetch import fetch  # noqa

NO_ET_STAGE = re.compile(r"matchday|group [a-l]\b|^matches > matchday|league phase|group stage", re.I)


def derive(r, stage_path):
    s1, s2_ = r["s1"], r["s2"]
    g1, g2 = r["goals1"], r["goals2"]
    out = dict(reg1=None, reg2=None, reg_basis="unknown", et_played="unknown", goals_list_consistent=False,
               goals_after_90=0)
    if s1 is None or s2_ is None:
        out["reg_basis"] = "no_score"
        return out
    consistent = len(g1) == s1 and len(g2) == s2_ and (s1 + s2_) > 0
    out["goals_list_consistent"] = bool(consistent)
    late = [g for g in g1 + g2 if g[0] > 90]
    out["goals_after_90"] = len(late)
    nostage = bool(NO_ET_STAGE.search(stage_path))
    if r["aet_flag"] or late:
        out["et_played"] = "yes"
    if consistent:
        out["reg1"] = sum(1 for g in g1 if g[0] <= 90)
        out["reg2"] = sum(1 for g in g2 if g[0] <= 90)
        out["reg_basis"] = "derived_from_goal_minutes"
        if not r["aet_flag"] and not late and r["pen1"] is None:
            out["et_played"] = "no"
    elif s1 + s2_ == 0 and not r["aet_flag"] and r["pen1"] is None:
        out["reg1"], out["reg2"], out["reg_basis"] = 0, 0, "goalless_no_extra_time_flag"
        out["et_played"] = "no"
    elif r["aet_flag"]:
        out["reg_basis"] = "unknown_extra_time_without_complete_goal_minutes"
    elif r["pen1"] is not None:
        out["reg_basis"] = "unknown_penalties_without_complete_goal_minutes"
    elif nostage:
        out["reg1"], out["reg2"], out["reg_basis"] = s1, s2_, "league_or_group_phase_no_extra_time_possible"
        out["et_played"] = "no"
    else:
        out["reg_basis"] = "unknown_knockout_score_not_verified_as_90min"
    return out


def main():
    rows = []
    for comp, season, title, role in s2.PAGES:
        r = fetch(title)
        if r.get("missing"):
            print("MISSING", title)
            continue
        sources = [(r, wp_parse.parse_page(r["wikitext"]), None)]
        for tt in dict.fromkeys(re.findall(r"\{\{:([^}|]+?)\s*\}\}", r["wikitext"])):  # transcluded final articles
            rr = fetch(tt)
            if not rr.get("missing"):
                sources.append((rr, wp_parse.parse_page(rr["wikitext"]), "Final"))
        for pr, ms, forced in sources:
            for m in ms:
                if forced:
                    m["stage_path"] = forced + (" > " + m["stage_path"] if m["stage_path"] else "")
                d = derive(m, m["stage_path"].lower())
                rows.append(dict(competition=comp, season=season, role=role, page_title=pr["title"], page_url=pr["url"],
                                 page_revid=pr["revid"], page_revision_timestamp=pr["timestamp"], retrieved=pr["retrieved"],
                                 **{k: v for k, v in m.items() if k not in ("goals1", "goals2")},
                                 goals1_n=len(m["goals1"]), goals2_n=len(m["goals2"]),
                                 goals1_min=json.dumps([g[:2] for g in m["goals1"]]), goals2_min=json.dumps([g[:2] for g in m["goals2"]]),
                                 **d))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(WORK, "wp_matches.csv"), index=False, encoding="utf-8")
    pd.set_option("display.width", 220)
    print(len(df))
    print(df.groupby(["competition", "season", "role"]).agg(n=("date", "size"), nodate=("date", lambda s: s.isna().sum()),
                                                           noscore=("s1", lambda s: s.isna().sum()),
                                                           aet=("aet_flag", "sum"), pen=("pen1", lambda s: s.notna().sum())).to_string())
    print(df.reg_basis.value_counts())


if __name__ == "__main__":
    main()
