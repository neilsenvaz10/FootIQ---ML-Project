#!/usr/bin/env python3
"""Build Player Impact Rating v2.1 for the 2026 World Cup model.

This is intentionally a model-derived rating, not a copied third-party player
rating. It starts from public squad metadata, then combines club-level priors,
national-team centrality, age/experience, position role, and replacement gap.
"""

from __future__ import annotations

import csv
import math
import re
import urllib.request
from collections import defaultdict
from io import StringIO
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "squads"
PROCESSED = ROOT / "data" / "processed"
INPUTS = ROOT / "data" / "inputs"
OUTPUTS = ROOT / "outputs"

SQUAD_SOURCE_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"

TEAM_ALIASES = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}

DISPLAY_NAMES = {
    "United States": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
}

POSITION_UNIT = {
    "GK": "GK",
    "DF": "Defence",
    "MF": "Midfield",
    "FW": "Attack",
}

POSITION_SORT = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}

# Club score is a prior, not the player rating. It captures training level,
# competitive environment, and big-match exposure. Fallback logic handles the
# long tail without pretending every club has been hand-rated.
CLUB_SCORE_OVERRIDES = {
    # Current super-elite / annual title-contender environments
    "Real Madrid": 98,
    "Manchester City": 98,
    "Paris Saint-Germain": 96,
    "Bayern Munich": 96,
    "Liverpool": 96,
    "Arsenal": 95,
    "Barcelona": 95,
    "Inter Milan": 94,
    "Atlético Madrid": 93,
    # Elite Champions League / top-six environments
    "Chelsea": 91,
    "Tottenham Hotspur": 90,
    "Manchester United": 90,
    "Newcastle United": 89,
    "Aston Villa": 88,
    "Bayer Leverkusen": 90,
    "Borussia Dortmund": 89,
    "RB Leipzig": 87,
    "Juventus": 89,
    "Milan": 89,
    "Napoli": 88,
    "Atalanta": 87,
    "Roma": 86,
    "Benfica": 87,
    "Porto": 86,
    "Sporting CP": 86,
    "PSV Eindhoven": 84,
    "Feyenoord": 82,
    "Ajax": 82,
    "Celtic": 79,
    "Rangers": 77,
    # Strong European league clubs and regular continental sides
    "Brighton & Hove Albion": 86,
    "Crystal Palace": 84,
    "West Ham United": 84,
    "Brentford": 82,
    "Fulham": 82,
    "Bournemouth": 82,
    "Nottingham Forest": 82,
    "Everton": 81,
    "Leeds United": 80,
    "Burnley": 78,
    "Sunderland": 78,
    "Wolverhampton Wanderers": 81,
    "Villarreal": 84,
    "Real Sociedad": 83,
    "Real Betis": 82,
    "Athletic Bilbao": 82,
    "Sevilla": 81,
    "Girona": 80,
    "Celta Vigo": 78,
    "Osasuna": 78,
    "Mallorca": 77,
    "Rayo Vallecano": 77,
    "Nice": 83,
    "Marseille": 83,
    "Lyon": 82,
    "Monaco": 84,
    "Lille": 82,
    "Rennes": 80,
    "Lens": 80,
    "Strasbourg": 79,
    "Auxerre": 76,
    "Saint-Étienne": 75,
    "Eintracht Frankfurt": 83,
    "VfB Stuttgart": 82,
    "TSG Hoffenheim": 80,
    "VfL Wolfsburg": 80,
    "Mainz 05": 79,
    "SC Freiburg": 79,
    "Werder Bremen": 77,
    "FC Augsburg": 77,
    "Borussia Mönchengladbach": 78,
    "FC St. Pauli": 76,
    "Hamburger SV": 76,
    "Bologna": 81,
    "Sassuolo": 77,
    "Torino": 78,
    "Parma": 76,
    "Genoa": 77,
    "Como": 76,
    "Venezia": 74,
    "Cremonese": 74,
    "Club Brugge": 79,
    "Genk": 76,
    "Anderlecht": 77,
    "Union Saint-Gilloise": 78,
    "Standard Liège": 75,
    "Copenhagen": 77,
    "Brøndby": 75,
    "Nordsjælland": 74,
    "Red Bull Salzburg": 79,
    "LASK": 74,
    "Austria Wien": 73,
    "Dinamo Zagreb": 78,
    "Red Star Belgrade": 77,
    "Young Boys": 77,
    "Lugano": 73,
    "Olympiacos": 78,
    "Panathinaikos": 77,
    "AEK Athens": 76,
    "PAOK": 77,
    "Galatasaray": 82,
    "Fenerbahçe": 81,
    "Beşiktaş": 79,
    "Trabzonspor": 76,
    "İstanbul Başakşehir": 75,
    "Kasımpaşa": 73,
    # Americas
    "Flamengo": 82,
    "Palmeiras": 82,
    "River Plate": 80,
    "Boca Juniors": 79,
    "Grêmio": 77,
    "Internacional": 77,
    "Atlético Mineiro": 77,
    "Santos": 75,
    "São Paulo": 76,
    "Independiente": 75,
    "Huracán": 73,
    "Cerro Porteño": 73,
    "LDU Quito": 75,
    "Universidad Católica": 73,
    "Guadalajara": 75,
    "América": 77,
    "Cruz Azul": 75,
    "Toluca": 75,
    "UNAM": 73,
    "Tijuana": 71,
    "Los Angeles FC": 76,
    "Inter Miami CF": 75,
    "New York City FC": 74,
    "Toronto FC": 72,
    "Vancouver Whitecaps FC": 73,
    "Philadelphia Union": 73,
    "Columbus Crew": 73,
    "Chicago Fire FC": 70,
    "Atlanta United FC": 72,
    "Minnesota United FC": 71,
    "FC Dallas": 71,
    "Orlando City SC": 72,
    "San Diego FC": 70,
    "Saprissa": 70,
    "Plaza Amador": 66,
    # Asia, Africa, Oceania and other strong domestic powers
    "Al-Hilal": 82,
    "Al-Nassr": 81,
    "Al-Ahli": 80,
    "Al-Ittihad": 80,
    "Al-Qadsiah": 76,
    "Al-Ettifaq": 75,
    "Al-Sadd": 76,
    "Al-Duhail": 75,
    "Al-Rayyan": 72,
    "Al-Wakrah": 71,
    "Al-Arabi": 72,
    "Al-Gharafa": 72,
    "Al Ain": 73,
    "Esteghlal": 73,
    "Persepolis": 73,
    "Sepahan": 72,
    "Tractor": 71,
    "Foolad": 68,
    "Ulsan HD": 74,
    "Jeonbuk Hyundai Motors": 73,
    "FC Tokyo": 72,
    "Kashima Antlers": 72,
    "Midtjylland": 76,
    "Bodø/Glimt": 76,
    "Malmö FF": 74,
    "Viking": 71,
    "Mamelodi Sundowns": 76,
    "Orlando Pirates": 72,
    "Kaizer Chiefs": 70,
    "Al Ahly": 78,
    "Zamalek": 74,
    "Pyramids": 73,
    "Espérance de Tunis": 72,
    "Club Africain": 70,
    "Auckland FC": 66,
    "Wellington Phoenix": 66,
}

