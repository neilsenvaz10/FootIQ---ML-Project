"""Team-name helpers shared by data preparation and the bracket endpoint (no data is created here)."""
from functools import lru_cache

import pandas as pd

import config as C


@lru_cache(maxsize=1)
def _spelling() -> dict:
    """Map each team to the spelling used in the historical international results (so 'USA' and 'United States' are one team)."""
    import sys

    sys.path.insert(0, str(C.ROOT / "scripts"))
    import build_worldcup_model_v2 as wc

    hist = pd.read_csv(C.INTL_RESULTS, usecols=["home_team", "away_team"])
    out = {}
    for n in sorted(set(hist.home_team) | set(hist.away_team)):
        out.setdefault(wc.normalize_team(n), n)
    return out


def canon_intl(name: str) -> str:
    import sys

    sys.path.insert(0, str(C.ROOT / "scripts"))
    import build_worldcup_model_v2 as wc

    return _spelling().get(wc.normalize_team(name), name)
