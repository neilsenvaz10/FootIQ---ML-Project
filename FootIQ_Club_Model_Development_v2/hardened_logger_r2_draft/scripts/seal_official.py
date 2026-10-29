import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""OFFICIAL sealing. Refuses unless --official AND FOOTIQ_OFFICIAL_MODE=1 AND a valid owner approval exists. There is no timestamp argument (system clock only).
NOT to be run until the owner has authorised it. `--sandbox` (tests only) requires all paths inside the system temp directory."""
import argparse, sys
from _common import *
ap = argparse.ArgumentParser(); ap.add_argument("--official", action="store_true"); ap.add_argument("--sandbox", action="store_true")
ap.add_argument("--approval", default=approval.CANONICAL_APPROVAL); ap.add_argument("--snapshot", action="append", required=True)
ap.add_argument("--ledger", default=engine.CANON_LEDGER); ap.add_argument("--anchor", default=engine.CANON_ANCHOR); ap.add_argument("--batch-id"); a = ap.parse_args()
if not approval.official_mode_enabled(a.official):
    out(dict(refused=True, reason="official mode is off (needs --official and FOOTIQ_OFFICIAL_MODE=1)")); sys.exit(2)
V, resolver = load_universe()
try:
    r = engine.seal_official(approval_path=a.approval, snapshot_paths=a.snapshot, ledger_root=a.ledger, anchor_path=a.anchor, V=V, resolver=resolver, official_flag=a.official, sandbox=a.sandbox,
                             pnr_of=latest_pnr(), batch_id=a.batch_id)
except (approval.ApprovalError, PermissionError, ledger.LedgerError, engine.ClockError, state.IntegrityError, state.ScopeError, state.OutOfOrderError) as e:
    out(dict(refused=True, error=type(e).__name__, detail=str(e)[:600])); sys.exit(2)
out(r)
