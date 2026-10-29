"""Stage 2b (read-only): independent competition-season verification, UEFA recovery tests, season/date consistency."""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
ENC = "utf-8-sig"
RAWS = os.path.join(SUB, "_raw_sources")
CUTOFF = "2026-10-01"

d = pd.read_csv(os.path.join(RDY, "04d_COMBINED_CLUB_MATCHES_v1.0.csv"), low_memory=False, encoding=ENC)
cm = pd.read_csv(os.path.join(SUB, "_build", "work", "club_matches_all.csv"), low_memory=False, keep_default_na=False, na_values=[""])
cm["season"] = cm.season.astype(str)
wp = pd.read_csv(os.path.join(RDY, "_build", "work", "wp_matches.csv"), low_memory=False)
prior = pd.read_csv(os.path.join(RDY, "01_COMPETITION_SEASON_COVERAGE_MATRIX.csv"), encoding=ENC)
prior["season"] = prior.season.astype(str)

# ---- independent evidence 1: openfootball file headers ("# Matches N")
hdr = {}
for f, g in cm.groupby("source_file"):
    txt = open(os.path.join(RAWS, f), encoding="utf-8").read(3000)
    mm = re.search(r"#\s*Matches\s+(\d+)", txt)
    key = (g.competition_id.iloc[0], str(g.season.iloc[0]))
    hdr[key] = hdr.get(key, 0) + (int(mm.group(1)) if mm else 0)
hdr_n = {}
for f, g in cm.groupby("source_file"):
    key = (g.competition_id.iloc[0], str(g.season.iloc[0]))
    hdr_n[key] = hdr_n.get(key, 0) + len(g)
header_vs_parsed = [dict(key=f"{k[0]}|{k[1]}", header=v, parsed=hdr_n[k]) for k, v in hdr.items() if v and v != hdr_n[k]]
pd.DataFrame(header_vs_parsed).to_csv(os.path.join(EV, "openfootball_header_vs_parsed_mismatch.csv"), index=False)

# ---- independent evidence 2: format knowledge
BIG = {"england:1-premierleague": 380, "espana:1-liga": 380, "italy:1-seriea": 380, "deutschland:1-bundesliga": 306}


def fmt_expected(cid, season):
    if cid in BIG:
        return BIG[cid], "format: 20/18 clubs x double round robin"
    if cid == "europe/france:fr1":
        y = int(season[:4])
        return (380 if y <= 2022 else 306), "format: 20 clubs (<=2022-23) / 18 clubs"
    if cid.startswith("champions-league:") and cid.split(":")[1] in ("cl", "el", "conf") and season[:4].isdigit():
        y = int(season[:4]); k = cid.split(":")[1]
        if y >= 2024:
            return (153 if k == "conf" else 189), "format: 36-team league phase + knockout playoff, R16, QF, SF, F"
        if y >= 2021:
            return (125 if k == "cl" else 141), "format: 32-team group stage (+KO playoff for EL/ECL) + knockout"
        if k == "el":
            return (205 if y in (2018, 2020) else None), "format: 48-team group stage + R32 + knockout" if y in (2018, 2020) else "COVID-reformatted: not derivable"
        if k == "cl":
            return (119 if y == 2019 else 125), "format: 32-team groups + knockout (2019-20 Lisbon single-leg finals)"
        return 0, "competition did not exist"
    return None, ""


def cnt(df, cond):
    return int(cond.sum())


rows = []
keys = set(zip(cm.competition_id, cm.season)) | set(zip(d.competition_id, d.season.astype(str)))
d["season"] = d.season.astype(str)
wp_ref = wp.groupby(["competition", "season"]).size().to_dict()
FAMNAME = {"champions-league:cl": "UEFA Champions League", "champions-league:el": "UEFA Europa League", "champions-league:conf": "UEFA Conference League",
           "england:facup": "FA Cup", "england:eflcup": "EFL Cup", "espana:cup": "Copa del Rey", "deutschland:cup": "DFB-Pokal",
           "italy:cup": "Coppa Italia", "europe/france:frcup": "Coupe de France"}
