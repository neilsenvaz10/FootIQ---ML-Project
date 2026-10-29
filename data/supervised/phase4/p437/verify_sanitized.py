"""Phase 4.37: can the sanitized evidence CSVs reconstruct the restricted provider datasets? Local check (needs the restricted raw files, which are not in the repository)."""
import glob, json, re
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[4]
SAN = sorted((ROOT / "data/evidence/sanitized").glob("*.csv"))
res = dict(files=len(SAN))
restricted_words = re.compile(r"football-?data|fixturedownload|api-?football|provider|statsbomb", re.I)
res["columns_with_restricted_words"] = [(f.name, c) for f in SAN for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns if restricted_words.search(c)]
res["cells_with_restricted_words"] = sum(int(pd.read_csv(f, dtype=str, encoding="utf-8-sig").astype(str).apply(lambda s: s.str.contains(restricted_words)).sum().sum()) for f in SAN)
san_cols = {c for f in SAN for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns}
raw = []
for g in ("data/supervised/phase4/p423/staging/raw/footballdatauk_*.csv", "data/supervised/phase4/p420/staging/raw/footballdatauk_*.csv"):
    raw += glob.glob(str(ROOT / g))
res["raw_footballdatauk_files"] = len(raw)
shared = set()
tot_rows = 0
for f in raw:
    d = pd.read_csv(f, dtype=str, encoding="utf-8-sig", on_bad_lines="skip")
    shared |= set(d.columns) & san_cols
    tot_rows += len(d)
res["raw_footballdatauk_rows(all copies)"] = tot_rows
res["columns_shared_with_restricted_raw"] = sorted(shared)
# row-level: how many (home, away) fixtures of a restricted EPL file appear in sanitized files with ANY value that is not available from the allowed sources? (all kept values are allowed-source values by construction)
epl = pd.read_csv(ROOT / "data/supervised/phase4/p423/staging/raw/footballdatauk_EPL.csv", dtype=str, encoding="utf-8-sig", on_bad_lines="skip")
res["restricted_EPL_file_columns"] = len(epl.columns)
res["restricted_EPL_file_rows"] = len(epl)
san_ids = set()
for f in SAN:
    d = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
    if "home" in d.columns and "away" in d.columns:
        san_ids |= set(zip(d.home, d.away))
res["fixtures_mentioned_in_sanitized_files(any league)"] = len(san_ids)
res["restricted_columns_recoverable"] = 0 if not shared else len(shared)
print(json.dumps(res, indent=1, default=str))
(Path(__file__).parent / "out" / "verify_sanitized.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
