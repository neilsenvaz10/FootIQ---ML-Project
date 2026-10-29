import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Validate an approval file (read-only). Usage: validate_approval.py [--approval PATH]. Exit 1 when rejected. Creates nothing."""
import argparse, sys
from _common import *
ap = argparse.ArgumentParser(); ap.add_argument("--approval", default=approval.CANONICAL_APPROVAL); a = ap.parse_args()
hashes = engine.E.verify_models(); msha = artifacts.manifest_sha(artifacts.manifest())
try:
    r = approval.validate_approval(a.approval, engine._now(), expected_models=hashes, expected_manifest_sha=msha, competition_id=state.COMP, season=state.SEASON)
    out(dict(valid=True, approved_by=r["approved_by"], expires_utc=r["expires_utc"], window=r["sealing_window"], max_fixtures=r["max_fixtures"]))
except approval.ApprovalError as e:
    out(dict(valid=False, problems=e.problems)); sys.exit(1)
