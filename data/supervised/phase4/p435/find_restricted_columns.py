"""Phase 4.35: lists the project files (phase 4 inputs and evidence) that carry football-data.co.uk / FixtureDownload / football-data.org columns or raw copies. Read-only."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
hits, raw = [], []
for dp, dn, fn in os.walk(ROOT / "data" / "supervised" / "phase4"):
    for f in fn:
        p = Path(dp) / f
        rel = p.relative_to(ROOT).as_posix()
        if "/p435/" in rel or "/p434/" in rel or "/p433/" in rel:
            continue
        if re.match(r"(footballdatauk_|fixturedownload)", f):
            raw.append(rel)
            continue
        if f.endswith(".csv") and p.stat().st_size < 5_000_000:
            head = p.open(encoding="utf-8-sig", errors="ignore").readline().lower()
            if re.search(r"footballdatauk|fixturedownload|provider_date|footballdata", head):
                hits.append(rel)
print(len(hits), "CSV files with restricted columns:")
print("\n".join(hits))
print(len(raw), "raw provider copies:")
print("\n".join(raw))
(Path(__file__).with_name("restricted_columns_files.txt")).write_text("\n".join(hits + raw) + "\n", encoding="utf-8")
