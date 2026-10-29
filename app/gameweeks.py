"""Gameweek view of the results store (read side): which fixtures exist, what state they are in, how reliable a forecast for them could be,
and how saved forecasts compare with verified results. Reads only; nothing here writes to the store or touches a model.

Terminology
  stored status      what the store holds (scheduled, awaiting_result, completed, ...)
  effective status   scheduled fixtures whose date has already passed are shown as awaiting_result (a played match without a verified result)
"""
import sqlite3
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import config as C
import disputes as DISP
import kickoff as KO

FIVE = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]
RESCHEDULE_DAYS = 7          # a fixture this far from its gameweek's median date is flagged as rescheduled / out of order
STALE_DAYS = 14              # fixture dated this far after the newest result of its competition => stale history (application label, not protocol)
UNPLAYED = ("scheduled", "awaiting_result")


class GameweekError(ValueError):
    """User-facing problem (unknown league, season or gameweek)."""


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def effective_status(status: str, match_date: str, today: date) -> str:
    return "awaiting_result" if status == "scheduled" and match_date < today.isoformat() else status


def check_league(key: str) -> None:
    if key not in FIVE:
        raise GameweekError(f"gameweek forecasts are available for the five domestic leagues only ({', '.join(FIVE)})")


def seasons(conn: sqlite3.Connection, key: str) -> list[str]:
    check_league(key)
    return [r[0] for r in conn.execute("SELECT DISTINCT season FROM matches WHERE competition_key=? AND kind='club' ORDER BY season DESC", (key,))]


def _fixture_rows(conn, key: str, season: str) -> list[dict]:
    rows = conn.execute(
        "SELECT m.*, t1.display_name AS home_display, t2.display_name AS away_display FROM matches m "
        "LEFT JOIN teams t1 ON t1.entity_id = m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id = m.away_entity_id "
        "WHERE m.competition_key=? AND m.season=? AND m.kind='club' ORDER BY m.match_date, m.record_id", (key, season)).fetchall()
    return [dict(r) for r in rows]


def competition_latest_result(conn, key: str) -> Optional[str]:
    return conn.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (key,)).fetchone()[0]


def _median_date(dates: list[str]) -> date:
    ordinals = sorted(date.fromisoformat(d).toordinal() for d in dates)
    return date.fromordinal(int(statistics.median(ordinals)))


def list_gameweeks(conn: sqlite3.Connection, key: str, season: str, today: Optional[date] = None, now: Optional[datetime] = None) -> dict:
    if now is None:
        now = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) if today else datetime.now(timezone.utc)
    today = today or now.date()
    if season not in seasons(conn, key):
        raise GameweekError(f"no data for season '{season}'")
    rows = [r for r in _fixture_rows(conn, key, season) if r["matchday_no"] is not None]
    disp = DISP.by_record(conn)
    by: dict[int, list[dict]] = {}
    for r in rows:
        by.setdefault(r["matchday_no"], []).append(r)
    saved = {int(r[0]): r[1] for r in conn.execute(
        "SELECT CAST(REPLACE(fr.matchday_label,'Matchday ','') AS INTEGER) AS md, COUNT(*) FROM forecast_runs fr WHERE fr.competition_key=? AND fr.season=? GROUP BY md", (key, season))}
    out = []
    for no in sorted(by):
        fx = by[no]
        eff = [effective_status(r["status"], r["match_date"], today) for r in fx]
        states = [KO.made_before_kickoff(now, r["match_date"], r["kickoff_utc"], key, disp.get(r["record_id"], ())) for r in fx]
        can_predict = [e in UNPLAYED and st == "yes" for e, st in zip(eff, states)]
        eff = ["awaiting_result" if e == "scheduled" and st == "no" else e for e, st in zip(eff, states)]
        med = _median_date([r["match_date"] for r in fx])
        resched = sum(abs((date.fromisoformat(r["match_date"]) - med).days) > RESCHEDULE_DAYS for r in fx)
        out.append(dict(
            matchday_no=no, label=f"Matchday {no}", fixtures=len(fx), first_date=min(r["match_date"] for r in fx), last_date=max(r["match_date"] for r in fx),
            completed=sum(e in ("completed", "awarded") for e in eff), upcoming=sum(e == "scheduled" for e in eff), awaiting_result=sum(e == "awaiting_result" for e in eff),
            postponed_or_cancelled=sum(e in ("postponed", "cancelled") for e in eff), predictable=sum(can_predict), rescheduled_fixtures=resched,
            order_issue=resched > 0, saved_forecast_runs=saved.get(no, 0)))
    nxt = next((g["matchday_no"] for g in out if g["upcoming"] > 0), None) or next((g["matchday_no"] for g in out if g["awaiting_result"] > 0), None)
    return dict(competition_key=key, season=season, seasons=seasons(conn, key), gameweeks=out, next_gameweek=nxt, today_utc=today.isoformat(),
                latest_result=competition_latest_result(conn, key))


