import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Operational status (read-only)."""
import argparse
from _common import *
ap = argparse.ArgumentParser(); ap.add_argument("--snapshot", action="append", default=[]); ap.add_argument("--ledger", default=engine.CANON_LEDGER); ap.add_argument("--anchor", default=engine.CANON_ANCHOR); a = ap.parse_args()
out(engine.status_report(a.ledger, a.anchor, [state.load_snapshot(p) for p in a.snapshot]))
