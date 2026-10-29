"""Prediction parity: the application's own forecast routine with team_form old versus variant B, on a SECOND private copy (the routine saves its runs into the store it is given).

    FOOTIQ_STORE_PATH=<private copy> .venv/Scripts/python.exe -X utf8 data/supervised/phase4/p43/parity_predictions.py

For each chosen gameweek, forecast.predict_gameweek runs once with the old team_form and once with variant B, with the same fixed clock. Compared: the returned forecasts (probabilities of
all three model variants, reliability, flags, reasons, pre-kickoff status, feature path) and the rows saved in `forecasts` (probabilities, feature_sha256, made_before_kickoff, reliability, flags).
This is the verification the stage asks for: no prediction or feature may differ. Frozen models are only read. Nothing touches data/footiq.sqlite or the first private copy."""
import json
import shutil
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIVE, private_copy_path, team_form_b, team_form_old  # noqa: E402

import forecast  # noqa: E402
import gameweeks as gw  # noqa: E402
from store import db  # noqa: E402

src = private_copy_path()
copy = src.with_name("phase4_p43_pred.sqlite")
if not copy.exists():
    shutil.copyfile(src, copy)
assert "rehearsal" in copy.parts

NOW = datetime(2026, 10, 27, 5, 0, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 27)
conn = db.connect(copy, readonly=True)
targets = []
for key in FIVE:
    lst = gw.list_gameweeks(conn, key, gw.seasons(conn, key)[0], TODAY)
    unplayed = [g["matchday_no"] for g in lst["gameweeks"] if g["predictable"] > 0]
    targets += [(key, lst["season"], md) for md in unplayed[:2]]          # the first two gameweeks that still have unplayed fixtures: a mix of awaiting-result and scheduled
conn.close()
print("gameweeks to forecast with each implementation:", targets)

ROWS = "SELECT record_id, model_variant, p_home, p_draw, p_away, feature_sha256, made_before_kickoff, reliability, flags_json FROM forecasts WHERE forecast_run_id=? ORDER BY record_id, model_variant"
report = []
for key, season, md in targets:
    results = {}
    for label, impl in (("old", team_form_old), ("new", team_form_b)):
        gw.team_form = impl
        t = time.perf_counter()
        r = forecast.predict_gameweek(key, season, md, forecast.EXPLICIT_ACTION, now=NOW, today=TODAY, db_path=copy)
        seconds = time.perf_counter() - t
        c = db.connect(copy, readonly=True)
        rows = [tuple(x) for x in c.execute(ROWS, (r["forecast_run_id"],))]
        c.close()
        r2 = {k: v for k, v in r.items() if k != "forecast_run_id"}
        results[label] = (r2, rows, seconds)
    same_payload = json.dumps(results["old"][0], sort_keys=True) == json.dumps(results["new"][0], sort_keys=True)
    same_rows = results["old"][1] == results["new"][1]
    entry = dict(key=key, season=season, matchday=md, fixtures_forecast=results["old"][0]["saved_fixtures"], rows_compared=len(results["old"][1]), same_returned_forecasts=same_payload, same_saved_rows=same_rows,
                 seconds=dict(old=round(results["old"][2], 1), new=round(results["new"][2], 1)),
                 feature_paths=sorted({f["feature_path"] for f in results["old"][0]["forecasts"]}), reliabilities=sorted({f["reliability"] for f in results["old"][0]["forecasts"]}),
                 made_before_kickoff=sorted({f["made_before_kickoff"] for f in results["old"][0]["forecasts"]}))
    report.append(entry)
    print(json.dumps(entry), flush=True)

out = dict(private_copy=copy.name, now=NOW.isoformat(), gameweeks=len(report), fixtures_forecast=sum(e["fixtures_forecast"] for e in report), rows_compared=sum(e["rows_compared"] for e in report),
           all_identical=all(e["same_returned_forecasts"] and e["same_saved_rows"] for e in report), per_gameweek=report)
Path(__file__).with_name("parity_predictions.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("ALL IDENTICAL:", out["all_identical"], "| gameweeks:", out["gameweeks"], "| fixtures:", out["fixtures_forecast"], "| saved rows compared:", out["rows_compared"])
