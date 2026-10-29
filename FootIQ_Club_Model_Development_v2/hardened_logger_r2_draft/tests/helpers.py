"""Shared test helpers. Variants of the real pilot snapshot built here are TEST INPUTS in temp folders; they are never stored as data."""
import copy, glob, hashlib, json, os, sys, tempfile
from email.utils import format_datetime

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from hardened import approval, artifacts, engine, ledger, state
from footiq_sources.reconcile import build_resolver

RUN = sorted(glob.glob(os.path.join(artifacts.V2, "source_adapters_r1", "pilot", "run_*")))[-1]
R3 = glob.glob(os.path.join(RUN, "snapshots", "openligadb", "*R3_getmatchdata*.json"))[0]
BASE = json.load(open(R3, encoding="utf-8"))
T0 = state.ts(json.load(open(R3 + ".meta.json"))["saved_utc"])
NEW_RESULTS = [m for m in BASE if m["matchIsFinished"] and m["matchDateTimeUTC"][:10] > state.CUTOFF]
TMP = tempfile.mkdtemp(prefix="footiq_hardened_tests_")
_G = {}


def universe():
    if "V" not in _G:
        _G["V"] = pd.read_pickle(artifacts.canonical_paths()["universe"])
        _G["VS"] = _G["V"][_G["V"].match_date >= "2025-07-01"].copy()
        _G["RES"] = build_resolver(_G["V"])
    return _G["V"], _G["VS"], _G["RES"]


def pin():
    if "PIN" not in _G:
        _G["PIN"] = artifacts.load_pin()
    return _G["PIN"]


def mk_snap(matches, retrieved, label, skew_s=2.0, bump=True):
    body = json.dumps(matches).encode("utf-8")
    p = os.path.join(TMP, f"{label}.json")
    with open(p, "wb") as fh:
        fh.write(body)
    r = state.ts(retrieved)
    meta = dict(sha256=hashlib.sha256(body).hexdigest(), saved_utc=r.strftime("%Y-%m-%dT%H:%M:%SZ"), snapshot_id=label + ".json", plan_sha256="test")
    if skew_s is not None:
        meta["headers"] = {"Date": format_datetime((r - pd.Timedelta(seconds=skew_s)).to_pydatetime(), usegmt=True)}
    with open(p + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    return state.load_snapshot(p)


def real_snap():
    if "REAL" not in _G:
        _G["REAL"] = state.load_snapshot(R3)
    return _G["REAL"]


def edit(matches, mid, fn, bump_update="2026-10-21T19:00:00"):
    out = copy.deepcopy(matches)
    for m in out:
        if m["matchID"] == mid:
            fn(m)
            m["lastUpdateDateTime"] = bump_update
    return out


def strip_results(matches, ids):
    def f(m):
        m["matchIsFinished"] = False; m["matchResults"] = []
    out = copy.deepcopy(matches)
    for m in out:
        if m["matchID"] in ids: f(m)
    return out


def set_score(m, h, a):
    for r in m["matchResults"]:
        if r["resultTypeKind"] == "After90Minutes":
            r["pointsTeam1"], r["pointsTeam2"] = h, a


def state_at(snaps, T, **kw):
    V, VS, RES = universe()
    return state.merged_state(VS, snaps, T, RES, "test", **kw)


def predict(snaps, T, **kw):
    V, VS, RES = universe()
    return engine.predict_core(VS, snaps, T, RES, pin(), **kw)


def mk_protocol(content="# protocol r2 test file\n"):
    p = os.path.join(TMP, "protocol_r2_test.md")
    open(p, "w", encoding="utf-8").write(content)
    return p


def mk_approval(now, name="approval.json", **over):
    hashes = engine.E.verify_models(); msha = artifacts.manifest_sha(artifacts.manifest())
    proto = mk_protocol()
    a = dict(approval_version=1, approved_by="test-owner", approved_utc=(now - pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), expires_utc=(now + pd.Timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             mode="official", protocol=dict(version="r2", sha256=artifacts.digest_file(proto), path=proto), models=hashes, artifact_manifest_sha256=msha, competition_id=state.COMP, season=state.SEASON,
             source_scope={"openligadb": {"league": "bl1", "season": "2026"}}, sealing_window=dict(start_utc=(now - pd.Timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"), end_utc=(now + pd.Timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")),
             max_fixtures=300, matchdays=[7, 8])
    a.update(over)
    p = os.path.join(TMP, name)
    json.dump(a, open(p, "w", encoding="utf-8"))
    return p, a
