"""Matches hub (read side of the results store): fixtures and results of the five domestic leagues and the UEFA Champions League, filtered and paginated.

GET /api/matches answers: which matches exist for a league (or all five), a season, a matchday and a status, a page at a time, with the facts the page needs to show them honestly:
the stored kickoff (never converted), the verified final score where one is stored, the source, the data freshness of each league and, for matches not yet played, the same
eligibility facts the gameweek page shows. It reads only: no forecast is computed or saved, no model is touched, and the gameweek view (the slow one) is never called.

Bounded by construction
  * one season of one league is at most about 400 rows, and every statement is anchored on the (competition_key, season) index; a unary plus on `status` and `kind` keeps the
    planner off the store-wide (status, match_date) index (the trap that makes the gameweek view slow; see docs/mini-project/phase4/P4_2_PERFORMANCE_INVESTIGATION.md)
  * a page holds at most MAX_LIMIT rows. Pagination is by keyset (an opaque cursor holding the sort key of the last row), so a deep page costs the same as the first one
  * a fixed set of statements per request: for each league involved a season list, a status count, a matchday list, one page of rows and (only if unplayed rows are shown) one season read
    for the reliability flags, plus the freshness statements; the count does not depend on how many matches exist (tests/test_matches.py)

Statuses (effective, from the stored status, the stored date and kickoff, and the server's UTC clock; never from a browser clock, and never "live")
  upcoming         stored scheduled, dated today or later, and not known to have kicked off (a stored UTC kickoff that has passed counts as kicked off; a local time without a time zone does not)
  awaiting_result  no verified result yet although the date has passed, or today's stored UTC kickoff has passed (the page does not say whether the match is in progress or finished)
  completed        a verified final result is stored (completed or awarded)
  other            postponed, cancelled or abandoned
"""
import base64
import json
import re
import sqlite3
from datetime import date, datetime, timezone
from typing import Optional

import config as C
import featured
import gameweeks
from store import sync as store_sync

DOMESTIC = tuple(featured.LEAGUES)
UCL = "UCL"                                              # the hub also lists the Champions League (Phase 4.20); the featured fixture, gameweeks and forecasts stay domestic-only
LEAGUES = DOMESTIC + (UCL,)
MATCHDAY_LABEL = re.compile(r"Matchday\s+(\d+)\s*$", re.I)
TEAM_ID = re.compile(r"^[A-Za-z0-9:_.\-]{3,120}$")
STATUSES = ("upcoming", "awaiting_result", "completed", "other", "all")
ORDERS = ("asc", "desc")
DEFAULT_LIMIT = 25
MAX_LIMIT = 50
MAX_MATCHDAY = 60
CACHE_TTL_SECONDS = featured.CACHE_TTL_SECONDS


class MatchesError(ValueError):
    """User-facing problem with the request (422)."""


class NotFound(MatchesError):
    """The requested season does not exist (404)."""


# ------------------------------------------------------------------------------------------------------------------ request checks
def check(comp: Optional[str], season: Optional[str], matchday: Optional[int], status: str, limit: int, order: Optional[str], team: Optional[str] = None) -> None:
    if comp is not None and comp not in LEAGUES:
        raise MatchesError(f"comp must be one of the five domestic leagues or the Champions League ({', '.join(LEAGUES)})")
    if team is not None:
        if comp is None:
            raise MatchesError("team can only be used together with comp")
        if not TEAM_ID.match(team):
            raise MatchesError("team must be a club identifier from the teams facet")
    if status not in STATUSES:
        raise MatchesError(f"status must be one of {', '.join(STATUSES)}")
    if order is not None and order not in ORDERS:
        raise MatchesError("order must be asc or desc")
    if not 1 <= limit <= MAX_LIMIT:
        raise MatchesError(f"limit must be between 1 and {MAX_LIMIT}")
    if matchday is not None and not 1 <= matchday <= MAX_MATCHDAY:
        raise MatchesError(f"matchday must be between 1 and {MAX_MATCHDAY}")
    if season is not None and not (len(season) == 7 and season[:4].isdigit() and season[4] == "-" and season[5:].isdigit()):
        raise MatchesError("season must look like 2026-27")


