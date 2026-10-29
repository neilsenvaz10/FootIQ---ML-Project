"""B4: write reports and the reproducibility manifest from the saved evaluation tables (no model is re-fitted or re-evaluated)."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
T = pd.read_pickle(os.path.join(OUT, "_eval_tables.pkl"))
M, PC, CF, CAL, ECE, LG, LGR, CV, HD, BOOT = (T[k] for k in ("M", "PC", "CF", "CAL", "ECE", "LG", "LGR", "CV", "HD", "BOOT"))
frozen = json.load(open(os.path.join(ART, "FROZEN.json")))
pre = json.load(open(os.path.join(OUT, "_pretraining_checks.json")))
prep = json.load(open(os.path.join(ART, "preprocessing_train_fitted.json")))
basep = json.load(open(os.path.join(ART, "baseline_parameters.json")))
cov = json.load(open(os.path.join(ART, "coverage_categories.json")))
grid = pd.read_csv(os.path.join(OUT, "03b_VALIDATION_C_GRID.csv"))
lock = json.load(open(os.path.join(OUT, "EVALUATION_LOCK.json")))
coef = json.load(open(os.path.join(ART, "multinomial_logreg_coefficients.json")))
NOW = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
MODELS = ["always_home", "elo_ordered_logit", "multinomial_logreg"]


def tbl(df, cols=None, fmt=4):
    if cols:
        df = df[cols]
    c = list(df.columns)
    out = ["| " + " | ".join(map(str, c)) + " |", "|" + "|".join("---" for _ in c) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(("" if (isinstance(v, float) and np.isnan(v)) else (f"{v:.{fmt}f}" if isinstance(v, float) else str(v))) for v in r) + " |")
    return "\n".join(out)


def W(n, t):
    open(os.path.join(OUT, n), "w", encoding="utf-8").write(t)


def mt(s):
    d = M[M.set == s].set_index("model")
    return d


ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC, usecols=["split"])
cnt = ds.split.value_counts().to_dict()
dsh, fsh = pre["dataset_sha256"], pre["feature_file_sha256"]

# ================================================================= 01 execution report
W("01_TRAINING_EXECUTION_REPORT.md", f"""# 01 Training execution report - FootIQ club baseline v1 (generated {NOW})

## 1. Protocol (fixed before any metric was computed)
1. `_scripts/b1_pretraining_checks.py` - mandatory verification (stop on failure).
2. `_scripts/b2_fit_select_freeze.py` - fit on **train**, select on **validation primary rows**, freeze artifacts. Test and forward-holdout labels are masked in this script (set to NaN right after loading) and were not read for any decision.
3. `_scripts/b3_locked_evaluation.py` - loads the frozen artifacts (SHA-256 re-verified), creates `EVALUATION_LOCK.json` and evaluates test and forward holdout **once**; it refuses to run again.
4. `_scripts/b4_reports.py` - writes the reports from saved tables.
No model, setting or rule was changed after step 3.

## 2. Pre-training verification ({sum(c['passed'] for c in pre['checks'])}/{len(pre['checks'])} checks passed)
{tbl(pd.DataFrame(pre['checks'])[['check', 'passed', 'detail']].assign(detail=lambda d: d.detail.str.slice(0, 110)))}

## 3. Data
* Dataset v1.1 `01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv` SHA-256 `{dsh}`; feature file SHA-256 `{fsh}`.
* Eligible matches {sum(cnt.values()):,}: train {cnt['train']:,}, validation {cnt['validation']:,}, test {cnt['test']:,}, forward holdout {cnt['forward_holdout']:,}.
* **Exact training sample: {frozen['train_rows']:,} matches** (2018-08-01 to 2023-06-30, domestic leagues only; no cup, continental or international record).
* Evaluation sets: validation primary {frozen['validation_primary_rows']:,}; test primary {int(M[(M.set=='test_primary')].n.iloc[0]):,}; forward-holdout primary {int(M[(M.set=='forward_holdout_primary')].n.iloc[0]):,}; calendar-year leagues are secondary sets reported separately (test {int(M[(M.set=='test_secondary_calendar_year')].n.iloc[0]):,}; holdout {int(M[(M.set=='forward_holdout_secondary_calendar_year')].n.iloc[0]):,}).
* Features (25, contract order): {', '.join(prep['feature_order'])}.

