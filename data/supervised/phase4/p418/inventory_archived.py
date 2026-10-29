"""Phase 4.18: READ-ONLY inventory of datasets, ratings, snapshots, tests, scripts and code that belong to the five competitions removed from the active scope (UEL, UECL, WC, UNL, COPA).
Nothing is moved or deleted; the list only says what is no longer used by the application. Writes data/supervised/phase4/p418/archived_artifacts_inventory.csv."""
import csv
import glob
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "archived_artifacts_inventory.csv"

# (category, glob relative to ROOT, why it is unused now, shared with the retained scope?)
CANDIDATES = [
    ("dataset rows", "data/miniproject/matches.csv", "holds ~4,774 rows of the five removed competitions (WC 1,094; UEL 1,424; UECL 729; UNL 658; COPA 869); the application filters them out", "SHARED FILE: the six supported competitions are in the same file"),
    ("dataset", "data/raw/international_results/*", "national-team results archive (World Cup, Nations League, Copa America and every other international)", "no"),
    ("ratings", "data/processed/international_matches.csv", "international matches with Elo columns", "no"),
    ("ratings", "data/processed/team_elo_*.csv", "national-team Elo history and latest ratings (the international model's input)", "no"),
    ("ratings", "data/processed/team_recent_form*.csv", "national-team recent form", "no"),
    ("dataset", "data/processed/worldcup_*", "World Cup 2026 fixtures, verified results, validation files", "no"),
    ("dataset", "data/processed/nations_league_*", "Nations League 2026 prediction files", "no"),
    ("dataset", "data/processed/live_tournament_*", "World Cup tournament simulation outputs", "no"),
    ("dataset", "data/processed/knockout_*", "World Cup knockout advancement validation", "no"),
    ("dataset", "data/processed/matchday_validation_v210.csv", "World Cup matchday validation", "no"),
    ("dataset", "data/processed/model_v2*_tournament_odds.csv", "World Cup title odds", "no"),
    ("model artifact", "data/model_artifacts/v27/*", "international v2.7 ensemble (frozen, preserved)", "no"),
    ("model artifact", "data/model_artifacts/*worldcup*", "World Cup model artifacts (frozen, preserved)", "no"),
    ("snapshot", "FootIQ_ML_Data_Readiness/raw_external/wikipedia/*Europa_League*", "Wikipedia snapshots of Europa League pages", "no"),
    ("snapshot", "FootIQ_ML_Data_Readiness/raw_external/wikipedia/*Conference_League*", "Wikipedia snapshots of Conference League pages", "no"),
    ("snapshot", "FootIQ_ML_Data_Readiness/raw_external/wikipedia/*World_Cup*", "Wikipedia snapshots of World Cup pages", "no"),
    ("snapshot", "FootIQ_ML_Data_Readiness/raw_external/wikipedia/*Nations_League*", "Wikipedia snapshots of Nations League pages", "no"),
    ("snapshot", "FootIQ_ML_Data_Readiness/raw_external/wikipedia/*Copa_Am*", "Wikipedia snapshots of Copa America pages", "no"),
    ("source clone", "FootIQ_Dataset_Submission/_raw_sources/euro", "openfootball clone: European Championship", "no"),
    ("source clone", "FootIQ_Dataset_Submission/_raw_sources/copa-america", "openfootball clone: Copa America", "no"),
    ("source clone", "FootIQ_Dataset_Submission/_raw_sources/world", "openfootball clone: World Cup", "no"),
    ("source clone", "FootIQ_Dataset_Submission/_raw_sources/south-america", "openfootball clone: South American competitions", "no"),
    ("source clone", "FootIQ_Dataset_Submission/_raw_sources/club-worldcup", "openfootball clone: Club World Cup", "no"),
    ("source clone", "FootIQ_Dataset_Submission/_raw_sources/martj42_refresh", "earlier refresh of the international results", "no"),
    ("staging (Phase 4.17)", "data/supervised/phase4/p417/staging/martj42", "downloaded CC0 international results archive (2026-10-28)", "no"),
    ("staging (Phase 4.17)", "data/supervised/phase4/p417/private_ratings", "private international rating refresh", "no"),
    ("staging (Phase 4.17)", "data/supervised/phase4/p417/compare_intl*.py", "comparison scripts and reports for the international data", "no"),
    ("staging (Phase 4.17)", "data/supervised/phase4/p417/verify_unl.py", "Nations League verification", "no"),
    ("staging (Phase 4.17)", "data/supervised/phase4/p417/rating_refresh*", "international rating refresh script and report", "no"),
    ("staging (Phase 4.17)", "data/supervised/phase4/p417/unl_verification.json", "Nations League verification result", "no"),
    ("script", "scripts/build_worldcup_model_v*.py", "World Cup / international model builders", "no"),
    ("script", "scripts/simulate_*.py", "World Cup simulators", "no"),
    ("script", "scripts/run_international_window_*.py", "international-window prediction runs", "no"),
    ("script", "scripts/run_nations_league_slate_v27.py", "Nations League slate", "no"),
    ("script", "scripts/run_friendlies_v24.py", "friendlies runs", "no"),
    ("script", "scripts/backtest_*worldcup*.py", "World Cup backtests", "no"),
    ("script", "scripts/backtest_euro_nations_v23.py", "Euro / Nations League backtest", "no"),
    ("script", "scripts/build_live_predictions_v27.py", "international live predictions (also imported by app/predict.py's archived international path)", "app/predict.py (archived path)"),
    ("script", "scripts/validate_*.py", "World Cup validations", "no"),
    ("application code", "app/worldcup_sim.py", "World Cup simulator wrapper (routes removed)", "no"),
    ("application code", "app/bracket.py", "World Cup bracket (route removed)", "no"),
    ("application code", "app/names.py", "international team-name canonicalisation used when building matches.csv", "app/prepare_data.py (archive build)"),
    ("application code", "frontend/src/pages/Simulator.jsx", "World Cup simulator page (no longer routed)", "no"),
    ("application code", "frontend/src/components/Bracket.jsx", "World Cup bracket component (no longer used)", "no"),
    ("test", "tests/test_live_tournament_v213.py", "World Cup tournament engine tests", "no"),
    ("test", "tests/test_matchday_report_v29.py", "World Cup matchday report tests", "no"),
    ("test", "tests/test_matchday_validation_v210.py", "World Cup matchday validation tests", "no"),
    ("test", "tests/test_lineup_impact_v212.py", "lineup-impact (World Cup) tests", "no"),
    ("test", "tests/test_confidence_gate_v211.py", "international confidence-gate tests", "no"),
    ("test", "tests/test_phase417_evidence.py", "evidence for the international / UEFA staging of Phase 4.17 (partly: UEL/UECL/WC/UNL)", "partly"),
    ("docs", "docs/mini-project/phase4/P4_17_INTERNATIONAL_AND_UEFA_COMPLETION.md", "Phase 4.17 report (national teams and UEFA clubs)", "history"),
    ("docs", "docs/mini-project/phase4/P4_16_COMPETITION_CAPABILITY_REGISTRY.csv", "11-competition registry (superseded by the six-competition registry)", "history"),
]


def size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else 0


rows = []
for cat, pattern, why, shared in CANDIDATES:
    paths = [Path(x) for x in glob.glob(str(ROOT / pattern.replace("/", os.sep)), recursive=True)]
    if not paths:
        continue
    for p in sorted(paths):
        rows.append(dict(category=cat, path=p.relative_to(ROOT).as_posix(), bytes=size(p), why_unused=why, shared_with_retained_scope=shared))
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
tot = {}
for r in rows:
    tot[r["category"]] = tot.get(r["category"], 0) + r["bytes"]
print(len(rows), "paths;", f"{sum(tot.values()) / 1e6:,.1f} MB in total")
for k, v in sorted(tot.items(), key=lambda x: -x[1]):
    print(f"  {k:24s} {v / 1e6:10,.2f} MB  ({sum(1 for r in rows if r['category'] == k)} paths)")
