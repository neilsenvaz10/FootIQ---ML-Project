"""League rule profiles (config/season_rules.json). A profile is usable only when verified AND implemented; everything else blocks."""
import json
from functools import lru_cache
from pathlib import Path

import config as C

PATH = C.ROOT / "config" / "season_rules.json"
CRITERIA = {"goal_difference", "goals_scored", "away_goals_total", "h2h_points", "h2h_goal_difference", "h2h_away_goals", "fair_play"}
UNAVAILABLE = {"fair_play"}           # needs card data FootIQ does not hold: ties reaching it are separated at random and reported


class RuleBlocked(ValueError):
    """The league/season has no verified, implemented rule profile."""


@lru_cache(maxsize=1)
def _all(path: str = str(PATH)) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["profiles"]


def reload() -> None:
    _all.cache_clear()


def profile_info(key: str, season: str) -> dict:
    """Public description (never raises): status, whether usable, why not, sources, notes."""
    p = _all().get(f"{key}|{season}")
    if p is None:
        return dict(key=key, season=season, usable=False, status="missing", reason="no rule profile exists for this league and season", sources=[])
    usable = p["status"] == "verified" and bool(p.get("implemented"))
    return dict(key=key, season=season, usable=usable, status=p["status"], implemented=bool(p.get("implemented")), reason=None if usable else p.get("blocked_reason", "profile not verified or not implemented"),
                sources=p.get("sources", []), live_confirmation=p.get("live_confirmation"), notes=p.get("interpretation_notes", []), bands=p.get("bands", {}), clubs=p.get("clubs"), terminal=p.get("terminal"),
                criteria=p.get("criteria"), h2h_scope=p.get("h2h_scope"), bounds_ready=usable and p.get("bounds_multi_club_prefix") is not None, bounds_notes=p.get("bounds_notes", []))


def get_profile(key: str, season: str) -> dict:
    info = profile_info(key, season)
    if not info["usable"]:
        raise RuleBlocked(f"{key} {season}: final-position predictions are blocked: {info['reason']}")
    p = dict(_all()[f"{key}|{season}"])
    for lst in p["criteria"].values():
        bad = [c for c in lst if c not in CRITERIA]
        if bad:
            raise RuleBlocked(f"{key} {season}: unknown criteria {bad}")
    return p
