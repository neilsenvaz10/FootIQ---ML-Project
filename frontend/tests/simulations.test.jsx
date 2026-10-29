import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Simulator, { WORLDCUP_GROUPS, estimateSeconds, validateInputs } from "../src/pages/Simulator.jsx";
import Simulations from "../src/pages/Simulations.jsx";
import { MetaProvider } from "../src/components/MetaContext.jsx";

const json = (body, status = 200) =>
  Promise.resolve({
    ok: status < 400,
    status,
    statusText: "OK",
    json: () => Promise.resolve(body),
  });

let handlers;
beforeEach(() => {
  handlers = {};
  vi.stubGlobal(
    "fetch",
    vi.fn((url, init) => {
      const u = new URL(url);
      if (handlers[u.pathname]) return handlers[u.pathname](u, init);
      if (u.pathname === "/api/meta") return json({ attribution: [], data_through: {}, limitations: [] });
      if (u.pathname === "/api/worldcup/simulate") {
        return json({
          mode: "pre_tournament",
          simulations: 1000,
          seed: 42,
          seconds: 1.2,
          engine: "v2.3 team power Monte Carlo",
          note: "Pre-tournament model test run.",
          metadata: {},
          title_odds: [
            {
              rank: 1,
              team: "France",
              group: "I",
              qualify_knockout_pct: 94.2,
              round_of_16_pct: 68.5,
              quarter_final_pct: 43.1,
              semi_final_pct: 27.8,
              final_pct: 16.5,
              champion_pct: 11.2,
            },
            {
              rank: 2,
              team: "Spain",
              group: "H",
              qualify_knockout_pct: 91.0,
              round_of_16_pct: 64.0,
              quarter_final_pct: 40.0,
              semi_final_pct: 25.0,
              final_pct: 15.0,
              champion_pct: 10.0,
            },
          ],
          group_tables: null,
        });
      }
      return json({ detail: `unhandled ${u.pathname}` }, 404);
    })
  );
});

afterEach(() => vi.unstubAllGlobals());

const renderWithProviders = (ui) =>
  render(
    <MemoryRouter>
      <MetaProvider>{ui}</MetaProvider>
    </MemoryRouter>
  );

describe("Simulations UI and World Cup Simulator (P4.5)", () => {
  it("renders tournament overview with 12 groups and 48 qualified nations", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Simulator />);

    expect(screen.getByText("FIFA World Cup 2026")).toBeInTheDocument();
    expect(screen.getByText(/48 Qualified Nations · 12 Groups/)).toBeInTheDocument();

    const toggleBtn = screen.getByRole("button", { name: /View all 48 qualified teams/i });
    expect(toggleBtn).toBeInTheDocument();

    await user.click(toggleBtn);
    expect(screen.getByTestId("worldcup-teams-grid")).toBeInTheDocument();
    expect(screen.getByText("Group A")).toBeInTheDocument();
    expect(screen.getByText("Group L")).toBeInTheDocument();

    // Verify groups object has 12 groups and 48 teams
    expect(Object.keys(WORLDCUP_GROUPS)).toHaveLength(12);
    const totalTeams = Object.values(WORLDCUP_GROUPS).reduce((acc, g) => acc + g.length, 0);
    expect(totalTeams).toBe(48);

    // Toggle off
    await user.click(screen.getByRole("button", { name: /Hide qualified teams/i }));
    expect(screen.queryByTestId("worldcup-teams-grid")).toBeNull();
  });

  it("fixes undersized simulation radio inputs with proper sizing and accessible labels", async () => {
    renderWithProviders(<Simulator />);

    const preRadio = screen.getByLabelText(/Pre-tournament/i);
    const archRadio = screen.getByLabelText(/Archived state/i);

    expect(preRadio).toBeInTheDocument();
    expect(archRadio).toBeInTheDocument();

    // Verify radio input has classes h-5 w-5
    expect(preRadio.className).toContain("h-5");
    expect(preRadio.className).toContain("w-5");
    expect(archRadio.className).toContain("h-5");
    expect(archRadio.className).toContain("w-5");

    // Pre-tournament should be selected by default
    expect(preRadio).toBeChecked();
    expect(archRadio).not.toBeChecked();

    const user = userEvent.setup();
    await user.click(archRadio);
    expect(archRadio).toBeChecked();
    expect(preRadio).not.toBeChecked();
  });

  it("displays qualification and advancement probabilities (qualify_knockout_pct) in leaderboard", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Simulator />);

    const runBtn = screen.getByRole("button", { name: "Run simulation" });
    await user.click(runBtn);

    expect(await screen.findByText(/Pre-tournament model test run/)).toBeInTheDocument();

    // Leaderboard shows Qualify percentage
    expect(screen.getByText(/Qualify 94.2%/)).toBeInTheDocument();
    expect(screen.getByText(/Qualify 91%/)).toBeInTheDocument();

    // Metadata chips
    expect(screen.getAllByText(/1,000/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/v2.3 team power Monte Carlo/).length).toBeGreaterThan(0);
  });

  it("allows group filtering in the leaderboard", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Simulator />);

    await user.click(screen.getByRole("button", { name: "Run simulation" }));
    expect(await screen.findByText("Title probabilities")).toBeInTheDocument();

    // Click filter for Group H
    const groupHBtn = screen.getByRole("button", { name: "H" });
    await user.click(groupHBtn);

    // Spain should be visible, France (Group I) should not be visible in filtered list
    expect(screen.getByText("Spain")).toBeInTheDocument();
    expect(screen.queryByText("France")).toBeNull();

    // Switch back to All
    await user.click(screen.getByRole("button", { name: "All" }));
    expect(screen.getByText("France")).toBeInTheDocument();
    expect(screen.getByText("Spain")).toBeInTheDocument();
  });

  it("validates simulation inputs correctly", () => {
    expect(validateInputs("1000", "")).toBeNull();
    expect(validateInputs("50", "")).toContain("Simulations must be a whole number");
    expect(validateInputs("50001", "")).toContain("Simulations must be a whole number");
    expect(validateInputs("1000", "-5")).toContain("Seed must be a whole number");
    expect(estimateSeconds("pre_tournament", 10000)).toBe(16);
    expect(estimateSeconds("current", 10000)).toBe(2);
  });
});
