"""Dashboard analytics (pandas). Reads the SQLite store when it exists (data/footiq.sqlite, built by app/store/build.py), otherwise the
original CSV (data/miniproject/matches.csv). Both give identical frames (tested). Set FOOTIQ_USE_STORE=0 to force the CSV."""
import os
from functools import lru_cache

import pandas as pd

import config as C
from store import db as store_db
from store import views as store_views


def use_store() -> bool:
    return os.environ.get("FOOTIQ_USE_STORE", "1") != "0" and store_db.exists()


@lru_cache(maxsize=1)
def matches() -> pd.DataFrame:
    if use_store():
        conn = store_db.connect(readonly=True)
        try:
            df = store_views.dashboard_matches(conn)
        finally:
            conn.close()
        df["season"] = df.season.astype(str)
    else:
        if not C.MATCHES_CSV.exists():
            raise FileNotFoundError("data/miniproject/matches.csv is missing - run: python app/prepare_data.py")
        df = pd.read_csv(C.MATCHES_CSV, encoding="utf-8-sig", dtype={"season": str}, keep_default_na=False)
    df = df[df.competition_key.isin(C.BY_KEY)].reset_index(drop=True)          # the six supported competitions; the archived ones stay in the data, out of the application
    df["home_goals"] = pd.to_numeric(df.home_goals)
    df["away_goals"] = pd.to_numeric(df.away_goals)
    return df


def reload() -> None:
    """Drop cached frames (call after a sync changed the store)."""
    matches.cache_clear()


def audit() -> list[dict]:
    """Per-competition summary computed from the loaded matches (same figures as data/miniproject/data_audit.csv)."""
    m = matches()
    dup = m.duplicated(["competition_key", "date", "home", "away", "stage"], keep=False)
    out = []
    for comp in C.COMPETITIONS:
        d = m[m.competition_key == comp["key"]]
        out.append(dict(
            competition_key=comp["key"], competition=comp["name"], group=comp["group"], rows=int(len(d)), seasons=int(d.season.nunique()), first_date=d.date.min(), last_date=d.date.max(),
            rows_with_outcome=int((d.outcome.fillna("") != "").sum()), duplicate_rows=int(dup[d.index].sum()), sources=" | ".join(sorted(d.source.unique())), licences=" | ".join(sorted(d.licence.unique())),
            validation_badge=comp["badge"]))
    return out


def season_coverage(key: str) -> list[dict]:
    """Rows per season versus the expected match count from the coverage matrix (club competitions only)."""
    m = matches()
    sc = m.groupby(["competition_key", "season"]).size().rename("rows_in_dataset").reset_index()
    cov = pd.read_csv(C.CLUB_COVERAGE_MATRIX, encoding="utf-8-sig")
    id_to_key = {c["source_id"]: c["key"] for c in C.COMPETITIONS if c["kind"] == "club"}
    exp = cov[["competition_id", "season", "expected_matches", "coverage_pct"]].copy()
    exp["competition_key"] = exp.competition_id.map(id_to_key)
    exp = exp.dropna(subset=["competition_key"]).drop(columns="competition_id")
    exp["season"] = exp.season.astype(str)
    sc = sc.merge(exp, on=["competition_key", "season"], how="left")
    sc["note"] = ""
    sc.loc[sc.expected_matches.notna() & (sc.rows_in_dataset < sc.expected_matches), "note"] = "incomplete or in progress"
    sc.loc[sc.expected_matches.isna(), "note"] = "no expected-count reference available"
    return sc[sc.competition_key == key].fillna("").to_dict("records")


def _sel(key: str, season: str | None = None) -> pd.DataFrame:
    d = matches()
    d = d[d.competition_key == key]
    return d[d.season == season] if season else d


def seasons(key: str) -> list[str]:
    return sorted(_sel(key).season.unique(), reverse=True)


def teams(key: str, season: str | None = None) -> list[str]:
    """Teams with at least one match in the competition (optionally only in one season)."""
    d = _sel(key, season)
    return sorted(set(d.home) | set(d.away))


def summary(key: str, season: str) -> dict:
    d = _sel(key, season)
    n = len(d)
    known = d[d.outcome.isin(["H", "D", "A"])]
    rate = lambda o: round(float((known.outcome == o).mean()), 4) if len(known) else None  # noqa: E731
    return dict(matches=n, goals_per_match=round(float((d.home_goals + d.away_goals).mean()), 3) if n else None,
                home_win_rate=rate("H"), draw_rate=rate("D"), away_win_rate=rate("A"), outcome_basis=d.outcome_basis.iloc[0] if n else "",
                first_date=d.date.min() if n else None, last_date=d.date.max() if n else None)


def standings(key: str, season: str) -> list[dict]:
    """League table from the scored matches in the dataset (3-1-0 points). Only meaningful for round-robin leagues."""
    d = _sel(key, season).sort_values("date", kind="mergesort")
    rows: dict[str, dict] = {}
    for r in d.itertuples():
        for team, gf, ga in ((r.home, r.home_goals, r.away_goals), (r.away, r.away_goals, r.home_goals)):
            t = rows.setdefault(team, dict(team=team, played=0, won=0, drawn=0, lost=0, gf=0, ga=0, form=[]))
            t["form"].append("W" if gf > ga else "D" if gf == ga else "L")
            t["played"] += 1
            t["gf"] += int(gf)
            t["ga"] += int(ga)
            t["won" if gf > ga else "drawn" if gf == ga else "lost"] += 1
    out = []
    for t in rows.values():
        t["form"] = t["form"][-5:]   # last five results, oldest first
        t["gd"] = t["gf"] - t["ga"]
        t["points"] = 3 * t["won"] + t["drawn"]
        out.append(t)
    out.sort(key=lambda t: (-t["points"], -t["gd"], -t["gf"], t["team"]))
    for i, t in enumerate(out, 1):
        t["pos"] = i
    return out


def recent_results(key: str, season: str, limit: int = 30) -> list[dict]:
    d = _sel(key, season).sort_values("date", ascending=False).head(limit)
    return d[["date", "stage", "home", "away", "home_goals", "away_goals", "shootout_winner"]].to_dict("records")


def team_form(key: str, team: str, n: int = 10) -> dict:
    d = _sel(key)
    d = d[(d.home == team) | (d.away == team)].sort_values("date").tail(n)
    out, pts = [], 0
    for r in d.itertuples():
        gf, ga = (r.home_goals, r.away_goals) if r.home == team else (r.away_goals, r.home_goals)
        res = "W" if gf > ga else "D" if gf == ga else "L"
        pts += {"W": 3, "D": 1, "L": 0}[res]
        out.append(dict(date=r.date, opponent=r.away if r.home == team else r.home, venue="H" if r.home == team else "A", gf=int(gf), ga=int(ga), result=res))
    return dict(team=team, last=out, points=pts, played=len(out))


def head_to_head(key: str, a: str, b: str, limit: int = 10) -> dict:
    d = _sel(key)
    d = d[((d.home == a) & (d.away == b)) | ((d.home == b) & (d.away == a))].sort_values("date", ascending=False)
    wa = wb = dr = 0
    for r in d.itertuples():
        ga, gb = (r.home_goals, r.away_goals) if r.home == a else (r.away_goals, r.home_goals)
        wa += ga > gb
        wb += gb > ga
        dr += ga == gb
    return dict(a=a, b=b, meetings=len(d), a_wins=int(wa), b_wins=int(wb), draws=int(dr),
                last=d.head(limit)[["date", "season", "home", "away", "home_goals", "away_goals"]].to_dict("records"))
