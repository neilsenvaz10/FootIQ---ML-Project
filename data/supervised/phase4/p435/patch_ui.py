"""Phase 4.35: removes the amber warning banners and chips the owner asked to remove from the interface (before-copies in p435/before/). Presentation only; the backend data and safeguards are unchanged."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FE = ROOT / "frontend" / "src"
BEFORE = Path(__file__).resolve().parent / "before"
BEFORE.mkdir(exist_ok=True)


def edit(rel, pairs):
    p = FE / rel
    shutil.copy2(p, BEFORE / rel.replace("/", "__"))
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    for a, b in pairs:
        assert s.count(a) == 1, (rel, a[:70], s.count(a))
        s = s.replace(a, b)
    p.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


edit("components/SyncStatus.jsx", [
    ('  const stale = data.competitions.filter((c) => c.state === "stale" && c.scheduled + c.awaiting_result > 0);\n', ""),
    ('        {stale.length > 0 && <span className={`rounded-full px-2.5 py-0.5 font-semibold ${TONE.stale}`}>{stale.length} leagues stale</span>}\n', ""),
    ('      {qr?.warning && (\n        <div role="alert" className="border-t border-warn/40 bg-warn/10 px-4 py-2 text-xs font-semibold text-warn">\n          {qr.warning}\n        </div>\n      )}\n', ""),
])
edit("lib/leagues.js", [
    ('  const partial = coverage?.note === "incomplete or in progress";\n', ""),
    ('''  if (partial) {
    out.push({
      key: "partial",
      tone: "warn",
      label: coverage.expected_matches ? `Partial season: ${coverage.rows_in_dataset} of ${coverage.expected_matches} matches in the data` : "Partial season",
      text: "The table covers only the matches stored so far; clubs may have played different numbers of matches.",
    });
  }
''', ""),
    ('''    if (sync.awaiting_result > 0) {
      out.push({ key: "missing", tone: "warn", label: `${sync.awaiting_result} fixture${sync.awaiting_result === 1 ? " has" : "s have"} no verified result`, text: "Matches whose date has passed but that have no verified result are not in the table." });
    }
    if (sync.state && sync.state !== "fresh") {
      out.push({ key: "stale", tone: "warn", label: `Data not fresh · newest verified result ${sync.latest_result ?? "unknown"}`, text: (sync.state_reasons ?? []).join(" ") || "No approved source has confirmed this league recently." });
    } else if (sync?.state === "fresh") {''', '''    if (sync?.state === "fresh") {'''),
])
edit("pages/Analytics.jsx", [
    ('      <Chip tone="info">{coverage?.note === "incomplete or in progress" ? "Partial season" : coverage?.expected_matches && coverage.rows_in_dataset === coverage.expected_matches ? "Expected match count present" : "Completeness unconfirmed"}</Chip>\n',
     '      {coverage?.note !== "incomplete or in progress" && coverage?.expected_matches && coverage.rows_in_dataset === coverage.expected_matches ? <Chip tone="info">Expected match count present</Chip> : null}\n'),
])
edit("components/home/LeagueOverview.jsx", [
    ('            {partial && row?.expected_matches ? <Chip tone="warn">Partial season: {int(row.rows_in_dataset)} of {int(row.expected_matches)} matches in the data</Chip> : null}\n', ""),
])
edit("pages/GameweekPredict.jsx", [
    ('''      {league && league.state === "stale" && (
        <Notice tone="warn" title={`${key} results are stale.`}>
          Newest verified result {league.latest_result ?? "unknown"}; {league.awaiting_result} played match(es) have no result in any approved source. Forecasts that depend on them are marked provisional.
        </Notice>
      )}

''', ""),
])
edit("lib/fixtures.js", [
    ('  return "time not confirmed";\n}', '  return "";\n}'),
    ('  return "Time not confirmed";\n}', '  return "";\n}'),
    ('  return { time: "Time not confirmed", note: null };', '  return { time: "", note: null };'),
    ('''  switch (timing?.phase) {
    case "today_time_zone_unconfirmed":
      return ["Today · time zone unconfirmed", "info"];
    case "today_time_unknown":
      return ["Today · time not stated", "info"];
    case "kickoff_passed":
      return ["Kickoff passed · no result yet", "warn"];
    default:
      return null;
  }''', '''  void timing;                                    // the "time not stated" / "kickoff passed" chips are no longer shown (owner request, Phase 4.35)
  return null;'''),
])
edit("components/Kickoff.jsx", [
    ('  const p = kickoffParts(k);\n  return (', '  const p = kickoffParts(k);\n  if (!p.time) return null;\n  return ('),
])
print("patched")