## 4. Preprocessing (fitted on train only, `artifacts/preprocessing_train_fitted.json`)
Median imputation (train medians) with missing indicators for {prep['indicator_columns']}; standardisation with train mean and standard deviation (population std). No target encoding, no categorical features, no scaling of the label. Recomputation of the statistics from the train rows reproduced them exactly.

## 5. Models
| model | specification |
|---|---|
| Always-home | predicts H for every match; its probabilities are the train class frequencies {basep['always_home_class_priors']} (needed for log loss / Brier) |
| Elo ordered logit | one parameter set mapping `elo_diff` to H/D/A: scale {basep['elo_ordered_logit']['scale_per_100_elo']:.4f} per 100 Elo, thresholds {basep['elo_ordered_logit']['threshold_away_draw']:.4f} and {basep['elo_ordered_logit']['threshold_draw_home']:.4f}; fitted by maximum likelihood on train (L-BFGS-B, converged: {basep['elo_ordered_logit']['converged']}) |
| Multinomial logistic regression | scikit-learn {frozen['dependency_versions']['scikit-learn']}, `LogisticRegression(penalty=l2, solver=lbfgs, max_iter=3000, random_state={SEED})`, 27 inputs (25 standardised features + 2 missing indicators); C selected on validation |

C grid on validation primary rows (log loss is the selection criterion):
{tbl(grid)}

Selected C = {frozen['selected_C']:g}. Log loss differs by less than 1e-6 for C >= 1 (the L2 penalty is no longer active), so the choice among these values is immaterial; the tie-break picked the numerically lowest loss.
Best model on validation primary log loss: **{frozen['selected_model_by_validation_primary_log_loss']}**.

## 6. Freeze record
Frozen at {frozen['frozen_at']}; evaluation executed once between {lock['started']} and {lock.get('finished', '?')}. Artifact SHA-256 values are in `10_REPRODUCIBILITY_MANIFEST.json`.

## 7. Dependencies and seeds
{frozen['dependency_versions']}; seed {SEED} (numpy seed, `random_state`, bootstrap generator). Training is deterministic (lbfgs, no sampling).
""")

# ================================================================= 02 comparison
pieces = []
for s in ["validation_primary", "test_primary", "forward_holdout_primary", "test_secondary_calendar_year", "forward_holdout_secondary_calendar_year"]:
    d = M[M.set == s].copy()
    d.insert(0, "evaluation_set", d.pop("set"))
    pieces.append(d)
allm = pd.concat(pieces)
bootm = BOOT.copy()
tp, hp = mt("test_primary"), mt("forward_holdout_primary")
W("02_MODEL_COMPARISON_REPORT.md", f"""# 02 Model comparison report (generated {NOW})

Lower log loss / Brier is better; higher accuracy / macro F1 is better. Primary sets are complete split-year league-seasons without identity flags (existing split manifest). Chance level for a 3-class problem: log loss 1.0986, Brier 0.6667.

{tbl(allm[['evaluation_set', 'model', 'n', 'accuracy', 'macro_f1', 'log_loss', 'brier']])}

## Decision made on validation only
Validation primary log loss: {', '.join(f"{m} {mt('validation_primary').loc[m, 'log_loss']:.4f}" for m in MODELS)}. The multinomial logistic regression was selected before test and holdout were evaluated.

