"""FootIQ mini-project API + static page.  Full reference: docs/mini-project/API_REFERENCE.md

    .venv\\Scripts\\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000
then open http://127.0.0.1:8000

CORS: off by default for other origins except the usual local dev servers. Set FOOTIQ_CORS_ORIGINS to a comma-separated list of exact
origins (never "*") to change it, e.g. FOOTIQ_CORS_ORIGINS=https://footiq.example.edu
"""
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import analytics
import forecast
import gameweeks
import config as C
import featured
import matches
import integrity
import performance
import predict
from seasonsim import rules as season_rules
from seasonsim import service as season_sim
from store import db as store_db
from store import sync as store_sync
import freshness
import uefa_league_phase
from store.sync import SyncManager

STATIC = Path(__file__).resolve().parent / "static"
DEFAULT_CORS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,http://127.0.0.1:3000"   # Vite / Create React App dev servers


def cors_origins() -> list[str]:
    origins = [o.strip() for o in os.environ.get("FOOTIQ_CORS_ORIGINS", DEFAULT_CORS).split(",") if o.strip()]
    if "*" in origins:
        raise RuntimeError('FOOTIQ_CORS_ORIGINS must list exact origins; "*" is not allowed')
    return origins


def _after_sync_change() -> None:
    """New results were stored: refresh derived views and rebuild the prediction HISTORY (never the model weights)."""
    analytics.reload()
    featured_cache.clear()
    matches_cache.clear()
    predict.reset_club_state()
    threading.Thread(target=lambda: _safe(predict.warm_up), daemon=True).start()


sync_manager = SyncManager(on_change=_after_sync_change)
featured_cache = featured.Cache()
matches_cache = featured.Cache()


@asynccontextmanager
async def lifespan(_):
    # build the club-prediction state in the background so the first prediction is fast (about 20-30 s)
    threading.Thread(target=lambda: _safe(predict.warm_up), daemon=True).start()
    sync_manager.start()          # start-up freshness check runs in its own thread after a short delay; it never blocks the app
    yield
    sync_manager.stop()


