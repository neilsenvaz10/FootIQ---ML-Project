"""Phase 4.38 maintainer tool: lists, from a store rebuilt in `snapshot` mode, the records that depend on the opt-in ATTESTED evidence mode, and the results that stay missing.
    python scripts/list_attested_records.py <replay.sqlite> [output_folder]
Writes ATTESTED_RECORDS.csv (80 results + 31 fixture-date corrections, each marked independently_reproducible = false, with source references and review provenance from the published evidence file)
and UNSUPPORTED_RESULTS.csv (results that no redistributable evidence supports: they stay missing). No restricted provider value is read or written."""
import csv
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "evidence" / "published"
ev = pd.read_csv(ROOT / "data" / "evidence" / "published" / "published_evidence_2026-10-28.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False).set_index("evidence_id")
c = sqlite3.connect(f"file:{DB.resolve().as_posix()}?mode=ro", uri=True)
LABEL = "attested, NOT independently reproducible from public data: one redistributable source supports the value; the maintainer attests a private cross-check agreed (not published)"
rows = []
for src, ref, rid, prov, rev in c.execute("SELECT source, source_ref, record_id, provenance, source_revision FROM match_sources WHERE provenance LIKE '%attested snapshot evidence%'"):
    m = c.execute("SELECT competition_key, home_name, away_name, match_date, status, home_goals_final, away_goals_final FROM matches WHERE record_id=?", (rid,)).fetchone()
    eid = ref.split(":", 1)[1] if ref.startswith("RECON:") else None
    if eid is None:                                                                           # league-results importer: the evidence id is LR-<record suffix>-<competition>
        cand = ev[(ev.record_id == rid) & (ev.importer == "league_results")]
        eid = cand.index[0] if len(cand) else ""
    e = ev.loc[eid] if eid in ev.index else None
    is_result = m[4] in ("completed", "awarded") and (ev.loc[eid, "action"] != "correct_date" if e is not None else True)
    rows.append(dict(kind="result" if is_result else "fixture_date_correction", competition_key=m[0], record_id=rid, home=m[1], away=m[2], match_date=m[3],
                     score=f"{m[5]}-{m[6]}" if is_result else "", evidence_id=eid, action=e["action"] if e is not None else "",
                     source_reference=(f"Wikipedia revision {rev or (e['wikipedia_revision'] if e is not None else '')} (CC BY-SA 4.0)" if is_result else "openfootball / OpenLigaDB date recorded in the evidence file"),
                     review_decision=e["review_decision"] if e is not None else "", confidence="attested_single_redistributable_source", uncertainty=e["uncertainty"] if e is not None else "",
                     licence=e["licence"] if e is not None else "", independently_reproducible="false", label=LABEL))
rows.sort(key=lambda r: (r["kind"], r["competition_key"], r["match_date"], r["record_id"]))
cols = list(rows[0].keys())
with open(OUT / "ATTESTED_RECORDS.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
miss = []
for eid, e in ev[(ev.importer == "reconcile") & (ev.action == "add_result_with_date")].iterrows():
    m = c.execute("SELECT status, match_date, home_name, away_name FROM matches WHERE record_id=?", (e["record_id"],)).fetchone()
    if m and m[0] not in ("completed", "awarded"):
        miss.append(dict(competition_key=e["competition_key"], record_id=e["record_id"], home=m[2], away=m[3], store_status=m[0], store_date=m[1], evidence_id=eid,
                         reason="the played day is carried only by a restricted source; no redistributable source supports it, so the result stays missing", independently_reproducible="false"))
with open(OUT / "UNSUPPORTED_RESULTS.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(miss[0].keys()) if miss else ["record_id"]); w.writeheader(); w.writerows(miss)
n_res = sum(r["kind"] == "result" for r in rows)
print(f"attested results {n_res}, fixture-date corrections {len(rows) - n_res}, unsupported results kept missing {len(miss)}")