## What the locked evaluation shows
* **Test (2024-25), primary:** logistic regression log loss {tp.loc['multinomial_logreg', 'log_loss']:.4f} vs Elo {tp.loc['elo_ordered_logit', 'log_loss']:.4f} vs always-home {tp.loc['always_home', 'log_loss']:.4f}; accuracy {tp.loc['multinomial_logreg', 'accuracy']:.3f} / {tp.loc['elo_ordered_logit', 'accuracy']:.3f} / {tp.loc['always_home', 'accuracy']:.3f}.
* **Forward holdout (2025-26 and early 2026-27), primary:** {hp.loc['multinomial_logreg', 'log_loss']:.4f} / {hp.loc['elo_ordered_logit', 'log_loss']:.4f} / {hp.loc['always_home', 'log_loss']:.4f}; accuracy {hp.loc['multinomial_logreg', 'accuracy']:.3f} / {hp.loc['elo_ordered_logit', 'accuracy']:.3f} / {hp.loc['always_home', 'accuracy']:.3f}. In accuracy and macro F1 the Elo mapping is on par with or ahead of the logistic regression on the holdout, while the logistic regression keeps a slightly lower log loss and Brier score.
* Both learned models beat always-home by a wide margin in log loss (about 0.064-0.069 nats). The logistic regression improves on the single-feature Elo mapping by only about 0.002-0.004 nats: the 22 extra features add very little beyond `elo_diff`.

Paired bootstrap of per-match log-loss differences (2,000 resamples, seed {SEED}; negative favours the first model):
{tbl(bootm, ['set', 'comparison', 'mean_difference', 'ci95_low', 'ci95_high', 'n'], fmt=5)}

The interval for logistic regression vs Elo excludes zero in the primary test and holdout sets, but the effect is tiny (0.2-0.4% of the loss). No claim of a practically relevant gain over a calibrated Elo rating is justified.

## Honest assessment
* All three models, including the best, stay close to the probability that bookmaker-free data allows: accuracy about 50% with draws essentially never predicted (see file 07).
* The results are robust across validation, test and holdout (always-home is clearly the worst model and the logistic regression has the lowest log loss in all three), and the holdout did not collapse: no sign of temporal leakage or overfitting to validation.
""")

# ================================================================= 03/04/05 are CSVs. 06 league report
sel = LG[LG.model == "multinomial_logreg"].merge(LG[LG.model == "elo_ordered_logit"][["set", "competition_id", "log_loss"]], on=["set", "competition_id"], suffixes=("", "_elo")).merge(
    LG[LG.model == "always_home"][["set", "competition_id", "log_loss"]].rename(columns={"log_loss": "log_loss_home"}), on=["set", "competition_id"])
sel["delta_vs_elo"] = sel.log_loss - sel.log_loss_elo
sel["delta_vs_always_home"] = sel.log_loss - sel.log_loss_home
sel = sel.rename(columns={"log_loss": "log_loss_logreg"})
sel.to_csv(os.path.join(OUT, "06c_LEAGUE_WISE_LOGREG_VS_BASELINES.csv"), index=False)
lt = sel[sel.set == "test_primary"].sort_values("log_loss_logreg")
lh = sel[sel.set == "forward_holdout_primary"].sort_values("log_loss_logreg")
g = LGR.pivot_table(index=["set", "league_group"], columns="model", values=["n", "accuracy", "log_loss", "brier"], aggfunc="first")
g.columns = [f"{a}_{b}" for a, b in g.columns]
g = g.reset_index()
gt = g[g.set.isin(["test_primary", "forward_holdout_primary"])][["set", "league_group", "n_multinomial_logreg", "accuracy_always_home", "accuracy_elo_ordered_logit", "accuracy_multinomial_logreg",
                                                                    "log_loss_always_home", "log_loss_elo_ordered_logit", "log_loss_multinomial_logreg"]]
gs = g[g.set.isin(["test_secondary_calendar_year", "forward_holdout_secondary_calendar_year"])][["set", "league_group", "n_multinomial_logreg", "accuracy_always_home", "accuracy_elo_ordered_logit", "accuracy_multinomial_logreg",
                                                                                                  "log_loss_always_home", "log_loss_elo_ordered_logit", "log_loss_multinomial_logreg"]]
cols6 = ["competition_id", "n", "accuracy", "log_loss_logreg", "log_loss_elo", "log_loss_home", "delta_vs_elo"]
W("06_LEAGUE_WISE_PERFORMANCE_REPORT.md", f"""# 06 League-wise performance report (generated {NOW})

