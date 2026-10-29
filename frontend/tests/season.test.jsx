import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { MetaProvider } from "../src/components/MetaContext.jsx";
import Simulations from "../src/pages/Simulations.jsx";
import { POINTS_ACTION, RANGES_LABEL, SIM_ACTION, fmtPct, rangeText, rangesAreValid, validateSims } from "../src/pages/SeasonSimulator.jsx";

configure({ asyncUtilTimeout: 5000 }); // the suite also runs beside a busy live backend
const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const META = { attribution: [], data_through: { club_results: "2026-10-24", international_ratings: "2026-06-02" }, limitations: [] };
const GWS = { competition_key: "BUNDESLIGA", season: "2026-27", seasons: ["2026-27", "2025-26"], next_gameweek: 8, gameweeks: [] };
const PROFILE_OK = { usable: true, status: "verified", sources: [{ title: "DFL Spielordnung (SpOL), Stand 11.06.2026", url: "https://media.dfl.de/x.pdf" }] };
const PO = (over = {}) => ({ label: "Experimental — Points-only simulation", can_run: true, blockers: [], limitations: ["Only win, draw and loss are simulated."], position_bounds: { available: true, blockers: [], bands: ["title", "top4", "relegation"] }, ...over });
const status = (over = {}) => ({
  competition_key: "BUNDESLIGA", season: "2026-27", state: "ready", reasons: [], notes: [], blockers: ["final-position predictions are disabled: no scoreline method has passed the predeclared acceptance criteria"], can_simulate: false, rule_profile: PROFILE_OK,
  points_only: PO(), latest_result: "2026-10-24", days_since_latest_result: 1, missing_share: 0,
  counts: { fixtures: 306, completed: 61, missing_results: 0, postponed: 0, remaining_to_simulate: 245 }, limits: { default: 10000, min: 1000, max: 50000 }, limitations: ["Static strengths."], saved_runs: 0, ...over,
});
const team = (name, i, n = 4) => ({ entity_id: `E${i}`, name, expected_points: 70 - i * 10, points_p10: 62 - i * 10, points_p90: 78 - i * 10, expected_rank: i + 1, rank_p10: 1, rank_p90: 3, expected_goal_difference: 20 - i * 10,
  p_title: i === 0 ? 0.62 : i === 1 ? 0.3 : 0.04, p_top4: 0.9, p_relegation: i === n - 1 ? 0.8 : 0.02, p_relegation_playoff: 0.1, position_probabilities: Array.from({ length: n }, (_, k) => (k === i ? 0.7 : 0.1)) });
const FULL_RUN = {
  run_id: 5, competition_key: "BUNDESLIGA", season: "2026-27",
  assumptions: { mode: "final_positions", created_utc: "2026-10-25T10:00:00Z", simulations: 10000, seed: 123, standard_error_max: 0.005, models: { primary: "club_v1 frozen", experimental_comparison: "club_v2 v2-r1" }, scoreline: { method: "S1 conditional Poisson", validation: { status: "test_only" } },
    data_cutoff: { latest_result_in_competition: "2026-10-24", latest_result_in_model_history: "2026-10-24" }, freshness: { last_sync_utc: "2026-10-25T08:38:29Z", completed_results_by_source: { openligadb: 25, openfootball: 36 } },
    eligibility: { state: "ready", reasons: [] }, remaining_fixtures: 245, input_sha256: "a".repeat(64), limitations: ["Static strengths."], rule_profile: { interpretation_notes: ["Final decider left unresolved."] } },
  result: { positions: { bands: { top4: [1, 2, 3, 4], relegation: [3, 4] } }, experimental: null,
    summary: { n: 10000, final_position_probabilities_supported: true, teams: [team("FC Bayern München", 0), team("Borussia Dortmund", 1), team("VfB Stuttgart", 2), team("Hamburger SV", 3)],
      tie_resolution: { share_with_an_unresolved_tie: 0.0002 } } },
};
const ptsTeam = (name, i) => ({ entity_id: `E${i}`, name, current_points: 20 - i * 3, remaining_fixtures: 25, expected_points: 80 - i * 10, points_sd: 6.2, points_p10: 72 - i * 10, points_p25: 76 - i * 10, points_median: 80 - i * 10, points_p75: 84 - i * 10, points_p90: 88 - i * 10,
  points_min: 60 - i * 10, points_max: 100 - i * 10, distribution: { first_points: 60 - i * 10, probabilities: Array.from({ length: 41 }, (_, k) => Math.exp(-((k - 20) ** 2) / 60) / 15.4) } });
