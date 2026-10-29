#!/usr/bin/env python3
"""Model v2.6 bake-off and calibration.

The goal is to choose the match prediction architecture honestly:
- build time-safe features from historical international matches
- train only on older matches
- calibrate probabilities and pass rules on a middle period
- test on recent matches
"""

from __future__ import annotations

import csv
import itertools
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import build_worldcup_model_v2 as v2
import build_worldcup_model_v23 as v23


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

CONFIG_PATH = OUTPUTS / "model_v26_config.json"
REPORT_PATH = OUTPUTS / "model_v26_bakeoff_report.md"
METRICS_PATH = PROCESSED / "model_v26_bakeoff_metrics.csv"
PASS_RULES_PATH = PROCESSED / "model_v26_pass_rules.csv"
CALIBRATION_BINS_PATH = PROCESSED / "model_v26_calibration_bins.csv"
TEST_PREDICTIONS_PATH = PROCESSED / "model_v26_test_predictions.csv"
FEATURE_IMPORTANCE_PATH = PROCESSED / "model_v26_feature_importance.csv"

LABELS = ["home_win", "draw", "away_win"]
LABEL_TO_INDEX = {label: idx for idx, label in enumerate(LABELS)}

V26_CONFIG = {
    "version": "v2.6",
    "purpose": "Model bake-off plus probability/pass calibration.",
    "data_source": "data/processed/international_matches.csv",
    "min_train_date": "2000-01-01",
    "train_end": "2018-12-31",
    "calibration_start": "2019-01-01",
    "calibration_end": "2022-12-31",
    "test_start": "2023-01-01",
    "test_end": "2026-12-31",
    "models": [
        "elo_formula",
        "v25_poisson_lite",
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
        "ensemble",
        "ensemble_logistic_consensus_gate",
    ],
    "feature_note": "Features are built by iterating matches chronologically and using only pre-match Elo plus prior team history.",
    "calibration_note": "Temperature scaling and public pass rules are selected on the calibration split only.",
}


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


def as_bool(value: Any) -> bool:
    return str(value).lower() == "true"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def tournament_bucket(tournament: str, is_world_cup: bool, is_competitive: bool) -> str:
    lower = tournament.lower()
    if is_world_cup:
        return "world_cup"
    if "uefa euro" in lower or "copa am" in lower or "african cup" in lower or "asian cup" in lower or "gold cup" in lower:
        return "continental_finals"
    if "qualification" in lower or "qualifier" in lower:
        return "qualifier"
    if "nations league" in lower:
        return "nations_league"
    if "friendly" in lower:
        return "friendly"
    if is_competitive:
        return "other_competitive"
    return "other"


def summarize_history(matches: deque[dict[str, Any]], as_of: datetime) -> dict[str, float]:
    if not matches:
        return {
            "matches_prior": 0,
            "ppg5": 1.0,
            "gd5": 0.0,
            "elochg5": 0.0,
            "oppelo5": 1500.0,
            "ppg10": 1.0,
            "gd10": 0.0,
            "elochg10": 0.0,
            "oppelo10": 1500.0,
            "days_since": 999.0,
        }

    def window_stats(window: list[dict[str, Any]]) -> tuple[float, float, float, float]:
        if not window:
            return 1.0, 0.0, 0.0, 1500.0
        return (
            sum(row["points"] for row in window) / len(window),
            sum(row["goal_diff"] for row in window) / len(window),
            sum(row["elo_change"] for row in window) / len(window),
            sum(row["opponent_pre_elo"] for row in window) / len(window),
        )

    history = list(matches)
    ppg5, gd5, elochg5, oppelo5 = window_stats(history[-5:])
    ppg10, gd10, elochg10, oppelo10 = window_stats(history[-10:])
    days_since = (as_of - history[-1]["date"]).days
    return {
        "matches_prior": len(history),
        "ppg5": ppg5,
        "gd5": gd5,
        "elochg5": elochg5,
        "oppelo5": oppelo5,
        "ppg10": ppg10,
        "gd10": gd10,
        "elochg10": elochg10,
        "oppelo10": oppelo10,
        "days_since": min(max(days_since, 0), 999),
    }


