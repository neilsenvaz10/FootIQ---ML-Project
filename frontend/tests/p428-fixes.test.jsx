import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { MetaProvider } from "../src/components/MetaContext.jsx";
import Predict from "../src/pages/Predict.jsx";
import SeasonSimulator from "../src/pages/SeasonSimulator.jsx";

configure({ asyncUtilTimeout: 5000 });
const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const META = { attribution: [], data_through: { club_results: "2026-10-24", international_ratings: "2026-06-02" }, limitations: [] };
const COMPS = [
  { key: "EPL", name: "English Premier League", group: "Domestic league", badge: "Validated", basis: "club v1 test", rows: 3090, seasons: 9, first_date: "2018-08-10", last_date: "2026-09-20", sources: "openfootball", licences: "CC0-1.0" },
  { key: "UCL", name: "UEFA Champions League", group: "Continental club", badge: "Not validated (indicative only)", basis: "no continental validation", rows: 1140, seasons: 9, first_date: "2018-09-18", last_date: "2026-09-10", sources: "openfootball | wikipedia", licences: "CC BY-SA 4.0" },
];
const TEAMS = { EPL: ["Arsenal FC", "Chelsea FC", "Everton FC"], UCL: ["Manchester City FC", "Real Madrid CF"] };
const PROFILE = { usable: true, status: "verified", sources: [] };
const status = (season, remaining) => ({
  competition_key: "BUNDESLIGA", season, state: remaining ? "ready" : "not_eligible", reasons: [], notes: [], blockers: [], can_simulate: false, rule_profile: PROFILE,
  points_only: { label: "Experimental", can_run: remaining > 0, blockers: [], limitations: [], position_bounds: { available: false, blockers: [], bands: [] } }, latest_result: "2026-10-24", days_since_latest_result: 1, missing_share: 0,
  counts: { fixtures: 306, completed: 306 - remaining, missing_results: 0, postponed: 0, remaining_to_simulate: remaining }, limits: { default: 10000, min: 1000, max: 50000 }, limitations: [], saved_runs: 0,
});

