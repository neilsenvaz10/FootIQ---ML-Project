import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Fixture reassessment side-car: never edits sealed records; appends to its OWN chained ledger when --write is given. Run after every manual poll."""
import argparse, sys
from _common import *
ap = argparse.ArgumentParser(); ap.add_argument("--snapshot", action="append", required=True); ap.add_argument("--ledger", default=engine.CANON_LEDGER); ap.add_argument("--anchor", default=engine.CANON_ANCHOR)
ap.add_argument("--checkpoint", action="store_true"); ap.add_argument("--write", action="store_true"); a = ap.parse_args()
if not os.path.isdir(a.ledger):
    out(dict(note="no official ledger: nothing to reassess")); sys.exit(0)
led = ledger.ChainedLedger(a.ledger, a.anchor); v = led.verify()
if not v["ok"]:
    out(dict(refused=True, errors=v["errors"])); sys.exit(2)
_, resolver = load_universe(); snaps = [state.load_snapshot(p) for p in a.snapshot]
res = engine.reassess(led.records(), snaps, engine._now(), resolver, analysis_checkpoint=a.checkpoint)
if a.write:
    side = ledger.ChainedLedger(a.ledger.rstrip("\\/") + "_reassessment", a.anchor.replace("anchor.jsonl", "anchor_reassessment.jsonl"), key_fields=("fixture_id", "assessment_key"))
    out(side.append_batch(res, "reassess_" + engine._now().strftime("%Y%m%dT%H%M%SZ")))
else:
    out(dict(assessments=len(res), by_eligibility=pd.Series([r["evaluation_eligibility"] for r in res]).value_counts().to_dict(), by_label=pd.Series([r["label_status"] for r in res]).value_counts().to_dict()))