# Variant B of docs/mini-project/phase4/P4_2_PERFORMANCE_INVESTIGATION.md: without the hint SQLite plans this on the store-wide (status, match_date) index and walks every completed
# match of every competition for each call (about 220,000 rows in the production store, twice per fixture). The hint changes the plan, never the result (tests/test_team_form_hint.py,
# and the parity runs in docs/mini-project/phase4/P4_3_CHECKPOINT_REPORT.md). A store built without the index falls back to the unhinted statement.
TEAM_FORM_SQL = (
    "SELECT m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final, t1.display_name AS hn, t2.display_name AS an FROM matches m INDEXED BY idx_matches_comp_season_date "
    "LEFT JOIN teams t1 ON t1.entity_id=m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=m.away_entity_id "
    "WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?) AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL "
    "ORDER BY m.match_date DESC, m.record_id DESC LIMIT ?")


def team_form(conn, competition_id: str, entity: str, before_date: str, n: int = 5) -> list[dict]:
    """Last n completed results of a team in this competition dated STRICTLY before `before_date` (nothing from that day or later)."""
    args = (competition_id, entity, entity, before_date, n)
    try:
        rows = conn.execute(TEAM_FORM_SQL, args).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such index" not in str(exc):
            raise
        rows = conn.execute(TEAM_FORM_SQL.replace(" INDEXED BY idx_matches_comp_season_date", ""), args).fetchall()
    out = []
    for r in reversed(rows):
        home = r["home_entity_id"] == entity
        gf, ga = (r["home_goals_final"], r["away_goals_final"]) if home else (r["away_goals_final"], r["home_goals_final"])
        out.append(dict(date=r["match_date"], opponent=(r["an"] if home else r["hn"]), venue="H" if home else "A", gf=gf, ga=ga, result="W" if gf > ga else "D" if gf == ga else "L"))
    return out


def assess(conn, fx: dict, comp_latest: Optional[str], today: date, season_rows: list[dict]) -> dict:
    """How much a forecast for this fixture can be trusted, from the data in the store (no model involved).
    reliability: 'full' | 'provisional' ('unavailable' is decided when scoring)."""
    reasons, flags = [], []
    fdate = fx["match_date"]
    if fx["kickoff_utc"] is None:
        flags.append("kickoff_time_unknown" if fx["kickoff_local"] is None else "kickoff_timezone_unknown")
    stale_days = None
    if comp_latest:
        stale_days = (date.fromisoformat(fdate) - date.fromisoformat(comp_latest)).days
        if stale_days > STALE_DAYS:
            flags.append("stale_history")
            reasons.append(f"The newest result in this competition is {comp_latest}, {stale_days} days before this fixture: team form and ratings are out of date.")
    for side, ent in (("home", fx["home_entity_id"]), ("away", fx["away_entity_id"])):
        missing = [r for r in season_rows if ent in (r["home_entity_id"], r["away_entity_id"]) and r["record_id"] != fx["record_id"] and r["match_date"] < fdate
                   and effective_status(r["status"], r["match_date"], today) == "awaiting_result"]
        unplayed = [r for r in season_rows if ent in (r["home_entity_id"], r["away_entity_id"]) and r["record_id"] != fx["record_id"] and r["match_date"] < fdate
                    and effective_status(r["status"], r["match_date"], today) == "scheduled"]
        name = fx["home_display"] if side == "home" else fx["away_display"]
        if missing:
            flags.append(f"missing_results_{side}")
            reasons.append(f"{name} has {len(missing)} earlier match(es) that should have been played but have no verified result; the forecast cannot use them.")
        if unplayed:
            flags.append(f"earlier_fixtures_unplayed_{side}")
            reasons.append(f"{name} still has {len(unplayed)} fixture(s) before this one that have not been played yet; the forecast is built from the history before them.")
    provisional = any(f in ("stale_history",) or f.startswith("missing_results_") for f in flags)
    if "kickoff_time_unknown" in flags or "kickoff_timezone_unknown" in flags:
        reasons.append("Kickoff time is not known; results dated on the fixture's day are excluded from the forecast, so no same-day information is used.")
    return dict(reliability="provisional" if provisional else "full", flags=flags, reasons=reasons, stale_days=stale_days)