def build_feature_frame() -> pd.DataFrame:
    rows = []
    with (PROCESSED / "international_matches.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    rows.sort(key=lambda row: (row["date"], safe_int(row["match_id"])))

    team_history: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=20))
    feature_rows: list[dict[str, Any]] = []
    min_date = parse_date(V26_CONFIG["min_train_date"])

    for raw in rows:
        date = parse_date(raw["date"])
        home = raw["home_team"]
        away = raw["away_team"]
        result = raw["result"]
        if result not in LABEL_TO_INDEX:
            continue
        home_elo = safe_float(raw["home_elo_pre"], 1500.0)
        away_elo = safe_float(raw["away_elo_pre"], 1500.0)
        home_hist = summarize_history(team_history[home], date)
        away_hist = summarize_history(team_history[away], date)
        is_comp = as_bool(raw["is_competitive"])
        is_wc = as_bool(raw["is_world_cup"])
        neutral = as_bool(raw["neutral"])
        bucket = tournament_bucket(raw["tournament"], is_wc, is_comp)
        if date >= min_date:
            feature_rows.append(
                {
                    "match_id": raw["match_id"],
                    "date": raw["date"],
                    "year": date.year,
                    "home_team": home,
                    "away_team": away,
                    "result": result,
                    "label_index": LABEL_TO_INDEX[result],
                    "tournament": raw["tournament"],
                    "tournament_bucket": bucket,
                    "neutral": int(neutral),
                    "home_field": int(not neutral),
                    "is_competitive": int(is_comp),
                    "is_world_cup": int(is_wc),
                    "home_elo_pre": home_elo,
                    "away_elo_pre": away_elo,
                    "elo_diff": home_elo - away_elo,
                    "abs_elo_diff": abs(home_elo - away_elo),
                    "elo_avg": (home_elo + away_elo) / 2.0,
                    "home_recent_ppg5": home_hist["ppg5"],
                    "away_recent_ppg5": away_hist["ppg5"],
                    "recent_ppg5_diff": home_hist["ppg5"] - away_hist["ppg5"],
                    "recent_gd5_diff": home_hist["gd5"] - away_hist["gd5"],
                    "recent_elochg5_diff": home_hist["elochg5"] - away_hist["elochg5"],
                    "recent_oppelo5_diff": home_hist["oppelo5"] - away_hist["oppelo5"],
                    "recent_ppg10_diff": home_hist["ppg10"] - away_hist["ppg10"],
                    "recent_gd10_diff": home_hist["gd10"] - away_hist["gd10"],
                    "recent_elochg10_diff": home_hist["elochg10"] - away_hist["elochg10"],
                    "rest_days_diff": home_hist["days_since"] - away_hist["days_since"],
                    "home_matches_prior_log": math.log1p(home_hist["matches_prior"]),
                    "away_matches_prior_log": math.log1p(away_hist["matches_prior"]),
                    "matches_prior_log_diff": math.log1p(home_hist["matches_prior"]) - math.log1p(away_hist["matches_prior"]),
                    "home_score": safe_int(raw["home_score"]),
                    "away_score": safe_int(raw["away_score"]),
                }
            )

        home_points = 3 if result == "home_win" else 1 if result == "draw" else 0
        away_points = 3 if result == "away_win" else 1 if result == "draw" else 0
        home_score = safe_int(raw["home_score"])
        away_score = safe_int(raw["away_score"])
        team_history[home].append(
            {
                "date": date,
                "points": home_points,
                "goal_diff": home_score - away_score,
                "elo_change": safe_float(raw["home_elo_change"]),
                "opponent_pre_elo": away_elo,
            }
        )
        team_history[away].append(
            {
                "date": date,
                "points": away_points,
                "goal_diff": away_score - home_score,
                "elo_change": safe_float(raw["away_elo_change"]),
                "opponent_pre_elo": home_elo,
            }
        )
    return pd.DataFrame(feature_rows)


def split_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = df[(df["date"] <= V26_CONFIG["train_end"])].copy()
    cal = df[(df["date"] >= V26_CONFIG["calibration_start"]) & (df["date"] <= V26_CONFIG["calibration_end"])].copy()
    test = df[(df["date"] >= V26_CONFIG["test_start"]) & (df["date"] <= V26_CONFIG["test_end"])].copy()
    return train, cal, test


