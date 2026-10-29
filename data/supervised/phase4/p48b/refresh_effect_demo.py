"""Phase 4.8B: how refreshed (imported) results change NEW predictions and leave saved ones alone. Private copies only; no network; production untouched.

State A = baseline + Bundesliga pilot payload (results to 2026-10-18). State B = A + the stored 2026-10-25 season payload (results to 2026-10-24).
The same gameweek (the one after the newest imported matchday) is forecast as of 2026-10-19 in A, then the refresh is applied to the SAME copy and it is forecast again as of 2026-10-25.
"""
import json
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
for p in (str(ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"), str(ROOT / "FootIQ_ML_Training_Preparation" / "_build")):
    sys.path.insert(0, p)
import analytics  # noqa: E402
import forecast  # noqa: E402
import predict  # noqa: E402
from store import baseline, db, sync  # noqa: E402

PILOT = ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1" / "pilot" / "run_20261021T141224Z" / "snapshots" / "openligadb" / "20261021T141231Z_R3_getmatchdata_bl1_2026.json"
LIVE = sorted((ROOT / "data" / "snapshots" / "openligadb").glob("*_bl1_2026_season.json"))[-1]
OUT = ROOT / "data" / "supervised" / "phase4" / "p48b" / "refresh_effect_demo.json"
KEY, SEASON = "BUNDESLIGA", "2026-27"


def rows(path, sql, *a):
    c = db.connect(path)
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def main():
    d = Path(tempfile.mkdtemp(prefix="p48b_demo_"))
    p = d / "demo.sqlite"
    c = db.connect(p)
    db.init(c)
    baseline.import_baseline(c)
    sync.replay_payload(c, PILOT.read_bytes(), now=datetime(2026, 10, 21, 14, 12, tzinfo=timezone.utc))
    newest_md = c.execute("select max(matchday_no) from matches where competition_key=? and season=? and status='completed'", (KEY, SEASON)).fetchone()[0]
    c.close()
    db.DEFAULT_PATH = p
    analytics.reload()
    predict.reset_club_state()
    md = newest_md + 2                                                  # the matchday after the one the refresh completes (A ends at matchday 6, the refresh completes 7)
    r1 = forecast.predict_gameweek(KEY, SEASON, md, forecast.EXPLICIT_ACTION, now=datetime(2026, 10, 19, 9, tzinfo=timezone.utc), today=date(2026, 10, 19), db_path=p)
    saved1 = rows(p, "SELECT * FROM forecasts ORDER BY forecast_id")
    c = db.connect(p)
    stats = sync.replay_payload(c, LIVE.read_bytes(), now=datetime(2026, 10, 25, 9, tzinfo=timezone.utc))
    c.close()
    predict.reset_club_state()
    analytics.reload()
    r2 = forecast.predict_gameweek(KEY, SEASON, md, forecast.EXPLICIT_ACTION, now=datetime(2026, 10, 25, 9, tzinfo=timezone.utc), today=date(2026, 10, 25), db_path=p)
    saved_after = rows(p, "SELECT * FROM forecasts ORDER BY forecast_id")
    feat = lambda rid, run: json.loads(rows(p, "SELECT feature_snapshot_json s FROM forecasts WHERE forecast_run_id=? AND record_id=? AND model_variant='club_v1'", run, rid)[0]["s"])  # noqa: E731
    out = []
    for f2 in r2["forecasts"]:
        f1 = next(x for x in r1["forecasts"] if x["record_id"] == f2["record_id"])
        a, b = feat(f1["record_id"], r1["forecast_run_id"]), feat(f2["record_id"], r2["forecast_run_id"])
        v2 = lambda rid, run: json.loads(rows(p, "SELECT feature_snapshot_json s FROM forecasts WHERE forecast_run_id=? AND record_id=? AND model_variant='club_v2_r1'", run, rid)[0]["s"])  # noqa: E731
        a2, b2 = v2(f1["record_id"], r1["forecast_run_id"]), v2(f2["record_id"], r2["forecast_run_id"])
        changed2 = sorted(k for k in a2 if a2[k] != b2[k] and not (a2[k] != a2[k] and b2[k] != b2[k]))
        watch = [k for k in a2 if k.startswith(("home_perf10", "away_perf10", "home_n_known_30", "away_n_known_30", "home_n_known_14", "away_n_known_14", "home_elo2", "away_elo2"))]
        out.append(dict(v2_inputs=len(a2), v2_inputs_changed=len(changed2), v2_schema_identical=sorted(a2) == sorted(b2), v2_selected={k: [a2[k], b2[k]] for k in watch},
                        v2_probabilities=[[round(x, 4) for x in f1["predictions"]["secondary"].values()], [round(x, 4) for x in f2["predictions"]["secondary"].values()]], fixture=f"{f2['home']} v {f2['away']}", date=f2["date"],
                        v1_before=[round(x, 4) for x in f1["predictions"]["primary"].values()], v1_after=[round(x, 4) for x in f2["predictions"]["primary"].values()],
                        home_n_prior=[a["home_n_prior"], b["home_n_prior"]], away_n_prior=[a["away_n_prior"], b["away_n_prior"]],
                        home_ppg5=[round(a["home_ppg5"], 3), round(b["home_ppg5"], 3)], away_ppg5=[round(a["away_ppg5"], 3), round(b["away_ppg5"], 3)],
                        home_elo=[round(a["home_elo"], 1), round(b["home_elo"], 1)], away_elo=[round(a["away_elo"], 1), round(b["away_elo"], 1)]))
    rep = dict(matchday=md, refresh_import=stats, cutoff_before=r1["data_cutoff_date"], cutoff_after=r2["data_cutoff_date"], saved_rows_unchanged_by_refresh_and_second_run=saved_after[: len(saved1)] == saved1,
               forecast_runs_kept=len(rows(p, "SELECT forecast_run_id FROM forecast_runs")), fixtures=out,
               max_abs_probability_change=max(abs(x - y) for o in out for x, y in zip(o["v1_before"], o["v1_after"])))
    OUT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    shutil.rmtree(d, ignore_errors=True)
    print(json.dumps({k: v for k, v in rep.items() if k != "fixtures"}, default=str))
    for o in out[:4]:
        print(o)


if __name__ == "__main__":
    main()
