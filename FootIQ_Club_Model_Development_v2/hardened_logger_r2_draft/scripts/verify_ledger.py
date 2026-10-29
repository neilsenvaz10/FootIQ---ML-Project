import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Verify an append-only ledger and its external anchor (read-only unless --recover is given explicitly)."""
import argparse, sys
from _common import *
ap = argparse.ArgumentParser(); ap.add_argument("--ledger", default=engine.CANON_LEDGER); ap.add_argument("--anchor", default=engine.CANON_ANCHOR); ap.add_argument("--recover", action="store_true"); a = ap.parse_args()
if not os.path.isdir(a.ledger):
    out(dict(ledger_exists=False, ok=True, note="no ledger yet (nothing has been sealed)")); sys.exit(0)
led = ledger.ChainedLedger(a.ledger, a.anchor)
if a.recover:
    out(dict(recover_actions=led.recover()))
v = led.verify()
out(dict(ok=v["ok"], errors=v["errors"], batches=v["batches"], records=v["records"], last_batch_sha256=v["last_batch_sha256"]))
sys.exit(0 if v["ok"] else 1)