FEATURE_COLUMNS = [
    "neutral",
    "home_field",
    "is_competitive",
    "is_world_cup",
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
    "abs_elo_diff",
    "elo_avg",
    "home_recent_ppg5",
    "away_recent_ppg5",
    "recent_ppg5_diff",
    "recent_gd5_diff",
    "recent_elochg5_diff",
    "recent_oppelo5_diff",
    "recent_ppg10_diff",
    "recent_gd10_diff",
    "recent_elochg10_diff",
    "rest_days_diff",
    "home_matches_prior_log",
    "away_matches_prior_log",
    "matches_prior_log_diff",
]


def design_matrix(train: pd.DataFrame, *others: pd.DataFrame) -> tuple[pd.DataFrame, list[pd.DataFrame]]:
    base = train[FEATURE_COLUMNS + ["tournament_bucket"]].copy()
    combined = [base]
    for frame in others:
        combined.append(frame[FEATURE_COLUMNS + ["tournament_bucket"]].copy())
    all_design = pd.get_dummies(pd.concat(combined, axis=0), columns=["tournament_bucket"], dtype=float)
    train_design = all_design.iloc[: len(train)].copy()
    outputs = []
    start = len(train)
    for frame in others:
        outputs.append(all_design.iloc[start : start + len(frame)].copy())
        start += len(frame)
    return train_design, outputs


def align_proba(proba: np.ndarray, classes: np.ndarray) -> np.ndarray:
    aligned = np.zeros((len(proba), len(LABELS)), dtype=float)
    for idx, cls in enumerate(classes):
        aligned[:, int(cls)] = proba[:, idx]
    row_sums = aligned.sum(axis=1)
    missing = row_sums == 0
    if np.any(missing):
        aligned[missing] = 1.0 / len(LABELS)
        row_sums = aligned.sum(axis=1)
    return aligned / row_sums[:, None]


def elo_formula_probs(frame: pd.DataFrame) -> np.ndarray:
    probs = []
    for row in frame.itertuples(index=False):
        elo_diff = row.elo_diff + (55.0 if row.home_field else 0.0)
        home_two_way = 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))
        base_draw = 0.275 if row.is_competitive else 0.255
        if row.neutral:
            base_draw += 0.015
        draw = clamp(base_draw - min(abs(row.elo_diff), 700.0) / 3500.0, 0.145, 0.31)
        home = home_two_way * (1.0 - draw)
        away = (1.0 - home_two_way) * (1.0 - draw)
        probs.append([home, draw, away])
    return np.array(probs, dtype=float)


def v25_poisson_probs(frame: pd.DataFrame) -> np.ndarray:
    probs = []
    for row in frame.itertuples(index=False):
        power_diff = (
            row.elo_diff / 13.5
            + row.recent_ppg5_diff * 3.2
            + row.recent_gd5_diff * 2.4
            + row.recent_elochg5_diff / 8.0
            + (3.0 if row.home_field else 0.0)
        )
        if not row.is_competitive:
            power_diff *= 0.92
        lambda_home, lambda_away = v23.expected_goals(power_diff, 0.0)
        if not row.is_competitive:
            lambda_home *= 1.03
            lambda_away *= 1.03
        home, draw, away = v2.scoreline_probabilities(lambda_home, lambda_away)
        probs.append([home, draw, away])
    return np.array(probs, dtype=float)


def train_ml_models(x_train: pd.DataFrame, y_train: np.ndarray) -> dict[str, Any]:
    models: dict[str, Any] = {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1200,
                        C=0.8,
                        class_weight="balanced",
                        random_state=20260607,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=350,
            max_depth=10,
            min_samples_leaf=35,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=20260607,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=220,
            learning_rate=0.035,
            max_depth=3,
            subsample=0.85,
            random_state=20260607,
        ),
    }
    for model in models.values():
        model.fit(x_train, y_train)
    return models


def temperature_scale(probs: np.ndarray, temperature: float) -> np.ndarray:
    clipped = np.clip(probs, 1e-9, 1.0)
    scaled = clipped ** (1.0 / temperature)
    return scaled / scaled.sum(axis=1, keepdims=True)


def tune_temperature(probs: np.ndarray, y_true: np.ndarray) -> tuple[float, float]:
    best_temp = 1.0
    best_loss = float("inf")
    for temp in np.round(np.arange(0.65, 2.81, 0.05), 2):
        scaled = temperature_scale(probs, float(temp))
        loss = log_loss(y_true, scaled, labels=[0, 1, 2])
        if loss < best_loss:
            best_temp = float(temp)
            best_loss = float(loss)
    return best_temp, best_loss


