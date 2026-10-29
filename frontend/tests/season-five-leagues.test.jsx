import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { MetaProvider } from "../src/components/MetaContext.jsx";
import SeasonSimulator, { SEASON_LEAGUES } from "../src/pages/SeasonSimulator.jsx";

configure({ asyncUtilTimeout: 5000 });
const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const META = { attribution: [], data_through: { club_results: "2026-10-26", international_ratings: "2026-06-02" }, limitations: [] };
const LABELS = { EPL: "Premier League", LALIGA: "La Liga", BUNDESLIGA: "Bundesliga", SERIEA: "Serie A", LIGUE1: "Ligue 1" };
const PROFILE = { usable: true, status: "verified", sources: [] };
const SPEC = { EPL: { fixtures: 380, completed: 80, clubs: 20, state: "ready" }, LALIGA: { fixtures: 380, completed: 99, clubs: 20, state: "ready" }, BUNDESLIGA: { fixtures: 306, completed: 63, clubs: 18, state: "ready" },
  SERIEA: { fixtures: 380, completed: 80, clubs: 20, state: "provisional" }, LIGUE1: { fixtures: 306, completed: 72, clubs: 18, state: "ready" } };
const status = (key) => {
  const sp = SPEC[key];
  const missing = key === "SERIEA" ? 3 : 0;
  return {
    competition_key: key, season: "2026-27", state: sp.state, reasons: missing ? [`${missing} fixture(s) dated up to today have no verified result (3.6% of played-date fixtures); they are simulated like future fixtures`] : [], notes: [],
    blockers: ["final-position predictions are disabled: no scoreline method has passed the predeclared acceptance criteria"], can_simulate: false, rule_profile: PROFILE,
    points_only: { label: "Experimental — Points-only simulation", can_run: true, blockers: [], limitations: ["Only win, draw and loss are simulated."], position_bounds: { available: key === "LALIGA" || key === "BUNDESLIGA", blockers: [], bands: ["title", "top4", "relegation"] } },
    latest_result: "2026-10-26", days_since_latest_result: 2, missing_share: 0,
    counts: { fixtures: sp.fixtures, completed: sp.completed, missing_results: missing, postponed: 0, remaining_to_simulate: sp.fixtures - sp.completed }, limits: { default: 10000, min: 1000, max: 50000 }, limitations: [], saved_runs: 0,
  };
};
const team = (name, i) => ({ entity_id: `E${i}`, name, current_points: 20 - i, remaining_fixtures: 25, expected_points: 80 - i * 10, points_sd: 6, points_p10: 72 - i * 10, points_p25: 76 - i * 10, points_median: 80 - i * 10, points_p75: 84 - i * 10, points_p90: 88 - i * 10, points_min: 60 - i * 10, points_max: 100 - i * 10,
  distribution: { first_points: 60 - i * 10, probabilities: Array.from({ length: 41 }, (_, k) => Math.exp(-((k - 20) ** 2) / 60) / 15.4) } });
const runFor = (key, seed, sims) => ({
  run_id: 31, competition_key: key, season: "2026-27",
  assumptions: { mode: "points_only", label: "Experimental — Points-only simulation", created_utc: "2026-10-28T11:00:00Z", simulations: sims, seed, standard_error_max: 0.005, models: { primary: "club_v1 frozen" }, points_rule: "3 / 1 / 0; no scores, no tie-breaks, no positions",
    data_cutoff: { latest_result_in_competition: "2026-10-26", latest_result_in_model_history: "2026-10-26" }, freshness: { last_sync_utc: null, completed_results_by_source: { wikipedia: 80 } }, eligibility: { state: SPEC[key].state, reasons: [] }, remaining_fixtures: SPEC[key].fixtures - SPEC[key].completed,
    input_sha256: "b".repeat(64), limitations: ["Only win, draw and loss are simulated."] },
  result: { mode: "points_only", summary: { n: sims, seed, ordering: "no finishing position", teams: [team(`${LABELS[key]} Club A`, 0), team(`${LABELS[key]} Club B`, 1)] },
    position_bounds: { status: "unavailable", label: "Experimental — position ranges", reason: "position ranges are available for the Bundesliga and La Liga only: they need verified tie-break settings for the league, which the other leagues do not have yet" } },
});

