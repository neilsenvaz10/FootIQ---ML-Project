#!/usr/bin/env python3
"""World Cup prediction model v2.

V2 addresses v1's biggest issue: Elo domination. It converts each layer into
0-100 feature scores, then combines them with explicit weights.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
INPUTS = ROOT / "data" / "inputs"
OUTPUTS = ROOT / "outputs"

TEAM_ALIASES = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Cape Verde Islands": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "Czechia": "Czech Republic",
}

DISPLAY_NAMES = {
    "United States": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
}

HOST_COUNTRY_BY_GROUND = {
    "Mexico City": "Mexico",
    "Guadalajara (Zapopan)": "Mexico",
    "Monterrey (Guadalupe)": "Mexico",
    "Toronto": "Canada",
    "Vancouver": "Canada",
    "Atlanta": "United States",
    "Boston (Foxborough)": "United States",
    "Dallas (Arlington)": "United States",
    "Houston": "United States",
    "Kansas City": "United States",
    "Los Angeles (Inglewood)": "United States",
    "Miami (Miami Gardens)": "United States",
    "New York/New Jersey (East Rutherford)": "United States",
    "Philadelphia": "United States",
    "San Francisco Bay Area (Santa Clara)": "United States",
    "Seattle": "United States",
}

GROUP_ORDER = list("ABCDEFGHIJKL")

ROUND_ORDER = {
    "Round of 32": 1,
    "Round of 16": 2,
    "Quarter-final": 3,
    "Semi-final": 4,
    "Match for third place": 5,
    "Final": 6,
}

MODEL_CONFIG = {
    "seed": 20260604,
    "simulations": 50000,
    "base_goal_rate": 1.18,
    "power_goal_scale": 43.0,
    "host_advantage_group_power": 3.0,
    "host_advantage_knockout_power": 2.0,
    "knockout_draw_penalty_noise": 3.5,
    "weights": {
        "elo_score": 0.30,
        "squad_score": 0.25,
        "manager_score": 0.15,
        "recent_form_score": 0.10,
        "tactical_score": 0.10,
        "ceiling_score": 0.05,
        "availability_score": 0.05,
    },
}

MANAGER_OVERRIDES = {
    "Argentina": ("Lionel Scaloni", 91, 84, "balanced possession / transition"),
    "France": ("Didier Deschamps", 94, 82, "pragmatic elite-transition"),
    "Spain": ("Luis de la Fuente", 86, 84, "possession / high technical control"),
    "England": ("Thomas Tuchel", 86, 88, "structured possession / pressing"),
    "Brazil": ("Carlo Ancelotti", 89, 86, "adaptive possession / star-led attack"),
    "Portugal": ("Roberto Martinez", 78, 76, "possession / attacking width"),
    "Netherlands": ("Ronald Koeman", 76, 74, "possession / wing progression"),
    "Germany": ("Julian Nagelsmann", 82, 90, "high-tempo positional play"),
    "Croatia": ("Zlatko Dalic", 87, 78, "midfield control / tournament management"),
    "Uruguay": ("Marcelo Bielsa", 82, 88, "high press / direct verticality"),
    "Morocco": ("Walid Regragui", 84, 80, "compact block / transition"),
    "Colombia": ("Nestor Lorenzo", 78, 78, "balanced possession / counters"),
    "Japan": ("Hajime Moriyasu", 80, 82, "compact transitions / tactical flexibility"),
    "Belgium": ("Rudi Garcia", 74, 72, "possession / direct attacking phases"),
    "Mexico": ("Javier Aguirre", 78, 72, "pragmatic tournament management"),
    "Canada": ("Jesse Marsch", 72, 80, "pressing / vertical transitions"),
    "United States": ("Mauricio Pochettino", 82, 86, "pressing / vertical possession"),
    "Turkey": ("Vincenzo Montella", 74, 76, "technical midfield / transitions"),
    "Switzerland": ("Murat Yakin", 76, 74, "compact tournament pragmatism"),
    "Ecuador": ("Sebastian Beccacece", 73, 76, "aggressive pressing / transitions"),
    "Austria": ("Ralf Rangnick", 84, 88, "pressing / vertical attacks"),
    "Ghana": ("Carlos Queiroz", 86, 78, "defensive structure / tournament experience"),
    "Panama": ("Thomas Christiansen", 72, 70, "compact / direct transitions"),
    "Paraguay": ("Gustavo Alfaro", 76, 72, "defensive block / set pieces"),
    "Australia": ("Tony Popovic", 70, 70, "compact / physical transitions"),
    "Norway": ("Stale Solbakken", 68, 70, "direct attack / star focal points"),
    "Senegal": ("Pape Thiaw", 70, 68, "athletic transitions"),
    "Algeria": ("Vladimir Petkovic", 74, 72, "balanced / experienced setup"),
    "DR Congo": ("Sebastien Desabre", 70, 72, "transition / athletic structure"),
    "Uzbekistan": ("Timur Kapadze", 66, 68, "compact / fast transitions"),
    "Qatar": ("Julen Lopetegui", 78, 80, "possession / positional play"),
    "South Africa": ("Hugo Broos", 76, 70, "compact / tournament pragmatism"),
    "Scotland": ("Steve Clarke", 73, 70, "compact 3/5-back structure"),
    "South Korea": ("Hong Myung-bo", 70, 70, "balanced / transition pace"),
    "New Zealand": ("Darren Bazeley", 62, 62, "compact / direct play"),
}

SQUAD_OVERRIDES = {
    "France": (94, 93, 96),
    "England": (92, 91, 93),
    "Spain": (91, 92, 88),
    "Argentina": (90, 91, 86),
    "Brazil": (90, 90, 89),
    "Portugal": (89, 89, 88),
    "Netherlands": (86, 86, 84),
    "Germany": (86, 86, 85),
    "Colombia": (84, 84, 81),
    "Uruguay": (83, 84, 79),
    "Croatia": (82, 82, 78),
    "Belgium": (81, 82, 77),
    "Morocco": (80, 81, 76),
    "Japan": (79, 78, 78),
    "Ecuador": (78, 79, 74),
    "Turkey": (78, 78, 75),
    "Switzerland": (77, 77, 75),
    "Mexico": (76, 76, 74),
    "United States": (77, 77, 75),
    "Canada": (74, 75, 70),
    "Senegal": (76, 76, 73),
    "Austria": (77, 77, 74),
    "Norway": (76, 78, 70),
    "Algeria": (73, 73, 70),
    "Ivory Coast": (74, 74, 72),
    "Ghana": (72, 72, 69),
    "Paraguay": (73, 73, 70),
    "Australia": (72, 72, 69),
    "Sweden": (72, 72, 69),
    "Czech Republic": (71, 71, 68),
    "Egypt": (72, 73, 68),
    "Iran": (71, 72, 68),
    "South Korea": (72, 72, 69),
}


def normalize_team(team: str) -> str:
    return TEAM_ALIASES.get(team, team)


def display_team(team: str) -> str:
    return DISPLAY_NAMES.get(team, team)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def percentile_scores(values: dict[str, float]) -> dict[str, float]:
    ranked = sorted(values.items(), key=lambda item: item[1])
    n = len(ranked)
    if n <= 1:
        return {team: 50.0 for team in values}
    return {team: 100.0 * idx / (n - 1) for idx, (team, _) in enumerate(ranked)}


def score_from_adjustment(value: float, scale: float) -> float:
    return clamp(50.0 + value * scale, 0.0, 100.0)


def poisson_pmf(lam: float, max_goals: int = 9) -> list[float]:
    probs = [math.exp(-lam)]
    for k in range(1, max_goals + 1):
        probs.append(probs[-1] * lam / k)
    total = sum(probs)
    probs[-1] += max(0.0, 1.0 - total)
    return probs


def sample_poisson(lam: float) -> int:
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= random.random()
    return k - 1


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def expected_goals(power_a: float, power_b: float) -> tuple[float, float]:
    diff = power_a - power_b
    base = MODEL_CONFIG["base_goal_rate"]
    scale = MODEL_CONFIG["power_goal_scale"]
    return (
        clamp(base * math.exp(diff / scale), 0.25, 3.2),
        clamp(base * math.exp(-diff / scale), 0.25, 3.2),
    )


def scoreline_probabilities(lambda_a: float, lambda_b: float, max_goals: int = 9) -> tuple[float, float, float]:
    pa = poisson_pmf(lambda_a, max_goals)
    pb = poisson_pmf(lambda_b, max_goals)
    a_win = draw = b_win = 0.0
    for i, p_i in enumerate(pa):
        for j, p_j in enumerate(pb):
            p = p_i * p_j
            if i > j:
                a_win += p
            elif i == j:
                draw += p
            else:
                b_win += p
    total = a_win + draw + b_win
    return a_win / total, draw / total, b_win / total


def build_tactical_adjustments() -> dict[str, dict[str, Any]]:
    rows = read_csv(PROCESSED / "statsbomb_team_event_summary.csv")
    by_team: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_team[normalize_team(row["team"])].append(row)
    raw: dict[str, dict[str, float]] = {}
    for team, team_rows in by_team.items():
        raw[team] = {
            "avg_xg": mean(safe_float(row, "shot_xg") for row in team_rows),
            "avg_shots": mean(safe_float(row, "shots") for row in team_rows),
            "avg_pressures": mean(safe_float(row, "pressures") for row in team_rows),
            "avg_pass_completion_pct": mean(safe_float(row, "pass_completion_pct") for row in team_rows),
            "avg_dribble_success_pct": mean(safe_float(row, "dribble_success_pct") for row in team_rows),
            "avg_duel_success_pct": mean(safe_float(row, "duel_success_pct") for row in team_rows),
        }
    if not raw:
        return {}
    metrics = list(next(iter(raw.values())).keys())
    stats = {}
    for metric in metrics:
        values = [profile[metric] for profile in raw.values()]
        sd = pstdev(values)
        stats[metric] = (mean(values), sd if sd else 1.0)
    out: dict[str, dict[str, Any]] = {}
    for team, profile in raw.items():
        zsum = 0.0
        for metric in metrics:
            avg, sd = stats[metric]
            zsum += (profile[metric] - avg) / sd
        adjustment = clamp((zsum / len(metrics)) * 10.0, -22.0, 22.0)
        out[team] = {
            "tactical_score": score_from_adjustment(adjustment, 1.35),
            "open_data_adjustment": adjustment,
            "status": "statsbomb_2018_2022_available",
        }
    return out


def ceiling_score_from_tier(tier: str) -> float:
    if "Tier 1" in tier:
        return 86.0
    if "Tier 2" in tier:
        return 66.0
    if "Tier 3" in tier:
        return 46.0
    return 25.0


def default_manager_scores(team: str, elo_score: float, tier: str) -> tuple[str, float, float, str]:
    if team in MANAGER_OVERRIDES:
        return MANAGER_OVERRIDES[team]
    base = 46.0 + elo_score * 0.32
    if "Tier 1" in tier:
        base += 8.0
    elif "Tier 4" in tier:
        base -= 6.0
    return "manual_required", clamp(base, 45.0, 78.0), clamp(base - 2.0, 42.0, 76.0), "profile proxy / manual review required"


def default_squad_scores(team: str, elo_score: float, tier: str) -> tuple[float, float, float]:
    if team in SQUAD_OVERRIDES:
        return SQUAD_OVERRIDES[team]
    base = 38.0 + elo_score * 0.47
    if "Tier 1" in tier:
        base += 6.0
    elif "Tier 2" in tier:
        base += 2.0
    elif "Tier 4" in tier:
        base -= 5.0
    squad = clamp(base, 35.0, 86.0)
    xi = clamp(squad + 1.0, 35.0, 88.0)
    bench = clamp(squad - 4.0, 30.0, 82.0)
    return squad, xi, bench


def create_or_refresh_team_profiles() -> list[dict[str, Any]]:
    v1_rows = {normalize_team(row["normalized_team"]): row for row in read_csv(PROCESSED / "model_v1_team_ratings.csv")}
    teams = [normalize_team(row["team"]) for row in read_csv(PROCESSED / "worldcup_2026_teams.csv")]
    elo_scores = percentile_scores({team: safe_float(v1_rows[team], "elo") for team in teams})
    rows = []
    for team in teams:
        v1 = v1_rows[team]
        tier = v1["contender_tier"]
        squad, xi, bench = default_squad_scores(team, elo_scores[team], tier)
        manager_name, manager_pedigree, tactical_flex, style = default_manager_scores(team, elo_scores[team], tier)
        rows.append(
            {
                "team": display_team(team),
                "normalized_team": team,
                "manager_name": manager_name,
                "preferred_style": style,
                "squad_quality_score": round(squad, 2),
                "expected_xi_score": round(xi, 2),
                "bench_depth_score": round(bench, 2),
                "manager_pedigree_score": round(manager_pedigree, 2),
                "tactical_flexibility_score": round(tactical_flex, 2),
                "profile_source_status": "public/manual seed; replace with licensed squad + analyst feed",
                "notes": "V2 seed value; editable before rerun",
            }
        )
    path = INPUTS / "model_v2_team_profiles.csv"
    write_csv(
        path,
        rows,
        [
            "team",
            "normalized_team",
            "manager_name",
            "preferred_style",
            "squad_quality_score",
            "expected_xi_score",
            "bench_depth_score",
            "manager_pedigree_score",
            "tactical_flexibility_score",
            "profile_source_status",
            "notes",
        ],
    )
    return rows


def read_availability_scores() -> dict[str, float]:
    path = INPUTS / "player_availability_overrides.csv"
    scores = defaultdict(lambda: 100.0)
    if not path.exists():
        return {}
    rows = read_csv(path)
    penalties = defaultdict(float)
    for row in rows:
        team = normalize_team(row.get("team", ""))
        if not team:
            continue
        status = (row.get("availability_status") or "").lower()
        if status not in {"out", "injured", "suspended", "doubtful", "limited"}:
            continue
        gap = safe_float(row, "replacement_gap")
        minutes = clamp(safe_float(row, "expected_minutes", 90.0) / 90.0, 0.0, 1.0)
        penalties[team] += gap * minutes
    for team, penalty in penalties.items():
        scores[team] = clamp(100.0 - penalty, 20.0, 100.0)
    return dict(scores)


def build_team_power() -> dict[str, dict[str, Any]]:
    profile_rows = create_or_refresh_team_profiles()
    profiles = {normalize_team(row["normalized_team"]): row for row in profile_rows}
    v1_rows = {normalize_team(row["normalized_team"]): row for row in read_csv(PROCESSED / "model_v1_team_ratings.csv")}
    teams = [normalize_team(row["team"]) for row in read_csv(PROCESSED / "worldcup_2026_teams.csv")]
    elo_scores = percentile_scores({team: safe_float(v1_rows[team], "elo") for team in teams})
    recent_scores = percentile_scores({team: safe_float(v1_rows[team], "recent_form_adjustment") for team in teams})
    tactical = build_tactical_adjustments()
    availability = read_availability_scores()
    weights = MODEL_CONFIG["weights"]
    out = {}
    for team in teams:
        v1 = v1_rows[team]
        profile = profiles[team]
        squad_score = (
            safe_float(profile, "squad_quality_score") * 0.45
            + safe_float(profile, "expected_xi_score") * 0.35
            + safe_float(profile, "bench_depth_score") * 0.20
        )
        manager_score = safe_float(profile, "manager_pedigree_score") * 0.65 + safe_float(profile, "tactical_flexibility_score") * 0.35
        tactical_score = tactical.get(team, {}).get("tactical_score", 50.0)
        ceiling_score = ceiling_score_from_tier(v1["contender_tier"])
        availability_score = availability.get(team, 100.0)
        power = (
            elo_scores[team] * weights["elo_score"]
            + squad_score * weights["squad_score"]
            + manager_score * weights["manager_score"]
            + recent_scores[team] * weights["recent_form_score"]
            + float(tactical_score) * weights["tactical_score"]
            + ceiling_score * weights["ceiling_score"]
            + availability_score * weights["availability_score"]
        )
        out[team] = {
            "team": team,
            "display_team": display_team(team),
            "group": v1["group"],
            "v1_total_rating": safe_float(v1, "total_rating"),
            "v1_title_tier": v1["contender_tier"],
            "elo_score": round(elo_scores[team], 3),
            "squad_score": round(squad_score, 3),
            "manager_score": round(manager_score, 3),
            "recent_form_score": round(recent_scores[team], 3),
            "tactical_score": round(float(tactical_score), 3),
            "ceiling_score": round(ceiling_score, 3),
            "availability_score": round(availability_score, 3),
            "v2_power_score": round(power, 3),
            "manager_name": profile["manager_name"],
            "preferred_style": profile["preferred_style"],
            "profile_source_status": profile["profile_source_status"],
            "open_tactical_data_status": tactical.get(team, {}).get("status", "no_open_tactical_data"),
        }
    return out


def host_power(team: str, ground: str, round_name: str) -> float:
    host = HOST_COUNTRY_BY_GROUND.get(ground, "")
    if host != team:
        return 0.0
    return MODEL_CONFIG["host_advantage_group_power"] if round_name.startswith("Matchday") else MODEL_CONFIG["host_advantage_knockout_power"]


def match_projection(team_a: str, team_b: str, powers: dict[str, dict[str, Any]], ground: str = "", round_name: str = "") -> dict[str, Any]:
    power_a = powers[team_a]["v2_power_score"] + host_power(team_a, ground, round_name)
    power_b = powers[team_b]["v2_power_score"] + host_power(team_b, ground, round_name)
    lambda_a, lambda_b = expected_goals(power_a, power_b)
    p_a, p_draw, p_b = scoreline_probabilities(lambda_a, lambda_b)
    return {
        "team1": team_a,
        "team2": team_b,
        "team1_power": power_a,
        "team2_power": power_b,
        "power_diff_team1": power_a - power_b,
        "team1_win_probability": p_a,
        "draw_probability": p_draw,
        "team2_win_probability": p_b,
        "team1_xg_internal": lambda_a,
        "team2_xg_internal": lambda_b,
    }


def public_verdict(projection: dict[str, Any]) -> tuple[str, str, str]:
    t1 = display_team(projection["team1"])
    t2 = display_team(projection["team2"])
    p1 = projection["team1_win_probability"]
    pd = projection["draw_probability"]
    p2 = projection["team2_win_probability"]
    fav_team = t1 if p1 >= p2 else t2
    dog_team = t2 if p1 >= p2 else t1
    fav_p = max(p1, p2)
    dog_p = min(p1, p2)
    gap = fav_p - dog_p
    if gap <= 0.14 or fav_p < 0.47:
        return "No strong edge", "Pass", "Model sees too little separation for a public winner call"
    if dog_p >= 0.29 and gap <= 0.19:
        return f"Upset watch: {dog_team} live", "Low-medium", "Underdog profile is strong enough to avoid a blind favorite pick"
    if fav_p >= 0.61 and gap >= 0.31:
        return f"{fav_team} win", "High", "Strong favorite across weighted v2 layers"
    if fav_p >= 0.53 and gap >= 0.22:
        return f"{fav_team} win lean", "Medium", "Clear edge, but still not framed as certainty"
    if fav_p + pd >= 0.75 and fav_p >= 0.42:
        return f"{fav_team} avoid defeat", "Medium-low", "Best call is protection against the draw/upset"
    return "No strong edge", "Pass", "Close enough that forcing a pick would be noise"


def simulate_match(projection: dict[str, Any]) -> tuple[int, int]:
    return sample_poisson(projection["team1_xg_internal"]), sample_poisson(projection["team2_xg_internal"])


def rank_group(teams: list[str], table: dict[str, dict[str, int]]) -> list[str]:
    return sorted(
        teams,
        key=lambda team: (
            table[team]["points"],
            table[team]["goal_diff"],
            table[team]["goals_for"],
            random.random(),
        ),
        reverse=True,
    )


def third_sort(entry: dict[str, Any]) -> tuple[int, int, int, float]:
    stats = entry["stats"]
    return stats["points"], stats["goal_diff"], stats["goals_for"], random.random()


def resolve_slot(slot: str, group_rankings: dict[str, list[str]], third_pool: dict[str, dict[str, Any]], results: dict[str, str]) -> str:
    if slot.startswith("W") or slot.startswith("L"):
        return results[slot]
    if len(slot) >= 2 and slot[0] in {"1", "2"} and slot[1] in GROUP_ORDER:
        return group_rankings[slot[1]][int(slot[0]) - 1]
    if slot.startswith("3"):
        groups = slot[1:].split("/")
        available = [third_pool[group] for group in groups if group in third_pool]
        if not available:
            available = list(third_pool.values())
        choice = sorted(available, key=third_sort, reverse=True)[0]
        del third_pool[choice["group"]]
        return choice["team"]
    raise RuntimeError(f"Unresolved slot: {slot}")


def knockout_winner(team_a: str, team_b: str, powers: dict[str, dict[str, Any]], ground: str, round_name: str) -> str:
    projection = match_projection(team_a, team_b, powers, ground, round_name)
    goals_a, goals_b = simulate_match(projection)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    diff = projection["power_diff_team1"] + random.gauss(0.0, MODEL_CONFIG["knockout_draw_penalty_noise"])
    p_a = sigmoid(diff / 10.0)
    return team_a if random.random() < p_a else team_b


def run_sim(powers: dict[str, dict[str, Any]], group_fixtures: list[dict[str, str]], knockout_fixtures: list[dict[str, str]]) -> dict[str, set[str]]:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for team, row in powers.items():
        groups[row["group"]].append(team)
    table = {
        team: {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
        for team in powers
    }
    for fixture in group_fixtures:
        team_a = normalize_team(fixture["team1"])
        team_b = normalize_team(fixture["team2"])
        projection = match_projection(team_a, team_b, powers, fixture["ground"], fixture["round"])
        goals_a, goals_b = simulate_match(projection)
        table[team_a]["goals_for"] += goals_a
        table[team_a]["goals_against"] += goals_b
        table[team_b]["goals_for"] += goals_b
        table[team_b]["goals_against"] += goals_a
        if goals_a > goals_b:
            table[team_a]["points"] += 3
        elif goals_b > goals_a:
            table[team_b]["points"] += 3
        else:
            table[team_a]["points"] += 1
            table[team_b]["points"] += 1
    for stats in table.values():
        stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]
    group_rankings = {group: rank_group(sorted(teams), table) for group, teams in groups.items()}
    reached = {
        "qualified": set(),
        "group_first": set(),
        "group_second": set(),
        "group_third_qualified": set(),
        "round_of_16": set(),
        "quarter_final": set(),
        "semi_final": set(),
        "final": set(),
        "champion": set(),
    }
    thirds = []
    for group in GROUP_ORDER:
        ranking = group_rankings[group]
        reached["group_first"].add(ranking[0])
        reached["group_second"].add(ranking[1])
        reached["qualified"].update(ranking[:2])
        thirds.append({"group": group, "team": ranking[2], "stats": table[ranking[2]]})
    thirds = sorted(thirds, key=third_sort, reverse=True)
    third_pool = {entry["group"]: entry for entry in thirds[:8]}
    reached["group_third_qualified"].update(entry["team"] for entry in thirds[:8])
    reached["qualified"].update(reached["group_third_qualified"])
    results: dict[str, str] = {}
    for fixture in knockout_fixtures:
        match_no = fixture["fixture_id"]
        round_name = fixture["round"]
        team_a = resolve_slot(fixture["team1"], group_rankings, third_pool, results)
        team_b = resolve_slot(fixture["team2"], group_rankings, third_pool, results)
        winner = knockout_winner(team_a, team_b, powers, fixture["ground"], round_name)
        loser = team_b if winner == team_a else team_a
        results[f"W{match_no}"] = winner
        results[f"L{match_no}"] = loser
        if round_name == "Round of 32":
            reached["round_of_16"].add(winner)
        elif round_name == "Round of 16":
            reached["quarter_final"].add(winner)
        elif round_name == "Quarter-final":
            reached["semi_final"].add(winner)
        elif round_name == "Semi-final":
            reached["final"].add(winner)
        elif round_name == "Final":
            reached["champion"].add(winner)
    return reached


def run_tournament(powers: dict[str, dict[str, Any]], fixtures: list[dict[str, str]]) -> list[dict[str, Any]]:
    random.seed(MODEL_CONFIG["seed"])
    group_fixtures = [fixture for fixture in fixtures if fixture["round"].startswith("Matchday")]
    knockout_fixtures = sorted(
        [fixture for fixture in fixtures if fixture["round"] in ROUND_ORDER],
        key=lambda fixture: (ROUND_ORDER[fixture["round"]], int(fixture["fixture_id"])),
    )
    counters = {
        key: Counter()
        for key in [
            "qualified",
            "group_first",
            "group_second",
            "group_third_qualified",
            "round_of_16",
            "quarter_final",
            "semi_final",
            "final",
            "champion",
        ]
    }
    sims = MODEL_CONFIG["simulations"]
    for _ in range(sims):
        reached = run_sim(powers, group_fixtures, knockout_fixtures)
        for key, teams in reached.items():
            counters[key].update(teams)
    rows = []
    for team, row in powers.items():
        rows.append(
            {
                "team": row["display_team"],
                "group": row["group"],
                "v2_power_score": row["v2_power_score"],
                "group_first_pct": round(100 * counters["group_first"][team] / sims, 2),
                "group_second_pct": round(100 * counters["group_second"][team] / sims, 2),
                "third_place_qualified_pct": round(100 * counters["group_third_qualified"][team] / sims, 2),
                "qualify_knockout_pct": round(100 * counters["qualified"][team] / sims, 2),
                "round_of_16_pct": round(100 * counters["round_of_16"][team] / sims, 2),
                "quarter_final_pct": round(100 * counters["quarter_final"][team] / sims, 2),
                "semi_final_pct": round(100 * counters["semi_final"][team] / sims, 2),
                "final_pct": round(100 * counters["final"][team] / sims, 2),
                "champion_pct": round(100 * counters["champion"][team] / sims, 2),
            }
        )
    rows.sort(key=lambda r: (r["champion_pct"], r["final_pct"], r["semi_final_pct"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["title_rank"] = idx
    return rows


def build_group_predictions(powers: dict[str, dict[str, Any]], fixtures: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for fixture in fixtures:
        if not fixture["round"].startswith("Matchday"):
            continue
        team_a = normalize_team(fixture["team1"])
        team_b = normalize_team(fixture["team2"])
        projection = match_projection(team_a, team_b, powers, fixture["ground"], fixture["round"])
        verdict, confidence, reason = public_verdict(projection)
        rows.append(
            {
                "fixture_id": fixture["fixture_id"],
                "date": fixture["date"],
                "time": fixture["time"],
                "group": fixture["group"].replace("Group ", ""),
                "ground": fixture["ground"],
                "team1": display_team(team_a),
                "team2": display_team(team_b),
                "public_verdict": verdict,
                "confidence": confidence,
                "model_reason": reason,
                "team1_win_probability_internal": round(projection["team1_win_probability"], 4),
                "draw_probability_internal": round(projection["draw_probability"], 4),
                "team2_win_probability_internal": round(projection["team2_win_probability"], 4),
                "team1_internal_xg": round(projection["team1_xg_internal"], 3),
                "team2_internal_xg": round(projection["team2_xg_internal"], 3),
                "team1_power": round(projection["team1_power"], 3),
                "team2_power": round(projection["team2_power"], 3),
                "power_diff_team1": round(projection["power_diff_team1"], 3),
            }
        )
    return rows


def compare_v1_v2(v2_odds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    v1 = {row["team"]: row for row in read_csv(PROCESSED / "model_v1_tournament_odds.csv")}
    rows = []
    for row in v2_odds:
        team = row["team"]
        old = v1.get(team)
        rows.append(
            {
                "team": team,
                "v1_title_rank": old["title_rank"] if old else "",
                "v2_title_rank": row["title_rank"],
                "v1_champion_pct": old["champion_pct"] if old else "",
                "v2_champion_pct": row["champion_pct"],
                "champion_pct_change": round(float(row["champion_pct"]) - float(old["champion_pct"]), 2) if old else "",
                "v1_final_pct": old["final_pct"] if old else "",
                "v2_final_pct": row["final_pct"],
                "final_pct_change": round(float(row["final_pct"]) - float(old["final_pct"]), 2) if old else "",
            }
        )
    rows.sort(key=lambda r: abs(float(r["champion_pct_change"] or 0)), reverse=True)
    return rows


def write_summary(v2_odds: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> None:
    pass_count = sum(1 for row in read_csv(PROCESSED / "model_v2_group_match_predictions.csv") if row["confidence"] == "Pass")
    lines = [
        "# World Cup Model v2",
        "",
        "V2 reduces Elo dominance by converting every feature layer into a 0-100 score before combining them.",
        "",
        "## Weighting",
        "",
        "| Layer | Weight |",
        "|---|---:|",
    ]
    for key, value in MODEL_CONFIG["weights"].items():
        lines.append(f"| {key} | {value:.0%} |")
    lines.extend(
        [
            "",
            "## Top Title Odds",
            "",
            "| Rank | Team | Champion % | Final % | Semi % |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for row in v2_odds[:12]:
        lines.append(f"| {row['title_rank']} | {row['team']} | {row['champion_pct']}% | {row['final_pct']}% | {row['semi_final_pct']}% |")
    lines.extend(
        [
            "",
            "## Biggest Changes vs v1",
            "",
            "| Team | V1 % | V2 % | Change |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in comparison[:10]:
        lines.append(f"| {row['team']} | {row['v1_champion_pct']}% | {row['v2_champion_pct']}% | {row['champion_pct_change']} |")
    lines.extend(
        [
            "",
            f"Group-stage no-edge/pass calls in v2: {pass_count}.",
            "",
            "## Honest Caveat",
            "",
            "The squad and manager layers are now structurally in the model, but several values are seed/proxy values. For a sellable product, replace them with licensed squad/player ratings and analyst-reviewed manager/formation profiles.",
        ]
    )
    (OUTPUTS / "world_cup_model_v2_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    fixtures = read_csv(PROCESSED / "worldcup_2026_matches.csv")
    powers = build_team_power()
    team_rows = sorted(powers.values(), key=lambda row: row["v2_power_score"], reverse=True)
    for idx, row in enumerate(team_rows, start=1):
        row["v2_power_rank"] = idx
    group_predictions = build_group_predictions(powers, fixtures)
    write_csv(
        PROCESSED / "model_v2_group_match_predictions.csv",
        group_predictions,
        [
            "fixture_id",
            "date",
            "time",
            "group",
            "ground",
            "team1",
            "team2",
            "public_verdict",
            "confidence",
            "model_reason",
            "team1_win_probability_internal",
            "draw_probability_internal",
            "team2_win_probability_internal",
            "team1_internal_xg",
            "team2_internal_xg",
            "team1_power",
            "team2_power",
            "power_diff_team1",
        ],
    )
    v2_odds = run_tournament(powers, fixtures)
    comparison = compare_v1_v2(v2_odds)
    write_csv(
        PROCESSED / "model_v2_team_power.csv",
        team_rows,
        [
            "v2_power_rank",
            "team",
            "display_team",
            "group",
            "v1_total_rating",
            "v1_title_tier",
            "elo_score",
            "squad_score",
            "manager_score",
            "recent_form_score",
            "tactical_score",
            "ceiling_score",
            "availability_score",
            "v2_power_score",
            "manager_name",
            "preferred_style",
            "profile_source_status",
            "open_tactical_data_status",
        ],
    )
    write_csv(
        PROCESSED / "model_v2_tournament_odds.csv",
        v2_odds,
        [
            "title_rank",
            "team",
            "group",
            "v2_power_score",
            "group_first_pct",
            "group_second_pct",
            "third_place_qualified_pct",
            "qualify_knockout_pct",
            "round_of_16_pct",
            "quarter_final_pct",
            "semi_final_pct",
            "final_pct",
            "champion_pct",
        ],
    )
    write_csv(
        PROCESSED / "model_v2_vs_v1_comparison.csv",
        comparison,
        [
            "team",
            "v1_title_rank",
            "v2_title_rank",
            "v1_champion_pct",
            "v2_champion_pct",
            "champion_pct_change",
            "v1_final_pct",
            "v2_final_pct",
            "final_pct_change",
        ],
    )
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "world_cup_model_v2_config.json").write_text(json.dumps(MODEL_CONFIG, indent=2), encoding="utf-8")
    write_summary(v2_odds, comparison)
    print(json.dumps({"teams": len(team_rows), "group_matches": len(group_predictions), "top": v2_odds[:5]}, indent=2))


if __name__ == "__main__":
    main()
