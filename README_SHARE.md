# World Cup Prediction Model

This archive is a research snapshot of the World Cup prediction project through
version 2.14, including the model source, trained v2.7 artifact, historical and
live validation tables, curated datasets, tests, workbooks, and generated reports.

## Start Here

- `outputs/world_cup_data_inventory.md`: dataset inventory and provenance.
- `outputs/model_v26_bakeoff_report.md`: model comparison and calibration work.
- `outputs/live_predictions_v27_report.md`: selected ensemble and live predictor.
- `outputs/confidence_gate_v28_report.md`: Strong Pick, Model Lean, and Pass policy.
- `outputs/worldcup_full_validation_report_2026-07-19.md`: tournament validation.
- `scripts/`: all model-building, simulation, live-data, and validation code.
- `tests/`: regression tests for the later live-model versions.

## Model Architecture

The regulation-result ensemble uses:

- 50% gradient boosting
- 30% Elo formula
- 20% logistic regression
- 0% Poisson-lite in the public 1/X/2 blend

Knockout simulations separately resolve regulation draws through extra time and
penalties. The public confidence layer can publish a Strong Pick, Model Lean, or
Pass without changing the underlying probabilities.

## Setup

Python 3.12 is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-share.txt
python3 -m pytest -q
```

Representative offline rebuild commands:

```bash
python3 scripts/build_foundation_tables.py
python3 scripts/build_player_impact_v21.py
python3 scripts/build_worldcup_model_v23.py
python3 scripts/model_bakeoff_v26.py
python3 scripts/build_live_predictions_v27.py
python3 scripts/build_confidence_gate_v28.py
```

Live API-Football jobs require a personal API key:

```bash
cp .env.example .env
```

Then replace the placeholder in `.env`. Never commit or share that file.

## Important Notes

- The supplied trained artifact is `data/model_artifacts/v27/live_match_model.pkl`.
- Provider caches and local dependency runtimes are intentionally excluded. They
  are generated locally and are not part of the model's source of truth.
- Predictions are probabilistic research outputs, not guarantees or betting advice.
- Before commercial redistribution, review the terms and licenses of every
  third-party dataset listed in the data inventory.
