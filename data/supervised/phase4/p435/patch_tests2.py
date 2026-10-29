"""Phase 4.35: second round of test updates (freshness / provisional chips removed)."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
T = ROOT / "frontend" / "tests"
B = Path(__file__).resolve().parent / "before"


def edit(name, pairs):
    p = T / name
    shutil.copy2(p, B / ("2_test__" + name))
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    for a, b in pairs:
        assert s.count(a) == 1, (name, a[:80], s.count(a))
        s = s.replace(a, b)
    p.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


edit("fixtures.test.js", [
    ('    expect(freshnessText({ state: "stale", latest_result: "2026-09-20" })).toEqual({ tone: "warn", text: "Data not fresh · newest verified result 2026-09-20" });\n    expect(freshnessText({ state: "unknown", latest_result: null })).toEqual({ tone: "warn", text: "Data not fresh · no verified result stored" });',
     '    expect(freshnessText({ state: "stale", latest_result: "2026-09-20" })).toBeNull(); // no "Data not fresh" warning chip any more (Phase 4.35)\n    expect(freshnessText({ state: "unknown", latest_result: null })).toBeNull();'),
])
edit("home.test.jsx", [
    ('    expect(within(b).getByText("Data not fresh · newest verified result 2026-10-25")).toBeInTheDocument();\n    expect(within(b).getByText("Provisional history")).toBeInTheDocument();\n    expect(within(b).queryByText("Fully supported history")).toBeNull();',
     '    expect(within(b).queryByText("Data not fresh · newest verified result 2026-10-25")).toBeNull(); // warning chips removed (Phase 4.35)\n    expect(within(b).queryByText("Provisional history")).toBeNull();\n    expect(within(b).queryByText("Fully supported history")).toBeNull();'),
    ('    expect(within(card).getByText("Data not fresh · newest verified result 2026-10-25")).toBeInTheDocument();', '    expect(within(card).queryByText("Data not fresh · newest verified result 2026-10-25")).toBeNull();'),
])
edit("matches.test.jsx", [
    ('    expect(await screen.findByText("Data not fresh · newest verified result 2026-10-25")).toBeInTheDocument();\n    expect(screen.getByText(/Historical data, synchronised periodically\\. Nothing here is live\\./)).toBeInTheDocument();',
     '    expect(await screen.findByText(/Historical data, synchronised periodically\\. Nothing here is live\\./)).toBeInTheDocument();\n    expect(screen.queryByText("Data not fresh · newest verified result 2026-10-25")).toBeNull(); // warning chip removed (Phase 4.35)'),
    ('    expect(await screen.findByText("Data not fresh in 2 of 5 competitions")).toBeInTheDocument();\n    expect(screen.getByText("Data freshness by competition").closest("details")).not.toHaveAttribute("open");\n    expect(screen.getByText(/Data not fresh · newest verified result 2026-09-20/)).toBeInTheDocument();\n    expect(screen.getAllByText(/Data fresh · newest verified result 2026-10-25/)).toHaveLength(3);',
     '    expect(await screen.findByText(/Historical data, synchronised periodically/)).toBeInTheDocument();\n    expect(screen.queryByText("Data not fresh in 2 of 5 competitions")).toBeNull(); // warning chip and the per-competition disclosure are not shown while data is stale (Phase 4.35)\n    expect(screen.queryByText("Data freshness by competition")).toBeNull();'),
    ('    expect(await screen.findByText("Historical only · newest verified result 2026-10-21 · not updated automatically")).toBeInTheDocument();',
     '    expect(await screen.findByText(/Historical data, synchronised periodically/)).toBeInTheDocument();\n    expect(screen.queryByText(/Historical only · newest verified result 2026-10-21/)).toBeNull(); // amber chip removed (Phase 4.35)'),
    ('    expect(await screen.findByText("Data not fresh in 1 of 6 competitions")).toBeInTheDocument();\n    expect(screen.getByText(/Historical only · newest verified result 2026-10-21/)).toBeInTheDocument();',
     '    expect(await screen.findByText(/Historical data, synchronised periodically/)).toBeInTheDocument();\n    expect(screen.queryByText("Data not fresh in 1 of 6 competitions")).toBeNull();\n    expect(screen.queryByText(/Historical only · newest verified result 2026-10-21/)).toBeNull();'),
])
print("patched")