SEAS_OK = lambda s: bool(re.match(r"^(201[89]|202[0-6])", s))
for cid, s in sorted(keys):
    if not SEAS_OK(s):
        continue
    c = cm[(cm.competition_id == cid) & (cm.season == s)]
    r = d[(d.competition_id == cid) & (d.season == s)]
    name = (r.competition_name.iloc[0] if len(r) else (c.competition_name.iloc[0] if len(c) else cid))
    ctype = (r.competition_type.iloc[0] if len(r) else (c.competition_type.iloc[0] if len(c) else ""))
    st = c.match_status.value_counts().to_dict()
    inprog = s in ("2026-27", "2026")
    sched_before = int(((c.match_date < CUTOFF)).sum()) if len(c) else 0
    unscored_past = int(((c.match_status == "unscored") & (c.match_date < (CUTOFF if inprog else "2026-10-21"))).sum()) if len(c) else 0
    exp, ev = fmt_expected(cid, s)
    hd = hdr.get((cid, s)) or None
    wref = wp_ref.get((FAMNAME.get(cid), s))
    if exp is None and hd:
        exp, ev = hd, "openfootball file header '# Matches' (source-declared schedule)"
    elif exp is None and wref:
        exp, ev = wref, "Wikipedia match-box count (community edited)"
    # league DRR
    teams = set(r.home_entity_id) | set(r.away_entity_id) | set(c.home_team_id) | set(c.away_team_id)
    n = len(teams)
    if ctype == "domestic_league" and exp is None and n > 1:
        exp, ev = None, "no authoritative count"
    if ctype == "domestic_league" and (cid not in BIG and cid != "europe/france:fr1") and n > 1:
        drr = n * (n - 1)
        if hd and abs(hd - drr) / drr <= 0.12:
            exp, ev = drr, f"double round robin of {n} teams AND header-declared {hd}"
        elif hd:
            exp, ev = hd, f"header-declared total {hd}; format has split/play-offs, not rules-derived"
    if inprog:
        exp_cut, ev_cut = sched_before, "source schedule dated before 2026-10-01 (fixtures exist, results may not)"
    else:
        exp_cut, ev_cut = exp, ev
    ver = len(r)
    dups = int(r.duplicated(["competition_id", "season", "match_date", "home_entity_id", "away_entity_id", "stage"]).sum()) if len(r) else 0
    lab = r.label_90_status.value_counts().to_dict() if len(r) else {}
    pr = prior[(prior.competition_id == cid) & (prior.season == s)]
    pv = int(pr.verified_completed_dated.iloc[0]) if len(pr) else None
    cancelled, postponed = int(st.get("cancelled", 0)), int(st.get("postponed", 0))
    abandoned, awarded = int(st.get("abandoned", 0)), int(st.get("awarded", 0))
    unc = int(lab.get("unknown", 0)) + unscored_past
    if exp_cut is not None and exp_cut > 0:
        pct = round(100 * ver / exp_cut, 1)
        unexplained = max(0, exp_cut - ver - cancelled - postponed - unscored_past) if not inprog else max(0, exp_cut - ver - cancelled - postponed)
    else:
        pct, unexplained = None, None
    src = "+".join(sorted(set(r.source_system))) if len(r) else ("openfootball" if len(c) else "")
    if ev.startswith("format") and hd and hd == exp:
        q = "A"
    elif ev.startswith("format") or "AND header" in ev:
        q = "A" if ev.startswith("format") else "B"
    elif ev.startswith("openfootball file header") or ev.startswith("header-declared"):
        q = "B" if "split" not in ev else "C"
    elif ev.startswith("Wikipedia"):
        q = "C"
    else:
        q = "D"
    ver_conf = int(lab.get("confirmed", 0))
    if inprog:
        suit = "FORWARD_HOLDOUT_ONLY"
    elif q in ("A", "B") and pct is not None and pct >= 98 and len(r) and ver_conf / len(r) >= 0.95 and dups == 0:
        suit = "SUITABLE"
    elif q in ("A", "B", "C") and pct is not None and pct >= 90 and len(r) and (ver_conf + lab.get("inferred_no_marker", 0)) / len(r) >= 0.9:
        suit = "SUITABLE_WITH_RESTRICTIONS"
    elif ver > 0:
        suit = "DESCRIPTIVE_ONLY_OR_NEEDS_CORRECTION"
    else:
        suit = "NO_DATA"
    rows.append(dict(scope="club", competition_id=cid, competition_name=name, competition_type=ctype, season=s,
                     expected_matches=exp_cut, expected_evidence=ev_cut, evidence_quality=q, source_records=len(c) if len(c) else (len(wp[(wp.competition == FAMNAME.get(cid)) & (wp.season == s)])),
                     source_declared_total=hd, verified_scores=ver, missing_results_vs_expected=(exp_cut - ver) if exp_cut else None,
                     unexplained_missing=unexplained, coverage_pct=pct, cancelled=cancelled, postponed=postponed, abandoned=abandoned, awarded=awarded,
                     unscored_date_passed=unscored_past, uncertain_status_or_label=unc, duplicate_fixtures=dups,
                     latest_completed_date=r.match_date.max() if len(r) else None, label90_confirmed=ver_conf, label90_inferred=int(lab.get("inferred_no_marker", 0)),
                     label90_unknown=int(lab.get("unknown", 0)), sources=src, season_in_progress=inprog, prior_report_verified=pv,
                     prior_report_difference=(ver - pv) if pv is not None else None, independent_ml_suitability=suit))
cs = pd.DataFrame(rows)
# ---- international editions
ed = pd.read_csv(os.path.join(EV, "international_edition_checks.csv"))
i1 = pd.read_csv(os.path.join(SUB, "01_Historical_International_Matches.csv"), low_memory=False, encoding=ENC)
i3 = pd.read_csv(os.path.join(SUB, "03_Recent_Match_Results.csv"), low_memory=False, encoding=ENC)
i3 = i3[i3.record_scope == "international"].rename(columns={"competition_name": "tournament"})
ia = pd.concat([i1, i3], ignore_index=True, sort=False)
ia["key"] = ia.match_date + "|" + ia.home_team + "|" + ia.away_team
YEAR = {("UEFA Euro", 2020): 2021, ("African Cup of Nations", 2021): 2022, ("African Cup of Nations", 2023): 2024, ("AFC Asian Cup", 2023): 2024,
        ("Copa América", 2021): 2021}
