import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Outcome reconciliation from the reassessment side-car (confirmed labels; conflicts needing adjudication). Read-only."""
import argparse, sys
from _common import *
ap = argparse.ArgumentParser(); ap.add_argument("--ledger", default=engine.CANON_LEDGER); ap.add_argument("--anchor", default=engine.CANON_ANCHOR); a = ap.parse_args()
side = ledger.ChainedLedger(a.ledger.rstrip("\\/") + "_reassessment", a.anchor.replace("anchor.jsonl", "anchor_reassessment.jsonl"), key_fields=("fixture_id", "assessment_key"))
if not os.path.isdir(side.root):
    out(dict(note="no reassessment ledger yet")); sys.exit(0)
v = side.verify()
if not v["ok"]:
    out(dict(refused=True, errors=v["errors"])); sys.exit(2)
latest = {}
for r in side.records():
    latest[(r["fixture_id"], r["model_key"])] = r
out(dict(outcomes=engine.reconcile_results(list(latest.values()))))
