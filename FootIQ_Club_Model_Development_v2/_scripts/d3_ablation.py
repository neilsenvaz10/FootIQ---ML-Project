"""Phase 5: feature-group ablation on the frozen chronological development folds (LR and HGB probes)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_models import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
assert os.path.exists(os.path.join(WORK, "protocol_frozen.json"))
F = load_dev()
F = F[F.match_date <= DEV_END]
base = GROUPS["elo2"]
SETS = {
    "01 Elo only (v1 Elo, K20/HA60)": GROUPS["elo_v1"],
    "02 Elo only (tuned Elo2)": base,
    "03 Elo2 + Elo extras (relative level, momentum, history depth, new-to-league)": base + GROUPS["elo_plus"],
    "04 Elo2 + home advantage": base + GROUPS["home_adv"],
    "05 Elo2 + recent form": base + GROUPS["form"],
    "06 Elo2 + goal-based (Poisson-style) features": base + GROUPS["goal"],
    "07 Elo2 + league context": base + GROUPS["league"],
    "08 Elo2 + rest and congestion": base + GROUPS["rest"],
    "09 v1 approved 25 features": GROUPS["v1_all25"],
    "10 Elo2 + all v2 groups": base + sum([GROUPS[g] for g in ("elo_plus", "home_adv", "form", "goal", "league", "rest")], []),
}
PROBES = {"LR(C=0.1)": ("lr", dict(C=0.1)), "HGB(depth3, lr0.05, 200 it)": ("hgb", dict(learning_rate=0.05, max_depth=3, max_iter=200, l2_regularization=1.0, min_samples_leaf=200))}
missing = [c for cols in SETS.values() for c in cols if c not in F.columns]
assert not missing, missing
rows = []
for sname, cols in SETS.items():
    for pname, (kind, hp) in PROBES.items():
        res, _ = fold_eval(F, kind, hp, cols)
        rr = pd.DataFrame(res)
        rows.append(dict(feature_set=sname, probe=pname, n_features=len(cols), fold1_ll=rr.log_loss[0], fold2_ll=rr.log_loss[1], fold3_ll=rr.log_loss[2], mean_log_loss=rr.log_loss.mean(),
                         std_log_loss=rr.log_loss.std(ddof=0), mean_brier=rr.brier.mean(), mean_accuracy=rr.accuracy.mean(), mean_macro_f1=rr.macro_f1.mean()))
        print(rows[-1]["feature_set"][:50], pname, round(rows[-1]["mean_log_loss"], 5), flush=True)
A = pd.DataFrame(rows)
ref = A[A.feature_set.str.startswith("02")].set_index("probe")
A["delta_vs_elo2_only"] = [r.mean_log_loss - ref.loc[r.probe, "mean_log_loss"] for r in A.itertuples()]
A["folds_better_than_elo2_only"] = [int(sum(getattr(r, f"fold{k}_ll") < ref.loc[r.probe, f"fold{k}_ll"] for k in (1, 2, 3))) for r in A.itertuples()]
A["decision"] = ""
for i, r in A.iterrows():
    if r.feature_set[:2] in ("01", "02", "09"):
        continue
    ok = r.delta_vs_elo2_only <= -0.0010 and r.folds_better_than_elo2_only >= 2
    A.loc[i, "decision"] = "gain >= 0.0010 and better in >= 2 folds" if ok else "rejected: gain < 0.0010 or not better in 2 of 3 folds"
A.to_csv(os.path.join(OUT, "04_FEATURE_ABLATION_RESULTS.csv"), index=False)
print(A[["feature_set", "probe", "mean_log_loss", "delta_vs_elo2_only", "folds_better_than_elo2_only", "decision"]].to_string())
