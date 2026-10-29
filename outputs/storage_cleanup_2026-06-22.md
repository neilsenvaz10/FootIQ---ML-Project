# Storage Cleanup - 2026-06-22

## Result

- Before: 915,844 KiB (about 894 MiB)
- After: about 57 MiB
- Recovered: about 837 MiB

## Deleted

- `data/raw/statsbomb/events` - regenerable StatsBomb event JSON
- `data/raw/statsbomb/three-sixty` - regenerable StatsBomb 360 JSON; unused by current model scripts
- `work/spreadsheet_build` - generated workbook preview renders
- Python `__pycache__` directories
- Temporary Excel lock file

## Retained

- All processed datasets and model artifacts
- API-Football and Open-Meteo caches
- Matchday prediction, validation, lineup, v2.11, and v2.12 outputs
- Player-impact data and Excel workbooks
- StatsBomb match metadata and lineup files
- Raw squad, international-results, World Bank, FIFA, and OpenFootball sources

The deleted StatsBomb payloads can be restored with `scripts/download_statsbomb_worldcup.py` if the foundation tables ever need to be rebuilt from raw source.
