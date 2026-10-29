"""Phase 4.20 part C: one-off edit script that extends app/matches.py and app/main.py (kept as a record of exactly what changed)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def rep(s, old, new, count=1):
    assert s.count(old) >= 1, f"not found: {old[:70]!r}"
    return s.replace(old, new, count)


p = ROOT / "app" / "matches.py"
s = p.read_text(encoding="utf-8")
s = rep(s, '"""Matches hub (read side of the results store): fixtures and results of the five domestic leagues, filtered and paginated.',
        '"""Matches hub (read side of the results store): fixtures and results of the five domestic leagues and the UEFA Champions League, filtered and paginated.')
s = rep(s, "import base64\nimport json\nimport sqlite3", "import base64\nimport json\nimport re\nimport sqlite3")
s = rep(s, "LEAGUES = featured.LEAGUES\n", '''DOMESTIC = featured.LEAGUES
UCL = "UCL"                                              # the hub also lists the Champions League (Phase 4.20); the featured fixture, gameweeks and forecasts stay domestic-only
LEAGUES = DOMESTIC + (UCL,)
MATCHDAY_LABEL = re.compile(r"Matchday\\s+(\\d+)\\s*$", re.I)
TEAM_ID = re.compile(r"^[A-Za-z0-9:_.\\-]{3,120}$")
''')
s = rep(s, '''def check(comp: Optional[str], season: Optional[str], matchday: Optional[int], status: str, limit: int, order: Optional[str]) -> None:
    if comp is not None and comp not in LEAGUES:
        raise MatchesError(f"comp must be one of the five domestic leagues ({', '.join(LEAGUES)})")''',
        '''def check(comp: Optional[str], season: Optional[str], matchday: Optional[int], status: str, limit: int, order: Optional[str], team: Optional[str] = None) -> None:
    if comp is not None and comp not in LEAGUES:
        raise MatchesError(f"comp must be one of the five domestic leagues or the Champions League ({', '.join(LEAGUES)})")
    if team is not None:
        if comp is None:
            raise MatchesError("team can only be used together with comp")
        if not TEAM_ID.match(team):
            raise MatchesError("team must be a club identifier from the teams facet")''')
s = rep(s, '''MATCHDAYS_SQL = "SELECT DISTINCT matchday_no FROM matches WHERE competition_key=? AND season=? AND +kind='club' AND matchday_no IS NOT NULL ORDER BY matchday_no"''',
        '''MATCHDAYS_SQL = "SELECT DISTINCT matchday_no FROM matches WHERE competition_key=? AND season=? AND +kind='club' AND matchday_no IS NOT NULL ORDER BY matchday_no"
UCL_MATCHDAYS_SQL = "SELECT DISTINCT matchday_label FROM matches WHERE competition_key=? AND season=? AND +kind='club' AND matchday_label IS NOT NULL"      # Champions League rows carry the number only inside the label
TEAMS_SQL = ("SELECT e, MAX(n) FROM (SELECT m.home_entity_id AS e, COALESCE(t.display_name, m.home_name) AS n FROM matches m LEFT JOIN teams t ON t.entity_id=m.home_entity_id "
             "WHERE m.competition_key=? AND m.season=? AND +m.kind='club' UNION ALL SELECT m.away_entity_id, COALESCE(t.display_name, m.away_name) FROM matches m LEFT JOIN teams t ON t.entity_id=m.away_entity_id "
             "WHERE m.competition_key=? AND m.season=? AND +m.kind='club') WHERE e IS NOT NULL GROUP BY e ORDER BY MAX(n)")''')
s = rep(s, "def _status_clause(status: str, today: str, now: str) -> tuple[str, tuple]:", '''def _extra(key: str, matchday: Optional[int], team: Optional[str]) -> tuple[str, list]:
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


def _status_clause(status: str, today: str, now: str) -> tuple[str, tuple]:''')
s = rep(s, '''def page_query(key: str, season: str, matchday: Optional[int], status: str, order: str, cursor: Optional[tuple], league: int, today: str, now: str, limit: int) -> tuple[str, tuple]:
    """The statement for one page of one league-season and its parameters. Exposed so tests can read its query plan."""
    clause, params = _status_clause(status, today, now)
    where, args = ["m.competition_key=?", "m.season=?", "+m.kind='club'", clause], [key, season, *params]
    if matchday is not None:
        where.append("m.matchday_no=?")
        args.append(matchday)
''', '''def page_query(key: str, season: str, matchday: Optional[int], status: str, order: str, cursor: Optional[tuple], league: int, today: str, now: str, limit: int, team: Optional[str] = None) -> tuple[str, tuple]:
    """The statement for one page of one league-season and its parameters. Exposed so tests can read its query plan."""
    clause, params = _status_clause(status, today, now)
    where, args = ["m.competition_key=?", "m.season=?", "+m.kind='club'", clause], [key, season, *params]
    extra, extra_args = _extra(key, matchday, team)
    if extra:
        where.append(extra[5:])                                   # without the leading " AND "
        args += extra_args
''')
s = rep(s, '''def _counts(conn, key: str, season: str, matchday: Optional[int], today: str, now: str) -> dict:
    sql = COUNTS_SQL.replace("{matchday}", " AND m.matchday_no=?" if matchday is not None else "")
    out = dict(upcoming=0, awaiting_result=0, completed=0, other=0)
    for status, passed, n in conn.execute(sql, (today, today, now, key, season, *([matchday] if matchday is not None else []))):''',
        '''def _counts(conn, key: str, season: str, matchday: Optional[int], today: str, now: str, team: Optional[str] = None) -> dict:
    extra, extra_args = _extra(key, matchday, team)
    sql = COUNTS_SQL.replace("{matchday}", extra)
    out = dict(upcoming=0, awaiting_result=0, completed=0, other=0)
    for status, passed, n in conn.execute(sql, (today, today, now, key, season, *extra_args)):''')
