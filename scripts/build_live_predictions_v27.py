#!/usr/bin/env python3
"""Build v2.7 live predictions from the v2.6 calibrated ensemble.

V2.7 is the production bridge:
- train and save reusable v2.6-selected model artifacts
- adapt v2.5 live data tables into the v2.6 feature schema
- score live fixtures with calibrated ensemble probabilities
- publish a conservative consensus public pick
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import build_worldcup_model_v2 as v2
import model_bakeoff_v26 as v26


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
ARTIFACT_DIR = ROOT / "data" / "model_artifacts" / "v27"
ARTIFACT_PATH = ARTIFACT_DIR / "live_match_model.pkl"

FEATURES_PATH = PROCESSED / "v27_live_model_features.csv"
PROBABILITIES_PATH = PROCESSED / "v27_live_probabilities.csv"
PUBLIC_PICKS_PATH = PROCESSED / "v27_live_public_picks.csv"
COMPARISON_PATH = PROCESSED / "v27_v25_comparison.csv"
REPORT_PATH = OUTPUTS / "live_predictions_v27_report.md"
CONFIG_PATH = OUTPUTS / "live_predictions_v27_config.json"

V27_CONFIG = {
    "version": "v2.7",
    "purpose": "Integrate the v2.6 calibrated ensemble into the v2.5 live-data pipeline.",
    "base_model": "v2.6 ensemble probabilities + logistic consensus gate",
    "artifact_path": "data/model_artifacts/v27/live_match_model.pkl",
    "live_input_tables": [
        "data/processed/v25_fixtures_live.csv",
        "data/processed/v25_provider_status_live.csv",
        "data/processed/v25_weather_context_live.csv",
        "data/processed/v25_data_quality_live.csv",
        "data/processed/v25_match_predictions_live.csv",
    ],
    "outputs": [
        "data/processed/v27_live_model_features.csv",
        "data/processed/v27_live_probabilities.csv",
        "data/processed/v27_live_public_picks.csv",
        "data/processed/v27_v25_comparison.csv",
        "outputs/live_predictions_v27_report.md",
    ],
    "training_note": "After v2.6 selected the architecture on a time-safe split, v2.7 trains final model artifacts on all available historical international matches. This does not create a new test score.",
    "public_pick_note": "The public pick speaks only when the ensemble and logistic model agree on the same non-pass pick.",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_date(value: Any) -> datetime | None:
    try:
        if not value:
            return None
        return datetime.strptime(str(value), "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def round_prob(value: float) -> float:
    return round(float(value), 5)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def pass_rule_for(model_name: str) -> dict[str, float]:
    rows = read_csv(PROCESSED / "model_v26_pass_rules.csv")
    by_model = {row["model"]: row for row in rows}
    row = by_model.get(model_name, {})
    return {
        "min_confidence": safe_float(row.get("min_confidence"), 0.56),
        "min_gap": safe_float(row.get("min_gap"), 0.0),
        "draw_risk_min": safe_float(row.get("draw_risk_min"), 0.27),
        "draw_gap_max": safe_float(row.get("draw_gap_max"), 0.04),
    }


def train_final_artifact(force: bool = False) -> dict[str, Any]:
    if ARTIFACT_PATH.exists() and not force:
        with ARTIFACT_PATH.open("rb") as handle:
            return pickle.load(handle)

    df = v26.build_feature_frame()
    x_train, _ = v26.design_matrix(df)
    y_train = df["label_index"].to_numpy(dtype=int)

    logistic = v26.Pipeline(
        [
            ("scale", v26.StandardScaler()),
            (
                "model",
                v26.LogisticRegression(
                    max_iter=1200,
                    C=0.8,
                    class_weight="balanced",
                    random_state=20260607,
                ),
            ),
        ]
    )
    gradient_boosting = v26.GradientBoostingClassifier(
        n_estimators=220,
        learning_rate=0.035,
        max_depth=3,
        subsample=0.85,
        random_state=20260607,
    )
    logistic.fit(x_train, y_train)
    gradient_boosting.fit(x_train, y_train)

    v26_config = load_json(OUTPUTS / "model_v26_config.json")
    ensemble_weights = v26_config.get(
        "ensemble_weights",
        {"elo_formula": 0.3, "v25_poisson_lite": 0.0, "logistic_regression": 0.2, "gradient_boosting": 0.5},
    )
    temperatures = v26_config.get(
        "temperatures",
        {"elo_formula": 0.85, "logistic_regression": 0.9, "gradient_boosting": 1.0, "ensemble": 0.9},
    )
    artifact = {
        "version": "v2.7",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_rows": int(len(df)),
        "training_date_min": str(df["date"].min()),
        "training_date_max": str(df["date"].max()),
        "feature_columns": list(x_train.columns),
        "labels": v26.LABELS,
        "models": {
            "logistic_regression": logistic,
            "gradient_boosting": gradient_boosting,
        },
        "ensemble_weights": ensemble_weights,
        "temperatures": temperatures,
        "pass_rules": {
            "ensemble": pass_rule_for("ensemble"),
            "logistic_regression": pass_rule_for("logistic_regression"),
        },
        "v26_reference_config": v26_config,
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with ARTIFACT_PATH.open("wb") as handle:
        pickle.dump(artifact, handle)
    return artifact


def load_lookup(path: Path, key: str, normalize_key: bool = False) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    out = {}
    for row in rows:
        lookup_key = row.get(key, "")
        if normalize_key:
            lookup_key = v2.normalize_team(lookup_key)
        if lookup_key:
            out[lookup_key] = row
    return out


def avg_total(row: dict[str, str], total_key: str, count_key: str, default: float = 0.0) -> float:
    count = safe_float(row.get(count_key), 0.0)
    if count <= 0:
        return default
    return safe_float(row.get(total_key), default * count) / count


def days_since(fixture_date: datetime | None, last_match_date: Any) -> float:
    if fixture_date is None:
        return 999.0
    last = parse_date(last_match_date)
    if last is None:
        return 999.0
    return min(max((fixture_date - last).days, 0), 999)


def choose_orientation(
    fixture: dict[str, str],
    provider: dict[str, str],
) -> tuple[str, str, str, int, int]:
    team1 = v2.normalize_team(fixture["team1"])
    team2 = v2.normalize_team(fixture["team2"])
    teams = {team1, team2}
    venue_edge = v2.normalize_team(fixture.get("venue_edge_team", ""))
    provider_home = v2.normalize_team(provider.get("provider_home", ""))
    provider_away = v2.normalize_team(provider.get("provider_away", ""))

    if venue_edge in teams:
        home = venue_edge
        away = team2 if home == team1 else team1
        source = "venue_edge_team"
        return home, away, source, 0, 1

    if provider_home in teams and provider_away in teams:
        source = "provider_home_away_neutral"
        return provider_home, provider_away, source, 1, 0

    return team1, team2, "fixture_order_neutral", 1, 0


def tournament_flags(context: str) -> tuple[int, int, str]:
    lower = context.lower()
    is_world_cup = int("world cup" in lower and "friendly" not in lower)
    is_competitive = int(
        is_world_cup
        or any(word in lower for word in ["qualifier", "qualification", "nations league", "euro", "copa", "gold cup"])
    )
    bucket = v26.tournament_bucket(context, bool(is_world_cup), bool(is_competitive))
    return is_competitive, is_world_cup, bucket


def build_live_feature_rows() -> list[dict[str, Any]]:
    fixtures = read_csv(PROCESSED / "v25_fixtures_live.csv")
    providers = load_lookup(PROCESSED / "v25_provider_status_live.csv", "fixture_key")
    weather = load_lookup(PROCESSED / "v25_weather_context_live.csv", "fixture_key")
    quality = load_lookup(PROCESSED / "v25_data_quality_live.csv", "fixture_key")
    elo = load_lookup(PROCESSED / "team_elo_latest.csv", "team", normalize_key=True)
    form = load_lookup(PROCESSED / "team_recent_form_latest.csv", "team", normalize_key=True)

    rows: list[dict[str, Any]] = []
    for fixture in fixtures:
        fixture_key = fixture["fixture_key"]
        provider = providers.get(fixture_key, {})
        weather_row = weather.get(fixture_key, {})
        quality_row = quality.get(fixture_key, {})
        home, away, orientation_source, neutral, home_field = choose_orientation(fixture, provider)
        fixture_date = parse_date(fixture.get("date"))
        home_elo_row = elo.get(home, {})
        away_elo_row = elo.get(away, {})
        home_form = form.get(home, {})
        away_form = form.get(away, {})
        is_comp, is_wc, bucket = tournament_flags(fixture.get("competition_context", ""))

        home_elo = safe_float(home_elo_row.get("elo_rating"), 1500.0)
        away_elo = safe_float(away_elo_row.get("elo_rating"), 1500.0)
        home_ppg5 = safe_float(home_form.get("ppg_last_5"), 1.0)
        away_ppg5 = safe_float(away_form.get("ppg_last_5"), 1.0)
        home_ppg10 = safe_float(home_form.get("ppg_last_10"), 1.0)
        away_ppg10 = safe_float(away_form.get("ppg_last_10"), 1.0)
        home_gd5 = avg_total(home_form, "goal_diff_last_5", "matches_last_5", 0.0)
        away_gd5 = avg_total(away_form, "goal_diff_last_5", "matches_last_5", 0.0)
        home_gd10 = avg_total(home_form, "goal_diff_last_10", "matches_last_10", 0.0)
        away_gd10 = avg_total(away_form, "goal_diff_last_10", "matches_last_10", 0.0)
        home_elochg5 = avg_total(home_form, "elo_change_last_5", "matches_last_5", 0.0)
        away_elochg5 = avg_total(away_form, "elo_change_last_5", "matches_last_5", 0.0)
        home_elochg10 = avg_total(home_form, "elo_change_last_10", "matches_last_10", 0.0)
        away_elochg10 = avg_total(away_form, "elo_change_last_10", "matches_last_10", 0.0)
        home_days = days_since(fixture_date, home_form.get("last_match_date") or home_elo_row.get("last_match_date"))
        away_days = days_since(fixture_date, away_form.get("last_match_date") or away_elo_row.get("last_match_date"))
        home_matches = safe_float(home_elo_row.get("matches_played"), 0.0)
        away_matches = safe_float(away_elo_row.get("matches_played"), 0.0)

        missing = []
        if home not in elo:
            missing.append(f"home_elo:{v2.display_team(home)}")
        if away not in elo:
            missing.append(f"away_elo:{v2.display_team(away)}")
        if home not in form:
            missing.append(f"home_form:{v2.display_team(home)}")
        if away not in form:
            missing.append(f"away_form:{v2.display_team(away)}")

        rows.append(
            {
                "fixture_key": fixture_key,
                "date": fixture.get("date", ""),
                "time_et": fixture.get("time_et", ""),
                "team1": fixture["team1"],
                "team2": fixture["team2"],
                "home_team": home,
                "away_team": away,
                "home_display": v2.display_team(home),
                "away_display": v2.display_team(away),
                "orientation_source": orientation_source,
                "competition_context": fixture.get("competition_context", ""),
                "tournament_bucket": bucket,
                "neutral": neutral,
                "home_field": home_field,
                "is_competitive": is_comp,
                "is_world_cup": is_wc,
                "home_elo_pre": home_elo,
                "away_elo_pre": away_elo,
                "elo_diff": home_elo - away_elo,
                "abs_elo_diff": abs(home_elo - away_elo),
                "elo_avg": (home_elo + away_elo) / 2.0,
                "home_recent_ppg5": home_ppg5,
                "away_recent_ppg5": away_ppg5,
                "recent_ppg5_diff": home_ppg5 - away_ppg5,
                "recent_gd5_diff": home_gd5 - away_gd5,
                "recent_elochg5_diff": home_elochg5 - away_elochg5,
                "recent_oppelo5_diff": safe_float(home_form.get("avg_opponent_elo_last_5"), 1500.0) - safe_float(away_form.get("avg_opponent_elo_last_5"), 1500.0),
                "recent_ppg10_diff": home_ppg10 - away_ppg10,
                "recent_gd10_diff": home_gd10 - away_gd10,
                "recent_elochg10_diff": home_elochg10 - away_elochg10,
                "rest_days_diff": home_days - away_days,
                "home_matches_prior_log": math.log1p(home_matches),
                "away_matches_prior_log": math.log1p(away_matches),
                "matches_prior_log_diff": math.log1p(home_matches) - math.log1p(away_matches),
                "temperature_c": weather_row.get("temperature_c", ""),
                "weather_goal_factor": weather_row.get("weather_goal_factor", ""),
                "weather_note": weather_row.get("weather_note", ""),
                "provider_status": provider.get("provider_status", ""),
                "live_score": provider.get("live_score", ""),
                "actual_90min_result": provider.get("actual_90min_result", ""),
                "data_quality_score": quality_row.get("data_quality_score", ""),
                "missing_live_features": ";".join(missing),
            }
        )
    return rows


def design_live_matrix(feature_rows: list[dict[str, Any]], feature_columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(feature_rows)
    design = pd.get_dummies(frame[v26.FEATURE_COLUMNS + ["tournament_bucket"]].copy(), columns=["tournament_bucket"], dtype=float)
    return design.reindex(columns=feature_columns, fill_value=0.0)


def predict_models(artifact: dict[str, Any], feature_rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    x_live = design_live_matrix(feature_rows, artifact["feature_columns"])
    raw: dict[str, np.ndarray] = {
        "elo_formula": v26.elo_formula_probs(pd.DataFrame(feature_rows)),
    }
    logistic = artifact["models"]["logistic_regression"]
    gradient_boosting = artifact["models"]["gradient_boosting"]
    raw["logistic_regression"] = v26.align_proba(logistic.predict_proba(x_live), logistic.classes_)
    raw["gradient_boosting"] = v26.align_proba(gradient_boosting.predict_proba(x_live), gradient_boosting.classes_)

    temperatures = artifact["temperatures"]
    probs = {
        name: v26.temperature_scale(values, safe_float(temperatures.get(name), 1.0))
        for name, values in raw.items()
    }
    weights = artifact["ensemble_weights"]
    ensemble = np.zeros_like(probs["elo_formula"])
    for name, weight in weights.items():
        if name == "v25_poisson_lite":
            continue
        if name in probs:
            ensemble += safe_float(weight) * probs[name]
    if ensemble.sum(axis=1).min() <= 0:
        ensemble = probs["elo_formula"]
    else:
        ensemble = ensemble / ensemble.sum(axis=1, keepdims=True)
    probs["ensemble"] = v26.temperature_scale(ensemble, safe_float(temperatures.get("ensemble"), 1.0))
    return probs


def team_result_from_home_pick(pick: str, feature_row: dict[str, Any]) -> str:
    if pick == "pass":
        return "pass"
    if pick == "draw":
        return "draw"
    team1 = v2.normalize_team(feature_row["team1"])
    home = feature_row["home_team"]
    if pick == "home_win":
        return "team1_win" if home == team1 else "team2_win"
    if pick == "away_win":
        return "team2_win" if home == team1 else "team1_win"
    return pick


def verdict_from_pick(team_pick: str, feature_row: dict[str, Any], probability: float, consensus: bool) -> tuple[str, str, str]:
    if team_pick == "pass":
        return (
            "Pass",
            "Pass",
            "The calibrated ensemble and logistic safety check do not agree strongly enough for a public pick.",
        )
    if team_pick == "draw":
        return (
            "Draw lean",
            "Low-medium",
            "The trained model sees draw as the strongest public outcome after calibration.",
        )
    team = feature_row["team1"] if team_pick == "team1_win" else feature_row["team2"]
    confidence = "High" if probability >= 0.66 and consensus else "Medium" if probability >= 0.58 else "Low-medium"
    return (
        f"{team} win lean",
        confidence,
        "Ensemble and logistic models agree on this non-pass outcome." if consensus else "Internal ensemble lean; public gate may still pass.",
    )


def build_prediction_tables(
    artifact: dict[str, Any],
    feature_rows: list[dict[str, Any]],
    probs_by_model: dict[str, np.ndarray],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    ensemble_rule = artifact["pass_rules"]["ensemble"]
    logistic_rule = artifact["pass_rules"]["logistic_regression"]
    ensemble_public = v26.pick_with_pass(
        probs_by_model["ensemble"],
        ensemble_rule["min_confidence"],
        ensemble_rule["min_gap"],
        ensemble_rule["draw_risk_min"],
        ensemble_rule["draw_gap_max"],
    )
    logistic_public = v26.pick_with_pass(
        probs_by_model["logistic_regression"],
        logistic_rule["min_confidence"],
        logistic_rule["min_gap"],
        logistic_rule["draw_risk_min"],
        logistic_rule["draw_gap_max"],
    )

    probability_rows = []
    public_rows = []
    comparison_rows = []
    v25_rows = load_lookup(PROCESSED / "v25_match_predictions_live.csv", "fixture_key")

    for idx, feature_row in enumerate(feature_rows):
        fixture_key = feature_row["fixture_key"]
        home = feature_row["home_team"]
        team1_norm = v2.normalize_team(feature_row["team1"])
        team1_is_home = team1_norm == home
        ensemble_probs = probs_by_model["ensemble"][idx]
        logistic_probs = probs_by_model["logistic_regression"][idx]
        gb_probs = probs_by_model["gradient_boosting"][idx]
        elo_probs = probs_by_model["elo_formula"][idx]

        team1_win = ensemble_probs[0] if team1_is_home else ensemble_probs[2]
        team2_win = ensemble_probs[2] if team1_is_home else ensemble_probs[0]
        draw = ensemble_probs[1]
        internal_pick = team_result_from_home_pick(v26.LABELS[int(np.argmax(ensemble_probs))], feature_row)
        consensus_home_pick = (
            ensemble_public[idx]
            if ensemble_public[idx] != "pass" and ensemble_public[idx] == logistic_public[idx]
            else "pass"
        )
        public_pick = team_result_from_home_pick(consensus_home_pick, feature_row)
        pick_probability = {
            "team1_win": team1_win,
            "draw": draw,
            "team2_win": team2_win,
            "pass": max(team1_win, draw, team2_win),
        }.get(public_pick, max(team1_win, draw, team2_win))
        verdict, confidence, reason = verdict_from_pick(public_pick, feature_row, float(pick_probability), consensus_home_pick != "pass")
        actual = feature_row.get("actual_90min_result", "")
        pick_correct = "" if not actual or public_pick == "pass" else actual == public_pick

        probability_rows.append(
            {
                "fixture_key": fixture_key,
                "date": feature_row["date"],
                "time_et": feature_row["time_et"],
                "team1": feature_row["team1"],
                "team2": feature_row["team2"],
                "model_home_team": feature_row["home_display"],
                "model_away_team": feature_row["away_display"],
                "orientation_source": feature_row["orientation_source"],
                "ensemble_team1_win_probability": round_prob(team1_win),
                "ensemble_draw_probability": round_prob(draw),
                "ensemble_team2_win_probability": round_prob(team2_win),
                "ensemble_internal_pick": internal_pick,
                "logistic_home_win_probability": round_prob(logistic_probs[0]),
                "logistic_draw_probability": round_prob(logistic_probs[1]),
                "logistic_away_win_probability": round_prob(logistic_probs[2]),
                "gradient_boosting_home_win_probability": round_prob(gb_probs[0]),
                "gradient_boosting_draw_probability": round_prob(gb_probs[1]),
                "gradient_boosting_away_win_probability": round_prob(gb_probs[2]),
                "elo_home_win_probability": round_prob(elo_probs[0]),
                "elo_draw_probability": round_prob(elo_probs[1]),
                "elo_away_win_probability": round_prob(elo_probs[2]),
            }
        )
        public_rows.append(
            {
                "fixture_key": fixture_key,
                "date": feature_row["date"],
                "time_et": feature_row["time_et"],
                "team1": feature_row["team1"],
                "team2": feature_row["team2"],
                "provider_status": feature_row.get("provider_status", ""),
                "live_score": feature_row.get("live_score", ""),
                "public_verdict": verdict,
                "confidence": confidence,
                "public_pick": public_pick,
                "internal_ensemble_pick": internal_pick,
                "ensemble_public_pick_before_consensus": team_result_from_home_pick(ensemble_public[idx], feature_row),
                "logistic_public_pick_before_consensus": team_result_from_home_pick(logistic_public[idx], feature_row),
                "team1_win_probability": round_prob(team1_win),
                "draw_probability": round_prob(draw),
                "team2_win_probability": round_prob(team2_win),
                "model_reason": reason,
                "temperature_c": feature_row.get("temperature_c", ""),
                "weather_note": feature_row.get("weather_note", ""),
                "data_quality_score": feature_row.get("data_quality_score", ""),
                "missing_live_features": feature_row.get("missing_live_features", ""),
                "actual_90min_result": actual,
                "pick_correct": pick_correct,
            }
        )
        v25 = v25_rows.get(fixture_key, {})
        comparison_rows.append(
            {
                "fixture_key": fixture_key,
                "team1": feature_row["team1"],
                "team2": feature_row["team2"],
                "v25_public_verdict": v25.get("public_verdict", ""),
                "v25_confidence": v25.get("confidence", ""),
                "v25_pick": v25.get("model_90min_pick", ""),
                "v25_team1_win_probability": v25.get("team1_win_probability_internal", ""),
                "v25_draw_probability": v25.get("draw_probability_internal", ""),
                "v25_team2_win_probability": v25.get("team2_win_probability_internal", ""),
                "v27_public_verdict": verdict,
                "v27_confidence": confidence,
                "v27_public_pick": public_pick,
                "v27_internal_ensemble_pick": internal_pick,
                "v27_team1_win_probability": round_prob(team1_win),
                "v27_draw_probability": round_prob(draw),
                "v27_team2_win_probability": round_prob(team2_win),
                "actual_90min_result": actual,
                "v25_pick_correct": v25.get("pick_correct", ""),
                "v27_pick_correct": pick_correct,
            }
        )
    return probability_rows, public_rows, comparison_rows


def write_feature_rows(feature_rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "fixture_key",
        "date",
        "time_et",
        "team1",
        "team2",
        "home_display",
        "away_display",
        "orientation_source",
        "competition_context",
        "tournament_bucket",
        *v26.FEATURE_COLUMNS,
        "temperature_c",
        "weather_goal_factor",
        "weather_note",
        "provider_status",
        "live_score",
        "actual_90min_result",
        "data_quality_score",
        "missing_live_features",
    ]
    write_csv(FEATURES_PATH, feature_rows, fieldnames)


def write_report(
    artifact: dict[str, Any],
    feature_rows: list[dict[str, Any]],
    public_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
) -> None:
    non_pass = [row for row in public_rows if row["public_pick"] != "pass"]
    final_scored = [row for row in public_rows if row["actual_90min_result"] and row["public_pick"] != "pass"]
    correct = [row for row in final_scored if str(row["pick_correct"]).lower() == "true"]
    v25_changed = [row for row in comparison_rows if row["v25_pick"] != row["v27_public_pick"]]
    missing_features = [row for row in feature_rows if row["missing_live_features"]]
    lines = [
        "# Live Predictions v2.7",
        "",
        "V2.7 plugs the calibrated v2.6 ensemble into the live v2.5 tables. The old v2.5 hand-weighted prediction remains visible only as a comparison layer.",
        "",
        "## What Changed",
        "",
        "- Final model artifacts are saved under `data/model_artifacts/v27/`.",
        "- Live fixtures are converted into the same feature schema used by the v2.6 bakeoff.",
        "- Public picks use the v2.6 consensus gate: ensemble and logistic regression must agree on the same non-pass result.",
        "- The Poisson-style layer stays useful for tournament path simulation, but it is no longer the primary live 1X2 decision engine.",
        "",
        "## Artifact",
        "",
        f"- Training rows: {artifact['training_rows']:,}.",
        f"- Training date range: {artifact['training_date_min']} to {artifact['training_date_max']}.",
        f"- Ensemble weights: elo {artifact['ensemble_weights'].get('elo_formula', 0):.1%}, logistic {artifact['ensemble_weights'].get('logistic_regression', 0):.1%}, gradient boosting {artifact['ensemble_weights'].get('gradient_boosting', 0):.1%}, Poisson {artifact['ensemble_weights'].get('v25_poisson_lite', 0):.1%}.",
        "",
        "## Live Run Summary",
        "",
        f"- Fixtures scored: {len(public_rows)}.",
        f"- Public non-pass picks: {len(non_pass)} ({round(100 * len(non_pass) / len(public_rows), 2) if public_rows else 0}%).",
        f"- V2.5 vs v2.7 changed calls: {len(v25_changed)}.",
        f"- Rows with missing Elo/form features: {len(missing_features)}.",
    ]
    if final_scored:
        lines.append(f"- Scored final non-pass picks: {len(correct)}/{len(final_scored)} correct.")
    else:
        lines.append("- Scored final non-pass picks: none yet.")
    lines.extend(
        [
            "",
            "## V2.7 Public Picks",
            "",
            "| Fixture | V2.7 public call | Internal lean | Team 1 | Draw | Team 2 | Data quality |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in public_rows:
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['public_verdict']} | {row['internal_ensemble_pick']} | "
            f"{float(row['team1_win_probability']) * 100:.2f}% | {float(row['draw_probability']) * 100:.2f}% | "
            f"{float(row['team2_win_probability']) * 100:.2f}% | {row['data_quality_score']} |"
        )
    lines.extend(
        [
            "",
            "## Comparison vs v2.5",
            "",
            "| Fixture | v2.5 call | v2.7 public call | v2.7 internal lean |",
            "|---|---|---|---|",
        ]
    )
    for row in comparison_rows:
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['v25_public_verdict']} | {row['v27_public_verdict']} | {row['v27_internal_ensemble_pick']} |"
        )
    lines.extend(
        [
            "",
            "## Honest Caveat",
            "",
            "This is a production-integration step, not a new accuracy claim. The historical accuracy claim still comes from the v2.6 time-safe test; v2.7 retrains final artifacts on all available historical data after the architecture was selected.",
        ]
    )
    OUTPUTS.mkdir(exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v2.7 live predictions.")
    parser.add_argument("--force-train", action="store_true", help="Retrain and overwrite the v2.7 model artifact.")
    args = parser.parse_args()

    artifact = train_final_artifact(force=args.force_train)
    feature_rows = build_live_feature_rows()
    probs_by_model = predict_models(artifact, feature_rows)
    probability_rows, public_rows, comparison_rows = build_prediction_tables(artifact, feature_rows, probs_by_model)

    write_feature_rows(feature_rows)
    write_csv(
        PROBABILITIES_PATH,
        probability_rows,
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "model_home_team",
            "model_away_team",
            "orientation_source",
            "ensemble_team1_win_probability",
            "ensemble_draw_probability",
            "ensemble_team2_win_probability",
            "ensemble_internal_pick",
            "logistic_home_win_probability",
            "logistic_draw_probability",
            "logistic_away_win_probability",
            "gradient_boosting_home_win_probability",
            "gradient_boosting_draw_probability",
            "gradient_boosting_away_win_probability",
            "elo_home_win_probability",
            "elo_draw_probability",
            "elo_away_win_probability",
        ],
    )
    write_csv(
        PUBLIC_PICKS_PATH,
        public_rows,
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "provider_status",
            "live_score",
            "public_verdict",
            "confidence",
            "public_pick",
            "internal_ensemble_pick",
            "ensemble_public_pick_before_consensus",
            "logistic_public_pick_before_consensus",
            "team1_win_probability",
            "draw_probability",
            "team2_win_probability",
            "model_reason",
            "temperature_c",
            "weather_note",
            "data_quality_score",
            "missing_live_features",
            "actual_90min_result",
            "pick_correct",
        ],
    )
    write_csv(
        COMPARISON_PATH,
        comparison_rows,
        [
            "fixture_key",
            "team1",
            "team2",
            "v25_public_verdict",
            "v25_confidence",
            "v25_pick",
            "v25_team1_win_probability",
            "v25_draw_probability",
            "v25_team2_win_probability",
            "v27_public_verdict",
            "v27_confidence",
            "v27_public_pick",
            "v27_internal_ensemble_pick",
            "v27_team1_win_probability",
            "v27_draw_probability",
            "v27_team2_win_probability",
            "actual_90min_result",
            "v25_pick_correct",
            "v27_pick_correct",
        ],
    )
    config = dict(V27_CONFIG)
    config["artifact_training_rows"] = artifact["training_rows"]
    config["artifact_training_date_min"] = artifact["training_date_min"]
    config["artifact_training_date_max"] = artifact["training_date_max"]
    config["ensemble_weights"] = artifact["ensemble_weights"]
    config["temperatures"] = artifact["temperatures"]
    config["pass_rules"] = artifact["pass_rules"]
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(artifact, feature_rows, public_rows, comparison_rows)

    non_pass = [row for row in public_rows if row["public_pick"] != "pass"]
    print(
        json.dumps(
            {
                "fixtures": len(public_rows),
                "non_pass_public_picks": len(non_pass),
                "artifact": str(ARTIFACT_PATH.relative_to(ROOT)),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
