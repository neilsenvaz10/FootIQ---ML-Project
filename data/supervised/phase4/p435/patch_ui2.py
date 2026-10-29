import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]; FE=ROOT/"frontend"/"src"; B=Path(__file__).resolve().parent/"before"
def edit(rel,pairs):
    p=FE/rel; shutil.copy2(p,B/("2__"+rel.replace("/","__")))
    raw=p.read_bytes().decode("utf-8"); crlf="\r\n" in raw; s=raw.replace("\r\n","\n")
    for a,b in pairs:
        assert s.count(a)==1,(rel,a[:70],s.count(a)); s=s.replace(a,b)
    p.write_bytes((s.replace("\n","\r\n") if crlf else s).encode("utf-8"))
edit("lib/fixtures.js",[
 ('return fresh.state === "fresh" ? { tone: "ok", text: `Data fresh · ${latest}` } : { tone: "warn", text: `Data not fresh · ${latest}` };','return fresh.state === "fresh" ? { tone: "ok", text: `Data fresh · ${latest}` } : null; // a "Data not fresh" warning chip is no longer shown (Phase 4.35)'),
 ('''  if (key === "UCL") {
    const latest = fresh.latest_result ? `newest verified result ${fresh.latest_result}` : "no verified result stored";
    return { tone: "warn", text: `Historical only · ${latest} · not updated automatically` };
  }
''','''  if (key === "UCL") return null;                    // the amber "Historical only" chip is no longer shown (Phase 4.35)
'''),
])
edit("pages/Matches.jsx",[
 ('{one ? <Chip tone={one.tone}>{one.text}</Chip> : <Chip tone={stale ? "warn" : "ok"}>{stale === 0 ? `Data fresh in all ${entries.length} competitions` : `Data not fresh in ${stale} of ${entries.length} competitions`}</Chip>}','{one ? <Chip tone={one.tone}>{one.text}</Chip> : stale === 0 ? <Chip tone="ok">{`Data fresh in all ${entries.length} competitions`}</Chip> : null}'),
 ('{!one && (\n        <details className="group">','{!one && stale === 0 && (\n        <details className="group">'),
 ('{competitionFreshness(k, c).text}','{competitionFreshness(k, c)?.text}'),
])
edit("components/home/FeaturedMatch.jsx",[
 ('{rel ? <Chip tone="warn">Provisional history</Chip> : <Chip tone="ok">Fully supported history</Chip>}','{rel ? null : <Chip tone="ok">Fully supported history</Chip>}'),
])
print("ok")