def _safe(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001  (warm-up failure must not stop the dashboard)
        print("warm-up failed:", exc)


app = FastAPI(title="FootIQ mini-project", version="1.1", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["GET", "POST"], allow_headers=["Content-Type"], allow_credentials=False)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    """Every error has the same shape: {"detail": "<message>"} (plus "errors" for parameter validation problems)."""
    first = exc.errors()[0]
    where = ".".join(str(x) for x in first["loc"] if x != "query")
    return JSONResponse(status_code=422, content=dict(detail=f"{where}: {first['msg']}", errors=[dict(field=".".join(str(x) for x in e["loc"]), message=e["msg"]) for e in exc.errors()]))


def _comp(key: str) -> dict:
    if key not in C.BY_KEY:
        raise HTTPException(404, f"unknown competition '{key}'")
    return C.BY_KEY[key]


def _team(key: str, team: str) -> None:
    if team not in analytics.teams(key):
        raise HTTPException(404, f"team '{team}' not found in {C.BY_KEY[key]['name']} (use the names from /api/competitions/{key}/teams)")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


def _store_ro():
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    return store_db.connect(readonly=True)


@app.get("/api/featured-fixture")
def featured_fixture(request: Request, comp: str | None = None, upcoming: int = Query(8, ge=1, le=featured.MAX_LIST), results: int = Query(8, ge=0, le=featured.MAX_LIST)):
    """Home dashboard data: the featured upcoming fixture (next scheduled fixture of the five domestic leagues whose teams are known), the fixtures after it, the latest verified
    results, per-competition freshness and per-fixture eligibility. Bounded indexed statements, cached for a minute (ETag, Cache-Control). Computes no forecast, saves nothing, never
    calls the gameweek view; `featured` is null with an `empty_state` when nothing can be featured. See docs/mini-project/API_REFERENCE.md."""
    try:
        featured.check_comp(comp)
    except featured.FeaturedError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    now = datetime.now(timezone.utc)

    def build():
        conn = store_db.connect(readonly=True)
        try:
            return featured.build(conn, sync_manager.cfg, now, comp, upcoming, results)
        finally:
            conn.close()

    payload, hit, etag = featured_cache.get_or_build((comp, upcoming, results, now.date().isoformat()), lambda: featured.store_fingerprint(store_db.DEFAULT_PATH), build)
    headers = {"Cache-Control": f"private, max-age={featured.CACHE_TTL_SECONDS}", "ETag": etag, "X-FootIQ-Cache": "hit" if hit else "miss"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(payload, headers=headers)


@app.get("/api/matches")
def list_matches(request: Request, comp: str | None = None, season: str | None = None, matchday: int | None = Query(None, ge=1, le=matches.MAX_MATCHDAY), status: str = "upcoming",
                 limit: int = Query(matches.DEFAULT_LIMIT, ge=1, le=matches.MAX_LIMIT), cursor: str | None = None, order: str | None = None, team: str | None = None):
    """Matches hub data: fixtures and results of the five domestic leagues, filtered by league, season (default: the newest of each league), matchday and status (upcoming, awaiting_result,
    completed, other, all), a page at a time (keyset cursor). Every query is bounded and anchored on the (competition, season) index. Reads the store only: no forecast, no model,
    never the gameweek view. Kickoffs are returned as stored, with `zone_verified` and a `timing` note for fixtures dated today whose time zone is unconfirmed.
    See docs/mini-project/API_REFERENCE.md."""
    try:
        matches.check(comp, season, matchday, status, limit, order, team)
        if cursor:
            matches.decode_cursor(cursor)
    except matches.MatchesError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    now = datetime.now(timezone.utc)

    def build():
        conn = store_db.connect(readonly=True)
        try:
            return matches.build(conn, sync_manager.cfg, now, comp, season, matchday, status, limit, cursor, order, team)
        finally:
            conn.close()

    try:
        payload, hit, etag = matches_cache.get_or_build((comp, season, matchday, status, limit, cursor, order, team, now.date().isoformat()), lambda: featured.store_fingerprint(store_db.DEFAULT_PATH), build)
    except matches.NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except matches.MatchesError as exc:
        raise HTTPException(422, str(exc)) from exc
    headers = {"Cache-Control": f"private, max-age={matches.CACHE_TTL_SECONDS}", "ETag": etag, "X-FootIQ-Cache": "hit" if hit else "miss"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(payload, headers=headers)


@app.get("/api/gameweeks")
def list_gameweeks(key: str, season: str | None = None):
    """Gameweeks of a domestic league season with dates, status counts and out-of-order flags. Defaults to the newest season."""
    _comp(key)
    conn = _store_ro()
    try:
        ss = gameweeks.seasons(conn, key)
        return gameweeks.list_gameweeks(conn, key, season or ss[0], now=datetime.now(timezone.utc))
    except gameweeks.GameweekError as exc:
        raise HTTPException(404 if "season" in str(exc) else 422, str(exc)) from exc
    finally:
        conn.close()


@app.get("/api/gameweek")
def gameweek(key: str, matchday: int = Query(ge=1, le=60), season: str | None = None):
    """Every fixture of one gameweek: status, kickoff knowledge, reliability flags, form, the latest SAVED forecast (if any) and predicted-versus-actual. Computes no forecast."""
    _comp(key)
    conn = _store_ro()
    try:
        ss = gameweeks.seasons(conn, key)
        return gameweeks.gameweek_fixtures(conn, key, season or ss[0], matchday, now=datetime.now(timezone.utc))
    except gameweeks.GameweekError as exc:
        raise HTTPException(404, str(exc)) from exc
    finally:
        conn.close()


class GameweekPredictRequest(BaseModel):
    key: str
    season: str
    matchday: int
    user_action: str


@app.post("/api/gameweek/predict")
def gameweek_predict(req: GameweekPredictRequest):
    """Forecast every unplayed fixture of the gameweek with the frozen club models and SAVE the run. Only valid as the result of the user pressing Predict gameweek."""
    _comp(req.key)
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    try:
        return forecast.predict_gameweek(req.key, req.season, req.matchday, req.user_action)
    except (forecast.ForecastError, gameweeks.GameweekError) as exc:
        raise HTTPException(422, str(exc)) from exc


class SeasonSimRequest(BaseModel):
    key: str
    season: str
    user_action: str
    simulations: int | None = None
    seed: int | None = None
    include_experimental: bool = False


@app.get("/api/season/status")
def season_status(key: str, season: str | None = None):
    """Eligibility (Ready / Provisional / Not eligible), rule profile, assumptions and gates for a league season. Computes nothing and saves nothing."""
    _comp(key)
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    try:
        conn = _store_ro()
        try:
            ss = gameweeks.seasons(conn, key)
        finally:
            conn.close()
        return season_sim.status(key, season or ss[0])
    except (gameweeks.GameweekError, season_sim.SimError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/season/simulate")
def season_simulate(req: SeasonSimRequest):
    """Run and SAVE a season simulation. Only valid as the result of the user pressing Run season simulation; refused while the league is not eligible, its rules are blocked, or no scoreline method has been approved."""
    _comp(req.key)
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    try:
        return season_sim.run_simulation(req.key, req.season, req.simulations, req.seed, req.user_action, req.include_experimental)
    except (season_sim.SimError, gameweeks.GameweekError, season_rules.RuleBlocked) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/season/points")
def season_points(req: SeasonSimRequest):
    """Run and SAVE an Experimental points-only simulation (3/1/0 points, no tie-breaks, no positions). Only valid as the result of the user pressing Run points-only simulation."""
    _comp(req.key)
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    try:
        return season_sim.run_points_only(req.key, req.season, req.simulations, req.seed, req.user_action)
    except (season_sim.SimError, gameweeks.GameweekError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/season/runs")
def season_runs(key: str, season: str):
    _comp(key)
    return season_sim.list_runs(key, season)


@app.get("/api/season/run")
def season_run(id: int = Query(ge=1)):
    try:
        return season_sim.get_run(id)
    except season_sim.SimError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/sync/status")
def sync_status():
    """Per-competition freshness: latest result, awaiting results, last successful sync, source, state (fresh/stale) and why. Never 'live'."""
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    conn = store_db.connect(readonly=True)
    try:
        st = store_sync.status(conn, sync_manager.cfg)
        st["scheduler"].update(lock_state=sync_manager.lock_state, lock_file=str(sync_manager.lock_path), process_id=os.getpid(), active_scheduler_threads=store_sync.active_scheduler_threads(), enabled_competitions=sync_manager.cfg.approved_competitions(), refresh_mode=sync_manager.cfg.refresh_mode)
        sch = st["scheduler"]
        if sync_manager.cfg.sync_mode == "startup":                                                      # no scheduler in this mode: report the one refresh of this launch
            sch["startup"] = dict(sync_manager.startup_state)
            if sync_manager.cfg.live_enabled:
                sch["status"] = store_sync.describe_startup(sync_manager.startup_state, sync_manager.cfg.startup_min_gap_minutes)
        elif sync_manager.cfg.live_enabled and sch["active_scheduler_threads"] == 0:                    # say what THIS process is doing, not just what the log history implies
            sch["status"] = ("not scheduling here: another FootIQ process holds the scheduler lock" if sync_manager.lock_state == "held_by_another_process"
                             else "not scheduling here: FOOTIQ_DISABLE_SYNC=1" if os.environ.get("FOOTIQ_DISABLE_SYNC") == "1" else sch["status"])
        return st
    finally:
        conn.close()


@app.get("/api/health")
def health():
    return dict(status="ok", club_prediction_ready=predict.club_ready(), data_rows=len(analytics.matches()))


@app.get("/api/meta")
def meta():
    audit = analytics.audit()
    club = [a for a in audit if C.BY_KEY[a["competition_key"]]["kind"] == "club"]
    return dict(
        attribution=[
            dict(source="openfootball (club leagues and the UEFA Champions League)", licence="CC0-1.0"),
            dict(source="Wikipedia (parts of the Champions League data)", licence="CC BY-SA 4.0", requirement="attribution and share-alike"),
            dict(source="OpenLigaDB (Bundesliga and La Liga results, refreshed when FootIQ starts)", licence="ODbL-1.0", requirement="attribution"),
        ],
        data_through=dict(club_results=max(a["last_date"] for a in club),
                          note="predictions only use history up to this date; a prediction date must be after it"),
        models=dict(
            club_v1=dict(role="primary club predictor", evidence="locked test and forward holdout, executed once; previously inspected"),
            club_v2_r1=dict(role="shown beside v1", evidence="development folds only; refit consumed earlier test/holdout; no unbiased evaluation")),
        integrity=integrity.check(),
        limitations=[
            "The Champions League is not validated: the club models were evaluated on domestic leagues only; its data is historical (not updated automatically).",
            "Only Bundesliga and La Liga are refreshed (once, when FootIQ starts); Premier League, Serie A and Ligue 1 are historical until the data provider's permission and disputed fixture dates are resolved.",
            "Ligue 1 2019-20 has 279 of 380 matches; all 2026-27 league seasons are partial."],
        validation_badges={c["key"]: c["badge"] for c in C.COMPETITIONS})


@app.get("/api/competitions")
def competitions():
    audit = {a["competition_key"]: a for a in analytics.audit()}
    return [dict(key=c["key"], name=c["name"], group=c["group"], badge=c["badge"], basis=c["basis"], **{k: audit[c["key"]][k] for k in (
        "rows", "seasons", "first_date", "last_date", "sources", "licences")}) for c in C.COMPETITIONS]


@app.get("/api/competitions/{key}/seasons")
def seasons(key: str):
    _comp(key)
    return analytics.seasons(key)


@app.get("/api/competitions/{key}/teams")
def teams(key: str, season: str | None = None):
    """All teams in the dataset for the competition, or only those that played in `season` (e.g. the current one)."""
    _comp(key)
    if season is not None and season not in analytics.seasons(key):
        raise HTTPException(404, f"no data for season '{season}'")
    return analytics.teams(key, season)


@app.get("/api/models/performance")
def model_performance():
    """Evaluation results read from the repository's own report files (nothing recomputed). See performance.py."""
    try:
        return performance.summary()
    except FileNotFoundError as exc:
        raise HTTPException(503, f"evaluation file missing: {exc.filename}") from exc


@app.get("/api/competitions/{key}/coverage")
def coverage(key: str):
    _comp(key)
    return analytics.season_coverage(key)


@app.get("/api/competitions/{key}/dashboard")
def dashboard(key: str, season: str):
    comp = _comp(key)
    if season not in analytics.seasons(key):
        raise HTTPException(404, f"no data for season '{season}'")
    return dict(competition=comp["name"], badge=comp["badge"], season=season, summary=analytics.summary(key, season),
                standings=analytics.standings(key, season) if comp["group"] == "Domestic league" else None,
                results=analytics.recent_results(key, season))


@app.get("/api/data-freshness")
def data_freshness():
    """One record per competition of the approved scope: latest result held, 'updated when FootIQ starts' or 'historical only', last successful refresh and missing-coverage warnings. Read-only."""
    conn = store_db.connect(readonly=True) if store_db.exists() else None
    try:
        st = store_sync.status(conn, sync_manager.cfg) if conn is not None else None
    finally:
        if conn is not None:
            conn.close()
    return freshness.build(analytics.matches(), st, sync_manager.cfg.approved_competitions(), sync_manager.cfg.live_enabled, sync_manager.cfg.sync_mode, datetime.now(timezone.utc).date())


@app.get("/api/competitions/{key}/league-phase")
def league_phase_table(key: str, season: str):
    """The 36-team UEFA league-phase table (UCL, UEL, UECL; seasons from 2024-25) built from the results in the data with the tie-breakers of the UEFA regulations that the data can evaluate.
    Provisional while the phase is running; coverage and unavailable criteria are stated in the response."""
    _comp(key)
    try:
        return uefa_league_phase.league_phase(analytics.matches(), key, season)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/team")
def team(key: str, team: str, opponent: str | None = None):
    _comp(key)
    _team(key, team)
    out = dict(form=analytics.team_form(key, team))
    if opponent:
        _team(key, opponent)
        if opponent == team:
            raise HTTPException(422, "opponent must differ from team")
        out["head_to_head"] = analytics.head_to_head(key, team, opponent)
    return out


@app.get("/api/predict")
def predict_match(key: str, home: str, away: str, date: str | None = None, venue: str | None = Query(None, pattern="^(neutral|home)$")):
    _comp(key)
    try:
        return predict.predict(key, home, away, date, venue)
    except predict.PredictionError as exc:
        raise HTTPException(422, str(exc)) from exc
