"""Verify the frozen model artifacts against the sha256 values recorded when they were frozen (read-only; never modifies anything).

The .json artifacts were hashed with Windows CRLF line endings and Git stores them with LF, so a file is accepted if it matches in
either form. Binary .pkl files must match byte for byte.
"""
import hashlib
import json
from functools import lru_cache

import config as C

FROZEN = {
    "club_v1": C.ROOT / "FootIQ_Club_Model_Baseline_v1" / "artifacts",
    "club_v2_r1": C.ROOT / "FootIQ_Club_Model_Development_v2" / "final_refit_v2_r1" / "artifacts",
}
V27_PKL = C.ROOT / "data" / "model_artifacts" / "v27" / "live_match_model.pkl"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@lru_cache(maxsize=1)
def check() -> dict:
    out = {}
    for name, folder in FROZEN.items():
        files = {}
        for fname, expected in json.loads((folder / "FROZEN.json").read_text(encoding="utf-8"))["artifact_sha256"].items():
            raw = (folder / fname).read_bytes()
            crlf = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            files[fname] = _sha(raw) == expected or (fname.endswith(".json") and _sha(crlf) == expected)
        out[name] = dict(ok=all(files.values()), files=files)
    # the v2.7 international artifact carries no recorded hash in the repo; its current hash is reported for reference
    out["international_v27"] = dict(ok=None, sha256=_sha(V27_PKL.read_bytes()), note="no frozen hash recorded in the repository; hash reported for reference")
    return out