const POINTS_RUN = {
  run_id: 8, competition_key: "BUNDESLIGA", season: "2026-27",
  assumptions: { mode: "points_only", label: "Experimental — Points-only simulation", created_utc: "2026-10-25T11:00:00Z", simulations: 10000, seed: 77, standard_error_max: 0.005, models: { primary: "club_v1 frozen" }, points_rule: "3 / 1 / 0; no scores, no tie-breaks, no positions",
    data_cutoff: { latest_result_in_competition: "2026-10-24", latest_result_in_model_history: "2026-10-24" }, freshness: { last_sync_utc: "2026-10-25T08:38:29Z", completed_results_by_source: { openligadb: 25, openfootball: 36 } },
    eligibility: { state: "ready", reasons: [] }, remaining_fixtures: 245, input_sha256: "b".repeat(64), limitations: ["Only win, draw and loss are simulated."] },
  result: { mode: "points_only", summary: { n: 10000, seed: 77, ordering: "no finishing position", teams: [ptsTeam("FC Bayern München", 0), ptsTeam("Borussia Dortmund", 1), ptsTeam("VfB Stuttgart", 2)] } },
};

const BANDS = [
  { id: "title", label: "Title", positions: [1, 1], places: 1 },
  { id: "top4", label: "Top four", positions: [1, 4], places: 4 },
  { id: "relegation", label: "Relegation", positions: [17, 18], places: 2 },
];
const rg = (g, p, se = 0.002) => ({ guaranteed: g, possible: p, unresolved: Number((p - g).toFixed(6)), se_guaranteed: se, se_possible: se });
const RANGES = (over = {}) => ({
  status: "available", label: "Experimental — position ranges (lower and upper bounds, not exact probabilities)", kind: "lower_and_upper_bounds",
  meaning: { guaranteed: "Lower bound: the share of simulated seasons in which the club is in this group whatever the scores turn out to be.", possible: "Upper bound: the share of simulated seasons in which the club could be in this group for some scores.", unresolved: "Possible minus guaranteed." },
  method: "In every simulated season the best and the worst finishing position of each club are computed under the verified tie-break rules.",
  bands: BANDS,
  clubs: [
    { entity_id: "E0", name: "FC Bayern München", title: rg(0.948, 0.961), top4: rg(1, 1, 0), relegation: rg(0, 0, 0) },
    { entity_id: "E1", name: "Borussia Dortmund", title: rg(0.029, 0.038), top4: rg(0.953, 0.964), relegation: rg(0, 0.0002) },
    { entity_id: "E2", name: "VfB Stuttgart", title: rg(0, 0.0004), top4: rg(0.2, 0.2501), relegation: rg(0.9996, 1) },
  ],
  checks: { lower_never_above_upper: true, all_values_between_0_and_100_percent: true, places_sums_consistent: true },
  ties: { tie_groups: 23099, tie_groups_fully_decided: 0, simulations: 10000 },
  rules: { profile_id: "BUNDESLIGA|2026-27", status: "verified", sources: [{ title: "DFL Spielordnung (SpOL), Stand 11.06.2026, para 2 no. 3 c)", url: "https://media.dfl.de/x.pdf", sha256: "c".repeat(64) }], live_confirmation: null,
    criteria_used: { two_clubs: ["goal_difference", "goals_scored"], three_or_more_clubs: ["goal_difference", "goals_scored"] }, deciders_never_simulated: {}, interpretation_notes: ["Final decider left unresolved."] },
  limitations: ["These are lower and upper bounds, not exact probabilities.", "The club in 16th place plays a relegation play-off, which is never simulated."],
  monte_carlo: { simulations: 10000, seed: 77, standard_error_max: 0.005 },
  ...over,
});
const RANGES_RUN = (pb = RANGES()) => ({ ...POINTS_RUN, result: { ...POINTS_RUN.result, position_bounds: pb } });

