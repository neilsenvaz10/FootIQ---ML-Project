"""config/season_sim.json: simulator gates and thresholds (environment variable FOOTIQ_SEASONSIM_CONFIG overrides the path, for tests and private copies)."""
import json
import os
from pathlib import Path

import config as C

DEFAULT = C.ROOT / "config" / "season_sim.json"


def load() -> dict:
    p = Path(os.environ.get("FOOTIQ_SEASONSIM_CONFIG") or DEFAULT)
    return json.loads(p.read_text(encoding="utf-8"))