def encode_cursor(key: tuple) -> str:
    return base64.urlsafe_b64encode(json.dumps(list(key), separators=(",", ":")).encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple:
    try:
        raw = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode())
        d, k, league, rid = raw
        if not (isinstance(d, str) and isinstance(k, str) and isinstance(rid, str) and isinstance(league, int) and 0 <= league < len(LEAGUES)):
            raise ValueError
        date.fromisoformat(d)
        return d, k, league, rid
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MatchesError("cursor is not valid (use the next_cursor of a previous answer)") from exc


# ------------------------------------------------------------------------------------------------------------------ SQL
# "kicked off or past": the date has passed, or it is today and a stored UTC kickoff has passed. Parameters: today, today, now.
PASSED = "(m.match_date < ? OR (m.match_date = ? AND m.kickoff_utc IS NOT NULL AND m.kickoff_utc <= ?))"
COLUMNS = featured.COLUMNS
JOIN = featured.JOIN
SEASONS_SQL = "SELECT DISTINCT season FROM matches WHERE competition_key=? AND kind='club' ORDER BY season DESC"
MATCHDAYS_SQL = "SELECT DISTINCT matchday_no FROM matches WHERE competition_key=? AND season=? AND +kind='club' AND matchday_no IS NOT NULL ORDER BY matchday_no"
UCL_MATCHDAYS_SQL = "SELECT DISTINCT matchday_label FROM matches WHERE competition_key=? AND season=? AND +kind='club' AND matchday_label IS NOT NULL"      # Champions League rows carry the number only inside the label
TEAMS_SQL = ("SELECT e, MAX(n) FROM (SELECT m.home_entity_id AS e, COALESCE(t.display_name, m.home_name) AS n FROM matches m LEFT JOIN teams t ON t.entity_id=m.home_entity_id "
             "WHERE m.competition_key=? AND m.season=? AND +m.kind='club' UNION ALL SELECT m.away_entity_id, COALESCE(t.display_name, m.away_name) FROM matches m LEFT JOIN teams t ON t.entity_id=m.away_entity_id "
             "WHERE m.competition_key=? AND m.season=? AND +m.kind='club') WHERE e IS NOT NULL GROUP BY e ORDER BY MAX(n)")
COUNTS_SQL = f"SELECT +m.status, {PASSED}, COUNT(*) FROM matches m WHERE m.competition_key=? AND m.season=? AND +m.kind='club'" + "{matchday} GROUP BY 1, 2"
RUNS_SQL = "SELECT matchday_label, COUNT(*) FROM forecast_runs WHERE competition_key=? AND season=? GROUP BY matchday_label"


def _extra(key: str, matchday: Optional[int], team: Optional[str]) -> tuple[str, list]:
    """The optional matchday and team conditions of one league-season statement (always parameterised)."""
    sql, args = "", []
    if matchday is not None:
        if key == UCL:
            sql += " AND m.matchday_label LIKE ?"
            args.append(f"%Matchday {int(matchday)}")
        else:
            sql += " AND m.matchday_no=?"
            args.append(matchday)
    if team is not None:
        sql += " AND (m.home_entity_id=? OR m.away_entity_id=?)"
        args += [team, team]
    return sql, args


def matchday_number(row: dict) -> Optional[int]:
    """The matchday of a stored row: the stored number or, for Champions League rows, the number at the end of the stage label."""
    if row["matchday_no"] is not None:
        return row["matchday_no"]
    m = MATCHDAY_LABEL.search(row["matchday_label"] or "")
    return int(m.group(1)) if m else None


def _status_clause(status: str, today: str, now: str) -> tuple[str, tuple]:
    if status == "upcoming":
        return f"+m.status='scheduled' AND NOT {PASSED}", (today, today, now)
    if status == "awaiting_result":
        return f"(+m.status='awaiting_result' OR (+m.status='scheduled' AND {PASSED}))", (today, today, now)
    if status == "completed":
        return "+m.status IN ('completed','awarded')", ()
    if status == "other":
        return "+m.status NOT IN ('scheduled','awaiting_result','completed','awarded')", ()
    return "1=1", ()


