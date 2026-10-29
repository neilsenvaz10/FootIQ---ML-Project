"""Phase 4.35: updates the frontend tests that asserted the amber banners and chips the owner asked to remove: they now assert that those warnings are NOT shown. Before-copies in p435/before/."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
T = ROOT / "frontend" / "tests"
BEFORE = Path(__file__).resolve().parent / "before"
BEFORE.mkdir(exist_ok=True)


def edit(name, pairs):
    p = T / name
    shutil.copy2(p, BEFORE / ("test__" + name))
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    for a, b in pairs:
        assert s.count(a) == 1, (name, a[:80], s.count(a))
        s = s.replace(a, b)
    p.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


edit("fixtures.test.js", [
    ('      expect(kickoffText(k)).toBe("time not confirmed");\n      expect(kickoffShort(k)).toBe("Time not confirmed");',
     '      expect(kickoffText(k)).toBe("");\n      expect(kickoffShort(k)).toBe("");'),
    ('expect(kickoffParts(k)).toEqual({ time: "Time not confirmed", note: null });', 'expect(kickoffParts(k)).toEqual({ time: "", note: null });'),
    ('''    expect(timingChip({ phase: "today_time_zone_unconfirmed" })).toEqual(["Today · time zone unconfirmed", "info"]);
    expect(timingChip({ phase: "today_time_unknown" })).toEqual(["Today · time not stated", "info"]);
    expect(timingChip({ phase: "kickoff_passed" })).toEqual(["Kickoff passed · no result yet", "warn"]);
''', '''    for (const phase of ["today_time_zone_unconfirmed", "today_time_unknown", "kickoff_passed"]) expect(timingChip({ phase })).toBeNull(); // no warning chip any more (Phase 4.35)
'''),
])
edit("gameweek.test.jsx", [
    ('    expect(screen.getByText(/EPL results are stale/)).toBeInTheDocument();', '    expect(screen.queryByText(/EPL results are stale/)).toBeNull(); // the amber stale notice is no longer shown (Phase 4.35)'),
    ('    expect(screen.getByText("time not confirmed")).toBeInTheDocument();', '    expect(screen.queryByText("time not confirmed")).toBeNull(); // nothing is said when the store has no time (Phase 4.35)'),
])
edit("home.test.jsx", [
    ('    ["no time at all", UNKNOWN, "time not confirmed"],', '    ["no time at all", UNKNOWN, ""],'),
    ('''    const b = await banner();
    expect(within(b).getByText(written)).toBeInTheDocument();
    expect(b).not.toHaveTextContent(/\\bUTC\\b/);''', '''    const b = await banner();
    if (written) expect(within(b).getByText(written)).toBeInTheDocument();
    else expect(b).not.toHaveTextContent(/time not confirmed/i);
    expect(b).not.toHaveTextContent(/\\bUTC\\b/);'''),
    ('    expect(within(b).getByText("Today · time zone unconfirmed")).toBeInTheDocument();', '    expect(within(b).queryByText("Today · time zone unconfirmed")).toBeNull(); // chip removed (Phase 4.35)'),
    ('    expect(within(card).getByText("Time not confirmed")).toBeInTheDocument();', '    expect(within(card).queryByText("Time not confirmed")).toBeNull(); // nothing is said when the store has no time (Phase 4.35)'),
    ('    expect(within(card).getByText("Partial season: 70 of 380 matches in the data")).toBeInTheDocument();', '    expect(within(card).queryByText("Partial season: 70 of 380 matches in the data")).toBeNull(); // chip removed (Phase 4.35)'),
])
edit("leagues.test.jsx", [
    ('  expect(screen.getByText(/Partial season: 7 of 380/)).toBeInTheDocument();\n  expect(screen.getByText(/3 fixtures have no verified result/)).toBeInTheDocument();',
     '  expect(screen.queryByText(/Partial season: 7 of 380/)).toBeNull();\n  expect(screen.queryByText(/3 fixtures have no verified result/)).toBeNull(); // amber notices removed (Phase 4.35)'),
    ('await screen.findByText(/Partial season: 7 of 380/);', 'await screen.findByText(/not an official tie-break/);'),
])
edit("matches.test.jsx", [
    ('    expect(first.getByText("Today · time zone unconfirmed")).toBeInTheDocument();', '    expect(first.queryByText("Today · time zone unconfirmed")).toBeNull(); // chip removed (Phase 4.35)'),
    ('    expect(row.getByText("Kickoff passed · no result yet")).toBeInTheDocument();', '    expect(row.queryByText("Kickoff passed · no result yet")).toBeNull(); // chip removed (Phase 4.35)'),
])
edit("redesign.test.jsx", [
    ('    expect(screen.getByText("1 leagues stale")).toBeInTheDocument();', '    expect(screen.queryByText("1 leagues stale")).toBeNull(); // the amber chip is no longer shown (Phase 4.35)'),
])
edit("sync-status.test.jsx", [
    ('    expect(await screen.findByRole("alert")).toHaveTextContent("57 unresolved sync finding(s) need a human decision");',
     '    await screen.findByText(/Scheduler:/);\n    expect(screen.queryByRole("alert")).toBeNull(); // the amber quarantine banner is no longer shown (Phase 4.35); the count stays in Details'),
])
print("patched")