def _outcome(h, a):
    return "H" if h > a else "A" if h < a else "D"


def gameweek_fixtures(conn: sqlite3.Connection, key: str, season: str, matchday_no: int, today: Optional[date] = None, now: Optional[datetime] = None) -> dict:
    """`now` decides whether a kickoff has passed. Given only `today` (tests, replays) it is the start of that day in UTC: nothing earlier than the day itself is assumed."""
    if now is None:
        now = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) if today else datetime.now(timezone.utc)
    today = today or now.date()
    if season not in seasons(conn, key):
        raise GameweekError(f"no data for season '{season}'")
    season_rows = _fixture_rows(conn, key, season)
    disp = DISP.by_record(conn)
    rows = [r for r in season_rows if r["matchday_no"] == matchday_no]
    if not rows:
        raise GameweekError(f"no Matchday {matchday_no} in {season}")
    comp_latest = competition_latest_result(conn, key)
    med = _median_date([r["match_date"] for r in rows])
    saved = latest_forecasts(conn, [r["record_id"] for r in rows])
    fixtures = []
    for r in rows:
        eff = effective_status(r["status"], r["match_date"], today)
        ko_state = KO.made_before_kickoff(now, r["match_date"], r["kickoff_utc"], key, disp.get(r["record_id"], ()))
        if eff == "scheduled" and ko_state == "no":
            eff = "awaiting_result"                                           # the kickoff has certainly passed although the date has not: still no verified result
        a = assess(conn, r, comp_latest, today, season_rows)
        if abs((date.fromisoformat(r["match_date"]) - med).days) > RESCHEDULE_DAYS:
            a["flags"].append("rescheduled_or_out_of_order")
            a["reasons"].append(f"Dated {r['match_date']}, far from the rest of Matchday {matchday_no} (around {med.isoformat()}): likely rescheduled.")
        completed = eff in ("completed", "awarded")
        fx = dict(
            record_id=r["record_id"], matchday_no=matchday_no, date=r["match_date"], kickoff_utc=r["kickoff_utc"], kickoff_local=r["kickoff_local"], home=r["home_display"] or r["home_name"], away=r["away_display"] or r["away_name"],
            home_entity=r["home_entity_id"], away_entity=r["away_entity_id"], stored_status=r["status"], status=eff, kickoff_state=ko_state,
            predictable=eff in UNPLAYED and ko_state == "yes" and bool(r["home_entity_id"] and r["away_entity_id"]),
            result=dict(home=r["home_goals_90"] if r["home_goals_90"] is not None else r["home_goals_final"], away=r["away_goals_90"] if r["away_goals_90"] is not None else r["away_goals_final"],
                        source=(r["source_system"] or "").split(" (")[0]) if completed else None,
            flags=a["flags"], reasons=a["reasons"], reliability=a["reliability"], stale_days=a["stale_days"],
            form=dict(home=team_form(conn, r["competition_id"], r["home_entity_id"], r["match_date"]), away=team_form(conn, r["competition_id"], r["away_entity_id"], r["match_date"])),
            forecast=saved.get(r["record_id"]))
        if not fx["predictable"] and not completed:
            if eff in UNPLAYED and ko_state != "yes":
                fx["reasons"].append(KO.BLOCKED_MESSAGE[ko_state] + (" Awaiting verified result." if eff == "awaiting_result" else ""))
            else:
                fx["reasons"].append(f"Not predicted: status is {eff}.")
        fx["evaluation"] = evaluate(fx) if completed and fx["forecast"] else None
        fixtures.append(fx)
    fixtures.sort(key=lambda f: (f["date"], f["kickoff_utc"] or "", f["record_id"]))
    return dict(competition_key=key, season=season, matchday_no=matchday_no, label=f"Matchday {matchday_no}", today_utc=today.isoformat(), now_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), latest_result=comp_latest, fixtures=fixtures,
                evaluation=summarise([f["evaluation"] for f in fixtures if f["evaluation"]]), runs=runs_for(conn, key, season, matchday_no))


