"""Published-evidence mode of the domestic importers (Phase 4.36).

The standard mode of `league_results_import.py` and `reconcile_import.py` verifies every change against a second source that is NOT redistributable (football-data.co.uk, FixtureDownload,
football-data.org). Their values can therefore not be published. The published-evidence mode is a SEPARATE, explicitly selected mode (`--evidence published`) that uses only evidence whose values
may lawfully be redistributed: Wikipedia (CC BY-SA 4.0), openfootball (CC0 1.0) and OpenLigaDB (ODbL 1.0). It keeps the same two-source rule, applied to those sources only:

  * a result needs the SAME score from at least two distinct allowed sources (the values of each are in the file);
  * a played day / corrected date needs the SAME date from at least two distinct allowed sources;
  * a file that carries any restricted-provider column is refused as a whole (restricted values must never be mixed into published evidence);
  * a record that does not meet the rule is not applied and is reported (`insufficient_published_evidence`): it is never accepted on a single source, and the stored values stay as they are.
Nothing in the standard mode is changed. The classification label in the file is recomputed from the recorded values; a label that contradicts them rejects the row."""
from pathlib import Path

import pandas as pd

ALLOWED_SOURCES = {"wikipedia": "CC BY-SA 4.0", "openfootball": "CC0-1.0", "openligadb": "ODbL-1.0"}
RESTRICTED_FRAGMENTS = ("footballdata", "fixturedownload", "provider_", "apifootball", "api_football", "statsbomb")
TWO = "two_redistributable_sources"
INSUFFICIENT = "insufficient_redistributable_evidence"
COLUMNS = ["evidence_id", "importer", "action", "competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "expected_store_status", "expected_store_date", "new_date", "home_goals", "away_goals",
           "wikipedia_score", "wikipedia_revision", "wikipedia_date", "openligadb_score", "openligadb_date", "openligadb_ref", "openfootball_score", "openfootball_date",
           "production_tier", "evidence_classification", "restricted_cross_check_used_in_production", "review_decision", "confidence", "uncertainty", "licence", "provenance"]
REQUIRED = COLUMNS


def forbidden_columns(columns) -> list:
    return [c for c in columns if any(f in str(c).lower() for f in RESTRICTED_FRAGMENTS)]


def load(path: Path, importer: str) -> pd.DataFrame:
    """Read a published-evidence file and keep the rows of one importer ('league_results' or 'reconcile'). Refuses a file with a restricted column or without the required columns."""
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=True)
    bad = forbidden_columns(df.columns)
    if bad:
        raise SystemExit(f"published evidence must not contain restricted provider columns: {bad}")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"published evidence file lacks columns: {missing}")
    df = df[df["importer"] == importer].reset_index(drop=True)
    for c in ("home_goals", "away_goals", "wikipedia_revision"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _nn(v) -> bool:
    return v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip() != ""


def score_sources(r) -> dict:
    """source -> recorded score, for the allowed sources that recorded one."""
    return {s: str(getattr(r, f"{s}_score")) for s in ALLOWED_SOURCES if hasattr(r, f"{s}_score") and _nn(getattr(r, f"{s}_score"))}


def date_sources(r, target) -> dict:
    """source -> recorded date, for the allowed sources that recorded one."""
    return {s: str(getattr(r, f"{s}_date")) for s in ALLOWED_SOURCES if hasattr(r, f"{s}_date") and _nn(getattr(r, f"{s}_date"))}


ATTESTED = False                       # set by an importer run with --evidence attested (see ATTESTED_NOTE); never on by default
ATTESTED_NOTE = ("attested snapshot evidence: ONE redistributable source (Wikipedia / the stored fixture date) supports this value; the maintainer attests that a private, non-redistributable cross-check agreed. "
                 "It is NOT independently reproducible from public data.")


def assess_attested(r, need_score: bool, need_date: bool, target_score: str | None, target_date: str | None) -> tuple[bool, list]:
    """Attested mode: the value must be supported by at least one redistributable source (a score: Wikipedia), no allowed source may disagree, and the row must carry the attestation flag."""
    issues = []
    if str(getattr(r, "restricted_cross_check_used_in_production", "")).lower() != "true":
        issues.append(("attestation_missing", "restricted_cross_check_used_in_production is not true"))
    if need_score:
        sc = score_sources(r)
        if sc.get("wikipedia") != target_score:
            issues.append(("no_wikipedia_support_for_score", f"score {target_score}, recorded {sc}"))
        if any(v != target_score for v in sc.values()):
            issues.append(("allowed_sources_disagree_on_score", f"{sc}"))
    if need_date:
        dt = date_sources(r, target_date)
        if not [s for s, v in dt.items() if v == target_date]:
            issues.append(("no_redistributable_source_for_date", f"date {target_date}, recorded {dt}"))
    return (not issues), issues


def assess(r, need_score: bool, need_date: bool, target_score: str | None, target_date: str | None) -> tuple[bool, list]:
    """Is the evidence sufficient under the two-source rule over the allowed sources? Returns (ok, [(code, detail)])."""
    if ATTESTED:
        return assess_attested(r, need_score, need_date, target_score, target_date)
    issues = []
    if need_score:
        sc = score_sources(r)
        agree = [s for s, v in sc.items() if v == target_score]
        if len(agree) < 2:
            issues.append(("insufficient_published_evidence", f"score {target_score}: allowed sources agreeing {agree}, recorded {sc}"))
        if len(agree) != len(sc):
            issues.append(("allowed_sources_disagree_on_score", f"{sc}"))
    if need_date:
        dt = date_sources(r, target_date)
        agree = [s for s, v in dt.items() if v == target_date]
        if len(agree) < 2:
            issues.append(("insufficient_published_evidence", f"date {target_date}: allowed sources agreeing {agree}, recorded {dt}"))
    return (not issues), issues


def check_label(r, ok: bool) -> list:
    """The label must follow from the values: two_redistributable_sources only when the rule is met."""
    label = str(r.evidence_classification)
    if label not in (TWO, INSUFFICIENT):
        return [("bad_evidence_classification", label)]
    if ATTESTED:                                                                # the file honestly says "insufficient"; attested mode accepts that label knowingly
        return []
    if (label == TWO) != ok:
        return [("label_contradicts_recorded_evidence", f"label {label}, rule met: {ok}")]
    return []
