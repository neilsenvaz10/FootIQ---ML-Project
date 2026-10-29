#!/usr/bin/env python3
"""Build a frozen, pre-final audit of the 2026 World Cup model.

Group matches are scored on the best regulation-time 1/X/2 read. Knockout
matches are scored on the archived full-match advancement read. The final is
excluded, and any fixture without a genuine pre-kickoff prediction is retained
for coverage accounting but never enters an accuracy denominator.
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

VALIDATION_PATH = PROCESSED / "matchday_validation_v210.csv"
SCHEDULE_PATH = PROCESSED / "worldcup_2026_matches.csv"
STATIC_GROUP_PATH = PROCESSED / "model_v23_group_match_predictions.csv"
ADVANCEMENT_PATH = PROCESSED / "worldcup_knockout_advancement_predictions_frozen.csv"
KNOCKOUT_RESULTS_PATH = PROCESSED / "worldcup_2026_knockout_results_verified.csv"

AUDIT_PATH = PROCESSED / "worldcup_full_validation_fixture_audit_2026-07-19.csv"
SUMMARY_PATH = PROCESSED / "worldcup_full_validation_summary_2026-07-19.csv"
REPORT_PATH = OUTPUTS / "worldcup_full_validation_report_2026-07-19.md"

OUTCOME_DISPLAY = {
    "team1_win": "Team 1 win",
    "draw": "Draw",
    "team2_win": "Team 2 win",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def simple_team_key(value: str) -> str:
    aliases = {
        "unitedstates": "usa",
        "czechrepublic": "czechia",
        "turkey": "turkiye",
        "ivorycoast": "cotedivoire",
        "capeverde": "caboverde",
        "southkorea": "korearepublic",
    }
    key = re.sub(r"[^a-z0-9]", "", value.lower())
    return aliases.get(key, key)


def pair_key(team1: str, team2: str) -> str:
    return "|".join(sorted([simple_team_key(team1), simple_team_key(team2)]))


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def accuracy(correct: int, total: int) -> float | None:
    return correct / total if total else None


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def wilson_interval(correct: int, total: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if not total:
        return None, None
    observed = correct / total
    denominator = 1 + z * z / total
    center = (observed + z * z / (2 * total)) / denominator
    half_width = z * math.sqrt(observed * (1 - observed) / total + z * z / (4 * total * total)) / denominator
    return center - half_width, center + half_width


def result_team(row: dict[str, Any], result: str) -> str:
    if result == "team1_win":
        return str(row["team1"])
    if result == "team2_win":
        return str(row["team2"])
    if result == "draw":
        return "Draw"
    return ""


def metric_row(scope: str, selection: str, correct: int, total: int, coverage: str, definition: str) -> dict[str, Any]:
    low, high = wilson_interval(correct, total)
    return {
        "scope": scope,
        "selection": selection,
        "correct": correct,
        "scored": total,
        "accuracy_pct": round(100 * correct / total, 2) if total else "",
        "ci_low_pct": round(100 * low, 2) if low is not None else "",
        "ci_high_pct": round(100 * high, 2) if high is not None else "",
        "coverage": coverage,
        "definition": definition,
    }


def summarize(rows: Iterable[dict[str, Any]], key: str = "correct") -> tuple[int, int]:
    scored = [row for row in rows if isinstance(row.get(key), bool)]
    return sum(1 for row in scored if row[key]), len(scored)


def group_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validations = read_csv(VALIDATION_PATH)
    validation_by_pair = {pair_key(row["team1"], row["team2"]): row for row in validations}
    schedule = [row for row in read_csv(SCHEDULE_PATH) if int(row["fixture_id"]) <= 72]

    group_order: dict[str, int] = defaultdict(int)
    audit_rows: list[dict[str, Any]] = []
    scored_rows: list[dict[str, Any]] = []

    for fixture in sorted(schedule, key=lambda row: int(row["fixture_id"])):
        group_order[fixture["group"]] += 1
        team_match_number = (group_order[fixture["group"]] - 1) // 2 + 1
        validation = validation_by_pair.get(pair_key(fixture["team1"], fixture["team2"]))
        if not validation:
            raise RuntimeError(f"Missing group validation row for fixture {fixture['fixture_id']}")

        eligible = as_bool(validation.get("eligible_for_accuracy")) and as_bool(validation.get("is_final"))
        prediction = validation.get("v27_internal_ensemble_pick", "")
        actual = validation.get("actual_result", "")
        correct: bool | str = prediction == actual if eligible and prediction and actual else ""
        exclusion_reason = ""
        if not eligible:
            exclusion_reason = "No genuine pre-kickoff snapshot; archived row is a post-kickoff backfill."

        row = {
            "fixture_id": fixture["fixture_id"],
            "stage": "Group stage",
            "round": f"Team group match {team_match_number}",
            "date": fixture["date"],
            "team1": validation["team1"],
            "team2": validation["team2"],
            "confidence_gate": validation.get("v28_tier", ""),
            "scoring_target": "Regulation 1/X/2",
            "prediction": result_team(validation, prediction),
            "prediction_probability": validation.get("top_probability", ""),
            "actual": result_team(validation, actual),
            "eligible_pre_kickoff": str(eligible).lower(),
            "correct": str(correct).lower() if isinstance(correct, bool) else "",
            "prediction_timestamp_et": validation.get("snapshot_timestamp_et", ""),
            "prediction_source": "data/processed/worldcup_matchday_v29_snapshots.csv",
            "result_source": validation.get("provider_status_long", "API-Football fixture result"),
            "exclusion_reason": exclusion_reason,
        }
        audit_rows.append(row)

        if eligible:
            scored = {
                **validation,
                "fixture_id": int(fixture["fixture_id"]),
                "team_match_number": team_match_number,
                "correct": bool(correct),
            }
            scored_rows.append(scored)

    return audit_rows, scored_rows


def static_group_baseline() -> list[dict[str, Any]]:
    validations = [row for row in read_csv(VALIDATION_PATH) if row["date"] <= "2026-06-27"]
    validation_by_pair = {pair_key(row["team1"], row["team2"]): row for row in validations}
    rows = []
    for prediction in read_csv(STATIC_GROUP_PATH):
        validation = validation_by_pair.get(pair_key(prediction["team1"], prediction["team2"]))
        if not validation or not validation.get("actual_result"):
            raise RuntimeError(f"Missing actual result for static fixture {prediction['fixture_id']}")
        actual = validation["actual_result"]
        same_orientation = simple_team_key(prediction["team1"]) == simple_team_key(validation["team1"])
        if not same_orientation and actual == "team1_win":
            actual = "team2_win"
        elif not same_orientation and actual == "team2_win":
            actual = "team1_win"
        rows.append(
            {
                **prediction,
                "actual_result": actual,
                "correct": prediction["model_90min_pick"] == actual,
            }
        )
    return rows


def knockout_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    predictions = read_csv(ADVANCEMENT_PATH)
    results = {row["fixture_id"]: row for row in read_csv(KNOCKOUT_RESULTS_PATH)}
    audit_rows: list[dict[str, Any]] = []
    scored_rows: list[dict[str, Any]] = []

    for prediction in predictions:
        result = results.get(prediction["fixture_id"])
        if not result:
            raise RuntimeError(f"Missing verified knockout result for fixture {prediction['fixture_id']}")
        eligible = as_bool(prediction["eligible_pre_kickoff"]) and bool(prediction["predicted_qualifier"])
        correct: bool | str = prediction["predicted_qualifier"] == result["winner"] if eligible else ""
        probability = as_float(prediction["predicted_probability"])

        row = {
            "fixture_id": prediction["fixture_id"],
            "stage": "Knockout stage",
            "round": prediction["round"],
            "date": prediction["date"],
            "team1": prediction["team1"],
            "team2": prediction["team2"],
            "confidence_gate": prediction["confidence_gate"],
            "scoring_target": "Full-match advancement",
            "prediction": prediction["predicted_qualifier"],
            "prediction_probability": prediction["predicted_probability"],
            "actual": result["winner"],
            "eligible_pre_kickoff": str(eligible).lower(),
            "correct": str(correct).lower() if isinstance(correct, bool) else "",
            "prediction_timestamp_et": prediction["prediction_timestamp_et"],
            "prediction_source": prediction["prediction_source"],
            "result_source": result["verification_source"],
            "exclusion_reason": prediction["eligibility_note"] if not eligible else "",
        }
        audit_rows.append(row)

        if eligible and probability is not None:
            actual_probability = probability if correct else 1 - probability
            scored_rows.append(
                {
                    **prediction,
                    "actual_qualifier": result["winner"],
                    "correct": bool(correct),
                    "prediction_probability": probability,
                    "actual_probability": actual_probability,
                    "brier_score": 2 * (1 - actual_probability) ** 2,
                    "log_loss": -math.log(max(actual_probability, 1e-12)),
                    "probability_band": "50-55%" if probability < 0.55 else "55-65%" if probability < 0.65 else "65%+",
                }
            )

    return audit_rows, scored_rows


def grouped_accuracy(rows: list[dict[str, Any]], key: str, order: list[Any]) -> list[tuple[Any, int, int, float | None]]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    output = []
    for value in order:
        correct, total = summarize(grouped.get(value, []))
        output.append((value, correct, total, accuracy(correct, total)))
    return output


def markdown_accuracy_table(rows: list[tuple[Any, int, int, float | None]], first_header: str) -> list[str]:
    lines = [f"| {first_header} | Correct | Scored | Accuracy |", "|---|---:|---:|---:|"]
    for label, correct, total, value in rows:
        lines.append(f"| {label} | {correct} | {total} | {pct(value)} |")
    return lines


def build_report(
    group_rows: list[dict[str, Any]],
    knockout_rows: list[dict[str, Any]],
    static_group_rows: list[dict[str, Any]],
    summary: list[dict[str, Any]],
) -> str:
    group_correct, group_total = summarize(group_rows)
    knockout_correct, knockout_total = summarize(knockout_rows)
    combined_correct = group_correct + knockout_correct
    combined_total = group_total + knockout_total

    group_public = [row for row in group_rows if row["v28_tier"] != "Pass"]
    group_public_correct, group_public_total = summarize(group_public)
    static_group_correct, static_group_total = summarize(static_group_rows)
    group_tiers = grouped_accuracy(group_rows, "v28_tier", ["Strong Pick", "Model Lean", "Pass"])
    group_match_numbers = grouped_accuracy(group_rows, "team_match_number", [1, 2, 3])
    knockout_rounds = grouped_accuracy(
        knockout_rows,
        "round",
        ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Third place"],
    )
    knockout_tiers = grouped_accuracy(knockout_rows, "confidence_gate", ["Strong Pick", "Model Lean", "Pass"])
    knockout_bands = grouped_accuracy(knockout_rows, "probability_band", ["50-55%", "55-65%", "65%+"])

    combined_by_tier = []
    for tier in ["Strong Pick", "Model Lean", "Pass"]:
        group_subset = [row for row in group_rows if row["v28_tier"] == tier]
        knockout_subset = [row for row in knockout_rows if row["confidence_gate"] == tier]
        correct_a, total_a = summarize(group_subset)
        correct_b, total_b = summarize(knockout_subset)
        combined_by_tier.append((tier, correct_a + correct_b, total_a + total_b, accuracy(correct_a + correct_b, total_a + total_b)))

    actual_counts = Counter(row["actual_result"] for row in group_rows)
    prediction_counts = Counter(row["v27_internal_ensemble_pick"] for row in group_rows)
    outcome_rows = []
    for outcome in ["team1_win", "draw", "team2_win"]:
        subset = [row for row in group_rows if row["actual_result"] == outcome]
        correct, total = summarize(subset)
        outcome_rows.append((OUTCOME_DISPLAY[outcome], correct, total, accuracy(correct, total)))

    group_actual_probability = sum(float(row["actual_probability"]) for row in group_rows) / group_total
    group_brier = sum(float(row["brier_score"]) for row in group_rows) / group_total
    group_log_loss = sum(float(row["log_loss"]) for row in group_rows) / group_total
    knockout_actual_probability = sum(float(row["actual_probability"]) for row in knockout_rows) / knockout_total
    knockout_brier = sum(float(row["brier_score"]) for row in knockout_rows) / knockout_total
    knockout_log_loss = sum(float(row["log_loss"]) for row in knockout_rows) / knockout_total

    predicted_draws = [row for row in group_rows if row["v27_internal_ensemble_pick"] == "draw"]
    predicted_draw_correct, predicted_draw_total = summarize(predicted_draws)
    actual_draws = [row for row in group_rows if row["actual_result"] == "draw"]
    actual_draw_correct, actual_draw_total = summarize(actual_draws)

    misses = [row for row in knockout_rows if not row["correct"]]
    combined_low, combined_high = wilson_interval(combined_correct, combined_total)
    group_low, group_high = wilson_interval(group_correct, group_total)
    knockout_low, knockout_high = wilson_interval(knockout_correct, knockout_total)

    lines = [
        "# World Cup Model Full Validation - Pre-Final",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "The final is excluded by request. Group matches are graded on the best 90-minute 1/X/2 read. Knockout matches are graded only on the full-match qualifier or placement winner after extra time and penalties.",
        "",
        "## Executive Answer",
        "",
        "| Scope | Correct | Scored | Accuracy | 95% Wilson interval |",
        "|---|---:|---:|---:|---:|",
        f"| Entire pre-final product target | {combined_correct} | {combined_total} | {pct(accuracy(combined_correct, combined_total))} | {pct(combined_low)} to {pct(combined_high)} |",
        f"| Group-stage best 90-minute read | {group_correct} | {group_total} | {pct(accuracy(group_correct, group_total))} | {pct(group_low)} to {pct(group_high)} |",
        f"| Group-stage published calls only | {group_public_correct} | {group_public_total} | {pct(accuracy(group_public_correct, group_public_total))} | {pct(wilson_interval(group_public_correct, group_public_total)[0])} to {pct(wilson_interval(group_public_correct, group_public_total)[1])} |",
        f"| Knockout full-match advancement | {knockout_correct} | {knockout_total} | {pct(accuracy(knockout_correct, knockout_total))} | {pct(knockout_low)} to {pct(knockout_high)} |",
        "",
        f"Bottom line: the honest combined record is **{combined_correct}/{combined_total} ({pct(accuracy(combined_correct, combined_total))})**. This is a hybrid product metric, not a claim that the model picked {combined_correct} regulation winners. The target changes from 90-minute result in groups to full-match advancement in knockouts.",
        "",
        "## Coverage And Integrity",
        "",
        "- Completed fixtures before the final: 103 (72 group matches and 31 knockout/placement matches).",
        f"- Genuine pre-kickoff predictions scored: {combined_total}/103 ({pct(combined_total / 103)}).",
        "- Excluded: 20 group fixtures whose local rows were collected after kickoff, plus South Africa-Canada in the Round of 32, which had no archived pre-kickoff advancement call.",
        "- Excluded rows remain in the fixture audit for transparency but do not enter any accuracy denominator.",
        "- The final is not included anywhere in this report.",
        "",
        "### Literal 72/72 Group Baseline",
        "",
        f"The static v2.3 group sheet was frozen on 4 June, before the tournament, and covered every group fixture. It scored **{static_group_correct}/{static_group_total} ({pct(accuracy(static_group_correct, static_group_total))})**. This is useful as a full-coverage baseline, but it is not mixed into the primary live-model total because it predates the v2.6-v2.9 ensemble, weather, lineup, and confidence-gate pipeline.",
        "",
        "## Group Stage",
        "",
        f"Best-read accuracy across every honestly frozen group prediction: **{group_correct}/{group_total} ({pct(accuracy(group_correct, group_total))})**.",
        "",
        "### Confidence Gate",
        "",
        *markdown_accuracy_table(group_tiers, "Gate attached to fixture"),
        "",
        f"The published slate was Strong Pick plus Model Lean: **{group_public_correct}/{group_public_total} ({pct(accuracy(group_public_correct, group_public_total))})**. Pass rows were not public picks; their internal reads are shown only to test whether the gate separated clean situations from uncertain ones.",
        "",
        "### By Each Team's Group Match Number",
        "",
        *markdown_accuracy_table(group_match_numbers, "Team match number"),
        "",
        "The first-match number is weak and incomplete: only 14/24 opening fixtures had valid pre-kickoff snapshots. All 24 final group fixtures were captured, which is why the later sample is operationally cleaner.",
        "",
        "### By Actual Outcome",
        "",
        *markdown_accuracy_table(outcome_rows, "Actual regulation outcome"),
        "",
        f"Draws were the main failure mode. The model called {prediction_counts['draw']} draws and got {predicted_draw_correct} right (precision {pct(accuracy(predicted_draw_correct, predicted_draw_total))}), while {actual_counts['draw']} matches actually drew and only {actual_draw_correct} were caught (recall {pct(accuracy(actual_draw_correct, actual_draw_total))}).",
        "",
        "### Probability Quality",
        "",
        f"- Mean probability assigned to the actual 1/X/2 result: {pct(group_actual_probability)}.",
        f"- Three-class Brier score: {group_brier:.4f} (lower is better; uniform probabilities score 0.6667).",
        f"- Log loss: {group_log_loss:.4f} (lower is better; uniform probabilities score 1.0986).",
        "",
        "## Knockout Stage",
        "",
        f"Full-match advancement accuracy: **{knockout_correct}/{knockout_total} ({pct(accuracy(knockout_correct, knockout_total))})**. This is the model's clearest positive result, but 30 calls still produce a wide confidence interval.",
        "",
        "### By Round",
        "",
        *markdown_accuracy_table(knockout_rounds, "Round"),
        "",
        "### By Attached Regulation Gate",
        "",
        *markdown_accuracy_table(knockout_tiers, "Gate attached to fixture"),
        "",
        "The gate was designed for 90-minute publishing, not for advancement. This table is diagnostic: a Pass can still have a useful full-match qualifier because extra time and penalties remove the draw outcome.",
        "",
        "### By Advancement Probability",
        "",
        *markdown_accuracy_table(knockout_bands, "Predicted qualifier probability"),
        "",
        f"- Mean probability assigned to the actual qualifier: {pct(knockout_actual_probability)}.",
        f"- Binary two-class Brier score: {knockout_brier:.4f} (a flat 50/50 forecast scores 0.5000).",
        f"- Log loss: {knockout_log_loss:.4f} (a flat 50/50 forecast scores 0.6931).",
        "",
        "### Advancement Misses",
        "",
        "| Match | Round | Model qualifier | Model probability | Actual qualifier |",
        "|---|---|---|---:|---|",
    ]
    for row in misses:
        lines.append(
            f"| {row['team1']} v {row['team2']} | {row['round']} | {row['predicted_qualifier']} | {pct(float(row['prediction_probability']))} | {row['actual_qualifier']} |"
        )

    lines.extend(
        [
            "",
            "## Combined Gate View",
            "",
            *markdown_accuracy_table(combined_by_tier, "Gate attached to fixture"),
            "",
            "This combines different targets, so it is useful for product monitoring but not for scientific comparison between gates.",
            "",
            "## France-England Postmortem",
            "",
            "- Official scorecard: wrong. The 90-minute read was Draw, the full-match bronze pick was France, and England won 6-4 in regulation.",
            "- The final pre-kickoff regulation distribution was France 32.80%, Draw 39.38%, England 27.82%. The lineup-adjusted full-match distribution was France 58.83%, England 41.17%.",
            "- That means England winning was an upset, not an impossible outcome. The model still has to take the loss; missed chances cannot be used to relabel it as correct.",
            "- The user-reported Olise big chances are relevant to process quality, but they need event-level xG or post-shot xG before they can support a formal claim that the read was unlucky rather than structurally wrong.",
            "- The larger warning is total-goal calibration. The base model expected about 2.12 total goals (1.128 plus 0.994), while the match produced 10. The third-place context, rotated defenders, open tactics, and game-state feedback created far more variance than the model allowed.",
            "",
            "## What This World Cup Says About The Model",
            "",
            "1. **Advancement is the strongest product.** The knockout engine went 25/30 and handled extra time/penalty paths much better than regulation outcome calls alone.",
            "2. **Model Lean is the most useful current gate.** It returned 18/26 in groups and 9/10 on attached knockout advancement calls. Strong Pick was only 1/3 in the group stage and is not validated by that tiny sample.",
            "3. **Draw calibration needs work.** The model caught only 5 of 16 genuine group-stage draws. This is the clearest repeatable technical weakness.",
            "4. **Pass is sensible but not sharply separated.** Pass-row internal group reads were 15/23 versus 18/26 for Model Lean. The gate reduced overstatement, but it has not yet created a huge accuracy gap.",
            "5. **Late tournament probabilities were directionally useful but volatile.** The model was perfect in the quarterfinals, split the semifinals, and missed the third-place game. That is promising, not proof of an 83% true future hit rate.",
            "6. **Operational capture improved during the tournament.** The model stored every third group fixture before kickoff, but missed the honest freeze on 20 earlier group matches. A production model cannot leave that coverage gap.",
            "",
            "## Business Verdict",
            "",
            "This is a credible research-stage model with a promising knockout-advancement product. It is not yet ready for a commercial accuracy claim. The combined 71.95% is real under the stated scoring rule, but it covers 82 of 103 pre-final fixtures, mixes two targets, has no closing-market benchmark, and has wide statistical uncertainty.",
            "",
            "The defensible external wording is: **'On 82 frozen pre-kickoff World Cup calls, the model recorded 65.38% group-stage 90-minute accuracy and 83.33% knockout advancement accuracy; the final was excluded.'**",
            "",
            "## Recommended Changes",
            "",
            "1. Freeze an automated T-75 prediction for every fixture, then a separate T-10 lineup update. Never overwrite either snapshot.",
            "2. Rebuild the draw layer as its own calibrated classifier and test it against low-xG, low-margin, and heat/tempo regimes.",
            "3. Suspend the Strong Pick label or raise its evidence requirement until it has at least 100 genuinely frozen calls with calibration evidence.",
            "4. Add a third-place/open-knockout variance regime so rotation and low defensive incentives affect total-goal variance, not just average team strength.",
            "5. Add event xG, big-chance, shot-location, and post-shot xG data for process reviews. That is how Olise-type misses can be measured rather than argued from memory.",
            "6. Benchmark every call against Elo-only and no-vig closing market probabilities. Accuracy without those baselines does not establish a sellable edge.",
            "",
            "## Audit Files",
            "",
            f"- Fixture-level audit: `{AUDIT_PATH.relative_to(ROOT)}`",
            f"- Summary metrics: `{SUMMARY_PATH.relative_to(ROOT)}`",
            f"- Frozen knockout call ledger: `{ADVANCEMENT_PATH.relative_to(ROOT)}`",
            f"- Group validation source: `{VALIDATION_PATH.relative_to(ROOT)}`",
            f"- Static 72-game baseline: `{STATIC_GROUP_PATH.relative_to(ROOT)}`",
            f"- Verified knockout results: `{KNOCKOUT_RESULTS_PATH.relative_to(ROOT)}`",
            "- Official result cross-check: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    group_audit_rows, group_rows = group_audit()
    knockout_audit_rows, knockout_rows = knockout_audit()
    static_group_rows = static_group_baseline()

    group_correct, group_total = summarize(group_rows)
    group_public = [row for row in group_rows if row["v28_tier"] != "Pass"]
    group_public_correct, group_public_total = summarize(group_public)
    static_group_correct, static_group_total = summarize(static_group_rows)
    knockout_correct, knockout_total = summarize(knockout_rows)
    combined_correct = group_correct + knockout_correct
    combined_total = group_total + knockout_total

    summary = [
        metric_row(
            "Entire pre-final tournament",
            "Hybrid product target",
            combined_correct,
            combined_total,
            f"{combined_total}/103",
            "Group 90-minute best reads plus knockout full-match advancement calls.",
        ),
        metric_row(
            "Group stage",
            "Best 90-minute read",
            group_correct,
            group_total,
            f"{group_total}/72",
            "Internal top 1/X/2 outcome regardless of confidence gate.",
        ),
        metric_row(
            "Group stage",
            "Published Strong Pick + Model Lean",
            group_public_correct,
            group_public_total,
            f"{group_public_total}/{group_total} genuine group calls",
            "Pass rows excluded from the public-pick denominator.",
        ),
        metric_row(
            "Group stage static v2.3",
            "Pre-tournament best 90-minute read",
            static_group_correct,
            static_group_total,
            f"{static_group_total}/72",
            "Full-coverage June 4 baseline; excluded from the live-model combined metric.",
        ),
        metric_row(
            "Knockout stage",
            "Full-match advancement",
            knockout_correct,
            knockout_total,
            f"{knockout_total}/31",
            "Qualifier or placement winner after extra time and penalties; final excluded.",
        ),
    ]

    audit_fieldnames = [
        "fixture_id",
        "stage",
        "round",
        "date",
        "team1",
        "team2",
        "confidence_gate",
        "scoring_target",
        "prediction",
        "prediction_probability",
        "actual",
        "eligible_pre_kickoff",
        "correct",
        "prediction_timestamp_et",
        "prediction_source",
        "result_source",
        "exclusion_reason",
    ]
    audit_rows = sorted(group_audit_rows + knockout_audit_rows, key=lambda row: int(row["fixture_id"]))
    write_csv(AUDIT_PATH, audit_rows, audit_fieldnames)
    write_csv(
        SUMMARY_PATH,
        summary,
        ["scope", "selection", "correct", "scored", "accuracy_pct", "ci_low_pct", "ci_high_pct", "coverage", "definition"],
    )
    REPORT_PATH.write_text(build_report(group_rows, knockout_rows, static_group_rows, summary), encoding="utf-8")

    print(f"group_best_read={group_correct}/{group_total} ({pct(accuracy(group_correct, group_total))})")
    print(f"group_published={group_public_correct}/{group_public_total} ({pct(accuracy(group_public_correct, group_public_total))})")
    print(f"knockout_advancement={knockout_correct}/{knockout_total} ({pct(accuracy(knockout_correct, knockout_total))})")
    print(f"combined={combined_correct}/{combined_total} ({pct(accuracy(combined_correct, combined_total))})")
    print(f"report={REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
