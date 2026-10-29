"""League time-zone kickoff rule (proposed in Phase 4.8C, production since Phase 4.8D Stage 2): a less blunt kickoff rule that uses the competition's verified time zones instead of "anywhere on Earth". Wired into the application through kickoff.made_before_kickoff since Phase 4.8D Stage 2.

`app/kickoff.py` calls this module for the five domestic leagues and keeps the strict global rule (`made_before_kickoff_global`) for everything else.

Principles
  * Never invent a kickoff. This module returns only 'yes' / 'unknown' / 'no' (and a reason); it never returns, stores or assumes a kickoff timestamp.
  * A stored UTC kickoff is used as it stands (time zones and daylight saving cannot matter): ahead of now -> 'yes', otherwise 'no'.
  * Date-only fixture: 'yes' only before the date has started in the EASTERNMOST verified zone of the league; 'no' only after it has ended in the WESTERNMOST zone;
    anything in between is 'unknown' and blocks a new prediction exactly as today. Daylight saving is handled by zoneinfo (the date's own offset).
  * Competition without a verified zone, or an unknown zone name -> the global rule of kickoff.py (never a guess).
  * Disputed date (the store and a source disagree; a DATE_DIFFERENCE quarantine exists): every candidate date is considered and the EARLIEST decides, so a dispute can only
    make the answer stricter.
  * Postponed or cancelled fixtures are not a question of time and stay blocked by their status, as in the gameweek page; a date moved later after a forecast was saved never
    rewrites that forecast (saved rows are immutable).
  * Optional evidence floor (`earliest_local_kickoff_hour`, off by default): an earliest local hour observed in the league's stored UTC kickoffs. It is evidence, not a kickoff, and
    only usable where the stored history contains it (see kickoff_hour_evidence.json: Premier League 12:30, La Liga 14:00, Bundesliga 15:30; none for Serie A / Ligue 1).
  * Feature cutoffs are separate and unchanged: a forecast is built from results dated strictly before the fixture's date.
Zones: a league's matches are played in the zones listed; Spain also lists the Canary Islands (UT+0/+1, one hour behind mainland Spain), which only makes the 'no' boundary later.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

import kickoff as GLOBAL_RULE

ZONES = {
    "EPL": ("Europe/London",),
    "LALIGA": ("Europe/Madrid", "Atlantic/Canary"),
    "BUNDESLIGA": ("Europe/Berlin",),
    "SERIEA": ("Europe/Rome",),
    "LIGUE1": ("Europe/Paris",),
}


def _start_utc(day: date, zone: str, hour: float = 0.0) -> datetime:
    """The UTC instant at which `day` has local time `hour` in `zone` (the day's own daylight-saving offset applies)."""
    local = datetime(day.year, day.month, day.day, tzinfo=ZoneInfo(zone)) + timedelta(hours=hour)
    return local.astimezone(timezone.utc)


def made_before_kickoff_tz(now: datetime, match_date: str, kickoff_utc: Optional[str], competition_key: Optional[str], alt_dates: Iterable[str] = (),
                           earliest_local_kickoff_hour: Optional[float] = None) -> str:
    zones = ZONES.get(competition_key or "")
    if kickoff_utc:
        return GLOBAL_RULE.made_before_kickoff_global(now, match_date, kickoff_utc)         # a stated instant needs no time-zone reasoning
    if not zones:
        return GLOBAL_RULE.made_before_kickoff_global(now, match_date, None)                # no verified zone: the strict global rule, never a guess
    days = sorted({date.fromisoformat(d) for d in (match_date, *alt_dates)})
    earliest_day = days[0]                                                            # a disputed date can only make the answer stricter
    east = min(zones, key=lambda z: -_offset_hours(z, earliest_day))                  # easternmost = largest offset on that day
    start = _start_utc(earliest_day, east, earliest_local_kickoff_hour or 0.0)
    if now < start:
        return "yes"
    west = min(zones, key=lambda z: _offset_hours(z, days[-1]))
    end = _start_utc(days[-1] + timedelta(days=1), west)
    return "no" if now > end else "unknown"


def _offset_hours(zone: str, day: date) -> float:
    return datetime(day.year, day.month, day.day, 12, tzinfo=ZoneInfo(zone)).utcoffset().total_seconds() / 3600


def cutoff_instants(match_date: str, competition_key: str, earliest_local_kickoff_hour: Optional[float] = None) -> dict:
    """For documentation and tests: the UTC instants where a date-only fixture turns from 'yes' to 'unknown' and from 'unknown' to 'no'. These are rule boundaries, not kickoffs."""
    d = date.fromisoformat(match_date)
    zones = ZONES[competition_key]
    east = min(zones, key=lambda z: -_offset_hours(z, d))
    west = min(zones, key=lambda z: _offset_hours(z, d))
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return dict(yes_until=_start_utc(d, east, earliest_local_kickoff_hour or 0.0).strftime(fmt), no_after=_start_utc(d + timedelta(days=1), west).strftime(fmt),
                global_yes_until=(datetime(d.year, d.month, d.day, tzinfo=timezone.utc) - timedelta(hours=14)).strftime(fmt))


# ----------------------------------------------------------------------------------------------------------------- evidence floor (Phase 4.8D Stage 1, isolated tests only)
# Earliest local kickoff hour seen in the stored UTC kickoffs of each league (data/supervised/phase4/p48c/kickoff_hour_evidence.json, 2026-10-27). It is evidence about the league's
# schedule, never a kickoff of a fixture. A league's floor is the observed earliest hour minus a safety margin, and only when the sample is large enough; Serie A and Ligue 1 have no
# stored UTC kickoffs, so they get no floor and keep the plain zone rule.
EVIDENCE = {"EPL": dict(earliest_observed_hour=12.5, n=299), "LALIGA": dict(earliest_observed_hour=14.0, n=287), "BUNDESLIGA": dict(earliest_observed_hour=15.5, n=270)}
SAFETY_MARGIN_HOURS = 2.0
MIN_SAMPLE = 200


def evidence_floor(competition_key: Optional[str]) -> Optional[float]:
    e = EVIDENCE.get(competition_key or "")
    return e["earliest_observed_hour"] - SAFETY_MARGIN_HOURS if e and e["n"] >= MIN_SAMPLE else None


def made_before_kickoff_proposed(now: datetime, match_date: Optional[str], kickoff_utc: Optional[str], competition_key: Optional[str], alt_dates: Iterable[str] = ()) -> str:
    """The full proposal: league time zones plus the conservative evidence floor. A missing or unreadable date is never guessed: it blocks ('unknown')."""
    try:
        if not kickoff_utc:
            date.fromisoformat(match_date or "")
            for d in alt_dates:
                date.fromisoformat(d)
    except ValueError:
        return "unknown"
    return made_before_kickoff_tz(now, match_date, kickoff_utc, competition_key, alt_dates=alt_dates, earliest_local_kickoff_hour=evidence_floor(competition_key))