let remainingBySeason;
let seasonsList;
let calls;
beforeEach(() => {
  calls = [];
  seasonsList = ["2026-27", "2025-26", "2024-25", "2023-24"];
  remainingBySeason = { "2026-27": 245, "2025-26": 0, "2024-25": 0, "2023-24": 0 };
  vi.stubGlobal(
    "fetch",
    vi.fn((url) => {
      const u = new URL(url);
      const p = u.pathname;
      calls.push({ path: p, q: Object.fromEntries(u.searchParams) });
      if (p === "/api/meta") return json(META);
      if (p === "/api/competitions") return json(COMPS);
      if (p === "/api/gameweeks") return json({ competition_key: u.searchParams.get("key"), season: seasonsList[0], seasons: seasonsList, next_gameweek: 8, gameweeks: [] });
      if (p === "/api/season/status") return json(status(u.searchParams.get("season"), remainingBySeason[u.searchParams.get("season")] ?? 0));
      if (p === "/api/season/runs") return json([]);
      const m = p.match(/^\/api\/competitions\/(\w+)\/(teams|coverage|seasons)$/);
      if (m && m[2] === "teams") return json(TEAMS[m[1]]);
      if (m) return json([]);
      return json({ detail: `unhandled ${p}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const simulator = () => (
  <MemoryRouter initialEntries={["/simulations?tab=season"]}>
    <MetaProvider>
      <SeasonSimulator />
    </MetaProvider>
  </MemoryRouter>
);

describe("Season simulator season list (Phase 4.28)", () => {
  it("offers only the season that still has unplayed fixtures and selects it by default", async () => {
    render(simulator());
    const select = await screen.findByLabelText("Season");
    await waitFor(() => expect(within(select).queryAllByRole("option").length).toBe(1));
    expect(within(select).getByRole("option", { name: "2026-27" })).toBeInTheDocument();
    expect(select).toHaveValue("2026-27");
    for (const old of ["2025-26", "2024-25", "2023-24"]) expect(within(select).queryByRole("option", { name: old })).toBeNull();
    await screen.findByTestId("eligibility-banner");
    expect(calls.filter((c) => c.path === "/api/season/status" && c.q.season === "2026-27").length).toBeGreaterThan(0);
  });

  it("keeps every season that has unplayed fixtures, newest first, and selects the newest", async () => {
    remainingBySeason = { "2026-27": 245, "2025-26": 0, "2024-25": 12, "2023-24": 0 };
    render(simulator());
    const select = await screen.findByLabelText("Season");
    await waitFor(() => expect(within(select).queryAllByRole("option").map((o) => o.textContent)).toEqual(["2026-27", "2024-25"]));
    expect(select).toHaveValue("2026-27");
  });

  it("explains when no season has anything left to simulate and runs no simulation", async () => {
    remainingBySeason = { "2026-27": 0, "2025-26": 0, "2024-25": 0, "2023-24": 0 };
    render(simulator());
    expect(await screen.findByText("No season to simulate")).toBeInTheDocument();
    expect(screen.getByLabelText("Season")).toBeDisabled();
    expect(screen.queryByTestId("eligibility-banner")).toBeNull();
    expect(calls.some((c) => c.path === "/api/season/simulate" || c.path === "/api/season/points")).toBe(false);
  });
});

function Probe() {
  const l = useLocation();
  return <span data-testid="loc">{l.search}</span>;
}
const predict = (route, strict) => {
  const tree = (
    <MemoryRouter initialEntries={[route]}>
      <MetaProvider>
        <Predict />
        <Probe />
      </MetaProvider>
    </MemoryRouter>
  );
  return render(strict ? <React.StrictMode>{tree}</React.StrictMode> : tree);
};

describe.each([
  ["without StrictMode (production build)", false],
  ["inside React.StrictMode (development)", true],
])("Predict Match prefill %s", (_name, strict) => {
  it("keeps the clubs and the competition chosen by the Matches link", async () => {
    predict("/predict?mode=manual&comp=EPL&home=Arsenal+FC&away=Chelsea+FC", strict);
    const home = await screen.findByLabelText("Home team");
    await waitFor(() => expect(within(home).queryByRole("option", { name: "Arsenal FC" })).not.toBeNull());
    await new Promise((r) => setTimeout(r, 60)); // let any deferred reset effect run
    expect(screen.getByLabelText("Home team")).toHaveValue("Arsenal FC");
    expect(screen.getByLabelText("Away team")).toHaveValue("Chelsea FC");
    expect(screen.getByTestId("loc").textContent).toContain("comp=EPL");
  });

  it("works for the Champions League identifiers too", async () => {
    predict("/predict?mode=manual&comp=UCL&home=Manchester+City+FC&away=Real+Madrid+CF", strict);
    const home = await screen.findByLabelText("Home team");
    await waitFor(() => expect(within(home).queryByRole("option", { name: "Manchester City FC" })).not.toBeNull());
    await new Promise((r) => setTimeout(r, 60));
    expect(screen.getByLabelText("Home team")).toHaveValue("Manchester City FC");
    expect(screen.getByLabelText("Away team")).toHaveValue("Real Madrid CF");
  });

  it("still clears the clubs when the user really changes the competition", async () => {
    const user = userEvent.setup();
    predict("/predict?mode=manual&comp=EPL&home=Arsenal+FC&away=Chelsea+FC", strict);
    const home = await screen.findByLabelText("Home team");
    await waitFor(() => expect(within(home).queryByRole("option", { name: "Arsenal FC" })).not.toBeNull());
    await user.selectOptions(await screen.findByLabelText("Competition"), "UCL");
    await waitFor(() => expect(screen.getByTestId("loc").textContent).toContain("comp=UCL"));
    await waitFor(() => expect(screen.getByLabelText("Home team")).toHaveValue(""));
    expect(screen.getByLabelText("Away team")).toHaveValue("");
  });
});
