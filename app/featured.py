"""Featured fixture for the Home dashboard (read side of the results store).

GET /api/featured-fixture answers four questions with a fixed number of bounded, indexed statements (never one statement per fixture):
  * featured      the next scheduled fixture of the five domestic leagues that can be featured (both teams known), or null with a reason
  * upcoming      the next few scheduled fixtures after it
  * recent_results the latest verified results of the five leagues
  * freshness     per competition: newest verified result, last successful sync, fresh or stale and why (the /api/sync/status rules)
and, for every fixture, the same eligibility facts the gameweek page shows (reliability, flags, reasons).

What it never does: compute or save a forecast, touch a model, write to the store, call the gameweek view, or invent a fixture, a kickoff time or a
score. A saved forecast is returned only if one already exists in `forecasts` (created earlier by the user's Predict gameweek action).

Statements per request (independent of how many fixtures exist): 5 newest-season lookups, 5 upcoming, 5 results, up to 5 season rows for the
reliability flags, 1 saved-forecast lookup, plus the sync-status statements (about 35 small ones, about 20 ms; see store/sync.py). The first four use
the (competition_key, season) index; the planner is kept on it with a unary plus on `status`, because without statistics it prefers the
(status, match_date) index and would walk every completed match in the store (the same trap that makes the gameweek view slow; see
docs/mini-project/phase4/P4_2_PERFORMANCE_INVESTIGATION.md). tests/test_featured.py asserts the plans.
"""
import hashlib
import json
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

import config as C
import gameweeks
import disputes as DISP
import kickoff as KO
from store import sync as store_sync

LEAGUES = gameweeks.FIVE
MAX_LIST = 12
CACHE_TTL_SECONDS = 60
PREFER_FRESH_DAYS = 3             # a fresh league's fixture may be featured instead of a stale league's when it is at most this many days later
FETCH_PER_LEAGUE = MAX_LIST          # rows fetched per league before the leagues are merged: bounds every statement

COLUMNS = ("m.record_id, m.competition_key, m.competition_id, m.season, m.matchday_no, m.matchday_label, m.match_date, m.kickoff_local, m.kickoff_utc, m.time_precision, "
           "m.home_entity_id, m.away_entity_id, m.home_name, m.away_name, m.status, m.source_system, m.home_goals_90, m.away_goals_90, m.home_goals_final, m.away_goals_final, "
           "t1.display_name AS home_display, t2.display_name AS away_display")
JOIN = "FROM matches m LEFT JOIN teams t1 ON t1.entity_id=m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=m.away_entity_id"
# `+m.status` / `+m.kind`: a unary plus stops SQLite from choosing the (status, match_date) index, which spans every competition in the store
NEWEST_SEASON_SQL = "SELECT season FROM matches WHERE competition_key=? AND kind='club' ORDER BY season DESC LIMIT 1"
UPCOMING_SQL = f"SELECT {COLUMNS} {JOIN} WHERE m.competition_key=? AND m.season=? AND +m.kind='club' AND +m.status='scheduled' AND m.match_date>=? ORDER BY m.match_date, m.kickoff_utc, m.record_id LIMIT ?"
RESULTS_SQL = (f"SELECT {COLUMNS} {JOIN} WHERE m.competition_key=? AND m.season=? AND +m.kind='club' AND +m.status IN ('completed','awarded') AND m.home_goals_final IS NOT NULL "
               "ORDER BY m.match_date DESC, m.record_id DESC LIMIT ?")
SEASON_SQL = "SELECT record_id, matchday_no, match_date, status, home_entity_id, away_entity_id FROM matches WHERE competition_key=? AND season=? AND +kind='club'"
STATEMENTS = dict(newest_season=NEWEST_SEASON_SQL, upcoming=UPCOMING_SQL, results=RESULTS_SQL, season_rows=SEASON_SQL)


class FeaturedError(ValueError):
    """User-facing problem with the request (unknown league)."""


def check_comp(comp: Optional[str]) -> None:
    if comp is not None and comp not in LEAGUES:
        raise FeaturedError(f"comp must be one of the five domestic leagues ({', '.join(LEAGUES)})")


def _utc_stamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rows(conn, sql: str, params: tuple) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params)]


def _team(row: dict, side: str) -> dict:
    ent = row[f"{side}_entity_id"]
    return dict(name=row[f"{side}_display"] or row[f"{side}_name"], entity=ent, resolved=bool(ent))