let calls;
beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((url, init) => {
      const u = new URL(url);
      const q = Object.fromEntries(u.searchParams);
      calls.push({ path: u.pathname, method: init?.method ?? "GET", body: init?.body ? JSON.parse(init.body) : undefined, q });
      if (u.pathname === "/api/meta") return json(META);
      if (u.pathname === "/api/gameweeks") return json({ competition_key: q.key, season: "2026-27", seasons: ["2026-27", "2025-26"], next_gameweek: 8, gameweeks: [] });
      if (u.pathname === "/api/season/status") return json(q.season === "2026-27" ? status(q.key) : { ...status(q.key), counts: { ...status(q.key).counts, remaining_to_simulate: 0 } });
      if (u.pathname === "/api/season/runs") return json([]);
      if (u.pathname === "/api/season/points") {
        const b = JSON.parse(init.body);
        return json(runFor(b.key, b.seed, b.simulations));
      }
      return json({ detail: `unhandled ${u.pathname}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const page = () => (
  <MemoryRouter initialEntries={["/simulations?tab=season"]}>
    <MetaProvider>
      <SeasonSimulator />
    </MetaProvider>
  </MemoryRouter>
);

describe("Season simulator covers the five domestic leagues (Phase 4.29)", () => {
  it("offers exactly the five domestic leagues and no Champions League", async () => {
    render(page());
    const league = await screen.findByLabelText("League");
    expect(SEASON_LEAGUES.slice().sort()).toEqual(Object.keys(LABELS).sort());
    expect(within(league).getAllByRole("option").map((o) => o.textContent).sort()).toEqual(Object.values(LABELS).sort());
    expect(within(league).queryByRole("option", { name: /Champions/i })).toBeNull();
  });

  it.each(Object.keys(LABELS))("%s: 2026-27 is selected, the button is enabled and the run posts the league, season, simulation count and seed", async (key) => {
    const user = userEvent.setup();
    render(page());
    await user.selectOptions(await screen.findByLabelText("League"), LABELS[key]);
    const season = await screen.findByLabelText("Season");
    await waitFor(() => expect(season).toHaveValue("2026-27"));
    expect(within(season).queryByRole("option", { name: "2025-26" })).toBeNull();                       // a finished season is not offered
    const button = await screen.findByRole("button", { name: /Run points-only simulation/ });
    await waitFor(() => expect(button).toBeEnabled());
    await user.type(await screen.findByLabelText(/Seed/i), "77");
    await user.click(button);
    expect(await screen.findByTestId("points-result")).toBeInTheDocument();
    const post = calls.filter((c) => c.path === "/api/season/points").pop();
    expect(post.body).toMatchObject({ key, season: "2026-27", simulations: 10000, seed: 77, user_action: expect.any(String) });
    expect(screen.getAllByText(/Experimental/).length).toBeGreaterThan(0);
    if (key !== "BUNDESLIGA" && key !== "LALIGA") expect(screen.getByText(/available for the Bundesliga and La Liga only/)).toBeInTheDocument();      // the reason ranges are missing stays visible
  }, 30000);

  it("keeps the missing-result warning visible for a provisional league and still allows the run", async () => {
    const user = userEvent.setup();
    render(page());
    await user.selectOptions(await screen.findByLabelText("League"), "Serie A");
    const banner = await screen.findByTestId("eligibility-banner");
    await waitFor(() => expect(within(banner).getByText(/Data: Provisional/)).toBeInTheDocument());
    expect(within(banner).getByText(/3 fixture\(s\) dated up to today have no verified result/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Run points-only simulation/ })).toBeEnabled();
  });

  it("shows the backend's actual reason when a run is blocked", async () => {
    const user = userEvent.setup();
    const base = status("EPL");
    fetch.mockImplementation((url) => {
      const u = new URL(url);
      if (u.pathname === "/api/meta") return json(META);
      if (u.pathname === "/api/gameweeks") return json({ competition_key: "EPL", season: "2026-27", seasons: ["2026-27"], next_gameweek: 8, gameweeks: [] });
      if (u.pathname === "/api/season/status") return json({ ...base, state: "not_eligible", points_only: { ...base.points_only, can_run: false, blockers: ["data quality: Not eligible"] }, reasons: ["the newest verified result is 40 days old (2026-09-18)"] });
      if (u.pathname === "/api/season/runs") return json([]);
      return json({ detail: "unhandled" }, 404);
    });
    render(page());
    await user.selectOptions(await screen.findByLabelText("League"), "Premier League");
    expect(await screen.findByText(/data quality: Not eligible/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Run points-only simulation/ })).toBeDisabled();
  });
});