irows = []
for _, e in ed.iterrows():
    t = e.competition_name
    y = int(e.season)
    yy = YEAR.get((t, y), y)
    sub = ia[(ia.tournament == t) & (ia.match_date.str[:4].astype(int) == yy)]
    if t == "UEFA Euro" and y == 2020:
        sub = ia[(ia.tournament == t) & (ia.match_date.str[:4] == "2021")]
    irows.append(dict(scope="international", competition_id=e.competition_id, competition_name=t, competition_type="international_tournament", season=str(y),
                      expected_matches=int(e.expected_matches), expected_evidence=e.expected_evidence, evidence_quality="A", source_records=len(sub),
                      source_declared_total=None, verified_scores=len(sub), missing_results_vs_expected=int(e.expected_matches) - len(sub),
                      unexplained_missing=max(0, int(e.expected_matches) - len(sub)), coverage_pct=round(100 * len(sub) / e.expected_matches, 1),
                      cancelled=0, postponed=0, abandoned=0, awarded=0, unscored_date_passed=0, uncertain_status_or_label=len(sub),
                      duplicate_fixtures=int(sub.duplicated("key").sum()), latest_completed_date=sub.match_date.max() if len(sub) else None,
                      label90_confirmed=0, label90_inferred=0, label90_unknown=len(sub), sources="martj42/international_results", season_in_progress=False,
                      prior_report_verified=None, prior_report_difference=None, independent_ml_suitability="NOT_90MIN_LABELLED"))
ics = pd.DataFrame(irows)
# international category summary rows (no authoritative expected count)
for catg, g in ia.groupby("competition_category", dropna=True):
    if pd.isna(catg):
        continue
    irows2 = dict(scope="international", competition_id="INTL-CATEGORY:" + str(catg), competition_name=str(catg), competition_type="category_aggregate", season="all",
                  expected_matches=None, expected_evidence="no authoritative count", evidence_quality="D", source_records=len(g), source_declared_total=None,
                  verified_scores=len(g), missing_results_vs_expected=None, unexplained_missing=None, coverage_pct=None, cancelled=0, postponed=0, abandoned=0, awarded=0,
                  unscored_date_passed=0, uncertain_status_or_label=len(g), duplicate_fixtures=int(g.duplicated("key").sum()), latest_completed_date=g.match_date.max(),
                  label90_confirmed=0, label90_inferred=0, label90_unknown=len(g), sources="martj42/international_results", season_in_progress=False,
                  prior_report_verified=None, prior_report_difference=None, independent_ml_suitability="NOT_90MIN_LABELLED")
    ics = pd.concat([ics, pd.DataFrame([irows2])], ignore_index=True)
full = pd.concat([cs, ics], ignore_index=True)
full.to_csv(os.path.join(OUT, "03_COMPETITION_SEASON_VERIFICATION.csv"), index=False, encoding=ENC)
print(len(cs), "club comp-seasons;", len(ics), "international rows")
print(full.independent_ml_suitability.value_counts().to_string())
dif = cs[cs.prior_report_difference.fillna(0) != 0]
print("rows where independent verified count differs from prior report:", len(dif))
print(dif[["competition_id", "season", "verified_scores", "prior_report_verified"]].head(10).to_string())
print(ics[["competition_name", "season", "expected_matches", "verified_scores"]][ics.expected_matches.notna() & (ics.expected_matches != ics.verified_scores)].to_string())

# ---- season label vs date consistency
def season_ok(s, dt):
    y = int(dt[:4]); mth = int(dt[5:7])
    if re.match(r"^\d{4}-\d{2}$", s):
        a = int(s[:4])
        return (y == a and mth >= 6) or (y == a + 1 and mth <= 8)
    if re.match(r"^\d{4}$", s):
        return abs(y - int(s)) <= 1
    return True


dd = d[d.match_date.notna()]
bad = dd[[not season_ok(s, x) for s, x in zip(dd.season, dd.match_date)]]
bad_cm = cm[cm.match_date.notna()]
bad_cm = bad_cm[[not season_ok(s, x) for s, x in zip(bad_cm.season, bad_cm.match_date)]]
bad_cm.groupby(["competition_id", "season"]).size().reset_index(name="rows").to_csv(os.path.join(EV, "season_label_date_inconsistent_openfootball.csv"), index=False)
print("04d rows with season/date inconsistency:", len(bad), "; openfootball rows:", len(bad_cm))
json.dump(dict(rows_04d_season_date_inconsistent=len(bad), openfootball_rows_season_date_inconsistent=len(bad_cm),
               header_mismatch_files=len(header_vs_parsed)), open(os.path.join(EV, "v2b_summary.json"), "w"))