def brier_score(y_true: np.ndarray, probs: np.ndarray) -> float:
    onehot = np.eye(len(LABELS))[y_true]
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def expected_calibration_error(y_true: np.ndarray, probs: np.ndarray, bins: int = 10) -> tuple[float, list[dict[str, Any]]]:
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    correct = (pred == y_true).astype(float)
    rows = []
    ece = 0.0
    for idx in range(bins):
        low = idx / bins
        high = (idx + 1) / bins
        mask = (conf >= low) & (conf < high if idx < bins - 1 else conf <= high)
        n = int(mask.sum())
        if not n:
            rows.append({"bin": idx + 1, "low": low, "high": high, "count": 0, "avg_confidence": "", "accuracy": "", "gap": ""})
            continue
        avg_conf = float(conf[mask].mean())
        acc = float(correct[mask].mean())
        gap = abs(avg_conf - acc)
        ece += (n / len(y_true)) * gap
        rows.append({"bin": idx + 1, "low": low, "high": high, "count": n, "avg_confidence": round(avg_conf, 4), "accuracy": round(acc, 4), "gap": round(gap, 4)})
    return float(ece), rows


def pick_with_pass(probs: np.ndarray, min_confidence: float, min_gap: float, draw_risk_min: float, draw_gap_max: float) -> list[str]:
    picks = []
    for p_home, p_draw, p_away in probs:
        ordered = sorted([p_home, p_draw, p_away], reverse=True)
        top = ordered[0]
        gap = ordered[0] - ordered[1]
        if top < min_confidence or gap < min_gap:
            picks.append("pass")
            continue
        if p_draw >= draw_risk_min and abs(p_home - p_away) <= draw_gap_max and max(p_home, p_away) <= 0.43:
            picks.append("pass")
            continue
        picks.append(LABELS[int(np.argmax([p_home, p_draw, p_away]))])
    return picks


def tune_pass_rule(probs: np.ndarray, y_true: np.ndarray) -> dict[str, Any]:
    best = None
    for min_conf in np.round(np.arange(0.34, 0.56, 0.02), 2):
        for min_gap in np.round(np.arange(0.00, 0.18, 0.02), 2):
            for draw_min in [0.27, 0.29, 0.31, 0.33]:
                for draw_gap in [0.04, 0.08, 0.12, 0.16]:
                    picks = pick_with_pass(probs, float(min_conf), float(min_gap), float(draw_min), float(draw_gap))
                    non_pass = [idx for idx, pick in enumerate(picks) if pick != "pass"]
                    coverage = len(non_pass) / len(picks)
                    if coverage < 0.30:
                        continue
                    if non_pass:
                        acc = float(np.mean([LABEL_TO_INDEX[picks[idx]] == y_true[idx] for idx in non_pass]))
                    else:
                        acc = 0.0
                    # Business objective: good accuracy, but do not pass everything.
                    objective = acc + 0.10 * coverage
                    candidate = {
                        "min_confidence": float(min_conf),
                        "min_gap": float(min_gap),
                        "draw_risk_min": float(draw_min),
                        "draw_gap_max": float(draw_gap),
                        "coverage": coverage,
                        "accepted_accuracy": acc,
                        "objective": objective,
                    }
                    if best is None or candidate["objective"] > best["objective"]:
                        best = candidate
    return best or {"min_confidence": 0.42, "min_gap": 0.04, "draw_risk_min": 0.29, "draw_gap_max": 0.12, "coverage": 1.0, "accepted_accuracy": 0.0, "objective": 0.0}