# ----------------------------------------------------------------------------------------------------------- saved forecasts
VARIANT_KEYS = {"club_v1": "primary", "club_v2_r1": "secondary", "elo_baseline": "elo_only"}


def latest_forecasts(conn, record_ids: list[str]) -> dict:
    """Most recent saved forecast per fixture (all model variants of the same run)."""
    if not record_ids:
        return {}
    marks = ",".join("?" * len(record_ids))
    rows = conn.execute(
        f"SELECT f.*, fr.created_utc, fr.model_id, fr.model_artifact_sha256, fr.data_cutoff_date, fr.data_cutoff_note, fr.user_action FROM forecasts f JOIN forecast_runs fr ON fr.forecast_run_id=f.forecast_run_id "
        f"WHERE f.record_id IN ({marks}) AND f.forecast_run_id=(SELECT MAX(f2.forecast_run_id) FROM forecasts f2 WHERE f2.record_id=f.record_id)", record_ids).fetchall()
    out: dict = {}
    import json

    for r in rows:
        e = out.setdefault(r["record_id"], dict(forecast_run_id=r["forecast_run_id"], created_utc=r["created_utc"], data_cutoff_date=r["data_cutoff_date"], data_cutoff_note=r["data_cutoff_note"],
                                                made_before_kickoff=r["made_before_kickoff"], reliability=r["reliability"], flags=json.loads(r["flags_json"] or "[]"),
                                                models=json.loads(r["model_id"]), artifact_sha256=json.loads(r["model_artifact_sha256"]), predictions={}, feature_sha256=None))
        e["predictions"][VARIANT_KEYS[r["model_variant"]]] = dict(home=r["p_home"], draw=r["p_draw"], away=r["p_away"])
        if r["model_variant"] == "club_v1":
            e["feature_sha256"] = r["feature_sha256"]
    return out


def runs_for(conn, key: str, season: str, matchday_no: int) -> list[dict]:
    rows = conn.execute("SELECT forecast_run_id, created_utc, data_cutoff_date, user_action, notes, (SELECT COUNT(DISTINCT record_id) FROM forecasts f WHERE f.forecast_run_id=fr.forecast_run_id) AS fixtures "
                        "FROM forecast_runs fr WHERE competition_key=? AND season=? AND matchday_label=? ORDER BY forecast_run_id DESC", (key, season, f"Matchday {matchday_no}")).fetchall()
    return [dict(r) for r in rows]


def evaluate(fx: dict) -> dict:
    """Predicted versus actual for one finished fixture, using the forecast saved BEFORE the result existed. Primary model = club v1."""
    import math

    f = fx["forecast"]
    p = f["predictions"].get("primary")
    res = fx["result"]
    if not p or res is None or res["home"] is None:
        return None
    actual = _outcome(res["home"], res["away"])
    probs = dict(H=p["home"], D=p["draw"], A=p["away"])
    predicted = max(probs, key=probs.get)
    counted = f["made_before_kickoff"] == "yes"
    return dict(actual=actual, predicted=predicted, correct=predicted == actual, p_actual=probs[actual], log_loss=-math.log(max(probs[actual], 1e-15)), made_before_kickoff=f["made_before_kickoff"],
                reliability=f["reliability"], counted=counted,
                note=None if counted else "Saved after kickoff or with an unknown kickoff relative to the saving time: shown, but not counted in the summary.")


def summarise(evals: list[dict]) -> dict:
    counted = [e for e in evals if e["counted"]]
    n = len(counted)
    return dict(finished_with_forecast=len(evals), counted=n, excluded=len(evals) - n, correct=sum(e["correct"] for e in counted),
                accuracy=(sum(e["correct"] for e in counted) / n) if n else None, mean_log_loss=(sum(e["log_loss"] for e in counted) / n) if n else None,
                caveat="Application forecast history. Not the official prospective evaluation; small samples, and only forecasts saved before kickoff are counted.")