def _after_cursor(cursor: tuple, league: int, order: str) -> tuple[str, tuple]:
    """Rows that sort after the cursor in the global order (date, kickoff, league order, record id), seen from one league (whose order number is constant)."""
    d, k, cl, rid = cursor
    key2, key3 = "(m.match_date, COALESCE(m.kickoff_utc,''))", "(m.match_date, COALESCE(m.kickoff_utc,''), m.record_id)"
    if order == "asc":
        if league == cl:
            return f"{key3} > (?, ?, ?)", (d, k, rid)
        return (f"{key2} >= (?, ?)" if league > cl else f"{key2} > (?, ?)"), (d, k)
    if league == cl:
        return f"{key3} < (?, ?, ?)", (d, k, rid)
    return (f"{key2} <= (?, ?)" if league < cl else f"{key2} < (?, ?)"), (d, k)


def page_query(key: str, season: str, matchday: Optional[int], status: str, order: str, cursor: Optional[tuple], league: int, today: str, now: str, limit: int, team: Optional[str] = None) -> tuple[str, tuple]:
    """The statement for one page of one league-season and its parameters. Exposed so tests can read its query plan."""
    clause, params = _status_clause(status, today, now)
    where, args = ["m.competition_key=?", "m.season=?", "+m.kind='club'", clause], [key, season, *params]
    extra, extra_args = _extra(key, matchday, team)
    if extra:
        where.append(extra[5:])                                   # without the leading " AND "
        args += extra_args
    if cursor:
        cond, p = _after_cursor(cursor, league, order)
        where.append(cond)
        args += list(p)
    d = "DESC" if order == "desc" else "ASC"
    sql = f"SELECT {COLUMNS} {JOIN} WHERE {' AND '.join(where)} ORDER BY m.match_date {d}, COALESCE(m.kickoff_utc,'') {d}, m.record_id {d} LIMIT ?"
    return sql, tuple(args + [limit])


def _counts(conn, key: str, season: str, matchday: Optional[int], today: str, now: str, team: Optional[str] = None) -> dict:
    extra, extra_args = _extra(key, matchday, team)
    sql = COUNTS_SQL.replace("{matchday}", extra)
    out = dict(upcoming=0, awaiting_result=0, completed=0, other=0)
    for status, passed, n in conn.execute(sql, (today, today, now, key, season, *extra_args)):
        if status == "scheduled":
            out["awaiting_result" if passed else "upcoming"] += n
        elif status == "awaiting_result":
            out["awaiting_result"] += n
        elif status in featured.FINISHED:
            out["completed"] += n
        else:
            out["other"] += n
    return out


# ------------------------------------------------------------------------------------------------------------------ items
def _item(row: dict, comp_name: str, eff: str, eligibility: Optional[dict], saved_runs: int, today: date, now: str) -> dict:
    result = None
    if eff in featured.FINISHED:
        h = row["home_goals_90"] if row["home_goals_90"] is not None else row["home_goals_final"]
        a = row["away_goals_90"] if row["away_goals_90"] is not None else row["away_goals_final"]
        if h is not None and a is not None:
            result = dict(home_goals=h, away_goals=a, source=(row["source_system"] or "").split(" (")[0])
    return dict(
        record_id=row["record_id"], competition_key=row["competition_key"], competition=comp_name, season=row["season"], matchday_no=matchday_number(row), matchday_label=row["matchday_label"],
        date=row["match_date"], kickoff=featured._kickoff(row), home=featured._team(row, "home"), away=featured._team(row, "away"), status=eff, stored_status=row["status"],
        result=result, result_missing=eff in featured.FINISHED and result is None, source=(row["source_system"] or "").split(" (")[0],
        timing=featured.timing(row, eff, today, now),
        eligibility=None if eligibility is None else {k: eligibility[k] for k in ("eligible", "predictable", "reliability", "flags")},
        saved_forecast_runs=saved_runs, validation_badge=C.BY_KEY[row["competition_key"]]["badge"])


