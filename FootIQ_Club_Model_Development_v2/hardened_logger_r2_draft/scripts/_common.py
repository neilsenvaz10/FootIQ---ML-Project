import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import pandas as pd
from hardened import artifacts, engine, state, ledger, approval
from footiq_sources.reconcile import build_resolver
sys.stdout.reconfigure(encoding="utf-8")


def load_universe():
    V = pd.read_pickle(artifacts.canonical_paths()["universe"])
    return V, build_resolver(V)


def latest_pnr():
    runs = sorted(glob.glob(os.path.join(artifacts.V2, "matched_v1_prospective_r1", "ingestion", "runs", "selftest_*")))
    if not runs:
        return None
    un = pd.read_csv(os.path.join(runs[-1], "unresolved_or_non_completed.csv"), encoding="utf-8-sig", low_memory=False)
    return un[(un.status == "past_date_no_result") & (un.competition_id == state.COMP)]


def out(obj):
    print(json.dumps(obj, indent=1, default=str))