def _kickoff(row: dict) -> dict:
    """What the store knows about the time; nothing is filled in. `zone_verified` is true only for a stored UTC time: a local time without a time zone is returned as stored,
    is never converted into a UTC timestamp, and is marked unverified."""
    state = "utc" if row["kickoff_utc"] else "local_without_time_zone" if row["kickoff_local"] else "unknown"
    return dict(state=state, utc=row["kickoff_utc"], local=row["kickoff_local"], time_precision=row["time_precision"], zone_verified=(state == "utc"))


def _has_started(row: dict, today: date, now_stamp: str) -> bool:
    """A fixture dated today whose stored UTC kickoff has passed is no longer 'upcoming' (it will show as awaiting a result)."""
    return row["match_date"] == today.isoformat() and bool(row["kickoff_utc"]) and row["kickoff_utc"] <= now_stamp


FINISHED = ("completed", "awarded")
NOT_PLAYED = ("postponed", "cancelled", "abandoned")


def effective_status(row: dict, today: date, now_stamp: str) -> str:
    """The stored status, except that a scheduled fixture with no verified result whose date has passed, or whose stored UTC kickoff has passed today, is 'awaiting_result'.
    Only the server's UTC clock and stored values are used (never a browser clock); a result is never inferred and 'live' does not exist."""
    status = row["status"]
    if status == "scheduled" and (row["match_date"] < today.isoformat() or _has_started(row, today, now_stamp)):
        return "awaiting_result"
    return status


def timing(row: dict, status: str, today: date, now_stamp: str) -> dict:
    """Where a fixture stands in time, and what cannot be known. `ambiguous` is true when the page cannot tell whether the match has started or finished: a fixture dated today whose
    kickoff has no verified time zone (or no time at all), or whose stored UTC kickoff has passed with no verified result yet."""
    if status in FINISHED:
        return dict(phase="result_stored", ambiguous=False, note=None)
    if status in NOT_PLAYED:
        return dict(phase="not_played", ambiguous=False, note=None)
    day = row["match_date"]
    if status == "awaiting_result":
        if day == today.isoformat():
            return dict(phase="kickoff_passed", ambiguous=True, note="The stored kickoff time (UTC) has passed and no verified result is stored yet. This page does not say whether the match is in progress or finished.")
        return dict(phase="date_passed", ambiguous=False, note="The date has passed and no verified result is stored.")
    if day > today.isoformat():
        return dict(phase="future_date", ambiguous=False, note=None)
    if row["kickoff_utc"]:
        return dict(phase="today_before_kickoff", ambiguous=False, note=None)
    if row["kickoff_local"]:
        return dict(phase="today_time_zone_unconfirmed", ambiguous=True,
                    note="Dated today. The kickoff is stored as a local time without a time zone, so it cannot be known whether the match has started. No time is converted or assumed.")
    return dict(phase="today_time_unknown", ambiguous=True, note="Dated today. No kickoff time is stored, so it cannot be known whether the match has started.")


def _assess(conn, row: dict, comp_latest: Optional[str], today: date, season_rows: list[dict], now: Optional[datetime] = None, disputed: Optional[dict] = None) -> dict:
    """Eligibility and reliability, from the same rules as the gameweek page (gameweeks.assess plus its rescheduled check). No model involved."""
    fx = dict(row, home_display=row["home_display"] or row["home_name"], away_display=row["away_display"] or row["away_name"])
    a = gameweeks.assess(conn, fx, comp_latest, today, season_rows)
    if row["matchday_no"] is not None:
        dates = [r["match_date"] for r in season_rows if r["matchday_no"] == row["matchday_no"]]
        if dates:
            med = gameweeks._median_date(dates)
            if abs((date.fromisoformat(row["match_date"]) - med).days) > gameweeks.RESCHEDULE_DAYS:
                a["flags"].append("rescheduled_or_out_of_order")
                a["reasons"].append(f"Dated {row['match_date']}, far from the rest of Matchday {row['matchday_no']} (around {med.isoformat()}): likely rescheduled.")
    eligible = bool(row["home_entity_id"] and row["away_entity_id"])
    if not eligible:
        a["reasons"].append("A team of this fixture is not matched to a club identity in the store, so it cannot be featured or forecast.")
    predictable = eligible
    if now is not None and eligible:                                      # Phase 4.8B: the same kickoff rule as the gameweek page and the forecast
        state = KO.made_before_kickoff(now, row["match_date"], row["kickoff_utc"], row["competition_key"], (disputed if disputed is not None else DISP.by_record(conn)).get(row["record_id"], ()))
        if state != "yes":
            predictable = False
            a["reasons"].append(KO.BLOCKED_MESSAGE[state])
    return dict(eligible=eligible, predictable=predictable, reliability=a["reliability"], flags=a["flags"], reasons=a["reasons"], stale_days=a["stale_days"])


