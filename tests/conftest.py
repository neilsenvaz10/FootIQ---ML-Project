"""Test runs never start the background synchronisation, whatever config/sync.json says (a test that starts the application's lifespan must not reach the network)."""
import os
from pathlib import Path

os.environ["FOOTIQ_DISABLE_SYNC"] = "1"

# pytest's temporary folders (several tests copy the 230 MB store) go to the project's drive, not the system drive. An explicit PYTEST_DEBUG_TEMPROOT still wins.
_TMP = Path(__file__).resolve().parents[1] / "data" / "supervised" / "pytest_tmp"
_TMP.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(_TMP))
