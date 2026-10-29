import re
from pathlib import Path
R=Path("D:/Foot IQ/app/store")
def sub(path, pairs):
    s=path.read_text(encoding="utf-8")
    for a,b in pairs:
        assert s.count(a)==1,(path.name,a[:70],s.count(a))
        s=s.replace(a,b)
    path.write_text(s,encoding="utf-8")

# --- published_evidence.py
p=R/"published_evidence.py"
s=p.read_text(encoding="utf-8")
s=s.replace('''def assess(r, need_score''','''ATTESTED = False                       # set by an importer run with --evidence attested (see ATTESTED_NOTE); never on by default
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


def assess(r, need_score''',1)
s=s.replace('''    issues = []
    if need_score:
        sc = score_sources(r)
        agree = [s for s, v in sc.items() if v == target_score]
        if len(agree) < 2:''','''    if ATTESTED:
        return assess_attested(r, need_score, need_date, target_score, target_date)
    issues = []
    if need_score:
        sc = score_sources(r)
        agree = [s for s, v in sc.items() if v == target_score]
        if len(agree) < 2:''',1)
s=s.replace('''    label = str(r.evidence_classification)
    if label not in (TWO, INSUFFICIENT):
        return [("bad_evidence_classification", label)]
''','''    label = str(r.evidence_classification)
    if label not in (TWO, INSUFFICIENT):
        return [("bad_evidence_classification", label)]
    if ATTESTED:                                                                # the file honestly says "insufficient"; attested mode accepts that label knowingly
        return []
''',1)
p.write_text(s,encoding="utf-8")

# --- league_results_import.py
sub(R/"league_results_import.py",[
 ('''    published_mode = evidence == "published"
    if evidence not in ("restricted", "published"):
        raise SystemExit("--evidence must be 'restricted' (default) or 'published'")''','''    published_mode = evidence in ("published", "attested")
    if evidence not in ("restricted", "published", "attested"):
        raise SystemExit("--evidence must be 'restricted' (default), 'published' or 'attested'")
    PE.ATTESTED = evidence == "attested"'''),
 ('''("published evidence file (Wikipedia, openfootball, OpenLigaDB values)" if published_mode else 'local staging files''','''("attested snapshot evidence (Wikipedia values; maintainer-attested cross-check)" if PE.ATTESTED else "published evidence file (Wikipedia, openfootball, OpenLigaDB values)" if published_mode else 'local staging files'''),
 ('''("Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; published evidence: score and date confirmed''','''(("Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; " + PE.ATTESTED_NOTE) if PE.ATTESTED else "Wikipedia contributors, 2026-27 league season page (results grid), CC BY-SA 4.0; published evidence: score and date confirmed'''),
 ('''("result from the Wikipedia results grid; fixture date from the stored fixture; published evidence: confirmed''','''(("result from the Wikipedia results grid; fixture date from the stored fixture; " + PE.ATTESTED_NOTE) if PE.ATTESTED else "result from the Wikipedia results grid; fixture date from the stored fixture; published evidence: confirmed'''),
 ('''ap.add_argument("--evidence", choices=("restricted", "published"), default="restricted", help="restricted (default)''','''ap.add_argument("--evidence", choices=("restricted", "published", "attested"), default="restricted", help="attested: like published but ONE redistributable source plus the maintainer's attestation is enough (labelled as such, snapshot use only); restricted (default)'''),
])