# ------------------------------------------------------------------------------------------------------------------ the answer
def build(conn: sqlite3.Connection, cfg: store_sync.SyncConfig, now: datetime, comp: Optional[str] = None, season: Optional[str] = None, matchday: Optional[int] = None,
          status: str = "upcoming", limit: int = DEFAULT_LIMIT, cursor: Optional[str] = None, order: Optional[str] = None, team: Optional[str] = None) -> dict:
    """The whole payload. `now` is injected so tests (and the cache) never depend on the clock."""
    check(comp, season, matchday, status, limit, order, team)
    after = decode_cursor(cursor) if cursor else None
    today_d, stamp = now.astimezone(timezone.utc).date(), featured._utc_stamp(now)
    today = today_d.isoformat()
    keys = [comp] if comp else list(LEAGUES)
    order = order or ("asc" if status == "upcoming" or matchday is not None else "desc")
    status_payload = store_sync.status(conn, cfg, now)
    fresh = featured._freshness(status_payload)
    ucl = next((c for c in status_payload["competitions"] if c["competition_key"] == UCL), None)
    if ucl:                                                                  # featured._freshness is domestic-only; the hub adds the Champions League entry from the same sync status
        fresh["competitions"][UCL] = {k: ucl[k] for k in featured.FRESHNESS_KEYS}

    all_seasons = {k: [r[0] for r in conn.execute(SEASONS_SQL, (k,))] for k in keys}
    if season:
        used = {k: season for k in keys if season in all_seasons[k]}
        if not used:
            raise NotFound(f"no data for season '{season}'" + (f" in {comp}" if comp else ""))
    else:
        used = {k: all_seasons[k][0] for k in keys if all_seasons[k]}

    counts = dict(upcoming=0, awaiting_result=0, completed=0, other=0)
    matchdays: set[int] = set()
    rows: list[dict] = []
    for k in keys:
        if k not in used:
            continue
        for name, n in _counts(conn, k, used[k], matchday, today, stamp, team).items():
            counts[name] += n
        if k == UCL:
            matchdays.update(int(m.group(1)) for (label,) in conn.execute(UCL_MATCHDAYS_SQL, (k, used[k])) if (m := MATCHDAY_LABEL.search(label or "")))
        else:
            matchdays.update(r[0] for r in conn.execute(MATCHDAYS_SQL, (k, used[k])))
        sql, args = page_query(k, used[k], matchday, status, order, after, LEAGUES.index(k), today, stamp, limit + 1, team)
        rows += featured._rows(conn, sql, args)
    counts["all"] = sum(counts.values())

    league_no = {k: i for i, k in enumerate(LEAGUES)}
    sort_key = lambda r: (r["match_date"], r["kickoff_utc"] or "", league_no[r["competition_key"]], r["record_id"])  # noqa: E731
    rows.sort(key=sort_key, reverse=(order == "desc"))
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_cursor(sort_key(page[-1])) if has_more and page else None

    effective = {r["record_id"]: featured.effective_status(r, today_d, stamp) for r in page}
    unplayed = {r["record_id"] for r in page if effective[r["record_id"]] in ("scheduled", "awaiting_result") and r["competition_key"] in DOMESTIC}      # eligibility is the gameweek page's rule: domestic only
    shown = sorted({(r["competition_key"], r["season"]) for r in page})
    season_rows = {ks: featured._rows(conn, featured.SEASON_SQL, ks) for ks in sorted({(r["competition_key"], r["season"]) for r in page if r["record_id"] in unplayed})}
    runs = {ks: dict(conn.execute(RUNS_SQL, ks).fetchall()) for ks in shown}
    disputed = featured.DISP.by_record(conn) if unplayed else {}
    teams = [dict(entity=e, name=n) for e, n in conn.execute(TEAMS_SQL, (keys[0], used[keys[0]]) * 2)] if len(keys) == 1 and keys[0] in used else []
    items = []
    for r in page:
        ks = (r["competition_key"], r["season"])
        eligibility = featured._assess(conn, r, fresh["competitions"][r["competition_key"]]["latest_result"], today_d, season_rows[ks], now, disputed) if r["record_id"] in unplayed else None
        items.append(_item(r, C.BY_KEY[r["competition_key"]]["name"], effective[r["record_id"]], eligibility, runs[ks].get(r["matchday_label"], 0) if r["matchday_label"] else 0, today_d, stamp))

    return dict(
        generated_utc=stamp, today_utc=today,
        scope=dict(competitions=keys, seasons=used, matchday=matchday, status=status, order=order, limit=limit, team=team),
        counts=counts, items=items, page=dict(limit=limit, returned=len(items), has_more=has_more, next_cursor=next_cursor),
        facets=dict(seasons=sorted({s for k in keys for s in all_seasons[k]}, reverse=True), matchdays=sorted(matchdays), teams=teams),
        freshness=fresh,
        notes=["Matches are read from the results store; nothing here is live.", "No forecast is computed here; open the gameweek or the manual predictor to make one."])
