"""Phase 4.37 maintainer tool: sanitized copies of the three dashboard files data/miniproject/{matches,data_audit,season_coverage}.csv for publication.
The originals contain 130 World Cup 2026 rows compiled from an API-Football provider file (99 + 9 rows) and from news / FIFA articles (22 + 2 rows), whose redistribution rights are unverified.
This script writes copies WITHOUT those rows to data/release_candidates/miniproject/ (originals untouched); audit and coverage are recomputed with the same logic as app/prepare_data.py.
Usage: python scripts/prepare_release_files.py"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import config as C  # noqa: E402

ENC, LF = "utf-8-sig", "\n"
OUT = ROOT / "data" / "release_candidates" / "miniproject"
OUT.mkdir(parents=True, exist_ok=True)
ALLOWED_SOURCES = {"openfootball", "martj42/international_results", "wikipedia", "openligadb"}
m = pd.read_csv(C.MATCHES_CSV, dtype=str, encoding=ENC, keep_default_na=False)
keep = m.source.isin(ALLOWED_SOURCES)
dropped = m[~keep]
m = m[keep].reset_index(drop=True)
m.to_csv(OUT / "matches.csv", index=False, encoding=ENC, lineterminator=LF)
mm = m.copy()
dup = mm.duplicated(["competition_key", "date", "home", "away", "stage"], keep=False)
audit = []
for comp in C.ALL_COMPETITIONS:
    d = mm[mm.competition_key == comp["key"]]
    audit.append(dict(competition_key=comp["key"], competition=comp["name"], group=comp["group"], rows=len(d), seasons=d.season.nunique(), first_date=d.date.min(), last_date=d.date.max(),
                      rows_with_outcome=int((d.outcome.fillna("") != "").sum()), duplicate_rows=int(dup[d.index].sum()), sources=" | ".join(sorted(d.source.unique())), licences=" | ".join(sorted(d.licence.unique())), validation_badge=comp["badge"]))
pd.DataFrame(audit).to_csv(OUT / "data_audit.csv", index=False, encoding=ENC, lineterminator=LF)
cov = pd.read_csv(C.CLUB_COVERAGE_MATRIX, encoding=ENC)
sc = mm.groupby(["competition_key", "season"]).size().rename("rows_in_dataset").reset_index()
exp = cov[["competition_id", "season", "expected_matches", "coverage_pct"]]
exp = exp.assign(competition_key=exp.competition_id.map({c["source_id"]: c["key"] for c in C.ALL_COMPETITIONS if c["kind"] == "club"})).dropna(subset=["competition_key"]).drop(columns="competition_id")
exp["season"] = exp.season.astype(str)
sc = sc.merge(exp, on=["competition_key", "season"], how="left")
sc["note"] = ""
sc.loc[sc.expected_matches.notna() & (sc.rows_in_dataset < sc.expected_matches), "note"] = "incomplete or in progress"
sc.loc[sc.expected_matches.isna(), "note"] = "no expected-count reference available"
sc.to_csv(OUT / "season_coverage.csv", index=False, encoding=ENC, lineterminator=LF)
print(f"kept {len(m)} rows, dropped {len(dropped)} ({dropped.source.map(lambda s: 'news/FIFA page' if s.startswith('http') else s).value_counts().to_dict()}) -> {OUT}")