def _fixture(row: dict, comp_name: str, eligibility: dict, saved: dict, detail: bool = False, clock: Optional[tuple] = None) -> dict:
    """`detail` (the featured fixture only) adds the reasons and the number of stale days; list items carry the flags, which are enough for a chip.
    `clock` is (today, now_stamp) of the server in UTC: it adds `timing`, which says what cannot be known about a fixture dated today."""
    elig = eligibility if detail else {k: eligibility[k] for k in ("eligible", "predictable", "reliability", "flags")}
    out = dict(record_id=row["record_id"], competition_key=row["competition_key"], competition=comp_name, season=row["season"], matchday_no=row["matchday_no"],
               matchday_label=row["matchday_label"], date=row["match_date"], kickoff=_kickoff(row), home=_team(row, "home"), away=_team(row, "away"), status=row["status"],
               source=(row["source_system"] or "").split(" (")[0], eligibility=elig, has_saved_forecast=row["record_id"] in saved)
    if clock:
        out["timing"] = timing(row, row["status"], *clock)
    return out


def _result(row: dict, comp_name: str) -> dict:
    h = row["home_goals_90"] if row["home_goals_90"] is not None else row["home_goals_final"]
    a = row["away_goals_90"] if row["away_goals_90"] is not None else row["away_goals_final"]
    return dict(record_id=row["record_id"], competition_key=row["competition_key"], competition=comp_name, season=row["season"], matchday_no=row["matchday_no"], date=row["match_date"],
                home=_team(row, "home"), away=_team(row, "away"), home_goals=h, away_goals=a, status=row["status"], source=(row["source_system"] or "").split(" (")[0])


FRESHNESS_KEYS = ("state", "state_reasons", "latest_result", "last_successful_sync_utc", "approved_sources", "awaiting_result", "scheduled",
                  "last_successful_external_check_utc", "last_successful_import_utc", "last_attempted_sync_utc", "provider_readiness", "imported_records", "quarantined_records", "history_note", "feed_lag")


def _freshness(status: dict) -> dict:
    keep = FRESHNESS_KEYS
    return dict(live_enabled=status["live_enabled"], periodic_minutes=status["periodic_minutes"], note=status["note"], attribution=status["attribution"],
                competitions={c["competition_key"]: {k: c[k] for k in keep} for c in status["competitions"] if c["competition_key"] in LEAGUES})