LEAGUE_HINT_SCORES = {
    "City": 70,
    "United": 69,
    "FC": 66,
    "SC": 65,
    "Athletic": 67,
    "Sporting": 67,
}

TEAM_SCORE_FALLBACK_BY_TIER = {
    "Tier 1 contender": 78,
    "Tier 2 dark horse": 73,
    "Tier 3 outsider": 66,
    "Tier 4 participant": 58,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


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


def fetch_squad_html() -> str:
    RAW.mkdir(parents=True, exist_ok=True)
    raw_path = RAW / "wikipedia_2026_world_cup_squads.html"
    if raw_path.exists():
        return raw_path.read_text(encoding="utf-8")
    request = urllib.request.Request(
        SQUAD_SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0 Codex local research"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    raw_path.write_text(html, encoding="utf-8")
    return html


def parse_age(raw: str) -> int:
    match = re.search(r"aged\s+(\d+)", str(raw))
    return int(match.group(1)) if match else 27


def clean_player(raw: str) -> tuple[str, bool]:
    text = str(raw).strip()
    captain = "(captain)" in text.lower()
    text = re.sub(r"\s*\(captain\)", "", text, flags=re.IGNORECASE).strip()
    return text, captain


def club_level_score(club: str, team_squad_score: float, tier: str) -> tuple[float, str]:
    if club in CLUB_SCORE_OVERRIDES:
        return float(CLUB_SCORE_OVERRIDES[club]), "club_manual_tier"
    lowered = club.lower()
    fallback = TEAM_SCORE_FALLBACK_BY_TIER.get(tier, 62)
    if any(token in lowered for token in ["real ", "inter ", "dynamo", "dinamo", "spartak", "lokomotiv"]):
        fallback += 2
    for token, score in LEAGUE_HINT_SCORES.items():
        if token.lower() in lowered:
            fallback = max(fallback, score)
    blended = clamp(0.55 * fallback + 0.45 * team_squad_score, 45.0, 82.0)
    return round(blended, 2), "club_fallback_from_team_tier"


def age_prime_score(age: int, position: str) -> float:
    if position == "GK":
        peak = 31
        spread = 8
    else:
        peak = 27
        spread = 7
    return round(clamp(100 - abs(age - peak) * (35 / spread), 45, 100), 2)


def cap_score(caps: float) -> float:
    return round(clamp(42 + 13 * math.log1p(max(caps, 0)), 42, 96), 2)


def goal_role_score(goals: float, caps: float, position: str) -> float:
    if caps <= 0:
        return 50.0
    rate = goals / caps
    multiplier = {"GK": 0, "DF": 155, "MF": 135, "FW": 145}.get(position, 125)
    return round(clamp(50 + rate * multiplier, 45, 98), 2)


def position_age_adjustment(position: str, age: int) -> float:
    if position == "GK":
        return 2.0 if 28 <= age <= 35 else -2.0 if age < 23 else 0.0
    if position == "DF":
        return 1.5 if 24 <= age <= 31 else -2.0 if age > 34 else 0.0
    if position == "MF":
        return 1.5 if 23 <= age <= 30 else -2.5 if age > 34 else 0.0
    if position == "FW":
        return 1.5 if 22 <= age <= 30 else -3.0 if age > 34 else 0.0
    return 0.0


def data_confidence(club_status: str, caps: float, is_captain: bool) -> float:
    base = 0.62 if club_status == "club_manual_tier" else 0.50
    if caps >= 50:
        base += 0.12
    elif caps >= 20:
        base += 0.08
    elif caps >= 5:
        base += 0.04
    if is_captain:
        base += 0.03
    return round(clamp(base, 0.45, 0.86), 2)


def load_team_context() -> tuple[list[dict[str, str]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    team_rows = read_csv(PROCESSED / "worldcup_2026_teams.csv")
    profiles = {
        normalize_team(row["normalized_team"]): row
        for row in read_csv(INPUTS / "model_v2_team_profiles.csv")
    }
    v1_rows = {
        normalize_team(row["normalized_team"]): row
        for row in read_csv(PROCESSED / "model_v1_team_ratings.csv")
    }
    return team_rows, profiles, v1_rows


def expected_role_rows(players: list[dict[str, Any]]) -> None:
    by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for player in players:
        by_position[player["position"]].append(player)
    for position_rows in by_position.values():
        position_rows.sort(key=lambda row: row["pre_role_rating"], reverse=True)

    starters: list[dict[str, Any]] = []
    desired = {"GK": 1, "DF": 4, "MF": 3, "FW": 3}
    for pos, count in desired.items():
        starters.extend(by_position.get(pos, [])[:count])
    if len(starters) < 11:
        starter_ids = {id(row) for row in starters}
        remaining = [row for row in players if id(row) not in starter_ids]
        remaining.sort(key=lambda row: row["pre_role_rating"], reverse=True)
        starters.extend(remaining[: 11 - len(starters)])

    starter_ids = {id(row) for row in starters[:11]}
    remaining = [row for row in players if id(row) not in starter_ids]
    remaining.sort(key=lambda row: row["pre_role_rating"], reverse=True)
    rotation_ids = {id(row) for row in remaining[:9]}

    for player in players:
        if id(player) in starter_ids:
            player["expected_role"] = "Starter"
            player["expected_minutes_share"] = 0.78
        elif id(player) in rotation_ids:
            player["expected_role"] = "Rotation"
            player["expected_minutes_share"] = 0.32
        else:
            player["expected_role"] = "Depth"
            player["expected_minutes_share"] = 0.10
    for player in players:
        if player["is_captain"] and player["expected_role"] != "Depth":
            player["expected_minutes_share"] = min(0.88, player["expected_minutes_share"] + 0.08)


def replacement_gap_rows(players: list[dict[str, Any]]) -> None:
    unit_map = {"GK": "GK", "DF": "Defence", "MF": "Midfield", "FW": "Attack"}
    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for player in players:
        by_unit[unit_map[player["position"]]].append(player)
    for unit_rows in by_unit.values():
        unit_rows.sort(key=lambda row: row["impact_score"], reverse=True)

    for player in players:
        unit_rows = by_unit[unit_map[player["position"]]]
        alternatives = [row for row in unit_rows if row is not player]
        if not alternatives:
            replacement = player["impact_score"] - 8
        elif player["expected_role"] == "Starter":
            replacement = alternatives[0]["impact_score"]
        else:
            replacement = mean([row["impact_score"] for row in alternatives[: min(2, len(alternatives))]])
        raw_gap = max(0.0, player["impact_score"] - replacement)
        if player["position"] == "FW" and player["goals"] >= 25:
            raw_gap += min(4.5, player["goals"] / 20.0)
        if player["impact_score"] >= 88:
            raw_gap += 1.5
        role_multiplier = {"Starter": 1.0, "Rotation": 0.45, "Depth": 0.15}[player["expected_role"]]
        if player["is_captain"]:
            raw_gap += 1.25
        player["replacement_gap"] = round(clamp(raw_gap * role_multiplier, 0, 18), 2)


def build_player_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    team_rows, profiles, v1_rows = load_team_context()
    html = fetch_squad_html()
    tables = pd.read_html(StringIO(html))
    if len(tables) < len(team_rows):
        raise RuntimeError(f"Expected at least {len(team_rows)} squad tables, found {len(tables)}")

    all_players: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for team_index, (team_row, table) in enumerate(zip(team_rows, tables[: len(team_rows)]), start=1):
        team_display = team_row["team"]
        team = normalize_team(team_display)
        profile = profiles[team]
        v1 = v1_rows[team]
        team_squad = safe_float(profile, "squad_quality_score", 60.0)
        expected_xi = safe_float(profile, "expected_xi_score", team_squad)
        tier = v1.get("contender_tier", "Tier 4 participant")

        team_players: list[dict[str, Any]] = []
        cap_values = [float(x) for x in table["Caps"].fillna(0).tolist()]
        max_caps = max(cap_values) if cap_values else 1.0
        for _, raw in table.iterrows():
            player_name, is_captain = clean_player(raw["Player"])
            position = str(raw["Pos."])
            if position not in POSITION_UNIT:
                position = "MF"
            age = parse_age(raw["Date of birth (age)"])
            caps = float(raw["Caps"] or 0)
            goals = float(raw["Goals"] or 0)
            club = str(raw["Club"])
            club_score, club_status = club_level_score(club, team_squad, tier)
            age_score = age_prime_score(age, position)
            international_score = cap_score(caps)
            goal_score = goal_role_score(goals, caps, position)
            goal_weight = {"GK": 0.0, "DF": 0.10, "MF": 0.18, "FW": 0.28}.get(position, 0.18)
            scorer_bonus = 0.0
            if position == "FW" and goals >= 35 and goals / max(caps, 1) >= 0.55:
                scorer_bonus += 4.0
            if goals >= 70:
                scorer_bonus += 4.0
            national_role = clamp(
                44
                + 30 * (caps / max(max_caps, 1))
                + 0.16 * (international_score - 50)
                + goal_weight * (goal_score - 50)
                + (6 if is_captain else 0)
                + scorer_bonus,
                40,
                96,
            )
            recent_minutes = clamp(
                0.52 * club_score
                + 0.22 * expected_xi
                + 0.16 * age_score
                + 0.10 * international_score,
                42,
                95,
            )
            tactical_fit = clamp(
                0.40 * national_role
                + 0.25 * expected_xi
                + 0.20 * club_score
                + 0.15 * age_score
                + position_age_adjustment(position, age),
                42,
                96,
            )
            form_score = clamp(
                0.50 * recent_minutes
                + 0.25 * age_score
                + 0.15 * club_score
                + 0.10 * international_score,
                42,
                96,
            )
            tournament_experience = clamp(
                0.58 * international_score + 0.22 * club_score + 0.20 * age_score + (4 if is_captain else 0),
                42,
                97,
            )
            overall = clamp(
                0.36 * club_score
                + 0.22 * team_squad
                + 0.16 * international_score
                + 0.12 * age_score
                + 0.12 * goal_score
                + 0.02 * expected_xi,
                42,
                96,
            )
            pre_role_rating = clamp(0.46 * overall + 0.34 * national_role + 0.20 * club_score, 40, 97)

            team_players.append(
                {
                    "team": team_display,
                    "normalized_team": team,
                    "group": team_row["group"],
                    "squad_slot": int(raw["No."]),
                    "player_name": player_name,
                    "position": position,
                    "unit": POSITION_UNIT[position],
                    "age": age,
                    "caps": int(caps),
                    "goals": int(goals),
                    "club": club,
                    "is_captain": is_captain,
                    "overall_rating": round(overall, 2),
                    "club_level_score": round(club_score, 2),
                    "recent_minutes_score": round(recent_minutes, 2),
                    "national_role_score": round(national_role, 2),
                    "tactical_fit_score": round(tactical_fit, 2),
                    "form_score": round(form_score, 2),
                    "tournament_experience_score": round(tournament_experience, 2),
                    "pre_role_rating": round(pre_role_rating, 2),
                    "availability_status": "Available",
                    "data_confidence": data_confidence(club_status, caps, is_captain),
                    "rating_source": "Player Impact Rating v2.1 public-squad heuristic",
                    "club_score_source": club_status,
                    "notes": "Model-derived rating; upgrade with verified minutes/event feed when available.",
                }
            )
        expected_role_rows(team_players)
        for player in team_players:
            player["impact_score"] = round(
                clamp(
                    0.30 * player["overall_rating"]
                    + 0.20 * player["club_level_score"]
                    + 0.22 * player["national_role_score"]
                    + 0.15 * player["tactical_fit_score"]
                    + 0.10 * player["form_score"]
                    + 0.03 * player["tournament_experience_score"],
                    40,
                    97,
                ),
                2,
            )
        replacement_gap_rows(team_players)
        for player in team_players:
            player["availability_penalty"] = 0.0
        team_players.sort(
            key=lambda row: (
                POSITION_SORT[row["position"]],
                row["squad_slot"],
            )
        )
        all_players.extend(team_players)
        source_rows.append(
            {
                "team": team_display,
                "squad_table_index": team_index,
                "players_found": len(team_players),
                "source_url": SQUAD_SOURCE_URL,
                "source_note": "Wikipedia squad table citing FIFA/national association final squad sources; player impact scores are model-derived.",
            }
        )
    return all_players, source_rows


def team_profile_rows(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = {
        normalize_team(row["normalized_team"]): row
        for row in read_csv(INPUTS / "model_v2_team_profiles.csv")
    }
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for player in players:
        by_team[normalize_team(player["team"])].append(player)

    rows = []
    for team_row in read_csv(PROCESSED / "worldcup_2026_teams.csv"):
        display = team_row["team"]
        team = normalize_team(display)
        profile = profiles[team]
        roster = by_team[team]
        starters = [p for p in roster if p["expected_role"] == "Starter"]
        rotation = [p for p in roster if p["expected_role"] == "Rotation"]
        attack = [p for p in starters if p["unit"] == "Attack"]
        defence = [p for p in starters if p["unit"] == "Defence"]
        keepers = [p for p in roster if p["position"] == "GK"]
        coverage = len([p for p in roster if p["player_name"]]) / 26
        squad_quality = mean([p["impact_score"] for p in roster]) if roster else 50
        expected_xi = mean([p["impact_score"] for p in starters]) if starters else squad_quality
        bench_depth = mean([p["impact_score"] for p in rotation]) if rotation else squad_quality
        defensive_spine = mean([p["impact_score"] for p in defence]) if defence else expected_xi
        attack_ceiling = mean([p["impact_score"] for p in attack]) if attack else expected_xi
        gk_score = max([p["impact_score"] for p in keepers], default=expected_xi)
        availability = clamp(100 - sum(p["availability_penalty"] for p in roster), 20, 100)
        rows.append(
            {
                "team": display,
                "normalized_team": team,
                "manager_name": profile["manager_name"],
                "preferred_style": profile["preferred_style"],
                "squad_quality_score": round(squad_quality, 2),
                "expected_xi_score": round(expected_xi, 2),
                "bench_depth_score": round(bench_depth, 2),
                "defensive_spine_score": round(defensive_spine, 2),
                "attack_ceiling_score": round(attack_ceiling, 2),
                "gk_score": round(gk_score, 2),
                "availability_score": round(availability, 2),
                "complete_ratings_pct": round(coverage, 2),
                "players_entered": len(roster),
                "manager_pedigree_score": profile["manager_pedigree_score"],
                "tactical_flexibility_score": profile["tactical_flexibility_score"],
                "profile_source_status": "Player Impact Rating v2.1; public squads + model-derived ratings",
                "notes": "Player names populated from public squad tables; ratings are our own transparent heuristic.",
            }
        )
    return rows


def write_outputs() -> None:
    players, source_rows = build_player_rows()
    team_rows = team_profile_rows(players)

    player_fields = [
        "team",
        "normalized_team",
        "group",
        "squad_slot",
        "player_name",
        "position",
        "unit",
        "expected_role",
        "expected_minutes_share",
        "age",
        "caps",
        "goals",
        "club",
        "is_captain",
        "overall_rating",
        "club_level_score",
        "recent_minutes_score",
        "national_role_score",
        "tactical_fit_score",
        "form_score",
        "tournament_experience_score",
        "availability_status",
        "replacement_gap",
        "impact_score",
        "availability_penalty",
        "data_confidence",
        "rating_source",
        "club_score_source",
        "notes",
    ]
    team_fields = [
        "team",
        "normalized_team",
        "manager_name",
        "preferred_style",
        "squad_quality_score",
        "expected_xi_score",
        "bench_depth_score",
        "defensive_spine_score",
        "attack_ceiling_score",
        "gk_score",
        "availability_score",
        "complete_ratings_pct",
        "players_entered",
        "manager_pedigree_score",
        "tactical_flexibility_score",
        "profile_source_status",
        "notes",
    ]
    source_fields = ["team", "squad_table_index", "players_found", "source_url", "source_note"]
    write_csv(PROCESSED / "player_impact_v21.csv", players, player_fields)
    write_csv(PROCESSED / "model_v21_team_profiles_from_players.csv", team_rows, team_fields)
    write_csv(PROCESSED / "player_impact_v21_source_audit.csv", source_rows, source_fields)

    model_profile_fields = [
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
    ]
    write_csv(INPUTS / "model_v21_team_profiles.csv", team_rows, model_profile_fields)

    top_players = sorted(players, key=lambda row: row["impact_score"], reverse=True)[:25]
    lines = [
        "# Player Impact Rating v2.1",
        "",
        "Version 2.1 populates World Cup squad player names and generates a transparent, model-derived impact rating. It does not copy EA, FIFA, Transfermarkt, or a paid provider rating.",
        "",
        "## Formula",
        "",
        "`impact_score = 30% overall + 20% club level + 22% national role + 15% tactical fit + 10% form/sharpness + 3% tournament experience`",
        "",
        "Replacement gap is calculated within each team's positional unit and is kept separate from base ability so injuries can move the model dynamically.",
        "",
        "## Current Limitations",
        "",
        "- Club level is a heuristic prior, not a licensed provider feed.",
        "- Recent minutes are inferred from club level, role, age, and caps until a real minutes feed is attached.",
        "- National role is inferred from caps, captaincy, and goals; it should be upgraded with recent starting XI/minute data.",
        "- Ratings are suitable for model development and analyst review, not as a claimed official player-rating product.",
        "",
        "## Top 25 Player Impact Scores",
        "",
        "| Rank | Player | Team | Pos | Club | Impact | Role | Replacement gap |",
        "|---:|---|---|---|---|---:|---|---:|",
    ]
    for idx, player in enumerate(top_players, start=1):
        lines.append(
            f"| {idx} | {player['player_name']} | {player['team']} | {player['position']} | {player['club']} | "
            f"{player['impact_score']:.2f} | {player['expected_role']} | {player['replacement_gap']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Source",
            "",
            f"- Squad names/positions/clubs/caps/goals: {SQUAD_SOURCE_URL}",
            "- Rating methodology: local Player Impact Rating v2.1 heuristic built for this project.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "world_cup_player_impact_v21_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"players={len(players)} teams={len(team_rows)}")
    print(PROCESSED / "player_impact_v21.csv")
    print(PROCESSED / "model_v21_team_profiles_from_players.csv")
    print(INPUTS / "model_v21_team_profiles.csv")


if __name__ == "__main__":
    write_outputs()
