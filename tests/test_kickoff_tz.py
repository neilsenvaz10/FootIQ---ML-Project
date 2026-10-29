"""Phase 4.8C proposal tests for app/kickoff_tz.py. The module is not wired into any endpoint; these tests also prove the production rule is unchanged."""
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import kickoff as K  # noqa: E402
import kickoff_tz as T  # noqa: E402


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


def test_a_stated_utc_kickoff_is_used_as_it_stands_in_every_zone():
    for key in T.ZONES:
        assert T.made_before_kickoff_tz(utc(2026, 10, 25, 14, 59, 59), "2026-10-25", "2026-10-25T15:00:00Z", key) == "yes"
        assert T.made_before_kickoff_tz(utc(2026, 10, 25, 15, 0, 0), "2026-10-25", "2026-10-25T15:00:00Z", key) == "no"


def test_a_date_only_fixture_stays_predictable_until_the_date_starts_in_the_leagues_own_zone():
    # Premier League, 2026-10-31 (UK summer time ended on 25 Oct: midnight local = 00:00 UTC). The global rule would already block from 2026-10-30 10:00 UTC.
    assert T.made_before_kickoff_tz(utc(2026, 10, 30, 23, 59), "2026-10-31", None, "EPL") == "yes"
    assert K.made_before_kickoff(utc(2026, 10, 30, 23, 59), "2026-10-31", None) == "unknown"
    assert T.made_before_kickoff_tz(utc(2026, 10, 31, 0, 0), "2026-10-31", None, "EPL") == "unknown"            # from local midnight it cannot be known
    assert T.made_before_kickoff_tz(utc(2026, 11, 1, 0, 0, 1), "2026-10-31", None, "EPL") == "no"


def test_daylight_saving_moves_the_boundary_by_the_dates_own_offset():
    # Madrid: 2026-10-25 is CEST (UTC+2), 2026-10-26 is CET (UTC+1) -> local midnight is 22:00 UTC and 23:00 UTC of the day before.
    assert T.cutoff_instants("2026-10-25", "LALIGA")["yes_until"] == "2026-10-24T22:00:00Z"
    assert T.cutoff_instants("2026-10-26", "LALIGA")["yes_until"] == "2026-10-25T23:00:00Z"
    # spring forward in Berlin (2026-03-29): the date itself starts at 23:00 UTC of the 28th (still CET), and ends at 22:00 UTC of the 29th (CEST)
    c = T.cutoff_instants("2026-03-29", "BUNDESLIGA")
    assert c["yes_until"] == "2026-03-28T23:00:00Z" and c["no_after"] == "2026-03-29T22:00:00Z"
    assert T.made_before_kickoff_tz(utc(2026, 3, 28, 22, 59), "2026-03-29", None, "BUNDESLIGA") == "yes"
    assert T.made_before_kickoff_tz(utc(2026, 3, 28, 23, 0), "2026-03-29", None, "BUNDESLIGA") == "unknown"


def test_spain_uses_the_easternmost_zone_to_start_and_the_westernmost_to_end():
    c = T.cutoff_instants("2026-10-31", "LALIGA")
    assert c["yes_until"] == "2026-10-30T23:00:00Z"                    # Madrid, UTC+1
    assert c["no_after"] == "2026-11-01T00:00:00Z"                     # Canary Islands, UTC+0: the date ends there an hour later
    assert T.made_before_kickoff_tz(utc(2026, 10, 31, 23, 30), "2026-10-31", None, "LALIGA") == "unknown"
    assert T.made_before_kickoff_tz(utc(2026, 11, 1, 0, 30), "2026-10-31", None, "LALIGA") == "no"


def test_unknown_competition_or_zone_falls_back_to_the_strict_global_rule():
    for now in (utc(2026, 10, 30, 9, 0), utc(2026, 10, 30, 12, 0), utc(2026, 11, 2, 0, 0)):
        assert T.made_before_kickoff_tz(now, "2026-10-31", None, "UCL") == K.made_before_kickoff(now, "2026-10-31", None)
        assert T.made_before_kickoff_tz(now, "2026-10-31", None, None) == K.made_before_kickoff(now, "2026-10-31", None)


def test_a_disputed_date_can_only_make_the_answer_stricter():
    # stored 2026-10-25, a source says 2026-10-23: the earlier candidate decides
    now = utc(2026, 10, 23, 12, 0)
    assert T.made_before_kickoff_tz(now, "2026-10-25", None, "EPL") == "yes"
    assert T.made_before_kickoff_tz(now, "2026-10-25", None, "EPL", alt_dates=["2026-10-23"]) == "unknown"
    assert T.made_before_kickoff_tz(utc(2026, 10, 26, 12, 0), "2026-10-25", None, "EPL", alt_dates=["2026-10-23"]) == "no"
    for now in (utc(2026, 10, 22, 12), utc(2026, 10, 23, 12), utc(2026, 10, 24, 12), utc(2026, 10, 26, 12)):
        strict = T.made_before_kickoff_tz(now, "2026-10-25", None, "EPL", alt_dates=["2026-10-23"])
        plain = T.made_before_kickoff_tz(now, "2026-10-25", None, "EPL")
        assert ["yes", "unknown", "no"].index(strict) >= ["yes", "unknown", "no"].index(plain)


