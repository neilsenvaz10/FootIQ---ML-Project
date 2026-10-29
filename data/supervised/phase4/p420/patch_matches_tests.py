"""Phase 4.20 part C: update frontend/tests/matches.test.jsx for the Champions League in the hub (record of exactly what changed)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
p = ROOT / "frontend" / "tests" / "matches.test.jsx"
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, f"expected one: {old[:70]!r} ({s.count(old)})"
    s = s.replace(old, new)


rep("expect(screen.getByText(/Showing 1 of 3 upcoming matches · all five leagues · newest season/)).toBeInTheDocument();",
    "expect(screen.getByText(/Showing 1 of 3 upcoming matches · all six competitions · newest season/)).toBeInTheDocument();")
rep('render(hub("/matches?comp=UCL&season=2026&matchday=999&status=live"));', 'render(hub("/matches?comp=UEL&season=2026&matchday=999&status=live&team=CLUB:X:y"));       // an archived competition is not a hub competition; a team without a league is dropped')
rep('.toEqual(["All leagues", "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]);', '.toEqual(["All leagues", "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1", "Champions League"]);')
rep('expect(await screen.findByText("Data not fresh in 2 of 5 leagues")).toBeInTheDocument();', 'expect(await screen.findByText("Data not fresh in 2 of 5 competitions")).toBeInTheDocument();')
rep('expect(screen.getByText("Data freshness by league").closest("details")).not.toHaveAttribute("open");', 'expect(screen.getByText("Data freshness by competition").closest("details")).not.toHaveAttribute("open");')

s += '''

// ---------------------------------------------------------------------------------------------------------------- Champions League in the hub (Phase 4.20)
const UCL_BADGE = "Not validated (indicative only)";
const ucl = (id, over = {}) => match(id, { competition_key: "UCL", competition: "UEFA Champions League", matchday_no: 3, matchday_label: "Matches > Matchday 3", validation_badge: UCL_BADGE, eligibility: null, source: "wikipedia", ...over });
const uclScope = (over = {}) => ({ competitions: ["UCL"], seasons: { UCL: "2026-27" }, matchday: null, status: "upcoming", order: "asc", limit: 25, team: null, ...over });
const uclFresh = { ...freshness().competitions.EPL, state: "stale", latest_result: "2026-10-21", approved_sources: [] };
const uclAnswer = (items, over = {}) => answer(items, { scope: uclScope(), freshness: { ...freshness(), competitions: { UCL: uclFresh } }, facets: { seasons: ["2026-27"], matchdays: [1, 2, 3, 4], teams: [{ entity: "CLUB:TST:harbour-city", name: "Harbour City" }, { entity: "CLUB:TST:ashgrove", name: "Ashgrove" }] }, ...over });

describe("Matches: the Champions League", () => {
  it("is a league choice, and asks for it by key", async () => {
    handlers["/api/matches"] = () => json(uclAnswer([ucl(1)]));
    const user = userEvent.setup();
    render(hub());
    await screen.findAllByRole("article");
    await user.click(screen.getByRole("radio", { name: "Champions League" }));
    await waitFor(() => expect(matchCalls().at(-1).q.comp).toBe("UCL"));
    expect(screen.getByTestId("where")).toHaveTextContent("comp=UCL");
    expect(await screen.findByText(/Champions League · newest season/)).toBeInTheDocument();
  });

  it("labels predictions as not validated, and offers no gameweek page (the Champions League has none)", async () => {
    handlers["/api/matches"] = () => json(uclAnswer([ucl(1)]));
    render(hub("/matches?comp=UCL"));
    const row = within(await screen.findByRole("article", { name: "Northbridge United v Eastvale Town" }));
    expect(row.getByText(`Predictions: ${UCL_BADGE}`)).toBeInTheDocument();
    expect(row.getByText("Matches > Matchday 3")).toBeInTheDocument();
    expect(row.queryByRole("link", { name: /Gameweek/ })).toBeNull();
    expect(row.getByRole("link", { name: /Predict Northbridge United v Eastvale Town manually/ })).toHaveAttribute("href", expect.stringContaining("comp=UCL"));
    expect(row.getByRole("link", { name: /Compare Northbridge United and Eastvale Town/ })).toBeInTheDocument();
  });

  it("does not repeat the not-validated chip on a finished match, and still names it in the details", async () => {
    const done = ucl(2, { date: "2026-10-21", status: "completed", stored_status: "completed", kickoff: UTC("2026-10-21"), result: { home_goals: 2, away_goals: 3, source: "wikipedia" }, timing: { phase: "result_stored", ambiguous: false, note: null } });
    handlers["/api/matches"] = () => json(uclAnswer([done], { scope: uclScope({ status: "completed" }) }));
    const user = userEvent.setup();
    render(hub("/matches?comp=UCL&status=completed"));
    const row = within(await screen.findByRole("article", { name: "Northbridge United v Eastvale Town" }));
    expect(row.queryByText(/^Predictions:/)).toBeNull();
    expect(row.getByText("Full time")).toBeInTheDocument();
    await user.click(row.getByRole("button", { name: /Match details/ }));
    expect(row.getByText(/Northbridge United 2-3 Eastvale Town \\(final score, penalties excluded\\)/)).toBeInTheDocument();
    expect(row.getByText("UEFA Champions League · season 2026-27")).toBeInTheDocument();
    expect(row.getByText(UCL_BADGE)).toBeInTheDocument();
    await user.click(row.getByRole("button", { name: /Match details/ }));
    expect(row.queryByText("UEFA Champions League · season 2026-27")).toBeNull();
  });

  it("filters by team once a league is chosen, resets it when the league changes, and ignores a team without a league", async () => {
    handlers["/api/matches"] = () => json(uclAnswer([ucl(1)]));
    const user = userEvent.setup();
    render(hub("/matches?comp=UCL"));
    await screen.findAllByRole("article");
    expect(within(screen.getByLabelText("Team")).getAllByRole("option").map((o) => o.textContent)).toEqual(["All teams", "Harbour City", "Ashgrove"]);
    await user.selectOptions(screen.getByLabelText("Team"), "CLUB:TST:ashgrove");
    await waitFor(() => expect(matchCalls().at(-1).q.team).toBe("CLUB:TST:ashgrove"));
    expect(screen.getByTestId("where")).toHaveTextContent("team=CLUB%3ATST%3Aashgrove");
    await user.click(screen.getByRole("radio", { name: "Premier League" }));
    await waitFor(() => expect(matchCalls().at(-1).q.comp).toBe("EPL"));
    expect(matchCalls().at(-1).q.team).toBeUndefined();
    expect(screen.getByTestId("where")).not.toHaveTextContent("team=");
  });

  it("shows no team filter for all competitions, and never sends a team without a league", async () => {
    render(hub("/matches?team=CLUB:TST:ashgrove"));
    await screen.findAllByRole("article");
    expect(screen.queryByLabelText("Team")).toBeNull();
    expect(matchCalls()[0].q.team).toBeUndefined();
  });

  it("says the Champions League is historical only and not updated automatically", async () => {
    handlers["/api/matches"] = () => json(uclAnswer([ucl(1)]));
    render(hub("/matches?comp=UCL"));
    expect(await screen.findByText("Historical only · newest verified result 2026-10-21 · not updated automatically")).toBeInTheDocument();
  });

  it("lists the Champions League in the freshness disclosure of the all-competitions view", async () => {
    handlers["/api/matches"] = () => json(answer([match(1)], { freshness: { ...freshness(), competitions: { ...freshness().competitions, UCL: uclFresh } } }));
    render(hub());
    expect(await screen.findByText("Data not fresh in 1 of 6 competitions")).toBeInTheDocument();
    expect(screen.getByText(/Historical only · newest verified result 2026-10-21/)).toBeInTheDocument();
  });
});
'''
p.write_text(s, encoding="utf-8")
print("tests patched")
