"""Phase 4.23 task 1-2: for each of the 16 fixtures past their date without a result, what does every source say? OFFLINE (store mode=ro + downloaded files). Writes staging/open16_evidence.csv."""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence as E  # noqa: E402

conn = E.connect()
rows = []
for k in E.LEAGUES:
    d = E.load(k, conn)
    for (h, a), s in d["rows"].items():
        if s["status"] in ("scheduled", "awaiting_result") and s["match_date"] < "2026-10-28":
            of, fd, fx, wk, ff = d["of"].get((h, a), {}), d["fduk"].get((h, a), {}), d["fxd"].get((h, a), {}), d["wiki"].get((h, a), {}), d["fduk_fx"].get((h, a), {})
            rows.append(dict(competition_key=k, record_id=s["record_id"], matchday=s["matchday_no"], home=s["home_name"], away=s["away_name"], store_date=s["match_date"], store_status=s["status"],
                             openfootball_date=of.get("date"), openfootball_score=of.get("score"), fduk_date=fd.get("date"), fduk_score=fd.get("score"), fduk_fixture_date=ff.get("date"),
                             fxd_date_utc=fx.get("utc"), fxd_score=fx.get("score"), wikipedia_score=wk.get("score"), wikipedia_note=wk.get("note"), wikipedia_revision=d["wiki_meta"]["revision"]))
df = pd.DataFrame(rows)
df.to_csv(HERE / "staging" / "open16_evidence.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 22)
print(len(df))
print(df[["competition_key", "home", "away", "store_date", "openfootball_score", "fduk_date", "fduk_score", "fxd_date_utc", "fxd_score", "wikipedia_score", "wikipedia_note"]].to_string())
