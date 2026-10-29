# Observed baseline environment

- Executable: `C:\Users\DELL\Desktop\world-cup-prediction-model\.venv\Scripts\python.exe`
- CPython: `3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]`
- Platform: `Windows-11-10.0.26300-SP0`, `AMD64`
- Base runtime: `C:\Users\DELL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python` (the venv is not self-contained)
- Audit runs used `-B -X utf8`; existing model inputs/artifact were not changed.
- Full environment: `capture_2026-10-20/environment.json`; exact installed distribution inventory: `capture_2026-10-20/requirements-observed.txt`.
- `pip freeze --all` was attempted and failed because this existing venv has no pip. No installation/upgrade was attempted; importlib.metadata captured installed versions instead.
- This is a version lock/inventory, not an offline wheelhouse or a demonstrated clean-machine installation. Existing sklearn artifact compatibility was exercised on this host only.

## Exact installed distribution versions

- cloudpickle==3.1.2
- colorama==0.4.6
- et_xmlfile==2.0.0
- iniconfig==2.3.1
- joblib==1.6.0
- lxml==5.4.0
- numpy==1.26.4
- openpyxl==3.1.2
- packaging==26.3
- pandas==2.2.1
- pluggy==1.7.0
- Pygments==2.21.0
- pytest==8.4.2
- python-dateutil==2.9.0.post0
- pytz==2026.5
- scikit-learn==1.5.1
- scipy==1.17.1
- six==1.17.0
- threadpoolctl==3.7.0
- tzdata==2026.5
