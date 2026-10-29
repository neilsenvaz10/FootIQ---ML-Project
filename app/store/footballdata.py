"""football-data.org (API v4) adapter, Phase 4.11. PREPARED OFFLINE: nothing here contacts the provider unless a caller supplies an HTTP opener and a token, and the three leagues are not in
`sync.APPROVED`, so the scheduler cannot request them.

  PL  -> england:1-premierleague   (competition_key EPL)
  SA  -> italy:1-seriea            (SERIEA)
  FL1 -> europe/france:fr1         (LIGUE1)

One request returns a whole league-season: GET https://api.football-data.org/v4/competitions/<code>/matches?season=<year>, header X-Auth-Token. The v4 match list is documented as
unpaginated (it carries `resultSet.count`); the adapter still refuses a response whose `count` differs from the number of matches it holds, so a truncated or paged answer is never ingested.

The token is read from an environment variable at request time (default FOOTBALL_DATA_API_TOKEN). It is never stored in a file of this project, never written to a snapshot, ledger, log or
error text (`redact`), and a missing or malformed token stops the cycle BEFORE any request is made.

Field names follow the provider's v4 documentation as read on 2026-10-26 (docs/mini-project/FOOTBALL_DATA_ORG_CHECKLIST.md). No real payload has ever been seen: items the documentation leaves open
are flagged on the record and need the first supervised read to confirm.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

SOURCE = "footballdata"
BASE = "https://api.football-data.org/v4"
DEFAULT_TOKEN_ENV = "FOOTBALL_DATA_API_TOKEN"
LICENCE = "football-data.org terms (free tier); storage and reuse permissions unconfirmed"
ATTRIBUTION = "Football data provided by the Football-Data.org API"
MATCH_DURATION_PAD_H = 3.0

# FootIQ competition key -> (provider code, store competition_id)
LEAGUES = {
    "EPL": ("PL", "england:1-premierleague"),
    "SERIEA": ("SA", "italy:1-seriea"),
    "LIGUE1": ("FL1", "europe/france:fr1"),
}
IN_PLAY = {"IN_PLAY", "PAUSED", "LIVE", "EXTRA_TIME", "PENALTY_SHOOTOUT"}
BLOCKING = {"POSTPONED": "postponed", "CANCELLED": "cancelled", "SUSPENDED": "abandoned"}     # the provider does not define these: they never become results


class TokenMissing(RuntimeError):
    """No API token in the environment: raised before any request."""


class TokenInvalid(RuntimeError):
    """The token is empty or malformed: raised before any request."""


class IncompleteResponse(ValueError):
    """The answer is truncated, paged or contradicts itself: rejected before it is saved or ingested."""


# ------------------------------------------------------------------------------------------------------------------ token
def load_token(env_name: str = DEFAULT_TOKEN_ENV) -> str:
    raw = os.environ.get(env_name)
    if raw is None or not raw.strip():
        raise TokenMissing(f"no football-data.org API token: set the environment variable {env_name} (never a file inside the repository)")
    tok = raw.strip()
    if not re.fullmatch(r"[\x21-\x7e]{16,128}", tok):                          # printable, no whitespace; real tokens are 32 characters, but the length is not documented
        raise TokenInvalid(f"the value of {env_name} does not look like an API token (16-128 printable characters without spaces); its value is not shown")
    return tok


def redact(text: str, env_names=(DEFAULT_TOKEN_ENV,)) -> str:
    """Remove every configured token value from a text before it is stored or printed."""
    out = text
    for name in env_names:
        tok = (os.environ.get(name) or "").strip()
        if len(tok) >= 8:
            out = out.replace(tok, "[token-redacted]")
    return out


# ------------------------------------------------------------------------------------------------------------------ parsing
def _utc(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _goals(node) -> Optional[tuple]:
    """(home, away) when both are non-negative integers, otherwise None (a null, a string, a negative or a boolean is never a score)."""
    if not isinstance(node, dict):
        return None
    h, a = node.get("home"), node.get("away")
    ok = lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0  # noqa: E731
    return (h, a) if ok(h) and ok(a) else None


def regular_score(m: dict) -> tuple:
    """(home, away, result_type, label_eligible, flags): the goals in the first 90 minutes, never inferred from a bare final score of an extra-time or penalty match."""
    sc = m.get("score") or {}
    dur = sc.get("duration")
    reg, full = _goals(sc.get("regularTime")), _goals(sc.get("fullTime"))
    if reg:
        return reg[0], reg[1], "after90_explicit", True, []
    if dur == "REGULAR" and full:
        return full[0], full[1], "after90_explicit", True, ["fulltime_taken_as_regular_time_unconfirmed"]
    if dur == "EXTRA_TIME":
        return None, None, "after_et", False, ["only_extra_time_result"]
    if dur == "PENALTY_SHOOTOUT":
        return None, None, "after_pens", False, ["only_penalty_result"]
    return None, None, "none", False, ["finished_without_usable_score"]


def parse_match(m: dict, retrieved_utc: str, snapshot_id: str, now: Optional[datetime] = None, competition_key: Optional[str] = None, season: str = ""):
    from store import sync
    common, _, _ = sync._adapters()
    now = now or datetime.now(timezone.utc)
    ko = _utc(m.get("utcDate"))
    raw_status = str(m.get("status") or "").upper()
    flags = ["third_party_api_no_editorial_review"]
    # Observed on the first real read (Phase 4.12): a fixture the provider has not scheduled yet (status SCHEDULED, as opposed to TIMED) carries utcDate "...T00:00:00Z". That is a placeholder,
    # not a kick-off and not a reliable date: it must never become a stored kick-off time or open a date dispute.
    provisional = raw_status == "SCHEDULED" and ko is not None and ko.strftime("%H:%M:%S") == "00:00:00"
    if provisional:
        ko = None
        flags.append("provisional_date_placeholder_ignored")
    h = a = None
    rtype, label_ok = "none", False
    if raw_status == "FINISHED":
        h, a, rtype, label_ok, f2 = regular_score(m)
        flags += f2
        status = "completed" if h is not None else "completed_unclassified_score"
    elif raw_status == "AWARDED":
        status, flags = "completed_unclassified_score", flags + ["awarded_needs_review"]       # how the provider scores an award is undefined: a human decides
    elif raw_status in BLOCKING:
        status = BLOCKING[raw_status]
    elif raw_status in IN_PLAY:
        status = "in_progress"
    elif raw_status in ("SCHEDULED", "TIMED"):
        status = "upcoming" if provisional else "unresolved" if ko is None else "past_date_no_result" if ko + timedelta(hours=MATCH_DURATION_PAD_H) < now else "upcoming"
    else:
        status, flags = "unresolved", flags + [f"unknown_status:{raw_status or 'missing'}"]    # an unknown status blocks, it is never guessed
    if ko is None and not provisional:
        flags.append("no_kickoff_in_source")
        if status in ("upcoming", "past_date_no_result"):
            status = "unresolved"
    if status != "completed":
        h = a = None
        label_ok = False
    home, away = m.get("homeTeam") or {}, m.get("awayTeam") or {}
    md = m.get("matchday")
    return common.StagingRecord(
        source=SOURCE, source_ref=str(m.get("id")), competition_key=competition_key or (m.get("competition") or {}).get("code") or "", season=str(season),
        stage=m.get("stage"), round=str(md) if isinstance(md, int) and not isinstance(md, bool) else None,
        home_raw=home.get("name") or "", away_raw=away.get("name") or "", status=status,
        kickoff_utc=ko.strftime("%Y-%m-%dT%H:%M:%SZ") if ko else None, kickoff_local=None, time_zone=None,
        time_precision="utc" if ko else "none", match_date=ko.strftime("%Y-%m-%d") if ko else None, date_provenance="source_stated" if ko else "none",
        regulation_home=h, regulation_away=a, result_type=rtype, label_eligible_90min=bool(label_ok and status == "completed"),
        source_ids=dict(id=m.get("id"), home_id=home.get("id"), away_id=away.get("id"), home_tla=home.get("tla"), away_tla=away.get("tla"), provider_status=raw_status,
                        home_alts=[x for x in (home.get("shortName"),) if x], away_alts=[x for x in (away.get("shortName"),) if x]),
        retrieved_utc=retrieved_utc, source_revision=str(m.get("lastUpdated") or ""), snapshot_id=snapshot_id, licence=LICENCE, attribution=ATTRIBUTION, flags=flags)


def validate_payload(body: bytes, code: str) -> dict:
    """A full-season answer must be a JSON object with this competition's matches only, a `resultSet.count` equal to the matches it holds, unique ids and matchdays 1..N of equal size.
    Anything else is truncated, paged, malformed or contradictory and is rejected before it is saved or ingested."""
    try:
        data = json.loads(body)
    except ValueError as exc:
        raise ValueError(f"malformed response: not JSON ({exc.__class__.__name__})") from None
    if not isinstance(data, dict) or not isinstance(data.get("matches"), list) or not data["matches"]:
        raise ValueError("malformed response: no match list")
    comp = (data.get("competition") or {}).get("code")
    if comp != code:
        raise ValueError(f"contradictory response: competition {comp!r}, expected {code!r}")
    rs = data.get("resultSet") or {}
    if not isinstance(rs.get("count"), int):
        raise IncompleteResponse("incomplete response: no resultSet.count to check completeness against")
    ms = data["matches"]
    if rs["count"] != len(ms):
        raise IncompleteResponse(f"incomplete response: resultSet.count {rs['count']} but {len(ms)} matches (truncated or paged)")
    for m in ms:
        if not isinstance(m, dict) or m.get("id") is None or not isinstance(m.get("homeTeam"), dict) or not isinstance(m.get("awayTeam"), dict):
            raise ValueError("malformed response: a match lacks its id or teams")
        mcomp = (m.get("competition") or {}).get("code")
        if mcomp and mcomp != code:
            raise ValueError(f"contradictory response: a match belongs to competition {mcomp}")
    if len({m["id"] for m in ms}) != len(ms):
        raise ValueError("contradictory response: duplicate match ids")
    sizes: dict = {}
    for m in ms:
        g = m.get("matchday")
        if not isinstance(g, int) or isinstance(g, bool):
            raise ValueError("malformed response: a match has no matchday")
        sizes[g] = sizes.get(g, 0) + 1
    if sorted(sizes) != list(range(1, len(sizes) + 1)) or len(set(sizes.values())) != 1:
        raise IncompleteResponse("incomplete response: matchdays are not 1..N with equal numbers of matches")
    return data


def parse_payload(body: bytes, retrieved_utc: str, snapshot_id: str, now: Optional[datetime] = None, competition_key: Optional[str] = None, season: str = "") -> list:
    data = json.loads(body)
    return [parse_match(m, retrieved_utc, snapshot_id, now, competition_key, season) for m in data["matches"]]


def identity_report(body: bytes, resolver, competition_id: str) -> dict:
    """Which team names of a payload resolve to a stored entity (exact or normalised name only, never fuzzy) and which would be quarantined. Read-only; for the supervised read."""
    data = json.loads(body)
    names = {}
    for m in data["matches"]:
        for side in ("homeTeam", "awayTeam"):
            t = m.get(side) or {}
            names[t.get("name") or ""] = t.get("shortName")
    out = dict(resolved={}, unresolved=[])
    for n, short in sorted(names.items()):
        e, how = resolver.resolve(SOURCE, competition_id, n)
        if e is None and short:
            e, how = resolver.resolve(SOURCE, competition_id, short)
        if e:
            out["resolved"][n] = [e, how]
        else:
            out["unresolved"].append(dict(name=n, short_name=short, method=how))
    return out


# ------------------------------------------------------------------------------------------------------------------ fetching
class FootballDataAdapter:
    """One authenticated GET per league-season through the shared HttpClient (rate limit, Retry-After, ledger of URLs only). `snap(name, body, meta)` stores the validated bytes."""

    def __init__(self, client, token: str, snap: Callable, now: Optional[Callable] = None):
        self.client, self._token, self._snap, self._now = client, token, snap, now

    def fetch_season(self, code: str, season: str, competition_key: Optional[str] = None):
        body, meta = self.client.get(f"{BASE}/competitions/{code}/matches", params={"season": season}, headers={"X-Auth-Token": self._token})
        validate_payload(body, code)                                                  # reject before anything is saved
        info = self._snap(f"{code}_{season}_season", body, meta)
        now = self._now() if self._now else None
        return parse_payload(body, info["saved_utc"], info["snapshot_id"], now, competition_key, season), info
