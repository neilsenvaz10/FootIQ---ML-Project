"""Offline dynamic-strength prototype (Elo-in-the-loop with the frozen club v1 coefficients). Nothing here is wired to the product."""
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from seasonsim import dynamic, pointsonly  # noqa: E402

ART = ROOT / "FootIQ_Club_Model_Baseline_v1" / "artifacts"


def league(T=6, seed=0):
    rng = np.random.default_rng(seed)
    fh, fa, dates = [], [], []
    d = 739000
    for rnd in range(2 * (T - 1)):
        perm = rng.permutation(T)
        for i in range(0, T, 2):
            fh.append(perm[i]); fa.append(perm[i + 1]); dates.append(d + 7 * rnd)
    F = len(fh)
    p = rng.dirichlet([4, 2.5, 3], size=F)
    return np.zeros(T, dtype=np.int64), np.array(fh), np.array(fa), np.array(dates), p, 1500 + 40 * rng.standard_normal(T)


def test_without_feedback_and_drift_it_is_exactly_the_static_points_only_simulation():
    base, fh, fa, dates, p, elo = league()
    static = pointsonly.simulate_points(base, fh, fa, p, 3000, 11)
    assert np.array_equal(dynamic.simulate_dynamic(base, fh, fa, dates, p, elo, 3000, 11, kappa=0.0, tau=0.0), static)
    nearly = dynamic.simulate_dynamic(base, fh, fa, dates, p, elo, 3000, 11, kappa=1e-12, tau=0.0)           # the general path with a vanishing update
    assert (nearly != static).mean() < 1e-4


def test_feedback_conserves_points_is_reproducible_and_widens_the_distribution():
    base, fh, fa, dates, p, elo = league(8, 1)
    a = dynamic.simulate_dynamic(base, fh, fa, dates, p, elo, 4000, 5, kappa=1.0)
    b = dynamic.simulate_dynamic(base, fh, fa, dates, p, elo, 4000, 5, kappa=1.0)
    assert np.array_equal(a, b)
    total = a.sum(axis=1)
    assert total.min() >= 2 * len(fh) and total.max() <= 3 * len(fh)                                           # every match adds 2 or 3 points
    s = dynamic.simulate_dynamic(base, fh, fa, dates, p, elo, 4000, 5, kappa=0.0)
    assert a.std(axis=0).mean() > s.std(axis=0).mean()                                                         # momentum widens the spread of final points
    assert abs(a.mean() - s.mean()) < 0.3                                                                      # but the average stays about the same
    w = dynamic.simulate_dynamic(base, fh, fa, dates, p, elo, 4000, 5, kappa=0.0, tau=12.0)
    assert w.std(axis=0).mean() > s.std(axis=0).mean()                                                         # random drift widens it too


def test_a_club_that_wins_early_becomes_more_likely_to_win_later():
    T = 4
    fh = np.array([0, 0, 0]); fa = np.array([1, 2, 3]); dates = np.array([100, 107, 114])
    p = np.tile(np.array([[0.45, 0.25, 0.30]]), (3, 1))
    elo = np.full(T, 1500.0)
    pts = dynamic.simulate_dynamic(np.zeros(T, dtype=np.int64), fh, fa, dates, p, elo, 40000, 3, kappa=2.0)
    base = dynamic.simulate_dynamic(np.zeros(T, dtype=np.int64), fh, fa, dates, p, elo, 40000, 3, kappa=0.0)
    assert pts[:, 0].var() > base[:, 0].var()                                                                    # the three results of club 0 become positively correlated


def test_the_tilt_formula_equals_the_frozen_model_exactly_when_only_elo_changes():
    """Linearity check against the real frozen artifact: evaluate the model on a feature row, then on the same row with the Elo columns shifted, and compare with the tilt formula."""
    import predict

    lg, V, tiers = predict._club_runtime()
    v2m, v1m, v1prep, v1elo = predict._club_models()
    import pandas as pd

    med = pd.Series(v1prep["median_train"])
    rng = np.random.default_rng(4)
    sl = dynamic.tilt_slopes()
    for _ in range(5):
        row = med.copy()
        row["home_elo"], row["away_elo"] = 1500 + rng.normal(0, 150), 1500 + rng.normal(0, 150)
        row["elo_diff"] = row["home_elo"] - row["away_elo"]
        dh, da = rng.normal(0, 40), rng.normal(0, 40)
        row2 = row.copy()
        row2["home_elo"] += dh; row2["away_elo"] += da; row2["elo_diff"] = row2["home_elo"] - row2["away_elo"]
        frame = pd.DataFrame([row, row2])[v1prep["feature_order"]]
        p = lg.v1_proba(v1m, v1prep, frame)
        logit = np.log(p[0]) + sl["home"] * dh + sl["away"] * da
        tilted = np.exp(logit - logit.max())
        tilted /= tilted.sum()
        assert np.allclose(tilted, p[1], atol=1e-9), (tilted, p[1])


def test_reading_the_frozen_artifacts_leaves_them_unchanged():
    files = [ART / "multinomial_logreg_coefficients.json", ART / "preprocessing_train_fitted.json", ART / "multinomial_logreg.pkl"]
    before = [hashlib.sha256(f.read_bytes()).hexdigest() for f in files]
    dynamic.tilt_slopes()
    dynamic.elo_constants()
    assert before == [hashlib.sha256(f.read_bytes()).hexdigest() for f in files]
    assert dynamic.elo_constants() == (20.0, 60.0)


def test_elo_slopes_have_the_documented_sign_and_size():
    sl = dynamic.tilt_slopes()
    assert sl["home"][0] > 0 > sl["home"][2] and sl["away"][2] > 0 > sl["away"][0]                                   # a stronger home club raises home-win odds; a stronger away club raises away-win odds
    assert sl["home"][0] * 50 == pytest.approx(0.132, abs=0.01) and sl["home"][2] * 50 == pytest.approx(-0.125, abs=0.01)


def test_no_fixtures_gives_the_current_points():
    out = dynamic.simulate_dynamic(np.array([3, 4]), np.array([], dtype=int), np.array([], dtype=int), np.array([], dtype=int), np.zeros((0, 3)), np.array([1500.0, 1500.0]), 5, 1)
    assert (out == np.array([3, 4])).all()


def test_dynamic_mode_is_not_wired_into_the_service_the_api_or_the_settings():
    """Production code must not import the dynamic prototype, the season API must not offer it, and no setting may switch it on."""
    import ast

    for rel in ("main.py", "seasonsim/service.py", "seasonsim/eligibility.py", "seasonsim/settings.py", "seasonsim/pointsonly.py", "seasonsim/pointbounds.py", "seasonsim/engine.py", "seasonsim/rules.py"):
        tree = ast.parse((ROOT / "app" / rel).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            if isinstance(node, ast.ImportFrom):
                imported |= {node.module or ""} | {a.name for a in node.names}
        assert not any("dynamic" in name for name in imported), (rel, imported)
    cfg = (ROOT / "config" / "season_sim.json").read_text(encoding="utf-8").lower()
    assert "dynamic" not in cfg and "kappa" not in cfg
    import main

    spec = main.app.openapi()
    season = {path: body for path, body in spec["paths"].items() if path.startswith("/api/season")}
    assert season and "dynamic" not in json.dumps(season).lower()
    fields = spec["components"]["schemas"]["SeasonSimRequest"]["properties"]
    assert set(fields) == {"key", "season", "user_action", "simulations", "seed", "include_experimental"}