let handlers;
let calls;
beforeEach(() => {
  handlers = {};
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((url, init) => {
      const u = new URL(url);
      calls.push({ path: u.pathname, method: init?.method ?? "GET", body: init?.body ? JSON.parse(init.body) : undefined, q: Object.fromEntries(u.searchParams) });
      if (handlers[u.pathname]) return handlers[u.pathname](u, init);
      if (u.pathname === "/api/meta") return json(META);
      if (u.pathname === "/api/gameweeks") return json(GWS);
      if (u.pathname === "/api/season/status") return json(status());
      if (u.pathname === "/api/season/runs") return json([]);
      if (u.pathname === "/api/worldcup/simulate") return json({ detail: "not used" }, 500);
      return json({ detail: `unhandled ${u.pathname}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const page = (tab = "season") => (
  <MemoryRouter initialEntries={[`/simulations?tab=${tab}`]}>
    <MetaProvider>
      <Simulations />
    </MetaProvider>
  </MemoryRouter>
);
const toFull = async () => userEvent.click(await screen.findByRole("tab", { name: /Final positions/ }));

describe("Season simulator tab", () => {
  it("is the whole Simulations page: there is no World Cup tab any more", async () => {
    render(page());
    expect(await screen.findByRole("heading", { name: "Season simulator" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "World Cup" })).toBeNull();
    expect(screen.queryByRole("heading", { name: /World Cup simulator/i })).toBeNull();
  });

  it("opens in the experimental points-only mode with eligibility, freshness and a labelled, enabled button, and runs nothing on load", async () => {
    render(page());
    const banner = await screen.findByTestId("eligibility-banner");
    expect(within(banner).getByText(/Data: Ready/)).toBeInTheDocument();
    expect(within(banner).getByText("2026-10-24")).toBeInTheDocument();
    expect(screen.getByText("Experimental — Points-only simulation")).toBeInTheDocument();
    expect(screen.getByText(/does not predict a league table or exact chances/)).toBeInTheDocument();
    expect(screen.getByText(/appear only as ranges \(a lower and an upper bound\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run points-only simulation" })).toBeEnabled();
    expect(calls.some((c) => c.path === "/api/season/simulate" || c.path === "/api/season/points")).toBe(false);
    expect(screen.getByTestId("assumptions-panel")).toBeInTheDocument();
  });

  it("posts the explicit points action and shows expected points, intervals and the points distribution; a run without ranges shows no position columns", async () => {
    handlers["/api/season/points"] = () => json(POINTS_RUN);
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    const result = await screen.findByTestId("points-result");
    const post = calls.find((c) => c.path === "/api/season/points");
    expect(post.method).toBe("POST");
    expect(post.body).toMatchObject({ key: "BUNDESLIGA", season: "2026-27", user_action: POINTS_ACTION, simulations: 10000 });
    expect(within(result).getByRole("heading", { name: "Expected final points" })).toBeInTheDocument();
    expect(within(result).getByText(/not a predicted table/)).toBeInTheDocument();
    expect(within(result).getAllByText("FC Bayern München").length).toBeGreaterThan(0);
    expect(within(result).getByText("80.0")).toBeInTheDocument();
    await userEvent.click(within(result).getAllByRole("button", { name: /FC Bayern/ })[0]);
    expect(within(result).getByRole("img", { name: /Distribution of final points for FC Bayern/ })).toBeInTheDocument();
    expect(within(result).getByText(/spread \(sd\) 6.2/)).toBeInTheDocument();
    for (const forbidden of [/Title/i, /Top 4/i, /Relegat/i, /Projected final standings/i, /Finishing-position/i]) expect(within(result).queryAllByText(forbidden).filter((n) => n.tagName !== "P" && !/not (a|yet)|does not|no (tie|finishing)|without/i.test(n.textContent))).toHaveLength(0);
    const panel = within(result).getByTestId("assumptions-panel");
    expect(within(panel).getByText(/club_v1 frozen/)).toBeInTheDocument();
    expect(within(panel).getByText(/2026-10-25T11:00:00Z/)).toBeInTheDocument();
    expect(within(panel).getByText(/openligadb: 25/)).toBeInTheDocument();
  });

  it("disables the points-only button and explains why for a league outside the scope or with poor data", async () => {
    handlers["/api/season/status"] = () => json(status({ state: "not_eligible", reasons: ["15 fixture(s) have no verified result"], points_only: PO({ can_run: false, blockers: ["data quality: Not eligible", "outside the approved scope of the points-only mode (Bundesliga and La Liga)"] }) }));
    render(page());
    expect(await screen.findByText(/Data: Not eligible/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run points-only simulation" })).toBeDisabled();
    expect(within(screen.getByTestId("blockers")).getByText(/outside the approved scope/)).toBeInTheDocument();
  });

  it("keeps the final-position mode disabled and says why, with the league rules notice", async () => {
    render(page());
    await toFull();
    expect(await screen.findByText(/League rules: verified/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run season simulation" })).toBeDisabled();
    expect(within(screen.getByTestId("blockers")).getByText(/no scoreline method has passed/)).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/season/simulate")).toBe(false);
  });

  it("final-position mode, when the backend allows it, shows standings and withheld probabilities as bounds", async () => {
    handlers["/api/season/status"] = () => json(status({ can_simulate: true, blockers: [] }));
    const run = JSON.parse(JSON.stringify(FULL_RUN));
    run.result.summary.final_position_probabilities_supported = false;
    Object.assign(run.result.summary.teams[0], { p_title: null, p_title_low: 0.6, p_title_high: 0.62 });
    handlers["/api/season/simulate"] = () => json(run);
    render(page());
    await toFull();
    await userEvent.click(await screen.findByRole("button", { name: "Run season simulation" }));
    const result = await screen.findByTestId("season-result");
    expect(calls.find((c) => c.path === "/api/season/simulate").body).toMatchObject({ user_action: SIM_ACTION, simulations: 10000 });
    expect(within(result).getByRole("heading", { name: "Projected final standings" })).toBeInTheDocument();
    expect(within(result).getAllByText("60.0–62.0%").length).toBeGreaterThan(0);
    expect(within(result).getByText(/Some probabilities withheld/)).toBeInTheDocument();
    expect(within(result).getByText(/never simulated/)).toBeInTheDocument();
  });

  it("shows the backend's refusal message", async () => {
    handlers["/api/season/points"] = () => json({ detail: "points-only simulation blocked: data quality: Not eligible" }, 422);
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    expect(await screen.findByText(/points-only simulation blocked/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByTestId("points-result")).not.toBeInTheDocument());
  });

  it("opens a saved points-only run from the history in its own mode", async () => {
    handlers["/api/season/runs"] = () => json([{ run_id: 8, mode: "points_only", created_utc: "2026-10-25T11:00:00Z", n_simulations: 10000, seed: 77 }]);
    handlers["/api/season/run"] = () => json(POINTS_RUN);
    render(page());
    expect(await screen.findByText(/points-only \(experimental\)/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "View" }));
    expect(await screen.findByTestId("points-result")).toBeInTheDocument();
  });

  it("shows title, top-four and relegation only as labelled lower and upper bounds, with a plain-language explanation", async () => {
    handlers["/api/season/points"] = () => json(RANGES_RUN());
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    const box = await screen.findByTestId("position-ranges");
    expect(within(box).getByRole("heading", { name: "Where could each club finish?" })).toBeInTheDocument();
    expect(within(box).getByText(new RegExp(RANGES_LABEL))).toBeInTheDocument();
    const how = within(box).getByTestId("ranges-explainer");
    expect(within(how).getByText(/How to read these ranges/)).toBeInTheDocument();
    expect(within(how).getByText(/Lower bound \("guaranteed"\)/)).toBeInTheDocument();
    expect(within(how).getByText(/Upper bound \("possible"\)/)).toBeInTheDocument();
    expect(within(how).getByText(/These are ranges, not predictions and not exact probabilities/)).toBeInTheDocument();
    expect(within(how).getByText(/Example: FC Bayern München is shown at/)).toBeInTheDocument();
    const list = within(box).getByRole("list", { name: "Position ranges for every club" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(3);
    expect(within(list).getByRole("button", { name: /^FC Bayern München\s+Title: lower bound 94\.8%, upper bound 96\.1%\./ })).toBeInTheDocument(); // the spoken name carries the band and both bounds
    expect(within(list).getByText("94.8–96.1%")).toBeInTheDocument();
    expect(within(list).getByText("2.9–3.8%")).toBeInTheDocument();
    expect(within(list).getAllByText("0–<0.1%")).toHaveLength(2); // above zero but below 0.05% is never shown as a plain 0.0%
    expect(within(list).getAllByText("100%").length).toBeGreaterThan(0);
    expect(within(list).getByText(">99.9–100%")).toBeInTheDocument();
    expect(screen.getAllByText(new RegExp(RANGES_LABEL)).length).toBeGreaterThan(1); // also a badge next to the experimental label
  });

  it("every displayed percentage is between 0% and 100% and no lower bound is shown above its upper bound", async () => {
    handlers["/api/season/points"] = () => json(RANGES_RUN());
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    const list = within(await screen.findByTestId("position-ranges")).getByRole("list", { name: "Position ranges for every club" });
    const numbers = [...list.textContent.matchAll(/(\d+(?:\.\d+)?)(?=[–%])/g)].map((m) => Number(m[1]));
    expect(numbers.length).toBeGreaterThan(10);
    expect(numbers.every((x) => x >= 0 && x <= 100)).toBe(true);
    const cells = [...list.querySelectorAll("[data-range]")];
    expect(cells).toHaveLength(9);
    for (const el of cells) {
      const [, lo, hi] = el.getAttribute("data-range").split(":").map((x, i) => (i === 0 ? x : Number(x)));
      expect(lo).toBeGreaterThanOrEqual(0);
      expect(hi).toBeLessThanOrEqual(1);
      expect(lo).toBeLessThanOrEqual(hi);
    }
  });

  it("formats edge values without a plain 0.0%, 100.0% or any number outside 0-100%, and validates the data it is given", () => {
    expect([0, 1e-9, 0.0004, 0.0005, 0.3, 0.9994, 0.9996, 1, 1.7, -0.2].map((v) => fmtPct(v))).toEqual(["0%", "<0.1%", "<0.1%", "0.1%", "30.0%", "99.9%", ">99.9%", "100%", "100%", "0%"]);
    expect(rangeText({ guaranteed: 0.948, possible: 0.961 })).toBe("94.8–96.1%");
    expect(rangeText({ guaranteed: 1, possible: 1 })).toBe("100%");
    expect(rangeText({ guaranteed: 0.3, possible: 0.3 })).toBe("30.0%");
    expect(rangesAreValid(RANGES())).toBe(true);
    expect(rangesAreValid({ ...RANGES(), clubs: [{ ...RANGES().clubs[0], title: rg(0.97, 0.96) }] })).toBe(false); // lower above upper
    expect(rangesAreValid({ ...RANGES(), clubs: [{ ...RANGES().clubs[0], title: { ...rg(0.5, 0.6), possible: 1.2 } }] })).toBe(false); // above 100%
    expect(rangesAreValid({ ...RANGES(), clubs: [{ ...RANGES().clubs[0], title: { ...rg(0.5, 0.6), guaranteed: -0.1 } }] })).toBe(false); // below 0%
    expect(rangesAreValid({ ...RANGES(), clubs: [{ ...RANGES().clubs[0], title: { ...rg(0.5, 0.6), guaranteed: NaN } }] })).toBe(false);
    expect(rangesAreValid({ status: "unavailable", reason: "x" })).toBe(false);
  });

  it("hides inconsistent ranges instead of showing wrong numbers", async () => {
    const bad = RANGES();
    bad.clubs[0].title = rg(0.97, 0.96);
    handlers["/api/season/points"] = () => json(RANGES_RUN(bad));
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    expect(await screen.findByText(/Position ranges hidden/)).toBeInTheDocument();
    expect(screen.queryByTestId("ranges-explainer")).not.toBeInTheDocument();
    expect(screen.queryByText("97.0–96.0%")).not.toBeInTheDocument();
  });

  it("explains why ranges are missing: switched off, or a saved run from before they existed", async () => {
    handlers["/api/season/points"] = () => json(RANGES_RUN({ status: "unavailable", label: "x", reason: "position ranges are switched off in config/season_sim.json" }));
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    expect(await screen.findByText(/Position ranges are not available for this run:/)).toBeInTheDocument();
    expect(screen.getByText(/switched off in config/)).toBeInTheDocument();
    expect(screen.queryByTestId("position-ranges")).not.toBeInTheDocument();
  });

  it("opens the detail of a club: lower bound, upper bound, unresolved share and sampling error", async () => {
    handlers["/api/season/points"] = () => json(RANGES_RUN());
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    const box = await screen.findByTestId("position-ranges");
    await userEvent.click(within(box).getByRole("button", { name: /^FC Bayern München/ }));
    const detail = within(box).getByRole("table", { name: "Range details for FC Bayern München" });
    expect(within(detail).getByText("Lower bound (guaranteed)")).toBeInTheDocument();
    expect(within(detail).getByText("Upper bound (possible)")).toBeInTheDocument();
    expect(within(detail).getByText("Unresolved")).toBeInTheDocument();
    expect(within(detail).getByText("94.8%")).toBeInTheDocument();
    expect(within(detail).getByText("96.1%")).toBeInTheDocument();
    expect(within(detail).getByText("1.3%")).toBeInTheDocument();
    expect(within(detail).getAllByText("±0.4 pp").length).toBeGreaterThan(0);
    expect(within(detail).getByText("(places 17–18)")).toBeInTheDocument();
  });

  it("discloses the rule limitations and a pending live-document confirmation", async () => {
    const ll = RANGES({ rules: { ...RANGES().rules, profile_id: "LALIGA|2026-27", live_confirmation: "PENDING: the text was read from the Internet Archive capture." }, limitations: ["The fair-play criterion needs card data that FootIQ does not hold."] });
    handlers["/api/season/points"] = () => json(RANGES_RUN(ll));
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    const box = await screen.findByTestId("position-ranges");
    expect(within(box).getByText(/live-document confirmation pending/)).toBeInTheDocument();
    const tech = within(box).getByTestId("ranges-technical");
    expect(within(tech).getByText(/fair-play criterion needs card data/)).toBeInTheDocument();
    expect(within(tech).getByText("Two clubs level on points:")).toBeInTheDocument();
    expect(within(tech).getByRole("link", { name: /DFL Spielordnung/ })).toHaveAttribute("href", "https://media.dfl.de/x.pdf");
  });

  it("offers no final standings or exact title, top-four or relegation probability, and the final-position mode stays disabled", async () => {
    handlers["/api/season/points"] = () => json(RANGES_RUN());
    render(page());
    await userEvent.click(await screen.findByRole("button", { name: "Run points-only simulation" }));
    const box = await screen.findByTestId("position-ranges");
    expect(within(box).queryByText(/Projected final standings/)).not.toBeInTheDocument();
    expect(within(box).queryByText(/Finishing-position/)).not.toBeInTheDocument();
    await toFull();
    expect(screen.getByRole("button", { name: "Run season simulation" })).toBeDisabled();
  });

  it("validates the number of simulations before posting", async () => {
    render(page());
    const input = await screen.findByRole("spinbutton", { name: "Simulations" });
    await userEvent.clear(input);
    await userEvent.type(input, "10");
    expect(screen.getByText(/whole number from 1,000 to 50,000/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run points-only simulation" })).toBeDisabled();
    expect(validateSims("20000", { min: 1000, max: 50000 })).toBeNull();
    expect(validateSims("1.5", { min: 1000, max: 50000 })).not.toBeNull();
  });
});
