"""Model performance summary, read from the evaluation files already in the repository. Nothing is recomputed or retrained here.

Every figure below comes from one of the files listed in `sources`. These results were inspected during development, so they are
historical evidence, not independent validation of future matches.
"""
import csv
import re
from functools import lru_cache

import config as C

R = C.ROOT
V1 = R / "FootIQ_Club_Model_Baseline_v1"
V2 = R / "FootIQ_Club_Model_Development_v2"
SOURCES = [
    "FootIQ_Club_Model_Baseline_v1/04_TEST_METRICS.csv",
    "FootIQ_Club_Model_Baseline_v1/05_FORWARD_HOLDOUT_METRICS.csv",
    "FootIQ_Club_Model_Baseline_v1/06a_LEAGUE_WISE_METRICS.csv",
    "FootIQ_Club_Model_Development_v2/08_LEAGUE_GROUP_PERFORMANCE.csv",
    "FootIQ_Club_Model_Development_v2/12_FINAL_V2_DEVELOPMENT_REPORT.md",
]
LEAGUES = {"EPL": "england:1-premierleague", "LALIGA": "espana:1-liga", "BUNDESLIGA": "deutschland:1-bundesliga", "SERIEA": "italy:1-seriea", "LIGUE1": "europe/france:fr1"}
MODEL_NAMES = {"always_home": "Always predict a home win", "elo_ordered_logit": "Elo-only mapping", "multinomial_logreg": "Club v1 (logistic regression)"}


