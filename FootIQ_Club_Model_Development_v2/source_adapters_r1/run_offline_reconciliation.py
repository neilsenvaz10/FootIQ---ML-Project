"""Offline reconciliation of the stored OpenLigaDB and Wikipedia snapshots against the frozen openfootball universe (read-only). Writes only to reports/."""
import glob, json, os, sys
import pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from datetime import datetime, timezone
from footiq_sources import openligadb as ol, wikipedia_matrix as wm
from footiq_sources.reconcile import build_resolver, reconcile_source
sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"; V_PATH = os.path.join(P, "FootIQ_ML_Training_Preparation", "_build", "work", "V_universe.pkl")
OUT = os.path.join(ROOT, "reports"); os.makedirs(OUT, exist_ok=True)
ING = os.path.join(P, "FootIQ_Club_Model_Development_v2", "matched_v1_prospective_r1", "ingestion", "runs")
selfrun = sorted(glob.glob(os.path.join(ING, "selftest_*")))[-1]
RUN_DATE = "2026-10-21"; NOW = datetime(2026, 10, 21, 14, 0, tzinfo=timezone.utc)
V = pd.read_pickle(V_PATH)
fx = pd.read_csv(os.path.join(selfrun, "fixtures.csv"), encoding="utf-8-sig", low_memory=False)
un = pd.read_csv(os.path.join(selfrun, "unresolved_or_non_completed.csv"), encoding="utf-8-sig", low_memory=False)
pnr = un[un.status == "past_date_no_result"]
res = build_resolver(V)
summ = {}
# ------------------------------------------------ OpenLigaDB Bundesliga 2026 (snapshot retrieved 2026-10-21)
payload = open(os.path.join(ROOT, "evidence", "openligadb_bl1_2026.json"), "rb").read()
recs = ol.parse_payload(payload, "2026-10-21T13:35:00Z", "openligadb_bl1_2026_snapshot", NOW, "deutschland:1-bundesliga")
comp = "deutschland:1-bundesliga"
miss = pnr[pnr.competition_id == comp].rename(columns={})[["home_entity_id", "away_entity_id", "match_date"]]
out = reconcile_source(recs, "openligadb", comp, "2026-27", V, miss, res, RUN_DATE)
for k, v in out.items():
    if isinstance(v, pd.DataFrame): v.to_csv(os.path.join(OUT, f"openligadb_bl1_{k}.csv"), index=False, encoding="utf-8-sig")
s = out["summary"]; allf = out["all"]
s["kickoff_utc_present_share"] = float(sum(r.kickoff_utc is not None for r in recs) / len(recs))
s["label_eligible_90min_completed"] = int(sum(r.label_eligible_90min for r in recs))
s["upcoming_records"] = int(sum(r.status == "upcoming" for r in recs)); s["past_date_no_result_records"] = int(sum(r.status == "past_date_no_result" for r in recs))
s["openfootball_missing_for_competition"] = int(len(miss)); s["of_missing_recovered_by_source"] = s["newly_recovered"]
s["latest_source_update_stamp"] = max(r.source_revision for r in recs); s["snapshot_retrieved_utc"] = "2026-10-21T13:35:00Z"
summ["openligadb_bl1_2026"] = s; print(s)
# ------------------------------------------------ Wikipedia Premier League 2026-27 (revision 1381300885)
rev = json.load(open(os.path.join(ROOT, "evidence", "pl_2026_27.json"), encoding="utf-8"))["query"]["pages"][0]["revisions"][0]
title = "2026\u201327 Premier League"; comp = "england:1-premierleague"
wrecs, meta = wm.parse_wikitext(rev["slots"]["main"]["content"], title, rev["revid"], rev["timestamp"], "2026-10-21T12:51:00Z", "wikipedia_pl_2026_27_snapshot")
for r in wrecs: r.season = "2026-27"
sched = pd.concat([V[(V.competition_id == comp) & (V.season_corrected == "2026-27")][["match_date", "home_entity_id", "away_entity_id"]],
                   fx[fx.competition_id == comp][["match_date", "home_entity_id", "away_entity_id"]],
                   pnr[pnr.competition_id == comp][["match_date", "home_entity_id", "away_entity_id"]]]).assign(competition_id=comp, season="2026-27")
sched["match_date"] = sched.match_date.astype(str)
ok, bad = wm.attach_schedule_dates(wrecs, sched.to_dict("records"), res, comp, meta["page_update_date"])
miss = pnr[pnr.competition_id == comp][["home_entity_id", "away_entity_id", "match_date"]]
out2 = reconcile_source(ok, "wikipedia", comp, "2026-27", V, miss, res, RUN_DATE)
for k, v in out2.items():
    if isinstance(v, pd.DataFrame): v.to_csv(os.path.join(OUT, f"wikipedia_pl_{k}.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame([dict(source_ref=r.source_ref, reason=why) for r, why in bad]).to_csv(os.path.join(OUT, "wikipedia_pl_rejected.csv"), index=False)
s2 = out2["summary"]; s2.update(page_title=title, revid=rev["revid"], revision_timestamp=rev["timestamp"], page_update_date=meta["page_update_date"], scored_cells=meta["n_scored"], unresolved_cells=meta["n_unresolved_cells"],
                               accepted_with_inherited_dates=len(ok), rejected=len(bad), rejected_reasons=pd.Series([w for _, w in bad]).value_counts().to_dict(),
                               records_with_source_stated_kickoff=0, all_dates_inherited_flagged=all(r.date_provenance == "inherited_from_openfootball_schedule" for r in ok),
                               openfootball_missing_for_competition=int(len(miss)), permalink=meta["permalink"])
summ["wikipedia_pl_2026_27"] = s2; print(s2)
# ------------------------------------------------ kickoff-time availability in openfootball schedule (for comparison)
summ["openfootball_upcoming_kickoff_local_present_share"] = float(fx.kickoff_local.notna().mean())
json.dump(summ, open(os.path.join(OUT, "reconciliation_summary.json"), "w"), indent=1, default=str)