s = rep(s, 'season=row["season"], matchday_no=row["matchday_no"], matchday_label=row["matchday_label"],\n        date=row["match_date"],',
        'season=row["season"], matchday_no=matchday_number(row), matchday_label=row["matchday_label"],\n        date=row["match_date"],')
s = rep(s, "        saved_forecast_runs=saved_runs)", '        saved_forecast_runs=saved_runs, validation_badge=C.BY_KEY[row["competition_key"]]["badge"], stage=row["stage"])')
s = rep(s, '''          status: str = "upcoming", limit: int = DEFAULT_LIMIT, cursor: Optional[str] = None, order: Optional[str] = None) -> dict:
    """The whole payload. `now` is injected so tests (and the cache) never depend on the clock."""
    check(comp, season, matchday, status, limit, order)''', '''          status: str = "upcoming", limit: int = DEFAULT_LIMIT, cursor: Optional[str] = None, order: Optional[str] = None, team: Optional[str] = None) -> dict:
    """The whole payload. `now` is injected so tests (and the cache) never depend on the clock."""
    check(comp, season, matchday, status, limit, order, team)''')
s = rep(s, "    fresh = featured._freshness(store_sync.status(conn, cfg, now))\n", '''    status_payload = store_sync.status(conn, cfg, now)
    fresh = featured._freshness(status_payload)
    ucl = next((c for c in status_payload["competitions"] if c["competition_key"] == UCL), None)
    if ucl:                                                                  # featured._freshness is domestic-only; the hub adds the Champions League entry from the same sync status
        fresh["competitions"][UCL] = {k: ucl[k] for k in featured.FRESHNESS_KEYS}
''')
s = rep(s, '''        for name, n in _counts(conn, k, used[k], matchday, today, stamp).items():
            counts[name] += n
        matchdays.update(r[0] for r in conn.execute(MATCHDAYS_SQL, (k, used[k])))
        sql, args = page_query(k, used[k], matchday, status, order, after, LEAGUES.index(k), today, stamp, limit + 1)''', '''        for name, n in _counts(conn, k, used[k], matchday, today, stamp, team).items():
            counts[name] += n
        if k == UCL:
            matchdays.update(int(m.group(1)) for (label,) in conn.execute(UCL_MATCHDAYS_SQL, (k, used[k])) if (m := MATCHDAY_LABEL.search(label or "")))
        else:
            matchdays.update(r[0] for r in conn.execute(MATCHDAYS_SQL, (k, used[k])))
        sql, args = page_query(k, used[k], matchday, status, order, after, LEAGUES.index(k), today, stamp, limit + 1, team)''')
s = rep(s, '''    unplayed = {r["record_id"] for r in page if effective[r["record_id"]] in ("scheduled", "awaiting_result")}''',
        '''    unplayed = {r["record_id"] for r in page if effective[r["record_id"]] in ("scheduled", "awaiting_result") and r["competition_key"] in DOMESTIC}      # eligibility is the gameweek page's rule: domestic only''')
s = rep(s, "    disputed = featured.DISP.by_record(conn) if unplayed else {}", '''    disputed = featured.DISP.by_record(conn) if unplayed else {}
    teams = [dict(entity=e, name=n) for e, n in conn.execute(TEAMS_SQL, (keys[0], used[keys[0]]) * 2)] if len(keys) == 1 and keys[0] in used else []''')
s = rep(s, "scope=dict(competitions=keys, seasons=used, matchday=matchday, status=status, order=order, limit=limit),", "scope=dict(competitions=keys, seasons=used, matchday=matchday, status=status, order=order, limit=limit, team=team),")
s = rep(s, "facets=dict(seasons=sorted({s for k in keys for s in all_seasons[k]}, reverse=True), matchdays=sorted(matchdays)),", "facets=dict(seasons=sorted({s for k in keys for s in all_seasons[k]}, reverse=True), matchdays=sorted(matchdays), teams=teams),")
p.write_text(s, encoding="utf-8")

p = ROOT / "app" / "main.py"
s = p.read_text(encoding="utf-8")
s = rep(s, "limit: int = Query(matches.DEFAULT_LIMIT, ge=1, le=matches.MAX_LIMIT), cursor: str | None = None, order: str | None = None):",
        "limit: int = Query(matches.DEFAULT_LIMIT, ge=1, le=matches.MAX_LIMIT), cursor: str | None = None, order: str | None = None, team: str | None = None):")
s = rep(s, "matches.check(comp, season, matchday, status, limit, order)", "matches.check(comp, season, matchday, status, limit, order, team)")
s = rep(s, "return matches.build(conn, sync_manager.cfg, now, comp, season, matchday, status, limit, cursor, order)", "return matches.build(conn, sync_manager.cfg, now, comp, season, matchday, status, limit, cursor, order, team)")
s = rep(s, "matches_cache.get_or_build((comp, season, matchday, status, limit, cursor, order, now.date().isoformat())", "matches_cache.get_or_build((comp, season, matchday, status, limit, cursor, order, team, now.date().isoformat())")
p.write_text(s, encoding="utf-8")
print("patched")
