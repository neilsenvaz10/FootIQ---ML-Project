"""Phase 4.17 step 3: PRIVATE rating refresh with the project's own pipeline (scripts/build_foundation_tables.build_international_matches_and_elo), redirected to private folders.
A) parity run on the LOCAL raw file: must reproduce data/processed exactly (proves the private run is the production method);
B) refresh run on the staged CC0 results (identity-normalised: 'China' -> 'China PR', 'Canton Ticino' -> 'Ticino', the names the project and its ratings use);
C) chronology replay, D) before/after predictions through app/predict.py with ONLY the in-process ratings path redirected.
data/processed, the frozen models and the production store are read-only here."""
import hashlib
import importlib
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIV = OUT / "private_ratings"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "app"))
import build_foundation_tables as bft  # noqa: E402

NAME_MAP = {"China": "China PR", "Canton Ticino": "Ticino"}


def run(raw_csv: Path, tag: str) -> Path:
    base = PRIV / tag
    if base.exists():
        shutil.rmtree(base)
    (base / "raw" / "international_results").mkdir(parents=True)
    shutil.copy(raw_csv, base / "raw" / "international_results" / "results.csv")
    bft.RAW, bft.PROCESSED = base / "raw", base / "processed"
    bft.build_international_matches_and_elo()
    return base / "processed"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


rep = {}
LOCAL = ROOT / "data" / "raw" / "international_results" / "results.csv"
STAGED = OUT / "staging" / "martj42" / "unpacked" / "international_results-master" / "results.csv"
# ---------------- A) parity
pa = run(LOCAL, "A_parity_local")
prod = ROOT / "data" / "processed"
files = ["international_matches.csv", "team_elo_latest.csv", "team_elo_match_history.csv"] + [p.name for p in prod.glob("team_recent_form*.csv")]
rep["A_parity_with_production_processed"] = {f: (sha(pa / f) == sha(prod / f)) if (pa / f).exists() and (prod / f).exists() else "missing" for f in files}
# ---------------- B) refresh on staged, identity-normalised
df = pd.read_csv(STAGED, dtype=str, keep_default_na=False)
before_names = set(df.home_team) | set(df.away_team)
for c in ("home_team", "away_team"):
    df[c] = df[c].replace(NAME_MAP)
(PRIV).mkdir(exist_ok=True)
norm_csv = PRIV / "staged_results_identity_normalised.csv"
df.to_csv(norm_csv, index=False)
rep["B_name_map_applied"] = NAME_MAP
pb = run(norm_csv, "B_refresh_staged")
elo_old, elo_new = pd.read_csv(prod / "team_elo_latest.csv"), pd.read_csv(pb / "team_elo_latest.csv")
im_old, im_new = pd.read_csv(prod / "international_matches.csv", low_memory=False), pd.read_csv(pb / "international_matches.csv", low_memory=False)
rep["B_rows"] = dict(matches_before=len(im_old), matches_after=len(im_new), last_date_before=im_old.date.max(), last_date_after=im_new.date.max(), teams_before=len(elo_old), teams_after=len(elo_new))
mv = elo_old.merge(elo_new, on="team", suffixes=("_old", "_new"), how="outer")
mv["delta"] = mv.elo_rating_new - mv.elo_rating_old
rep["B_new_teams"] = sorted(mv[mv.elo_rating_old.isna()].team.tolist())
rep["B_teams_dropped"] = sorted(mv[mv.elo_rating_new.isna()].team.tolist())
rep["B_biggest_rating_moves"] = mv.dropna(subset=["delta"]).reindex(mv.delta.abs().sort_values(ascending=False).index).head(10)[["team", "elo_rating_old", "elo_rating_new", "delta"]].round(1).values.tolist()
rep["B_top10_before"] = elo_old.head(10)[["team", "elo_rating"]].round(0).values.tolist()
rep["B_top10_after"] = elo_new.head(10)[["team", "elo_rating"]].round(0).values.tolist()
# the rating pipeline sees historical changes too (the dataset was edited upstream): quantify them
old_m = im_old.merge(im_new, on=["date", "home_team", "away_team"], suffixes=("_o", "_n"))
rep["B_historical_rows_whose_score_changed_in_the_new_file"] = int(((old_m.home_score_o != old_m.home_score_n) | (old_m.away_score_o != old_m.away_score_n)).sum())
# ---------------- C) chronology replay on the refreshed table
h = pd.read_csv(pb / "team_elo_match_history.csv", low_memory=False)
h = h.sort_values(["team", "date", "match_id"])
h["prev_post"] = h.groupby("team").post_elo.shift(1)
chk = h.dropna(subset=["prev_post"])
rep["C_chronology"] = dict(rows=len(h), dates_sorted_in_match_order=bool(im_new.date.is_monotonic_increasing), rows_whose_pre_rating_is_not_the_previous_post=int(((chk.pre_elo - chk.prev_post).abs() > 0.002).sum()),
                           first_match_rating_is_1500=bool((h.groupby("team").head(1).pre_elo == 1500.0).all()), same_team_twice_on_one_date=int(h.duplicated(["team", "date"]).sum()))
# ---------------- D) predictions before/after (ratings path redirected in this process only)
import predict  # noqa: E402
import build_live_predictions_v27 as v27  # noqa: E402
orig = v27.PROCESSED
pairs = [("WC", "Spain", "Argentina", "neutral"), ("WC", "France", "England", "neutral"), ("UNL", "Portugal", "Spain", "home"), ("UNL", "Netherlands", "Germany", "home"), ("COPA", "Argentina", "Colombia", "neutral"), ("COPA", "Brazil", "Uruguay", "neutral")]
pre, post = [], []
for key, a, b, v in pairs:
    try:
        r = predict.predict(key, a, b, "2026-10-20", v)
        pre.append((key, a, b, "ok", r["data_through"], [round(r["primary"][x], 3) for x in ("home", "draw", "away")], r["gate"]["public_pick"], round(r["inputs"]["home"]["elo"]), round(r["inputs"]["away"]["elo"])))
    except Exception as e:  # noqa: BLE001
        pre.append((key, a, b, "ERR", str(e)[:90]))
v27.PROCESSED = pb
predict._intl_runtime.cache_clear()                                  # the runtime (artifact, ratings, form) is cached: rebuild it from the private ratings
for key, a, b, v in pairs:
    try:
        r = predict.predict(key, a, b, "2026-10-20", v)
        post.append((key, a, b, "ok", r["data_through"], [round(r["primary"][x], 3) for x in ("home", "draw", "away")], r["gate"]["public_pick"], round(r["inputs"]["home"]["elo"]), round(r["inputs"]["away"]["elo"])))
    except Exception as e:  # noqa: BLE001
        post.append((key, a, b, "ERR", str(e)[:90]))
v27.PROCESSED = orig
predict._intl_runtime.cache_clear()
rep["D_predictions_before_production_ratings"] = pre
rep["D_predictions_after_private_refresh"] = post
rep["D_production_processed_untouched"] = {f: sha(prod / f) == sha(pa / f) for f in ("international_matches.csv", "team_elo_latest.csv")}
(OUT / "rating_refresh_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(rep, indent=1, ensure_ascii=False, default=str)[:7000])
