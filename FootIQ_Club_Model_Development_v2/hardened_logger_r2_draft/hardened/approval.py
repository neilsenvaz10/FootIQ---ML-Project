"""Validation of the owner's approval file. Official mode is OFF by default: it needs the environment switch FOOTIQ_OFFICIAL_MODE=1, an explicit --official flag AND a valid approval.
The approval is never created by code in this package."""
import hashlib
import json
import os
from datetime import datetime, timezone

from . import artifacts

CANONICAL_APPROVAL = os.path.join(artifacts.V2, "matched_v1_prospective_r1", "OFFICIAL_LOGGING_APPROVED.json")
REQUIRED = ["approval_version", "approved_by", "approved_utc", "expires_utc", "mode", "protocol", "models", "artifact_manifest_sha256", "competition_id", "season", "source_scope",
            "sealing_window", "max_fixtures"]
HEX = set("0123456789abcdef")


class ApprovalError(RuntimeError):
    def __init__(self, problems):
        super().__init__("approval rejected: " + "; ".join(problems)); self.problems = problems


def official_mode_enabled(flag: bool) -> bool:
    return bool(flag) and os.environ.get("FOOTIQ_OFFICIAL_MODE") == "1"


def _ts(s):
    t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _hex64(x):
    return isinstance(x, str) and len(x) == 64 and set(x.lower()) <= HEX


def validate_approval(path, now, *, expected_models, expected_manifest_sha, competition_id, season, protocol_version="r2"):
    """Returns the approval dict or raises ApprovalError listing every problem."""
    problems = []
    if not os.path.exists(path):
        raise ApprovalError(["approval file does not exist"])
    raw = open(path, "rb").read()
    if not raw.strip():
        raise ApprovalError(["approval file is empty"])
    try:
        a = json.loads(raw.decode("utf-8"))
    except Exception:
        raise ApprovalError(["approval file is not valid JSON"])
    if not isinstance(a, dict) or not a:
        raise ApprovalError(["approval must be a non-empty JSON object"])
    for k in REQUIRED:
        if k not in a:
            problems.append(f"missing field {k}")
    if problems:
        raise ApprovalError(problems)
    try:
        if a["mode"] != "official": problems.append("mode must be 'official'")
        if not str(a["approved_by"]).strip(): problems.append("approved_by empty")
        ap, ex = _ts(a["approved_utc"]), _ts(a["expires_utc"])
        if ap > now: problems.append("approved_utc is in the future")
        if ex <= now: problems.append("approval expired")
        if ex <= ap: problems.append("expires_utc not after approved_utc")
        pr = a["protocol"]
        if not isinstance(pr, dict) or pr.get("version") != protocol_version: problems.append(f"protocol version must be {protocol_version}")
        else:
            if not _hex64(pr.get("sha256")): problems.append("protocol sha256 malformed")
            elif not os.path.exists(pr.get("path", "")): problems.append("protocol file path does not exist")
            elif artifacts.digest_file(pr["path"]) != pr["sha256"].lower(): problems.append("protocol file hash does not match the approved protocol sha256")
        m = a["models"]
        for k, v in expected_models.items():
            if not isinstance(m, dict) or m.get(k) != v: problems.append(f"model hash mismatch: {k}")
        if a["artifact_manifest_sha256"] != expected_manifest_sha: problems.append("artifact manifest hash mismatch (code, preprocessing, Elo parameters, contracts or snapshots differ from the approved state)")
        if a["competition_id"] != competition_id or a["season"] != season: problems.append("competition/season not approved")
        ss = a["source_scope"]
        if not isinstance(ss, dict) or ss.get("openligadb") != {"league": "bl1", "season": "2026"}: problems.append("source scope must be OpenLigaDB bl1/2026")
        w = a["sealing_window"]
        if not isinstance(w, dict) or "start_utc" not in w or "end_utc" not in w: problems.append("sealing_window malformed")
        else:
            s, e = _ts(w["start_utc"]), _ts(w["end_utc"])
            if not (s <= now <= e): problems.append("current time is outside the authorised sealing window")
            if e <= s: problems.append("sealing window end before start")
        if not isinstance(a["max_fixtures"], int) or a["max_fixtures"] < 1: problems.append("max_fixtures must be a positive integer")
        if "matchdays" in a and not (isinstance(a["matchdays"], list) and all(isinstance(x, int) for x in a["matchdays"]) and a["matchdays"]): problems.append("matchdays malformed")
    except (ValueError, TypeError, KeyError):
        problems.append("approval contains malformed values")
    if problems:
        raise ApprovalError(problems)
    return a
