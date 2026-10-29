"""Phase 4.36: adds the published-evidence mode to league_results_import.py and reconcile_import.py (before-copies in p436/before/). The standard mode is not changed."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
B = Path(__file__).resolve().parent / "before"
B.mkdir(exist_ok=True)


def edit(rel, pairs):
    p = ROOT / rel
    shutil.copy2(p, B / Path(rel).name)
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    for a, b in pairs:
        assert s.count(a) == 1, (rel, a[:90], s.count(a))
        s = s.replace(a, b)
    p.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


# ------------------------------------------------------------------------------------------------------------------------------- league_results_import.py
edit("app/store/league_results_import.py", [
    ("from store import baseline as B  # noqa: E402\n", "from store import baseline as B  # noqa: E402\nfrom store import published_evidence as PE  # noqa: E402\n"),
    ('PRODUCTION = ROOT / "data" / "footiq.sqlite"\nSOURCE, LICENCE', 'PRODUCTION = ROOT / "data" / "footiq.sqlite"\nPUBLISHED = ROOT / "data" / "evidence" / "published" / "published_evidence_2026-10-28.csv"\nSOURCE, LICENCE'),
    ('''def stored_by_record(conn: sqlite3.Connection, keys) -> dict:''', '''def load_published(path: Path) -> pd.DataFrame:
    """Rows of the published-evidence file for this importer, shaped like a staged file (see published_evidence.py)."""
    df = PE.load(Path(path), "league_results")
    df["date"] = df["new_date"]
    df["store_date"] = df["expected_store_date"]
    df["staged_file"] = Path(path).name
    return df


def validate_published(df: pd.DataFrame, known_entities: set, as_of: str) -> tuple[list, set]:
    """Published-evidence mode: the same row checks as `validate`, with the second-source rule applied to redistributable sources only (score from two distinct allowed sources, date from two)."""
    issues, bad = [], set()
    seen = {}

    def flag(i, code, detail):
        issues.append(dict(row=int(i), code=code, detail=detail))
        bad.add(int(i))

    for r in df.itertuples():
        i = r.Index
        if r.action != "update_result":
            flag(i, "bad_action", str(r.action))
        if r.competition_key not in ALLOWED:
            flag(i, "competition_not_allowed", str(r.competition_key))
        if str(r.season) != SEASON:
            flag(i, "bad_season", str(r.season))
        for side in (r.home_entity, r.away_entity):
            if not isinstance(side, str) or not side:
                flag(i, "missing_team_identifier", f"{r.home} v {r.away}")
            elif side not in known_entities:
                flag(i, "unknown_team_identifier", side)
        if r.home_entity == r.away_entity:
            flag(i, "home_equals_away", str(r.home_entity))
        if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", str(r.date)):
            flag(i, "bad_date", str(r.date))
        elif str(r.date) > as_of:
            flag(i, "result_dated_in_the_future", f"{r.date} > {as_of}")
        elif not "2026-07-01" <= str(r.date) <= "2027-06-30":
            flag(i, "date_outside_season", str(r.date))
        if str(r.date) != str(r.store_date):
            flag(i, "dates_disagree", f"published {r.date}, store {r.store_date}")
        try:
            hg, ag = float(r.home_goals), float(r.away_goals)
            ok = hg.is_integer() and ag.is_integer() and 0 <= hg <= MAX_GOALS and 0 <= ag <= MAX_GOALS
        except (TypeError, ValueError):
            ok = False
        if not ok:
            flag(i, "implausible_score", f"{r.home_goals}-{r.away_goals}")
            continue
        target = f"{int(hg)}-{int(ag)}"
        sufficient, found = PE.assess(r, True, True, target, str(r.date))
        for code, detail in found + PE.check_label(r, sufficient):
            flag(i, code, detail)
        if r.record_id in seen:
            flag(i, "duplicate_in_file", f"{r.record_id} also on row {seen[r.record_id]}")
        else:
            seen[r.record_id] = i
    pairs = {}
    for r in df.itertuples():
        pairs.setdefault((r.competition_key, r.home_entity, r.away_entity), []).append(r.Index)
    for k, idx in pairs.items():
        if len(idx) > 1:
            for i in idx[1:]:
                if int(i) not in bad:
                    flag(i, "duplicate_pairing_in_file", f"{k[1]} v {k[2]}")
    return issues, bad


def stored_by_record(conn: sqlite3.Connection, keys) -> dict:'''),
    ("def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, paths=None, as_of: str | None = None, report_dir: Path | None = None) -> dict:\n    as_of = as_of or date.today().isoformat()\n    store = Path(store).resolve()\n    paths = list(paths) if paths else staged_paths()",
     "def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, paths=None, as_of: str | None = None, report_dir: Path | None = None, evidence: str = \"restricted\", published: Path | None = None) -> dict:\n    as_of = as_of or date.today().isoformat()\n    store = Path(store).resolve()\n    published_mode = evidence == \"published\"\n    if evidence not in (\"restricted\", \"published\"):\n        raise SystemExit(\"--evidence must be 'restricted' (default) or 'published'\")\n    published = Path(published) if published else PUBLISHED\n    paths = [published] if published_mode else (list(paths) if paths else staged_paths())"),
    ("        df = load_staged(paths)\n        issues, bad = validate(df, known, as_of)\n", "        if published_mode:\n            df = load_published(published)\n            issues, bad = validate_published(df, known, as_of)\n        else:\n            df = load_staged(paths)\n            issues, bad = validate(df, known, as_of)\n"),
    ("report = dict(mode=\"apply\" if apply else \"dry-run\", store=str(store), as_of=as_of, staged_files=", "report = dict(mode=\"apply\" if apply else \"dry-run\", evidence=evidence, store=str(store), as_of=as_of, staged_files="),
    ("VALUES ('league_results_import','local staging files (Wikipedia results grids, cross-checked)',?,'running')\", (ts,)).lastrowid",
     "VALUES ('league_results_import',?,?,'running')\", (\"published evidence file (Wikipedia, openfootball, OpenLigaDB values)\" if published_mode else 'local staging files (Wikipedia results grids, cross-checked)', ts)).lastrowid"),
    ("                    stg = next((Path(p) for p in paths if Path(p).name == f\"staged_results_{d['competition_key']}.csv\"), None)\n",
     "                    stg = published if published_mode else next((Path(p) for p in paths if Path(p).name == f\"staged_results_{d['competition_key']}.csv\"), None)\n"),
    ("\"Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; score and date cross-checked with a second source (not stored)\"))",
     "(\"Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; published evidence: score and date confirmed by a second redistributable source recorded in the evidence file\" if published_mode else \"Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; score and date cross-checked with a second source (not stored)\")))"),
    ("\"result from the Wikipedia results grid; fixture date from the stored fixture; score and date confirmed by a second, independent source (cross-check only, not stored)\") for d in linked])",
     "(\"result from the Wikipedia results grid; fixture date from the stored fixture; published evidence: confirmed by a second redistributable source recorded in the evidence file\" if published_mode else \"result from the Wikipedia results grid; fixture date from the stored fixture; score and date confirmed by a second, independent source (cross-check only, not stored)\")) for d in linked])"),
    ("    ap.add_argument(\"--report-dir\", help=\"write the JSON report and decisions CSV here\")\n    a = ap.parse_args(argv)\n    rep = run(Path(a.store), a.apply, a.production, Path(a.backup) if a.backup else None, [Path(x) for x in a.staged] if a.staged else None, a.as_of, Path(a.report_dir) if a.report_dir else None)",
     "    ap.add_argument(\"--report-dir\", help=\"write the JSON report and decisions CSV here\")\n    ap.add_argument(\"--evidence\", choices=(\"restricted\", \"published\"), default=\"restricted\", help=\"restricted (default): the Phase 4.20 staging files with their local cross-check columns; published: only redistributable evidence (see published_evidence.py)\")\n    ap.add_argument(\"--published-evidence\", help=\"published evidence CSV (default: data/evidence/published/published_evidence_2026-10-28.csv)\")\n    a = ap.parse_args(argv)\n    rep = run(Path(a.store), a.apply, a.production, Path(a.backup) if a.backup else None, [Path(x) for x in a.staged] if a.staged else None, a.as_of, Path(a.report_dir) if a.report_dir else None, a.evidence, Path(a.published_evidence) if a.published_evidence else None)"),
])

# ------------------------------------------------------------------------------------------------------------------------------- reconcile_import.py
edit("app/store/reconcile_import.py", [
    ("from store import league_results_import as L  # noqa: E402\n", "from store import league_results_import as L  # noqa: E402\nfrom store import published_evidence as PE  # noqa: E402\n"),
    ('PRODUCTION = ROOT / "data" / "footiq.sqlite"\nMAX_SHIFT_DAYS', 'PRODUCTION = ROOT / "data" / "footiq.sqlite"\nPUBLISHED = ROOT / "data" / "evidence" / "published" / "published_evidence_2026-10-28.csv"\nMAX_SHIFT_DAYS'),
    ("def _isnull(v) -> bool:", '''def load_published(path: Path) -> pd.DataFrame:
    """Rows of the published-evidence file for this importer, shaped like a proposal file (see published_evidence.py)."""
    df = PE.load(Path(path), "reconcile")
    df["change_id"] = df["evidence_id"]
    df["tier"] = df["production_tier"]
    df["evidence"] = df["review_decision"]
    return df


def _isnull(v) -> bool:'''),
    ("def classify(df: pd.DataFrame, bad: set, stored: dict, tiers: set) -> list:", '''def validate_published(df: pd.DataFrame, known: set, as_of: str) -> tuple[list, set]:
    """Published-evidence mode: the same row checks as `validate`, with the second-source rule applied to redistributable sources only. Provider-assisted changes cannot exist here (they need football-data.org)."""
    issues, bad = [], set()
    seen_id, seen_rec = {}, {}

    def flag(i, code, detail):
        issues.append(dict(row=int(i), code=code, detail=detail))
        bad.add(int(i))

    for r in df.itertuples():
        i = r.Index
        if r.action not in ACTIONS:
            flag(i, "bad_action", str(r.action))
            continue
        if r.tier not in TIERS:
            flag(i, "bad_tier", str(r.tier))
        if r.tier == "provider_assisted":
            flag(i, "provider_assisted_not_available_in_published_mode", str(r.change_id))
        if r.competition_key not in ALLOWED:
            flag(i, "competition_not_allowed", str(r.competition_key))
        for e in (r.home_entity, r.away_entity):
            if _isnull(e) or e not in known:
                flag(i, "unknown_team_identifier", str(e))
        if r.home_entity == r.away_entity:
            flag(i, "home_equals_away", str(r.home_entity))
        if _isnull(r.evidence) or not str(r.evidence).strip():
            flag(i, "no_evidence", str(r.change_id))
        if r.change_id in seen_id:
            flag(i, "duplicate_change_id", f"{r.change_id} also on row {seen_id[r.change_id]}")
        seen_id.setdefault(r.change_id, i)
        if r.record_id in seen_rec:
            flag(i, "two_changes_for_one_fixture", f"{r.record_id} also on row {seen_rec[r.record_id]}")
        seen_rec.setdefault(r.record_id, i)
        if _isnull(r.expected_store_date) or not ISO.fullmatch(str(r.expected_store_date)):
            flag(i, "bad_expected_date", str(r.expected_store_date))
        if r.action in ("add_result", "add_result_with_date"):
            try:
                hg, ag = float(r.home_goals), float(r.away_goals)
                good = hg.is_integer() and ag.is_integer() and 0 <= hg <= MAX_GOALS and 0 <= ag <= MAX_GOALS
            except (TypeError, ValueError):
                good = False
            if not good:
                flag(i, "implausible_score", f"{r.home_goals}-{r.away_goals}")
                continue
            target = f"{int(hg)}-{int(ag)}"
            if _isnull(r.new_date) or not ISO.fullmatch(str(r.new_date)):
                flag(i, "bad_date", str(r.new_date))
                continue
            ok, found = PE.assess(r, True, r.action == "add_result_with_date", target, str(r.new_date))
            for code, detail in found + PE.check_label(r, ok):
                flag(i, code, detail)
            if str(r.new_date) > as_of:
                flag(i, "result_dated_in_the_future", f"{r.new_date} > {as_of}")
            elif r.action == "add_result" and str(r.new_date) != str(r.expected_store_date):
                flag(i, "date_differs_for_add_result", f"{r.new_date} vs stored {r.expected_store_date}")
            elif r.action == "add_result_with_date" and (_days(str(r.new_date), str(r.expected_store_date)) > MAX_SHIFT_DAYS or str(r.new_date) == str(r.expected_store_date)):
                flag(i, "bad_date_shift", f"{r.expected_store_date} -> {r.new_date}")
            if r.tier != "strong":
                flag(i, "result_must_be_strong", str(r.tier))
        elif r.action == "correct_date":
            if _isnull(r.new_date) or not ISO.fullmatch(str(r.new_date)):
                flag(i, "bad_date", str(r.new_date))
                continue
            if str(r.new_date) == str(r.expected_store_date):
                flag(i, "no_change", str(r.new_date))
            elif _days(str(r.new_date), str(r.expected_store_date)) > MAX_SHIFT_DAYS:
                flag(i, "date_shift_too_large", f"{r.expected_store_date} -> {r.new_date}")
            if str(r.new_date) < as_of:
                flag(i, "corrected_date_in_the_past", str(r.new_date))
            ok, found = PE.assess(r, False, True, None, str(r.new_date))
            for code, detail in found + PE.check_label(r, ok):
                flag(i, code, detail)
            if r.tier == "decision":
                flag(i, "date_correction_cannot_be_a_decision", str(r.tier))
        elif r.action == "set_postponed":
            if r.tier != "decision":
                flag(i, "postponement_must_be_a_decision", str(r.tier))
            if str(r.expected_store_date) >= as_of:
                flag(i, "postponement_of_a_future_fixture", str(r.expected_store_date))
            if not _isnull(r.home_goals) or not _isnull(r.away_goals):
                flag(i, "postponement_with_a_score", f"{r.home_goals}-{r.away_goals}")
    return issues, bad


def classify(df: pd.DataFrame, bad: set, stored: dict, tiers: set) -> list:'''),
    ("def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, proposals: Path = PROPOSALS, tiers=(\"strong\",), as_of: str | None = None, report_dir: Path | None = None) -> dict:\n    as_of = as_of or date.today().isoformat()\n    store = Path(store).resolve()\n",
     "def run(store: Path, apply: bool = False, production: bool = False, backup: Path | None = None, proposals: Path = PROPOSALS, tiers=(\"strong\",), as_of: str | None = None, report_dir: Path | None = None, evidence: str = \"restricted\") -> dict:\n    as_of = as_of or date.today().isoformat()\n    store = Path(store).resolve()\n    if evidence not in (\"restricted\", \"published\"):\n        raise SystemExit(\"--evidence must be 'restricted' (default) or 'published'\")\n    published_mode = evidence == \"published\"\n    if published_mode and proposals == PROPOSALS:\n        proposals = PUBLISHED\n"),
    ("        df = load_proposals(proposals)\n        issues, bad = validate(df, known, as_of)\n", "        if published_mode:\n            df = load_published(proposals)\n            issues, bad = validate_published(df, known, as_of)\n        else:\n            df = load_proposals(proposals)\n            issues, bad = validate(df, known, as_of)\n"),
    ("report = dict(mode=\"apply\" if apply else \"dry-run\", store=str(store), as_of=as_of, tiers_enabled=", "report = dict(mode=\"apply\" if apply else \"dry-run\", evidence=evidence, store=str(store), as_of=as_of, tiers_enabled="),
    ("VALUES ('reconcile_import','Phase 4.23 reconciliation proposals (offline evidence)',?,'running')\", (ts,)).lastrowid",
     "VALUES ('reconcile_import',?,?,'running')\", (\"published evidence file (Wikipedia, openfootball, OpenLigaDB values)\" if published_mode else 'Phase 4.23 reconciliation proposals (offline evidence)', ts)).lastrowid"),
    ("(snap, \"reconciliation\", \"csv\", None, L._rel(Path(proposals)), report[\"proposals_sha256\"], Path(proposals).stat().st_size, ts, None, \"scores: Wikipedia CC BY-SA 4.0; dates are facts cross-checked in several public sources\",",
     "(snap, \"reconciliation\", \"csv\", None, L._rel(Path(proposals)), report[\"proposals_sha256\"], Path(proposals).stat().st_size, ts, None, (\"published evidence: values from Wikipedia (CC BY-SA 4.0), openfootball (CC0) and OpenLigaDB (ODbL); restricted cross-check sources are not part of it\" if published_mode else \"scores: Wikipedia CC BY-SA 4.0; dates are facts cross-checked in several public sources\"),"),
    ("    ap.add_argument(\"--report-dir\", help=\"write the JSON report and decisions CSV here\")\n    a = ap.parse_args(argv)", "    ap.add_argument(\"--report-dir\", help=\"write the JSON report and decisions CSV here\")\n    ap.add_argument(\"--evidence\", choices=(\"restricted\", \"published\"), default=\"restricted\", help=\"restricted (default): the Phase 4.23 proposals with their local cross-check columns; published: only redistributable evidence (see published_evidence.py)\")\n    a = ap.parse_args(argv)"),
])
print("patched")