Groups were fixed a priori from the competition id and tier: G1 top-5 European leagues; G2 other European tier-1; G3 European tier-2; G4 European tier-3 and below; G5 non-European leagues. Calendar-year leagues are reported separately (secondary sets). Full tables: `06a_LEAGUE_WISE_METRICS.csv`, `06b_LEAGUE_GROUP_METRICS.csv`, `06c_LEAGUE_WISE_LOGREG_VS_BASELINES.csv`.

## League groups, primary sets (split-year leagues)
{tbl(gt)}

## Calendar-year leagues (secondary sets, never pooled with the primary metric)
{tbl(gs)}

## Leagues with at least 100 evaluated matches - logistic regression, test primary, ordered by log loss
{tbl(lt, cols6)}

## Same, forward holdout primary
{tbl(lh, cols6)}

## Reading the tables
* Predictability falls with tier: the top-5 and other tier-1 leagues have log loss about 0.98-1.00, tier-2 about 1.05-1.06, lower tiers up to 1.06; the non-European and calendar-year leagues sit in between.
* Per-league samples of 100-400 matches carry large sampling error (a log-loss standard error of about 0.02-0.04); differences of a few hundredths between leagues are not significant.
* The logistic regression and the Elo mapping are almost indistinguishable in every group; the largest advantage of the logistic regression appears in non-European leagues on the holdout.
""")

# ================================================================= 07 calibration and confusion
cm_t = CF[(CF.set == "test_primary") & (CF.model == "multinomial_logreg")].pivot(index="true", columns="predicted", values="count").reindex(index=CLASSES, columns=CLASSES)
cm_h = CF[(CF.set == "forward_holdout_primary") & (CF.model == "multinomial_logreg")].pivot(index="true", columns="predicted", values="count").reindex(index=CLASSES, columns=CLASSES)
cm_e = CF[(CF.set == "test_primary") & (CF.model == "elo_ordered_logit")].pivot(index="true", columns="predicted", values="count").reindex(index=CLASSES, columns=CLASSES)
calt = CAL[(CAL.set == "test_primary") & (CAL.model == "multinomial_logreg")]
ece_t = ECE[ECE.set.isin(["validation_primary", "test_primary", "forward_holdout_primary", "test_secondary_calendar_year", "forward_holdout_secondary_calendar_year"]) & (ECE.model != "always_home")]
pc_t = PC[PC.model.isin(["multinomial_logreg", "elo_ordered_logit"]) & PC.set.isin(["test_primary", "forward_holdout_primary"])]
W("07_CALIBRATION_AND_CONFUSION_ANALYSIS.md", f"""# 07 Calibration and confusion-matrix analysis (generated {NOW})

Tables: `07a_PER_CLASS_PERFORMANCE.csv`, `07b_CONFUSION_MATRICES.csv`, `07c_CALIBRATION_BINS.csv`, `07d_CALIBRATION_ECE.csv`. Class order H, D, A.

## Confusion matrices (rows = truth, columns = prediction), test primary
Logistic regression:
{tbl(cm_t.reset_index().rename(columns={'true': 'true \\ predicted'}))}

Elo ordered logit:
{tbl(cm_e.reset_index().rename(columns={'true': 'true \\ predicted'}))}

Forward holdout primary, logistic regression:
{tbl(cm_h.reset_index().rename(columns={'true': 'true \\ predicted'}))}

## Class-specific performance (test and holdout primary)
{tbl(pc_t[['set', 'model', 'cls', 'support', 'predicted_count', 'precision', 'recall', 'f1', 'mean_predicted_prob', 'observed_rate']])}