def evaluate_model(name: str, probs: np.ndarray, y_true: np.ndarray, pass_rule: dict[str, Any]) -> dict[str, Any]:
    pred = probs.argmax(axis=1)
    picks = pick_with_pass(
        probs,
        pass_rule["min_confidence"],
        pass_rule["min_gap"],
        pass_rule["draw_risk_min"],
        pass_rule["draw_gap_max"],
    )
    non_pass = [idx for idx, pick in enumerate(picks) if pick != "pass"]
    pass_idx = [idx for idx, pick in enumerate(picks) if pick == "pass"]
    accepted_acc = float(np.mean([LABEL_TO_INDEX[picks[idx]] == y_true[idx] for idx in non_pass])) if non_pass else 0.0
    pass_actual_draw_or_upset = 0.0
    if pass_idx:
        # "Messy match" proxy: actual draw or not won by the highest-probability favorite.
        messy = 0
        for idx in pass_idx:
            fav = int(np.argmax(probs[idx]))
            actual = int(y_true[idx])
            if actual == LABEL_TO_INDEX["draw"] or actual != fav:
                messy += 1
        pass_actual_draw_or_upset = messy / len(pass_idx)
    draw_pred = pred == LABEL_TO_INDEX["draw"]
    actual_draw = y_true == LABEL_TO_INDEX["draw"]
    draw_precision = float(np.mean(actual_draw[draw_pred])) if np.any(draw_pred) else 0.0
    draw_recall = float(np.mean(draw_pred[actual_draw])) if np.any(actual_draw) else 0.0
    ece, _ = expected_calibration_error(y_true, probs)
    return {
        "model": name,
        "matches": len(y_true),
        "log_loss": round(float(log_loss(y_true, probs, labels=[0, 1, 2])), 5),
        "brier": round(brier_score(y_true, probs), 5),
        "argmax_accuracy": round(float(accuracy_score(y_true, pred)), 5),
        "ece": round(ece, 5),
        "draw_precision": round(draw_precision, 5),
        "draw_recall": round(draw_recall, 5),
        "public_coverage": round(len(non_pass) / len(picks), 5),
        "public_pass_rate": round(len(pass_idx) / len(picks), 5),
        "public_pick_accuracy": round(accepted_acc, 5),
        "pass_messy_rate": round(pass_actual_draw_or_upset, 5),
    }


def evaluate_custom_public_gate(name: str, probs: np.ndarray, y_true: np.ndarray, public_picks: list[str]) -> dict[str, Any]:
    pred = probs.argmax(axis=1)
    non_pass = [idx for idx, pick in enumerate(public_picks) if pick != "pass"]
    pass_idx = [idx for idx, pick in enumerate(public_picks) if pick == "pass"]
    accepted_acc = float(np.mean([LABEL_TO_INDEX[public_picks[idx]] == y_true[idx] for idx in non_pass])) if non_pass else 0.0
    pass_actual_draw_or_upset = 0.0
    if pass_idx:
        messy = 0
        for idx in pass_idx:
            fav = int(np.argmax(probs[idx]))
            actual = int(y_true[idx])
            if actual == LABEL_TO_INDEX["draw"] or actual != fav:
                messy += 1
        pass_actual_draw_or_upset = messy / len(pass_idx)
    draw_pred = pred == LABEL_TO_INDEX["draw"]
    actual_draw = y_true == LABEL_TO_INDEX["draw"]
    draw_precision = float(np.mean(actual_draw[draw_pred])) if np.any(draw_pred) else 0.0
    draw_recall = float(np.mean(draw_pred[actual_draw])) if np.any(actual_draw) else 0.0
    ece, _ = expected_calibration_error(y_true, probs)
    return {
        "model": name,
        "matches": len(y_true),
        "log_loss": round(float(log_loss(y_true, probs, labels=[0, 1, 2])), 5),
        "brier": round(brier_score(y_true, probs), 5),
        "argmax_accuracy": round(float(accuracy_score(y_true, pred)), 5),
        "ece": round(ece, 5),
        "draw_precision": round(draw_precision, 5),
        "draw_recall": round(draw_recall, 5),
        "public_coverage": round(len(non_pass) / len(public_picks), 5),
        "public_pass_rate": round(len(pass_idx) / len(public_picks), 5),
        "public_pick_accuracy": round(accepted_acc, 5),
        "pass_messy_rate": round(pass_actual_draw_or_upset, 5),
    }


def build_ensemble_weights(cal_probs: dict[str, np.ndarray], y_cal: np.ndarray) -> dict[str, float]:
    names = ["elo_formula", "v25_poisson_lite", "logistic_regression", "gradient_boosting"]
    best_weights = None
    best_loss = float("inf")
    steps = [i / 10.0 for i in range(11)]
    for weights in itertools.product(steps, repeat=len(names)):
        if abs(sum(weights) - 1.0) > 1e-9:
            continue
        if weights[-1] == 0 and weights[-2] == 0:
            continue
        probs = sum(weight * cal_probs[name] for weight, name in zip(weights, names))
        loss = log_loss(y_cal, probs, labels=[0, 1, 2])
        if loss < best_loss:
            best_loss = float(loss)
            best_weights = dict(zip(names, weights))
    return best_weights or {"elo_formula": 0.1, "v25_poisson_lite": 0.2, "logistic_regression": 0.3, "gradient_boosting": 0.4}


