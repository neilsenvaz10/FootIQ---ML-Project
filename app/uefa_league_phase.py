"""UEFA Champions League league-phase table (seasons from 2024-25, the 36-team single table). Pure functions plus one reader over the dashboard frame.

Rules: UEFA Regulations of the UEFA Champions League 2026/27, Article 18.01 "Equality of points - league phase" (https://documents.uefa.com/r/Regulations-of-the-UEFA-Champions-League-2026/27/Article-18-Equality-of-points-league-phase-Online,
read on 2026-10-28; ten criteria in this order: goal difference, goals scored, away goals scored, wins, away wins, opponents' points, opponents' goal difference, opponents' goals scored, disciplinary points, club coefficient): 3 points for a win, 1 for a draw; ties on points are broken, in order, by 1 goal difference, 2 goals scored, 3 away goals
scored, 4 wins, 5 away wins; criteria 6-8 (points, goal difference and goals scored collectively by the league-phase opponents) apply only after the final matches have been played; 9 disciplinary points
and 10 the UEFA club coefficient are NOT available in the data, so a tie that survives criteria 1-8 is shown as an unresolved tie (shared rank, alphabetical) and is never broken by a guess.
While the phase is in progress only criteria 1-5 are used. The top eight go straight to the round of 16, 9th to 24th play the knockout play-offs, 25th to 36th are eliminated; a zone is only given when
every team tied at a boundary falls on the same side of it.
Seasons before 2024-25 had group stages: no table is produced for them."""
import re
from typing import Optional

RULES_SOURCE = "UEFA Regulations of the UEFA Champions League 2026/27, Article 18.01 (documents.uefa.com), read 2026-10-28; the in-progress display (criteria 1-5 only, shared ranks) is a presentation convention, not part of Article 18"
MATCHES_PER_TEAM = {"UCL": 8}                          # the Champions League (Europa and Conference League are outside the supported scope)
FIRST_SEASON = "2024-25"
LEAGUE_STAGE = re.compile(r"^(League\b|League phase|Matches\s*>\s*Matchday)", re.I)
ZONES = ((8, "round of 16 (direct)"), (24, "knockout play-off"), (36, "eliminated"))


def is_league_phase_stage(stage: Optional[str]) -> bool:
    s = str(stage or "")
    return bool(LEAGUE_STAGE.match(s)) and not re.search(r"play-?off|knockout|round of|final", s, re.I)


def _zone_of(pos: int) -> str:
    return next(name for limit, name in ZONES if pos <= limit)


def table(matches: list, complete: bool = False) -> list:
    """matches: [{home, away, hg, ag}] (played only). Returns rows sorted by rank. `complete` = every scheduled league-phase match has been played (criteria 6-8 apply)."""
    t: dict = {}
    for m in matches:
        for side, other in (("home", "away"), ("away", "home")):
            me, op = m[side], m[other]
            gf, ga = (m["hg"], m["ag"]) if side == "home" else (m["ag"], m["hg"])
            r = t.setdefault(me, dict(team=me, played=0, won=0, drawn=0, lost=0, gf=0, ga=0, away_gf=0, away_won=0, opponents=[]))
            r["played"] += 1
            r["gf"] += gf
            r["ga"] += ga
            r["opponents"].append(op)
            if side == "away":
                r["away_gf"] += gf
            if gf > ga:
                r["won"] += 1
                r["away_won"] += 1 if side == "away" else 0
            elif gf == ga:
                r["drawn"] += 1
            else:
                r["lost"] += 1
    for r in t.values():
        r["gd"] = r["gf"] - r["ga"]
        r["points"] = 3 * r["won"] + r["drawn"]
    for r in t.values():                                                  # criteria 6-8: what the opponents achieved, summed over the opponents faced
        r["opp_points"] = sum(t[o]["points"] for o in r["opponents"])
        r["opp_gd"] = sum(t[o]["gd"] for o in r["opponents"])
        r["opp_gf"] = sum(t[o]["gf"] for o in r["opponents"])

    def key(r):
        k = (-r["points"], -r["gd"], -r["gf"], -r["away_gf"], -r["won"], -r["away_won"])
        return k + ((-r["opp_points"], -r["opp_gd"], -r["opp_gf"]) if complete else ())

    rows = sorted(t.values(), key=lambda r: (key(r), r["team"]))
    i = 0
    while i < len(rows):                                                  # shared rank for teams equal on every available criterion
        j = i
        while j + 1 < len(rows) and key(rows[j + 1]) == key(rows[i]):
            j += 1
        for n in range(i, j + 1):
            rows[n]["rank"] = i + 1
            rows[n]["tied_unresolved"] = j > i
            lo, hi = i + 1, j + 1
            zones = {_zone_of(p) for p in range(lo, hi + 1)}
            rows[n]["zone"] = next(iter(zones)) if len(zones) == 1 and rows[n]["rank"] <= 36 else "undetermined (tied across a boundary)"
        i = j + 1
    for r in rows:
        del r["opponents"]
        r["position"] = r.pop("rank")
    return rows


def league_phase(df, key: str, season: str) -> dict:
    """The table of one competition-season from the dashboard frame `df` (columns: competition_key, season, stage, home, away, home_goals, away_goals)."""
    if key not in MATCHES_PER_TEAM:
        raise ValueError(f"{key} has no league phase")
    if season < FIRST_SEASON:
        raise ValueError(f"{key} {season} had a group stage: the 36-team league phase started in {FIRST_SEASON}")
    d = df[(df.competition_key == key) & (df.season.astype(str) == season)]
    d = d.loc[d.stage.map(is_league_phase_stage).astype(bool)] if len(d) else d
    played = d.loc[d.home_goals.notna() & d.away_goals.notna()] if len(d) else d
    ms = [dict(home=r.home, away=r.away, hg=int(r.home_goals), ag=int(r.away_goals)) for r in played.itertuples()]
    expected = MATCHES_PER_TEAM[key] * 18
    complete = len(ms) == expected
    rows = table(ms, complete)
    return dict(competition_key=key, season=season, matches_in_data=len(d), matches_played=len(ms), matches_expected=expected, complete=complete, teams=len(rows),
                criteria_applied="1-8 (final table)" if complete else "1-5 (provisional: the league phase is not finished)", unavailable_criteria="9 disciplinary points, 10 UEFA club coefficient: ties that remain are shown as shared ranks",
                rules_source=RULES_SOURCE, coverage_note=(None if len(d) >= expected else f"only {len(d)} of {expected} league-phase fixtures are in the data" + ("" if len(ms) else "; no result yet")), table=rows)
