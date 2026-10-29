"""Build (or re-run the idempotent import into) data/footiq.sqlite from the repository baseline. Offline: no network access.

    .venv\\Scripts\\python.exe -X utf8 app/store/build.py [--path data/footiq.sqlite] [--fresh]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import baseline, db  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(db.DEFAULT_PATH))
    ap.add_argument("--fresh", action="store_true", help="delete the existing database file first (it is rebuildable)")
    a = ap.parse_args()
    p = Path(a.path)
    if a.fresh and p.exists():
        for ext in ("", "-wal", "-shm"):
            Path(str(p) + ext).unlink(missing_ok=True)
    t = time.time()
    conn = db.connect(p)
    db.init(conn)
    out = baseline.import_baseline(conn)
    out["seconds"] = round(time.time() - t, 1)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