def build(conn: sqlite3.Connection, cfg: store_sync.SyncConfig, now: datetime, comp: Optional[str] = None, upcoming: int = 8, results: int = 8) -> dict:
    """The whole payload. `now` is injected so tests (and the cache) never depend on the clock."""
    check_comp(comp)
    today, now_stamp = now.astimezone(timezone.utc).date(), _utc_stamp(now)
    keys = [comp] if comp else list(LEAGUES)
    fresh = _freshness(store_sync.status(conn, cfg, now))

    leagues, up_rows, res_rows = [], [], []
    for key in keys:
        row = conn.execute(NEWEST_SEASON_SQL, (key,)).fetchone()
        season = row[0] if row else None
        info = dict(competition_key=key, name=C.BY_KEY[key]["name"], season=season, upcoming_found=0, started_today=0, next_fixture_date=None,
                    latest_result=fresh["competitions"][key]["latest_result"], state=fresh["competitions"][key]["state"])
        if season:
            found = _rows(conn, UPCOMING_SQL, (key, season, today.isoformat(), FETCH_PER_LEAGUE))
            live = [r for r in found if not _has_started(r, today, now_stamp)]
            info.update(upcoming_found=len(live), started_today=len(found) - len(live), next_fixture_date=live[0]["match_date"] if live else None)
            up_rows += live
            if results:
                res_rows += _rows(conn, RESULTS_SQL, (key, season, FETCH_PER_LEAGUE))
        leagues.append(info)

    order = {k: i for i, k in enumerate(LEAGUES)}
    up_rows.sort(key=lambda r: (r["match_date"], r["kickoff_utc"] or "", order[r["competition_key"]], r["record_id"]))
    res_rows.sort(key=lambda r: (r["match_date"], r["record_id"]), reverse=True)

    # the featured fixture is the first one whose two teams are known; when that league's data is stale, the first such fixture of a league with fresh data
    # within PREFER_FRESH_DAYS of it is preferred. The stale warning is never hidden: every chip is computed from the chosen fixture's own league.
    eligible = [r for r in up_rows if r["home_entity_id"] and r["away_entity_id"]]
    first = eligible[0] if eligible else None
    if first and fresh["competitions"][first["competition_key"]]["state"] != "fresh":
        limit_day = (date.fromisoformat(first["match_date"]) + timedelta(days=PREFER_FRESH_DAYS)).isoformat()
        first = next((r for r in eligible if r["match_date"] <= limit_day and fresh["competitions"][r["competition_key"]]["state"] == "fresh"), first)
    listed = [r for r in up_rows if r is not first][:upcoming]
    shown = ([first] if first else []) + listed

    # reliability facts only for what is shown: one narrow statement per league involved, then pure Python
    season_of = {l["competition_key"]: l["season"] for l in leagues}
    season_rows = {key: _rows(conn, SEASON_SQL, (key, season_of[key])) for key in sorted({r["competition_key"] for r in shown})}
    disputed = DISP.by_record(conn)                                  # one read per payload, not per fixture
    assessed = {r["record_id"]: _assess(conn, r, fresh["competitions"][r["competition_key"]]["latest_result"], today, season_rows[r["competition_key"]], now, disputed) for r in shown}
    saved = gameweeks.latest_forecasts(conn, [r["record_id"] for r in shown])

    featured, empty = None, None
    if first:
        featured = _fixture(first, C.BY_KEY[first["competition_key"]]["name"], assessed[first["record_id"]], saved, detail=True, clock=(today, now_stamp))
        featured["forecast"] = saved.get(first["record_id"])
    elif up_rows:
        empty = dict(code="no_eligible_fixture", message="Upcoming fixtures are stored, but none can be featured: a team in each is not matched to a club identity.")
    else:
        empty = dict(code="no_upcoming_fixture", message=f"No scheduled fixture dated {today.isoformat()} or later is stored for {'this league' if comp else 'the five domestic leagues'}.")
    return dict(
        generated_utc=now_stamp, today_utc=today.isoformat(), scope=dict(competitions=keys, rule="newest season of each league; scheduled fixtures dated today or later; both teams known; a fresh league is preferred within 3 days"),
        featured=featured, empty_state=empty,
        upcoming=[_fixture(r, C.BY_KEY[r["competition_key"]]["name"], assessed[r["record_id"]], saved, clock=(today, now_stamp)) for r in listed],
        recent_results=[_result(r, C.BY_KEY[r["competition_key"]]["name"]) for r in res_rows[:results]],
        leagues=leagues, freshness=fresh,
        notes=["Fixtures and results are read from the results store; nothing here is live.", "No forecast is computed here; a forecast appears only if it was saved earlier with Predict gameweek."])


# ----------------------------------------------------------------------------------------------------------------- cache
def store_fingerprint(path: Path) -> tuple:
    """Changes whenever the store file (or its write-ahead log) is written: size and modification time, nothing is read from the database."""
    out = []
    for p in (Path(path), Path(str(path) + "-wal")):
        try:
            st = p.stat()
            out.append((st.st_mtime_ns, st.st_size))
        except OSError:
            out.append(None)
    return tuple(out)


class Cache:
    """In-process cache of built payloads: a minute at most, dropped when the store file changes, the UTC date changes, or clear() is called (a sync did)."""

    def __init__(self, ttl: float = CACHE_TTL_SECONDS, clock: Callable[[], float] = time.monotonic):
        self.ttl, self.clock = ttl, clock
        self._items: dict = {}
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def get_or_build(self, key: tuple, fingerprint: Callable[[], tuple], builder: Callable[[], dict]) -> tuple[dict, bool, str]:
        """(payload, was_cached, etag). `fingerprint` is a function: it is called when the request arrives and again after the build, because opening the store can itself
        tidy its write-ahead log; the entry keeps the later value. Concurrent first requests build once."""
        with self._lock:
            hit = self._items.get(key)
            if hit and hit["fingerprint"] == fingerprint() and self.clock() - hit["at"] < self.ttl:
                return hit["payload"], True, hit["etag"]
            payload = builder()
            etag = '"' + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20] + '"'
            self._items[key] = dict(payload=payload, fingerprint=fingerprint(), at=self.clock(), etag=etag)
            return payload, False, etag
