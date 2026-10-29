"""Phase 4.8D Stage 1: before/after predictions for the approved imports. PRIVATE COPIES ONLY (nothing is saved to production).

BEFORE = the production file as it was before the imports (the verified backup restore); AFTER = production now (post-import), copied. The same gameweek is forecast on both with
the same clock (2026-10-27 15:00 UTC) and the frozen club models. Also: schemas, model hashes, past-fixture refusal, production forecasts still empty.
"""
import json
import os
import shutil
import sqlite3
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
for p in (str(ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"), str(ROOT / "FootIQ_ML_Training_Preparation" / "_build")):
    sys.path.insert(0, p)
import analytics  # noqa: E402
import forecast  # noqa: E402
import predict  # noqa: E402
from store import baseline_hash, db  # noqa: E402

OUT = ROOT / "data" / "supervised" / "phase4" / "p48d"
PROD = ROOT / "data" / "footiq.sqlite"
BEFORE_SRC = OUT / "restore_test_bundesliga.sqlite"
NOW = datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)
CASES = [("BUNDESLIGA", 8, "bundesliga"), ("LALIGA", 11, "laliga")]


def rows(path, sql, *a):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def run_state(path, tag):
    db.DEFAULT_PATH = path
    analytics.reload()
    predict.reset_club_state()
    out = {}
    for key, md, _ in CASES:
        r = forecast.predict_gameweek(key, "2026-27", md, forecast.EXPLICIT_ACTION, now=NOW, today=NOW.date(), db_path=path)
        feats = {}
        for fx in r["forecasts"]:
            f1 = json.loads(rows(path, "SELECT feature_snapshot_json s FROM forecasts WHERE forecast_run_id=? AND record_id=? AND model_variant='club_v1'", r["forecast_run_id"], fx["record_id"])[0]["s"])
            f2 = json.loads(rows(path, "SELECT feature_snapshot_json s FROM forecasts WHERE forecast_run_id=? AND record_id=? AND model_variant='club_v2_r1'", r["forecast_run_id"], fx["record_id"])[0]["s"])
            feats[fx["record_id"]] = (f1, f2)
        out[key] = dict(run=r, feats=feats)
    return out


def main():
    prod_before = baseline_hash.physical_sha256(PROD)
    work = OUT / "pred_work"
    if work.exists():
        shutil.rmtree(work, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))
    work.mkdir(parents=True)
    before, after = work / "before.sqlite", work / "after.sqlite"
    shutil.copyfile(BEFORE_SRC, before)
    for e in ("", "-wal", "-shm"):
        if Path(str(PROD) + e).exists():
            shutil.copyfile(str(PROD) + e, str(after) + e)
    for p in (before, after):
        c = sqlite3.connect(p)
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        c.execute("PRAGMA journal_mode=DELETE")
        c.close()
    forecast.artifact_hashes.cache_clear()
    B = run_state(before, "before")
    A = run_state(after, "after")
    rep = dict(clock=NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), model_artifact_sha256=forecast.artifact_hashes(), leagues={})
    for key, md, _ in CASES:
        rb, ra = B[key]["run"], A[key]["run"]
        fixtures = []
        for fx in ra["forecasts"]:
            ob = next(x for x in rb["forecasts"] if x["record_id"] == fx["record_id"])
            (b1, b2), (a1, a2) = B[key]["feats"][fx["record_id"]], A[key]["feats"][fx["record_id"]]
            changed1 = {k: [b1[k], a1[k]] for k in a1 if b1[k] != a1[k] and not (b1[k] != b1[k] and a1[k] != a1[k])}
            fixtures.append(dict(fixture=f"{fx['home']} v {fx['away']}", date=fx["date"], v1_schema_identical=sorted(a1) == sorted(b1), v2_schema_identical=sorted(a2) == sorted(b2), v1_inputs=len(a1), v2_inputs=len(a2),
                                 v1_inputs_changed=len(changed1), v2_inputs_changed=sum(1 for k in a2 if b2[k] != a2[k]),
                                 v1_before=[round(x, 4) for x in ob["predictions"]["primary"].values()], v1_after=[round(x, 4) for x in fx["predictions"]["primary"].values()],
                                 v2_before=[round(x, 4) for x in ob["predictions"]["secondary"].values()], v2_after=[round(x, 4) for x in fx["predictions"]["secondary"].values()],
                                 key_inputs={k: changed1[k] for k in changed1 if k.endswith(("_elo", "_ppg5", "_n_prior", "_gf5", "_ga5", "_days_rest"))}))
        rep["leagues"][key] = dict(matchday=md, data_cutoff_before=rb["data_cutoff_date"], data_cutoff_after=ra["data_cutoff_date"], fixtures=fixtures,
                                   max_abs_probability_change_v1=max((abs(x - y) for f in fixtures for x, y in zip(f["v1_before"], f["v1_after"])), default=0.0))
    # a fixture past its kickoff cannot get a new pre-match prediction (checked on the AFTER copy; matchday 7 was played on 2026-10-25)
    db.DEFAULT_PATH = after
    refusals = {}
    for key, md in (("BUNDESLIGA", 7), ("LALIGA", 10)):
        try:
            forecast.predict_gameweek(key, "2026-27", md, forecast.EXPLICIT_ACTION, now=NOW, today=NOW.date(), db_path=after)
            refusals[key] = "NOT REFUSED"
        except forecast.ForecastError as exc:
            refusals[key] = str(exc)[:160]
    rep["past_fixture_refusals"] = refusals
    rep["production_forecast_rows"] = rows(PROD, "SELECT (SELECT COUNT(*) FROM forecasts) f, (SELECT COUNT(*) FROM forecast_runs) r")[0]
    rep["production_sha256_before"], rep["production_sha256_after"] = prod_before, baseline_hash.physical_sha256(PROD)
    rep["production_untouched"] = prod_before == rep["production_sha256_after"]
    (OUT / "after_import_predictions.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    db.DEFAULT_PATH = PROD
    analytics.reload()
    shutil.rmtree(work, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))
    print(json.dumps({k: rep[k] for k in rep if k != "leagues"}, indent=1, default=str)[:2500])
    for key, L in rep["leagues"].items():
        print(key, L["matchday"], L["data_cutoff_before"], L["data_cutoff_after"], L["max_abs_probability_change_v1"])
        for f in L["fixtures"]:
            if f["v1_inputs_changed"]:
                print("  ", f["fixture"], f["date"], f["v1_before"], "->", f["v1_after"], "| v2", f["v2_before"], "->", f["v2_after"], f["v1_inputs_changed"], f["v2_inputs_changed"])


if __name__ == "__main__":
    main()