def feature_importance_rows(models: dict[str, Any], columns: list[str]) -> list[dict[str, Any]]:
    rows = []
    gb = models.get("gradient_boosting")
    if gb is not None and hasattr(gb, "feature_importances_"):
        for feature, value in sorted(zip(columns, gb.feature_importances_), key=lambda item: item[1], reverse=True):
            rows.append({"model": "gradient_boosting", "feature": feature, "importance": round(float(value), 6)})
    rf = models.get("random_forest")
    if rf is not None and hasattr(rf, "feature_importances_"):
        for feature, value in sorted(zip(columns, rf.feature_importances_), key=lambda item: item[1], reverse=True):
            rows.append({"model": "random_forest", "feature": feature, "importance": round(float(value), 6)})
    logistic = models.get("logistic_regression")
    if logistic is not None:
        coefs = logistic.named_steps["model"].coef_
        for class_idx, class_name in enumerate(LABELS):
            for feature, value in sorted(zip(columns, coefs[class_idx]), key=lambda item: abs(item[1]), reverse=True)[:20]:
                rows.append({"model": f"logistic_{class_name}", "feature": feature, "importance": round(float(value), 6)})
    return rows


def write_report(metrics: list[dict[str, Any]], pass_rules: list[dict[str, Any]], split_counts: dict[str, int], ensemble_weights: dict[str, float]) -> None:
    ordered = sorted(metrics, key=lambda row: (safe_float(row["log_loss"]), safe_float(row["brier"])))
    winner = ordered[0]
    public_ordered = sorted(metrics, key=lambda row: (-safe_float(row["public_pick_accuracy"]), -safe_float(row["public_coverage"]), safe_float(row["log_loss"])))
    public_winner = public_ordered[0]
    lines = [
        "# Model v2.6 Bake-Off + Calibration",
        "",
        "V2.6 compares match-prediction architectures on time-safe historical data. The production model should not be chosen by gut feel; it should beat simple baselines on recent unseen matches.",
        "",
        "## Data Split",
        "",
        f"- Train: {V26_CONFIG['min_train_date']} through {V26_CONFIG['train_end']} ({split_counts['train']} matches).",
        f"- Calibration: {V26_CONFIG['calibration_start']} through {V26_CONFIG['calibration_end']} ({split_counts['calibration']} matches).",
        f"- Test: {V26_CONFIG['test_start']} through {V26_CONFIG['test_end']} ({split_counts['test']} matches).",
        "",
        "## Best Model",
        "",
        f"- Best calibrated probability model: **{winner['model']}** by log loss.",
        f"- Best public-pick gate after pass rules: **{public_winner['model']}** by accepted-pick accuracy.",
        "- Recommended production shape: ensemble probabilities for the simulator, with a conservative public gate for match calls.",
        "",
        "## Ensemble Weights",
        "",
    ]
    for name, weight in ensemble_weights.items():
        lines.append(f"- {name}: {weight:.1%}")
    lines.extend(
        [
            "",
            "## Test Metrics",
            "",
            "| Model | Log loss | Brier | Argmax acc | ECE | Public coverage | Public pick acc | Pass messy rate | Draw precision | Draw recall |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(metrics, key=lambda item: safe_float(item["log_loss"])):
        lines.append(
            f"| {row['model']} | {row['log_loss']} | {row['brier']} | {row['argmax_accuracy']} | {row['ece']} | {row['public_coverage']} | {row['public_pick_accuracy']} | {row['pass_messy_rate']} | {row['draw_precision']} | {row['draw_recall']} |"
        )
    lines.extend(
        [
            "",
        "## Pass Rule Meaning",
            "",
            "A pass means the model refuses to sell the match as a public pick. It can still have an internal lean, but the confidence/gap/draw-risk combination is not strong enough. The consensus gate is stricter: it passes unless ensemble and logistic regression agree on the same non-pass public pick.",
            "",
            "## Honest Read",
            "",
            "This bake-off chooses the match model only. The World Cup tournament simulator remains a separate layer that will consume whichever match model wins.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df = build_feature_frame()
    train, cal, test = split_frame(df)
    x_train, [x_cal, x_test] = design_matrix(train, cal, test)
    y_train = train["label_index"].to_numpy(dtype=int)
    y_cal = cal["label_index"].to_numpy(dtype=int)
    y_test = test["label_index"].to_numpy(dtype=int)

    models = train_ml_models(x_train, y_train)
    raw_cal_probs: dict[str, np.ndarray] = {
        "elo_formula": elo_formula_probs(cal),
        "v25_poisson_lite": v25_poisson_probs(cal),
    }
    raw_test_probs: dict[str, np.ndarray] = {
        "elo_formula": elo_formula_probs(test),
        "v25_poisson_lite": v25_poisson_probs(test),
    }
    for name, model in models.items():
        raw_cal_probs[name] = align_proba(model.predict_proba(x_cal), model.classes_)
        raw_test_probs[name] = align_proba(model.predict_proba(x_test), model.classes_)

    temperatures: dict[str, float] = {}
    cal_probs: dict[str, np.ndarray] = {}
    test_probs: dict[str, np.ndarray] = {}
    for name, probs in raw_cal_probs.items():
        temp, _ = tune_temperature(probs, y_cal)
        temperatures[name] = temp
        cal_probs[name] = temperature_scale(probs, temp)
        test_probs[name] = temperature_scale(raw_test_probs[name], temp)

    ensemble_weights = build_ensemble_weights(cal_probs, y_cal)
    cal_probs["ensemble"] = sum(weight * cal_probs[name] for name, weight in ensemble_weights.items())
    test_probs["ensemble"] = sum(weight * test_probs[name] for name, weight in ensemble_weights.items())
    temp, _ = tune_temperature(cal_probs["ensemble"], y_cal)
    temperatures["ensemble"] = temp
    cal_probs["ensemble"] = temperature_scale(cal_probs["ensemble"], temp)
    test_probs["ensemble"] = temperature_scale(test_probs["ensemble"], temp)

    pass_rules = []
    pass_rule_by_model = {}
    metrics = []
    calibration_rows = []
    base_model_names = [name for name in V26_CONFIG["models"] if name != "ensemble_logistic_consensus_gate"]
    for name in base_model_names:
        rule = tune_pass_rule(cal_probs[name], y_cal)
        pass_rule_by_model[name] = rule
        pass_rules.append(
            {
                "model": name,
                "temperature": round(temperatures[name], 3),
                **{key: round(value, 5) if isinstance(value, float) else value for key, value in rule.items()},
            }
        )
        metrics.append(evaluate_model(name, test_probs[name], y_test, rule))
        ece, bins = expected_calibration_error(y_test, test_probs[name])
        for row in bins:
            calibration_rows.append({"model": name, **row})

    ensemble_public_cal = pick_with_pass(
        cal_probs["ensemble"],
        pass_rule_by_model["ensemble"]["min_confidence"],
        pass_rule_by_model["ensemble"]["min_gap"],
        pass_rule_by_model["ensemble"]["draw_risk_min"],
        pass_rule_by_model["ensemble"]["draw_gap_max"],
    )
    logistic_public_cal = pick_with_pass(
        cal_probs["logistic_regression"],
        pass_rule_by_model["logistic_regression"]["min_confidence"],
        pass_rule_by_model["logistic_regression"]["min_gap"],
        pass_rule_by_model["logistic_regression"]["draw_risk_min"],
        pass_rule_by_model["logistic_regression"]["draw_gap_max"],
    )
    ensemble_public_test = pick_with_pass(
        test_probs["ensemble"],
        pass_rule_by_model["ensemble"]["min_confidence"],
        pass_rule_by_model["ensemble"]["min_gap"],
        pass_rule_by_model["ensemble"]["draw_risk_min"],
        pass_rule_by_model["ensemble"]["draw_gap_max"],
    )
    logistic_public_test = pick_with_pass(
        test_probs["logistic_regression"],
        pass_rule_by_model["logistic_regression"]["min_confidence"],
        pass_rule_by_model["logistic_regression"]["min_gap"],
        pass_rule_by_model["logistic_regression"]["draw_risk_min"],
        pass_rule_by_model["logistic_regression"]["draw_gap_max"],
    )
    consensus_cal = [
        ensemble_pick if ensemble_pick != "pass" and ensemble_pick == logistic_pick else "pass"
        for ensemble_pick, logistic_pick in zip(ensemble_public_cal, logistic_public_cal)
    ]
    consensus_test = [
        ensemble_pick if ensemble_pick != "pass" and ensemble_pick == logistic_pick else "pass"
        for ensemble_pick, logistic_pick in zip(ensemble_public_test, logistic_public_test)
    ]
    consensus_non_pass_cal = [idx for idx, pick in enumerate(consensus_cal) if pick != "pass"]
    consensus_acc_cal = (
        float(np.mean([LABEL_TO_INDEX[consensus_cal[idx]] == y_cal[idx] for idx in consensus_non_pass_cal]))
        if consensus_non_pass_cal
        else 0.0
    )
    pass_rules.append(
        {
            "model": "ensemble_logistic_consensus_gate",
            "temperature": round(temperatures["ensemble"], 3),
            "min_confidence": "",
            "min_gap": "",
            "draw_risk_min": "",
            "draw_gap_max": "",
            "coverage": round(len(consensus_non_pass_cal) / len(consensus_cal), 5),
            "accepted_accuracy": round(consensus_acc_cal, 5),
            "objective": "ensemble_and_logistic_must_agree",
        }
    )
    metrics.append(evaluate_custom_public_gate("ensemble_logistic_consensus_gate", test_probs["ensemble"], y_test, consensus_test))
    ece, bins = expected_calibration_error(y_test, test_probs["ensemble"])
    for row in bins:
        calibration_rows.append({"model": "ensemble_logistic_consensus_gate", **row})

    prediction_rows = []
    for idx, row in enumerate(test.itertuples(index=False)):
        out = {
            "match_id": row.match_id,
            "date": row.date,
            "home_team": row.home_team,
            "away_team": row.away_team,
            "actual_result": row.result,
            "tournament": row.tournament,
            "tournament_bucket": row.tournament_bucket,
        }
        for name in base_model_names:
            probs = test_probs[name][idx]
            pick = LABELS[int(np.argmax(probs))]
            public = pick_with_pass(
                probs.reshape(1, -1),
                pass_rule_by_model[name]["min_confidence"],
                pass_rule_by_model[name]["min_gap"],
                pass_rule_by_model[name]["draw_risk_min"],
                pass_rule_by_model[name]["draw_gap_max"],
            )[0]
            out[f"{name}_home_win_prob"] = round(float(probs[0]), 5)
            out[f"{name}_draw_prob"] = round(float(probs[1]), 5)
            out[f"{name}_away_win_prob"] = round(float(probs[2]), 5)
            out[f"{name}_argmax_pick"] = pick
            out[f"{name}_public_pick"] = public
        probs = test_probs["ensemble"][idx]
        out["ensemble_logistic_consensus_gate_home_win_prob"] = round(float(probs[0]), 5)
        out["ensemble_logistic_consensus_gate_draw_prob"] = round(float(probs[1]), 5)
        out["ensemble_logistic_consensus_gate_away_win_prob"] = round(float(probs[2]), 5)
        out["ensemble_logistic_consensus_gate_argmax_pick"] = LABELS[int(np.argmax(probs))]
        out["ensemble_logistic_consensus_gate_public_pick"] = consensus_test[idx]
        prediction_rows.append(out)

    write_csv(METRICS_PATH, metrics, list(metrics[0].keys()))
    write_csv(PASS_RULES_PATH, pass_rules, list(pass_rules[0].keys()))
    write_csv(CALIBRATION_BINS_PATH, calibration_rows, list(calibration_rows[0].keys()))
    write_csv(TEST_PREDICTIONS_PATH, prediction_rows, list(prediction_rows[0].keys()))
    feature_rows = feature_importance_rows(models, list(x_train.columns))
    write_csv(FEATURE_IMPORTANCE_PATH, feature_rows, ["model", "feature", "importance"])

    config = dict(V26_CONFIG)
    config["split_counts"] = {"train": len(train), "calibration": len(cal), "test": len(test)}
    config["temperatures"] = temperatures
    config["ensemble_weights"] = ensemble_weights
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(metrics, pass_rules, config["split_counts"], ensemble_weights)
    print(
        json.dumps(
            {
                "train": len(train),
                "calibration": len(cal),
                "test": len(test),
                "best_log_loss": sorted(metrics, key=lambda row: row["log_loss"])[0],
                "best_public_pick": sorted(metrics, key=lambda row: (-row["public_pick_accuracy"], -row["public_coverage"]))[0],
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