**The draw class is essentially never predicted** (a few matches out of thousands): the draw probability stays near 0.26 for almost every match because no feature separates draws; the F1 of the draw class is about 0.00-0.01. Away wins are recognised moderately (F1 about 0.45-0.48), home wins well (F1 about 0.63, helped by over-predicting H).

## Calibration
Expected calibration error (10 equal-width bins; per class, and top-label confidence):
{tbl(ece_t, ['set', 'model', 'cls', 'ece'], fmt=4)}

Reliability bins for the logistic regression on test primary (full set in `07c_CALIBRATION_BINS.csv`):
{tbl(calt[calt.cls == 'H'][['cls', 'bin', 'n', 'mean_predicted', 'observed_frequency']])}

{tbl(calt[calt.cls == 'D'][['cls', 'bin', 'n', 'mean_predicted', 'observed_frequency']])}

{tbl(calt[calt.cls == 'A'][['cls', 'bin', 'n', 'mean_predicted', 'observed_frequency']])}

Assessment: class-wise ECE is 0.003-0.014 on the test set and 0.011-0.021 on the holdout - good for a model of this simplicity; the mean predicted probability of each class matches the observed rate within about 1 percentage point on the test set. The holdout draw rate (27.5%) was above the mean predicted draw probability (25.9%) and away wins were slightly over-predicted (30.2% vs 28.7%), which shows ordinary season-to-season variation rather than miscalibration of a single model (the Elo mapping shows the same pattern). No post-hoc calibration was applied or tuned.
""")

# ================================================================= 08 missing-history sensitivity
cvp = CV.pivot_table(index=["set", "coverage_group"], columns="model", values=["n", "accuracy", "log_loss", "brier"], aggfunc="first")
cvp.columns = [f"{a}_{b}" for a, b in cvp.columns]
cvp = cvp.reset_index()
cvp["logreg_minus_elo_logloss"] = cvp.log_loss_multinomial_logreg - cvp.log_loss_elo_ordered_logit
cvp["logreg_minus_home_logloss"] = cvp.log_loss_multinomial_logreg - cvp.log_loss_always_home
hdp = HD.pivot_table(index=["set", "history_depth"], columns="model", values=["n", "accuracy", "log_loss", "brier"], aggfunc="first")
hdp.columns = [f"{a}_{b}" for a, b in hdp.columns]
hdp = hdp.reset_index()
hdp["logreg_minus_elo_logloss"] = hdp.log_loss_multinomial_logreg - hdp.log_loss_elo_ordered_logit
c6 = ["set", "coverage_group", "n_multinomial_logreg", "accuracy_always_home", "accuracy_elo_ordered_logit", "accuracy_multinomial_logreg", "log_loss_always_home", "log_loss_elo_ordered_logit", "log_loss_multinomial_logreg", "logreg_minus_elo_logloss"]
h6 = ["set", "history_depth", "n_multinomial_logreg", "accuracy_always_home", "accuracy_elo_ordered_logit", "accuracy_multinomial_logreg", "log_loss_always_home", "log_loss_elo_ordered_logit", "log_loss_multinomial_logreg", "logreg_minus_elo_logloss"]
lgt = pd.DataFrame(cov["league_table"])
W("08_MISSING_HISTORY_SENSITIVITY_REPORT.md", f"""# 08 Missing-history sensitivity report (generated {NOW})

## Categories (defined from TRAIN-period evidence in `b2_fit_select_freeze.py`, stored in `artifacts/coverage_categories.json` before the test / holdout evaluation)
* **League coverage group:** `well_covered` = at least 3 league-seasons in the train period and at least 80% of them verified complete (`season_completeness_by_league_season.csv`): {int((lgt.coverage_group == 'well_covered').sum())} leagues; `incomplete_history` = other leagues present in train: {int((lgt.coverage_group == 'incomplete_history').sum())} leagues; `no_training_history` = leagues absent from the train period (appear only later).
* **Match history depth:** min(home_n_prior, away_n_prior) with cut points taken from the train distribution: shallow < {cov['history_depth_cut_points']['q33']:.0f}, deep >= {cov['history_depth_cut_points']['q67']:.0f}.
Only primary evaluation rows (complete league-seasons) are used, so these groups describe *structural* gaps in the history that feeds the features, not unfinished evaluation seasons.

