from pathlib import Path
p=Path("D:/Foot IQ/app/store/reconcile_import.py")
s=p.read_text(encoding="utf-8")
def rep(a,b):
    global s
    assert s.count(a)==1,(a[:60],s.count(a)); s=s.replace(a,b)
rep('''    if evidence not in ("restricted", "published"):
        raise SystemExit("--evidence must be 'restricted' (default) or 'published'")
    published_mode = evidence == "published"''','''    if evidence not in ("restricted", "published", "attested"):
        raise SystemExit("--evidence must be 'restricted' (default), 'published' or 'attested'")
    published_mode = evidence in ("published", "attested")
    PE.ATTESTED = evidence == "attested"''')
rep('''("published evidence file (Wikipedia, openfootball, OpenLigaDB values)" if published_mode else 'Phase 4.23''','''("attested snapshot evidence (Wikipedia values; maintainer-attested cross-check)" if PE.ATTESTED else "published evidence file (Wikipedia, openfootball, OpenLigaDB values)" if published_mode else 'Phase 4.23''')
rep('''("published evidence: values from Wikipedia (CC BY-SA 4.0), openfootball (CC0) and OpenLigaDB (ODbL); restricted cross-check sources are not part of it" if published_mode''','''(PE.ATTESTED_NOTE + " Values: Wikipedia (CC BY-SA 4.0), openfootball (CC0), OpenLigaDB (ODbL)." if PE.ATTESTED else "published evidence: values from Wikipedia (CC BY-SA 4.0), openfootball (CC0) and OpenLigaDB (ODbL); restricted cross-check sources are not part of it" if published_mode''')
rep('''f"{d['action_type']} ({d['tier']}): {d['evidence']} | store before:''','''(f"{d['action_type']} ({d['tier']}): {PE.ATTESTED_NOTE}" if PE.ATTESTED else f"{d['action_type']} ({d['tier']}): {d['evidence']}") + f" | store before:''')
rep('''ap.add_argument("--evidence", choices=("restricted", "published"), default="restricted", help="restricted (default)''','''ap.add_argument("--evidence", choices=("restricted", "published", "attested"), default="restricted", help="attested: one redistributable source plus the maintainer's attestation (labelled, snapshot use only); restricted (default)''')
p.write_text(s,encoding="utf-8")