def test_same_day_without_a_kickoff_is_never_predictable_and_the_evidence_floor_is_opt_in():
    assert T.made_before_kickoff_tz(utc(2026, 10, 31, 8, 0), "2026-10-31", None, "EPL") == "unknown"                       # same local day: blocked
    assert T.made_before_kickoff_tz(utc(2026, 10, 31, 8, 0), "2026-10-31", None, "EPL", earliest_local_kickoff_hour=12.5) == "yes"   # only when explicitly given observed evidence
    assert T.made_before_kickoff_tz(utc(2026, 10, 31, 12, 30), "2026-10-31", None, "EPL", earliest_local_kickoff_hour=12.5) == "unknown"


def test_the_rule_never_produces_a_kickoff_timestamp_and_the_global_rule_is_kept_for_everything_else():
    for now in (utc(2026, 10, 30, 12), utc(2026, 10, 31, 12), utc(2026, 11, 2, 12)):
        out = T.made_before_kickoff_tz(now, "2026-10-31", None, "BUNDESLIGA")
        assert out in ("yes", "unknown", "no") and not re.search(r"\d{4}-\d\d-\d\d", out)
    assert K.made_before_kickoff_global(utc(2026, 10, 24, 9, 59, 59), "2026-10-25", None) == "yes" and K.made_before_kickoff_global(utc(2026, 10, 24, 10, 0, 0), "2026-10-25", None) == "unknown"
    assert K.made_before_kickoff(utc(2026, 10, 24, 10, 0, 0), "2026-10-25", None) == "unknown"          # no competition given: the strict global rule, unchanged
    assert K.made_before_kickoff(utc(2026, 10, 24, 10, 0, 0), "2026-10-25", None, "UCL") == "unknown"   # a competition without verified zones: also the global rule


def test_the_production_entry_point_uses_the_zone_rule_for_the_five_leagues_and_the_application_calls_it_with_the_competition():
    now = utc(2026, 10, 31, 8, 0)
    assert K.made_before_kickoff(now, "2026-10-31", None, "EPL") == T.made_before_kickoff_proposed(now, "2026-10-31", None, "EPL") == "yes"       # the global rule says unknown here
    assert K.made_before_kickoff(now, "2026-10-31", None) == "unknown"
    for mod in ("gameweeks.py", "featured.py", "predict.py"):
        text = (ROOT / "app" / mod).read_text(encoding="utf-8")
        assert "KO.made_before_kickoff(" in text and "disputes" in text.lower() or "DISP" in text
    assert "kickoff_state" in (ROOT / "app" / "forecast.py").read_text(encoding="utf-8")                       # the forecast takes the page's answer: one rule everywhere


@pytest.mark.parametrize("key", list(T.ZONES))
def test_every_league_behaves_the_same_way_through_the_production_entry_point(key):
    d = "2026-11-07"
    assert K.made_before_kickoff(utc(2026, 11, 7, 14, 59, 59), d, "2026-11-07T15:00:00Z", key) == "yes"
    assert K.made_before_kickoff(utc(2026, 11, 7, 15, 0, 0), d, "2026-11-07T15:00:00Z", key) == "no"
    assert K.made_before_kickoff(utc(2026, 11, 9, 0, 0), d, None, key) == "no"                              # a past date-only fixture
    assert K.made_before_kickoff(utc(2026, 11, 6, 0, 0), d, None, key) == "yes"                             # two days ahead
    assert K.made_before_kickoff(utc(2026, 11, 7, 23, 59), d, None, key) in ("unknown", "no")              # never 'yes' late on the match day
    assert K.made_before_kickoff(utc(2026, 11, 6, 12, 0), "nonsense", None, key) == "unknown"             # unreadable date: blocked


def test_where_the_proposal_is_never_more_permissive_than_reality():
    """Safety property: for every league and every instant around a date, 'yes' implies the date has not started in ANY of the league's zones."""
    for key, zones in T.ZONES.items():
        for day in ("2026-03-29", "2026-10-25", "2026-10-31", "2026-12-26"):
            for h in range(-40, 50, 3):
                now = datetime.fromisoformat(day + "T00:00:00+00:00") + timedelta(hours=h)
                if T.made_before_kickoff_tz(now, day, None, key) == "yes":
                    d = date.fromisoformat(day)
                    assert all(now < T._start_utc(d, z) for z in zones), (key, day, h)