## By league coverage group
{tbl(cvp[c6])}

## By match history depth
{tbl(hdp[h6])}

## Findings (no model was altered after seeing these tables)
* The learned models beat always-home in every coverage group on both test and holdout. The ranking logistic regression ~ Elo > always-home is the same for well-covered and incomplete-history leagues.
* Well-covered leagues are *harder* than leagues with incomplete history (log loss about 1.01 vs 1.00 on test and 1.01 vs 1.03 on the holdout, with no consistent direction): the incomplete-history groups contain different, often smaller or more predictable leagues, so the comparison is confounded by league composition. There is no evidence in these data that incomplete history harms the model by a measurable margin, but there is also no evidence that it is harmless: the groups are not matched.
* History depth: matches whose clubs have few prior matches (shallow) are where the logistic regression gains most against Elo on the holdout (0.997 vs 1.016), plausibly because the form features partially compensate for an unreliable young Elo; for deep histories there is no gain.
* Leagues absent from the training period (`no_training_history`) are the largest test group; the model transfers to them without degradation (log loss 0.999 on test, 0.956 on the holdout, partly a composition effect again).
* Limits: the categories are coarse; the number of leagues per group is small; sampling error per group (a few hundred to a few thousand matches) is 0.01-0.03 in log loss.
""")

# ================================================================= 10 manifest
arts = {f: sha(os.path.join(ART, f)) for f in sorted(os.listdir(ART))}
outs = {f: sha(os.path.join(OUT, f)) for f in sorted(os.listdir(OUT)) if os.path.isfile(os.path.join(OUT, f)) and f not in ("10_REPRODUCIBILITY_MANIFEST.json", "00_README.md")}
eh = json.load(open(os.path.join(OUT, "_evaluation_split_hashes.json")))
man = dict(experiment="FootIQ club 90-minute 1X2 controlled baseline v1", generated=NOW, dataset=dict(version="v1.1", dataset_file="FootIQ_ML_Training_Preparation/01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv", dataset_sha256=dsh,
                                                                                                    feature_file="FootIQ_ML_Training_Preparation/02_CORRECTED_FEATURE_DATASET_v1.1.csv", feature_file_sha256=fsh,
                                                                                                    rows=sum(cnt.values()), split_rows=cnt),
           feature_order=prep["feature_order"], model_input_columns=coef["input_columns"], preprocessing=prep, hyperparameters=dict(multinomial_logreg=dict(C=frozen["selected_C"], penalty="l2", solver="lbfgs", max_iter=3000, random_state=SEED),
           elo_ordered_logit=basep["elo_ordered_logit"], always_home=basep["always_home_class_priors"], c_grid=grid.to_dict("records")), random_seed=SEED, dependency_versions=frozen["dependency_versions"],
           python="3.12.14 (project .venv)", split_boundaries=BOUNDS, evaluation_split_hashes=eh, artifacts_sha256=arts, output_files_sha256=outs, freeze_record=frozen, evaluation_lock=lock,
           selected_model_by_validation=frozen["selected_model_by_validation_primary_log_loss"], procedure="b1 -> b2 -> b3 (once) -> b4; re-running b2 or b3 is refused by the freeze / lock files",
           notes="Scripts are in _scripts/. Running them again requires deleting artifacts/FROZEN.json and EVALUATION_LOCK.json by hand, which would void the controlled-experiment guarantee.")
json.dump(man, open(os.path.join(OUT, "10_REPRODUCIBILITY_MANIFEST.json"), "w"), indent=1, default=str)
print("reports written")
