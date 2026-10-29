import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Pre-sealing checks. Read-only. Exit 1 if any check fails. Never prints the contact."""
import argparse, subprocess, sys
from _common import *
ap = argparse.ArgumentParser(); ap.add_argument("--snapshot", action="append", default=[]); ap.add_argument("--approval", default=approval.CANONICAL_APPROVAL)
ap.add_argument("--ledger", default=engine.CANON_LEDGER); ap.add_argument("--anchor", default=engine.CANON_ANCHOR); a = ap.parse_args()
now = engine._now(); rows = []


def chk(name, ok, detail=""):
    rows.append(dict(check=name, ok=bool(ok), detail=detail))


hashes = engine.E.verify_models(); mf = artifacts.manifest(); msha = artifacts.manifest_sha(mf)
chk("model artifacts match their frozen records", True, ", ".join(hashes))
try:
    pr = artifacts.verify(artifacts.load_pin()); chk("artifact manifest equals the pinned draft manifest", not pr, "; ".join(pr[:3]))
except OSError:
    chk("pinned manifest present", False)
try:
    approval.validate_approval(a.approval, now, expected_models=hashes, expected_manifest_sha=msha, competition_id=state.COMP, season=state.SEASON); chk("approval file valid", True)
except approval.ApprovalError as e:
    chk("approval file valid", False, "; ".join(e.problems[:3]))
chk("official mode switch (info only)", True, "FOOTIQ_OFFICIAL_MODE=1" if os.environ.get("FOOTIQ_OFFICIAL_MODE") == "1" else "off (default)")
if os.path.isdir(a.ledger):
    v = ledger.ChainedLedger(a.ledger, a.anchor).verify(); chk("ledger + anchor verify", v["ok"], "; ".join(v["errors"][:3]))
else:
    chk("ledger + anchor verify", True, "no ledger yet")
snaps = []
for p in a.snapshot:
    try:
        snaps.append(state.load_snapshot(p)); chk(f"snapshot {os.path.basename(p)}: hash, scope, parse", True)
    except Exception as e:
        chk(f"snapshot {os.path.basename(p)}", False, type(e).__name__)
if snaps:
    try:
        state.check_order(snaps); chk("snapshot order and monotone content", True)
    except Exception as e:
        chk("snapshot order and monotone content", False, str(e)[:120])
    n = max(snaps, key=lambda s: s.retrieved); age = (now - n.retrieved).total_seconds() / 3600
    chk("newest snapshot within 24 h", 0 <= age <= 24, f"{age:.2f} h")
    chk("poll-time clock skew <= 120 s", n.clock_skew_s is not None and abs(n.clock_skew_s) <= 120, str(n.clock_skew_s))
chk("contact file present (value not shown)", os.path.exists(os.environ.get("FOOTIQ_CONTACT_FILE", os.path.join(artifacts.P, "config", "contact.local"))))
chk("contact file git-ignored", subprocess.run(["git", "-C", artifacts.P, "check-ignore", "-q", "config/contact.local"]).returncode == 0)
st = subprocess.run(["git", "-C", artifacts.P, "diff", "--cached", "--name-only"], capture_output=True, text=True).stdout.split()
chk("nothing staged in git", not st, f"{len(st)} staged")
out(dict(time_utc=str(now), passed=all(r["ok"] for r in rows), checks=rows))
sys.exit(0 if all(r["ok"] for r in rows) else 1)