# ------------------------------------------------------------------------------------------------ Phase 4.8D Stage 1: evidence floor (isolated tests only)
def test_the_floor_is_the_observed_earliest_hour_minus_a_margin_and_only_with_enough_evidence():
    assert T.evidence_floor("EPL") == 10.5 and T.evidence_floor("LALIGA") == 12.0 and T.evidence_floor("BUNDESLIGA") == 13.5
    assert T.evidence_floor("SERIEA") is None and T.evidence_floor("LIGUE1") is None and T.evidence_floor(None) is None        # no stored UTC kickoffs: no floor, plain zone rule
    for key, e in T.EVIDENCE.items():
        assert T.evidence_floor(key) <= e["earliest_observed_hour"] - T.SAFETY_MARGIN_HOURS


def test_proposed_rule_allows_same_day_only_until_the_floor_and_never_after():
    # Premier League, Saturday 2026-10-31 (GMT): floor 10:30 local = 10:30 UTC
    assert T.made_before_kickoff_proposed(utc(2026, 10, 31, 10, 29), "2026-10-31", None, "EPL") == "yes"
    assert T.made_before_kickoff_proposed(utc(2026, 10, 31, 10, 30), "2026-10-31", None, "EPL") == "unknown"
    assert T.made_before_kickoff_proposed(utc(2026, 10, 31, 20, 0), "2026-10-31", None, "EPL") == "unknown"
    assert K.made_before_kickoff(utc(2026, 10, 31, 10, 29), "2026-10-31", None) == "unknown"                  # the production rule blocks it far earlier
    # Madrid in summer time (UTC+2): 2026-10-24 floor 12:00 local = 10:00 UTC; Berlin winter time: 13:30 local = 12:30 UTC
    assert T.made_before_kickoff_proposed(utc(2026, 10, 24, 9, 59), "2026-10-24", None, "LALIGA") == "yes"
    assert T.made_before_kickoff_proposed(utc(2026, 10, 24, 10, 0), "2026-10-24", None, "LALIGA") == "unknown"
    assert T.made_before_kickoff_proposed(utc(2026, 11, 7, 12, 29), "2026-11-07", None, "BUNDESLIGA") == "yes"
    assert T.made_before_kickoff_proposed(utc(2026, 11, 7, 12, 30), "2026-11-07", None, "BUNDESLIGA") == "unknown"
    # no floor for Serie A: only the plain zone rule (local midnight)
    assert T.made_before_kickoff_proposed(utc(2026, 11, 7, 22, 59), "2026-11-08", None, "SERIEA") == "yes"
    assert T.made_before_kickoff_proposed(utc(2026, 11, 7, 23, 0), "2026-11-08", None, "SERIEA") == "unknown"


def test_past_fixtures_are_never_predictable_under_the_proposal_and_a_stated_kickoff_beats_every_floor():
    for key in T.ZONES:
        assert T.made_before_kickoff_proposed(utc(2026, 11, 3, 0, 0, 1), "2026-10-31", None, key) == "no"
        assert T.made_before_kickoff_proposed(utc(2026, 10, 31, 15, 0, 0), "2026-10-31", "2026-10-31T15:00:00Z", key) == "no"
        assert T.made_before_kickoff_proposed(utc(2026, 10, 31, 14, 59, 59), "2026-10-31", "2026-10-31T15:00:00Z", key) == "yes"


def test_disputed_dates_and_unreadable_dates_are_conservative_and_unknown_competitions_fall_back():
    now = utc(2026, 10, 24, 9, 0)
    assert T.made_before_kickoff_proposed(now, "2026-10-25", None, "LALIGA") == "yes"
    assert T.made_before_kickoff_proposed(now, "2026-10-25", None, "LALIGA", alt_dates=["2026-10-24"]) == "yes"          # the earlier candidate is Saturday: floor 12:00 local = 10:00 UTC, still ahead
    assert T.made_before_kickoff_proposed(utc(2026, 10, 24, 10, 30), "2026-10-25", None, "LALIGA", alt_dates=["2026-10-24"]) == "unknown"
    assert T.made_before_kickoff_proposed(now, "not-a-date", None, "EPL") == "unknown" and T.made_before_kickoff_proposed(now, None, None, "EPL") == "unknown"
    assert T.made_before_kickoff_proposed(now, "2026-10-31", None, "UCL") == K.made_before_kickoff(now, "2026-10-31", None)
    assert T.made_before_kickoff_proposed(now, "2026-10-31", None, "EPL", alt_dates=["31/10/2026"]) == "unknown"


def test_the_proposal_never_says_yes_when_a_league_zone_has_already_reached_the_floor():
    for key, zones in T.ZONES.items():
        floor = T.evidence_floor(key) or 0.0
        for day in ("2026-03-29", "2026-10-25", "2026-10-31"):
            d = date.fromisoformat(day)
            for h in range(-30, 40, 2):
                now = datetime.fromisoformat(day + "T00:00:00+00:00") + timedelta(hours=h)
                if T.made_before_kickoff_proposed(now, day, None, key) == "yes":
                    assert all(now < T._start_utc(d, z, floor) for z in zones), (key, day, h)
