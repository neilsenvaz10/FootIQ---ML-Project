"""Kickoff safety (Phase 4.8B): may a NEW pre-match prediction still be generated for this fixture?

One conservative rule shared by the gameweek forecast, the gameweek page and the manual head-to-head prediction:
  * stated kickoff (UTC) in the future                       -> "yes"
  * no kickoff time: the fixture's date has not started anywhere on Earth yet (before 00:00 on that date in UTC+14) -> "yes"
  * stated kickoff passed, or the whole date window passed (after 24:00 on that date in UTC-12)                    -> "no"
  * anything in between (kickoff unknown, date possibly under way)                                                 -> "unknown"
Only "yes" allows a new prediction. "no" and "unknown" never do: a stored forecast stays as it was, a missing one is not created.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

BLOCKED_MESSAGE = {
    "no": "Awaiting verified result: the kickoff has passed, so no new pre-match prediction is generated. Any forecast saved earlier is kept as a historical record.",
    "unknown": "Kickoff time unconfirmed and the match date may already be under way (league time zone, or a disputed date): no new pre-match prediction is generated.",
}


def made_before_kickoff(now: datetime, match_date: str, kickoff_utc: Optional[str], competition_key: Optional[str] = None, alt_dates=()) -> str:
    """The production rule (Phase 4.8D Stage 2). A stated UTC kickoff is used as it stands. Without one, a league with verified time zones (the five domestic leagues) is judged in
    those zones with a conservative evidence floor and the earliest of any disputed dates (kickoff_tz.py); any other competition, or no competition given, keeps the strict global
    rule below. A kickoff time is never invented."""
    if competition_key is None:
        return made_before_kickoff_global(now, match_date, kickoff_utc)
    import kickoff_tz                                              # imported here: kickoff_tz itself falls back to the global rule below
    return kickoff_tz.made_before_kickoff_proposed(now, match_date, kickoff_utc, competition_key, alt_dates)


def made_before_kickoff_global(now: datetime, match_date: str, kickoff_utc: Optional[str]) -> str:
    """'yes' only when it is certain: the stated kickoff is in the future, or (kickoff time unknown) the fixture's date has not started anywhere on Earth yet.
    'no' when the kickoff / the whole date window has passed; 'unknown' in between."""
    if kickoff_utc:
        ko = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00"))
        return "yes" if now < ko else "no"
    d = date.fromisoformat(match_date)
    earliest = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) - timedelta(hours=14)         # UTC+14 is the earliest time zone
    latest = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1, hours=12)    # UTC-12 is the latest
    if now < earliest:
        return "yes"
    return "no" if now > latest else "unknown"