def _rows(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _f(x):
    return float(x)


def _metric(r):
    return dict(n=int(r["n"]), accuracy=_f(r["accuracy"]), log_loss=_f(r["log_loss"]), brier=_f(r["brier"]), macro_f1=_f(r["macro_f1"]))


def _club_v1():
    def block(rows, name, period):
        sel = [r for r in rows if r["set"] == name]
        return dict(period=period, n=int(sel[0]["n"]), models=[dict(model=r["model"], label=MODEL_NAMES[r["model"]], **_metric(r)) for r in sel])

    test = _rows(V1 / "04_TEST_METRICS.csv")
    hold = _rows(V1 / "05_FORWARD_HOLDOUT_METRICS.csv")
    per = _rows(V1 / "06a_LEAGUE_WISE_METRICS.csv")
    leagues = []
    for key, cid in LEAGUES.items():
        entry = dict(key=key, competition=C.BY_KEY[key]["name"])
        for label, setname in (("test", "test_primary"), ("forward_holdout", "forward_holdout_primary")):
            by = {r["model"]: r for r in per if r["set"] == setname and r["competition_id"] == cid}
            entry[label] = dict(n=int(by["multinomial_logreg"]["n"]), accuracy=_f(by["multinomial_logreg"]["accuracy"]), log_loss=_f(by["multinomial_logreg"]["log_loss"]),
                                always_home_log_loss=_f(by["always_home"]["log_loss"]))
        leagues.append(entry)
    return dict(
        role="Primary club predictor (domestic leagues)", status="Validated on domestic leagues",
        evaluation=[block(test, "test_primary", "Test season 2024-07-01 to 2025-06-30"), block(hold, "forward_holdout_primary", "Forward holdout 2025-07-01 to 2026-09-30")],
        per_league=leagues,
        notes=["All domestic leagues pooled (about 100 competitions); the per-league rows below are the five leagues in this project.",
               "Log loss is the main score (lower is better). Accuracy about 50% on three outcomes is typical; the model almost never predicts a draw."])


def _club_v2():
    row = next(r for r in _rows(V2 / "08_LEAGUE_GROUP_PERFORMANCE.csv") if r["group"] == "all")
    return dict(
        role="Candidate shown beside v1", status="Development-validated only (no unbiased evaluation)",
        development=dict(period="3 chronological folds, 2021-22 to 2023-24", n=int(row["n"]), accuracy=_f(row["acc_v2LR"]), log_loss_v2=_f(row["logloss_v2_LR_full"]),
                         log_loss_v1_lr=_f(row["logloss_v1_LR_25"]), log_loss_v1_elo=_f(row["logloss_v1_Elo_mapping"]), delta_vs_v1_lr=_f(row["delta_v2LR_vs_v1LR"])),
        notes=["The gain over v1 is small (about 0.003 log loss) and was measured on the same folds used to choose features and hyperparameters.",
               "The final v2-r1 model was refit on data that includes v1's earlier test and forward-holdout periods, so no unbiased test of it exists.",
               "Prospective (future-match) evaluation was planned but is out of scope for this project."])


# _international() and _worldcup() describe archived competitions (kept, not used by summary())
def _international():
    text = (R / "outputs" / "model_v26_bakeoff_report.md").read_text(encoding="utf-8")
    split = {k: int(v) for k, v in re.findall(r"- (Train|Calibration|Test): [\d-]+ through [\d-]+ \((\d+) matches\)", text)}
    models = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 8 and cells[0] in ("ensemble", "ensemble_logistic_consensus_gate", "elo_formula", "gradient_boosting", "logistic_regression"):
            models[cells[0]] = dict(log_loss=_f(cells[1]), brier=_f(cells[2]), accuracy=_f(cells[3]), ece=_f(cells[4]), public_coverage=_f(cells[5]), public_pick_accuracy=_f(cells[6]))
    labels = {"ensemble": "v2.7 ensemble (used by the app)", "elo_formula": "Elo formula only", "gradient_boosting": "Gradient boosting", "logistic_regression": "Logistic regression"}
    return dict(
        role="International predictor (Nations League, Copa America, World Cup single matches)", status="Validated on pooled internationals; no competition-specific figure",
        split=dict(train_matches=split["Train"], calibration_matches=split["Calibration"], test_matches=split["Test"], test_period="2023-01-01 to 2026 (chronological)"),
        models=[dict(model=k, label=v, **models[k]) for k, v in labels.items() if k in models],
        gate=dict(label="Confidence gate (only confident picks)", **models["ensemble_logistic_consensus_gate"]),
        notes=["Test set pools all international matches, friendlies included; it is not specific to the Nations League or Copa America.",
               "The gate declines to call uncertain matches, so its accuracy applies only to the share of matches in 'public_coverage'."])


def _worldcup():
    rows = _rows(R / "data" / "processed" / "worldcup_full_validation_summary_2026-07-19.csv")
    keep = {"Group stage": "Group stage, best 90-minute read", "Knockout stage": "Knockout stage, advancement calls", "Entire pre-final tournament": "Whole tournament (before the final)"}
    out = [dict(scope=keep[r["scope"]], correct=int(r["correct"]), scored=int(r["scored"]), accuracy_pct=_f(r["accuracy_pct"]), ci_low_pct=_f(r["ci_low_pct"]), ci_high_pct=_f(r["ci_high_pct"]))
           for r in rows if r["scope"] in keep and r["selection"] in ("Best 90-minute read", "Full-match advancement", "Hybrid product target")]
    return dict(role="Tournament simulator and World Cup match reads", status="Validated against the 2026 tournament (small sample)", results=out,
                notes=["Only 30 knockout matches and 52 group matches were scored, so the confidence intervals are wide.", "The final is not included."])


@lru_cache(maxsize=1)
def summary() -> dict:
    return dict(
        club_v1=_club_v1(), club_v2_r1=_club_v2(),
        uefa_club=dict(status="Not validated", note="The club models were evaluated on domestic leagues only; no accuracy figure exists for the Champions League."),
        caveats=["Historical evaluation: these results were inspected during development and are not new independent evidence.",
                 "Later models (club v2-r1) were trained on periods that earlier models used as test data.",
                 "Probabilities are estimates; football outcomes are uncertain."],
        sources=SOURCES)
