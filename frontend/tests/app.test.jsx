import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ApiError, api, buildUrl } from "../src/lib/api.js";
import { badgeTone, nextDay, pct } from "../src/lib/format.js";
import ProbBar from "../src/components/ProbBar.jsx";
import Predict from "../src/pages/Predict.jsx";
import Simulator, { estimateSeconds, validateInputs } from "../src/pages/Simulator.jsx";
import AboutTheData from "../src/components/AboutTheData.jsx";
import TeamComparison from "../src/pages/TeamComparison.jsx";
import { MetaProvider } from "../src/components/MetaContext.jsx";

// ---------------------------------------------------------------- fixtures shaped exactly like the real backend responses
const COMPS = [
  { key: "EPL", name: "English Premier League", group: "Domestic league", badge: "Validated", basis: "club v1 test", rows: 3090, seasons: 9, first_date: "2018-08-10", last_date: "2026-09-20", sources: "openfootball", licences: "CC0-1.0" },
  { key: "UCL", name: "UEFA Champions League", group: "Continental club", badge: "Not validated (indicative only)", basis: "no continental validation", rows: 1140, seasons: 9, first_date: "2018-09-18", last_date: "2026-09-10", sources: "openfootball | wikipedia", licences: "CC0-1.0 | CC BY-SA 4.0" },
  { key: "UNL", name: "UEFA Nations League", group: "International", badge: "Partially validated", basis: "pooled", rows: 658, seasons: 6, first_date: "2018-09-06", last_date: "2025-06-08", sources: "martj42", licences: "CC0-1.0" },
];
const META = {
  attribution: [{ source: "openfootball", licence: "CC0-1.0" }, { source: "Wikipedia", licence: "CC BY-SA 4.0", requirement: "attribution and share-alike" }],
  data_through: { club_results: "2026-09-20", international_ratings: "2026-06-02", note: "" },
  limitations: ["UEFA club competitions are not validated."],
};
const TEAMS = { EPL: ["Arsenal FC", "Chelsea FC", "Everton FC"], UCL: ["Manchester City FC", "Real Madrid CF"], UNL: ["France", "Spain"] };
const trio = (model, home, draw, away) => ({ model, home, draw, away });
const CLUB_PREDICTION = {
  competition_key: "EPL", competition: "English Premier League", validation_badge: "Validated", validation_basis: "club v1 test", home: "Arsenal FC", away: "Chelsea FC",
  date: "2026-09-21", data_through: "2026-09-20", primary: trio("Club v1", 0.6, 0.25, 0.15), secondary: trio("Club v2-r1", 0.55, 0.25, 0.2), elo_only: trio("Elo", 0.5, 0.3, 0.2),
  history: { home_prior_matches: 10, away_prior_matches: 12 }, notes: [],
};

let health;
let handlers;
const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });

beforeEach(() => {
  health = { status: "ok", club_prediction_ready: true, data_rows: 1 };
  handlers = {};
  vi.stubGlobal(
    "fetch",
    vi.fn((url) => {
      const u = new URL(url);
      const p = u.pathname;
      if (handlers[p]) return handlers[p](u);
      if (p === "/api/health") return json(health);
      if (p === "/api/meta") return json(META);
      if (p === "/api/competitions") return json(COMPS);
      const m = p.match(/^\/api\/competitions\/(\w+)\/(teams|coverage|seasons)$/);
      if (m && m[2] === "teams") return json(TEAMS[m[1]]);
      if (m) return json([]);
      return json({ detail: `unmocked ${p}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const renderPage = (ui, route = "/") =>
  render(
    <MemoryRouter initialEntries={[route]}>
      <MetaProvider>{ui}</MetaProvider>
    </MemoryRouter>,
  );
const pick = async (user, label, value) => {
  const select = await screen.findByLabelText(label);
  await waitFor(() => expect(within(select).queryByRole("option", { name: value })).not.toBeNull()); // options arrive after the season list loads
  await user.selectOptions(select, value);
};

// ---------------------------------------------------------------- API client
describe("api client", () => {
  it("builds query strings and skips empty values", () => {
    const url = buildUrl("/api/predict", { key: "EPL", home: "Arsenal FC", date: "", venue: undefined });
    expect(url).toMatch(/\/api\/predict\?key=EPL&home=Arsenal\+FC$/);
  });
  it("turns backend errors into ApiError with the detail message", async () => {
    fetch.mockImplementationOnce(() => json({ detail: "date must be formatted YYYY-MM-DD" }, 422));
    await expect(api("/api/predict")).rejects.toMatchObject({ name: "ApiError", status: 422, message: "date must be formatted YYYY-MM-DD" });
  });
  it("explains when the backend is unreachable", async () => {
    fetch.mockImplementationOnce(() => Promise.reject(new TypeError("Failed to fetch")));
    await expect(api("/api/health")).rejects.toBeInstanceOf(ApiError);
    await expect(api("/api/health")).resolves.toMatchObject({ status: "ok" }); // next call uses the normal mock
  });
});

describe("formatting helpers", () => {
  it("formats probabilities, dates and badge tones", () => {
    expect(pct(0.6923)).toBe("69.2%");
    expect(nextDay("2026-09-20")).toBe("2026-09-21");
    expect(nextDay("2026-12-31")).toBe("2027-01-01");
    expect(badgeTone("Validated")).toBe("ok");
    expect(badgeTone("Partially validated")).toBe("warn");
    expect(badgeTone("Not validated (indicative only)")).toBe("bad");
  });
});

describe("ProbBar", () => {
  it("shows all three probabilities that sum to 100%", () => {
    render(<ProbBar probs={{ home: 0.5, draw: 0.3, away: 0.2 }} homeLabel="A win" awayLabel="B win" />);
    expect(screen.getByRole("img")).toHaveAttribute("aria-label", "A win 50.0%, Draw 30.0%, B win 20.0%");
  });
});

// ---------------------------------------------------------------- pages
// P4.2: the competition cards and the two dataset charts moved from the old Home page to "About the data" on the Models page. Same data, same assertions.
describe("About the data (moved from the old Home page)", () => {
  it("lists every competition with badge and counts, plus limitations", async () => {
    renderPage(<AboutTheData />);
    expect(await screen.findByText("UEFA Champions League", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getAllByText("Not validated (indicative only)").length).toBeGreaterThan(0);
    expect(screen.getByText(/3,090 matches/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "About the data" })).toBeInTheDocument();
    expect(screen.queryByText("UEFA club competitions are not validated.")).toBeNull(); // detailed limitations live on the Models page
  });
  it("shows an error state when the backend fails", async () => {
    handlers["/api/competitions"] = () => json({ detail: "boom" }, 500);
    renderPage(<AboutTheData />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});

describe("Match prediction page", () => {
  it("keeps club prediction disabled until /api/health reports ready, then enables it", async () => {
    health.club_prediction_ready = false;
    const user = userEvent.setup();
    renderPage(<Predict />, "/predict?comp=EPL");
    await pick(user, "Home team", "Arsenal FC");
    await pick(user, "Away team", "Chelsea FC");
    expect(await screen.findByText(/Club models are warming up/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Predict" })).toBeDisabled();
    health.club_prediction_ready = true;
    await waitFor(() => expect(screen.getByRole("button", { name: "Predict" })).toBeEnabled(), { timeout: 5000 });
    expect(screen.getByText("Club models ready.")).toBeInTheDocument();
  }, 10000);

  it("shows probabilities, badge, notes and the estimates disclaimer for a club prediction", async () => {
    handlers["/api/predict"] = (u) => {
      expect(Object.fromEntries(u.searchParams)).toEqual({ key: "EPL", home: "Arsenal FC", away: "Chelsea FC" });
      return json(CLUB_PREDICTION);
    };
    const user = userEvent.setup();
    renderPage(<Predict />, "/predict?comp=EPL");
    await pick(user, "Home team", "Arsenal FC");
    await pick(user, "Away team", "Chelsea FC");
    await user.click(await screen.findByRole("button", { name: "Predict" }));
    expect(await screen.findByText("Arsenal FC vs Chelsea FC")).toBeInTheDocument();
    expect(screen.getAllByText("60.0%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Validated").length).toBeGreaterThan(0);
    expect(screen.getByText(/Estimates, not guaranteed results/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Elo-only baseline" }));
    expect(screen.getByText("50.0%", { selector: "div.text-xl" })).toBeInTheDocument();
  });

  it("flags unvalidated competitions and renders the backend's NOT validated note", async () => {
    handlers["/api/predict"] = () =>
      json({ ...CLUB_PREDICTION, competition_key: "UCL", competition: "UEFA Champions League", validation_badge: "Not validated (indicative only)", home: "Manchester City FC", away: "Real Madrid CF", notes: ["This competition is NOT validated: indicative."] });
    const user = userEvent.setup();
    renderPage(<Predict />, "/predict?comp=UCL");
    await pick(user, "Home team", "Manchester City FC");
    await pick(user, "Away team", "Real Madrid CF");
    await user.click(await screen.findByRole("button", { name: "Predict" }));
    expect(await screen.findByText(/This competition is NOT validated/)).toBeInTheDocument();
    expect(screen.getAllByText("Not validated (indicative only)").length).toBeGreaterThan(1);
  });

  it("prevents the same team twice and dates before the data cut-off, and shows server errors", async () => {
    handlers["/api/predict"] = () => json({ detail: "'Chelsea FC' has no matches in the dataset" }, 422);
    const user = userEvent.setup();
    renderPage(<Predict />, "/predict?comp=EPL");
    await pick(user, "Home team", "Arsenal FC");
    const away = await screen.findByLabelText("Away team");
    expect(within(away).queryByRole("option", { name: "Arsenal FC" })).toBeNull(); // same team is not offered
    await pick(user, "Away team", "Chelsea FC");
    await user.type(screen.getByLabelText("Prediction date"), "2020-01-01");
    expect(await screen.findByText(/The date must be on or after 2026-09-21/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Predict" })).toBeDisabled();
    await user.clear(screen.getByLabelText("Prediction date"));
    await user.click(screen.getByRole("button", { name: "Predict" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("has no matches in the dataset");
  });

  it("offers no venue choice: every supported competition is a club competition", async () => {
    renderPage(<Predict />, "/predict?comp=EPL");
    await screen.findByLabelText("Competition");
    await screen.findByLabelText("Home team");
    expect(screen.queryByLabelText("Venue")).toBeNull();
    expect(screen.queryByText(/Project confidence gate/)).toBeNull();
  });
});

describe("Team comparison page", () => {
  it("never offers the selected team as the other team and shows head-to-head", async () => {
    handlers["/api/team"] = (u) =>
      json({
        form: { team: u.searchParams.get("team"), played: 2, points: 4, last: [{ date: "2026-09-01", opponent: "X", venue: "H", gf: 2, ga: 1, result: "W" }, { date: "2026-09-08", opponent: "Y", venue: "A", gf: 1, ga: 1, result: "D" }] },
        ...(u.searchParams.get("opponent") ? { head_to_head: { a: "Arsenal FC", b: "Chelsea FC", meetings: 17, a_wins: 9, b_wins: 4, draws: 4, last: [{ date: "2026-04-01", season: "2025-26", home: "Arsenal FC", away: "Chelsea FC", home_goals: 1, away_goals: 0 }] } } : {}),
      });
    const user = userEvent.setup();
    renderPage(<TeamComparison />);
    await pick(user, "Team A", "Arsenal FC");
    const b = screen.getByLabelText("Team B");
    expect(within(b).queryByRole("option", { name: "Arsenal FC" })).toBeNull();
    await pick(user, "Team B", "Chelsea FC");
    expect(await screen.findByText(/Meetings in this competition's dataset: 17/)).toBeInTheDocument();
  });
});

describe("World Cup simulator page", () => {
  it("defaults to a small simulation count and validates inputs", async () => {
    const user = userEvent.setup();
    renderPage(<Simulator />);
    expect(screen.getByLabelText("Simulations")).toHaveValue(1000);
    const run = screen.getByRole("button", { name: "Run simulation" });
    await user.clear(screen.getByLabelText("Simulations"));
    await user.type(screen.getByLabelText("Simulations"), "50");
    expect(run).toBeDisabled();
    expect(screen.getByText(/Simulations must be a whole number from 100/)).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Simulations"));
    await user.type(screen.getByLabelText("Simulations"), "1000");
    await user.type(screen.getByLabelText("Seed"), "abc");
    expect(run).toBeDisabled();
    expect(screen.getByText(/Seed must be a whole number/)).toBeInTheDocument();
  });

  it("sends mode, seed and simulations and renders ranking and group tables", async () => {
    let seen;
    handlers["/api/worldcup/simulate"] = (u) => {
      seen = Object.fromEntries(u.searchParams);
      return json({
        mode: "current", simulations: 1000, seed: 7, seconds: 0.3, engine: "v2.3", note: "Archived state.", metadata: {},
        title_odds: [{ rank: 1, team: "Spain", group: "H", round_of_16_pct: 100, quarter_final_pct: 100, semi_final_pct: 100, final_pct: 100, champion_pct: 55.5 }, { rank: 2, team: "Argentina", group: "J", round_of_16_pct: 100, quarter_final_pct: 100, semi_final_pct: 100, final_pct: 100, champion_pct: 44.5 }],
        group_tables: { A: [{ team: "Mexico", played: 3, points: 9, goal_diff: 6, goals_for: 6 }] },
      });
    };
    const user = userEvent.setup();
    renderPage(<Simulator />);
    await user.click(screen.getByLabelText(/Archived state/));
    await user.type(screen.getByLabelText("Seed"), "7");
    await user.click(screen.getByRole("button", { name: "Run simulation" }));
    expect(await screen.findByText(/Ran 1,000 simulations with seed 7/)).toBeInTheDocument();
    expect(seen).toEqual({ simulations: "1000", seed: "7", mode: "current" });
    expect(screen.getByText("55.5")).toBeInTheDocument();
    expect(screen.getByText("Group A")).toBeInTheDocument();
  });

  it("shows the backend error for a failed run", async () => {
    handlers["/api/worldcup/simulate"] = () => json({ detail: "start Python with -X utf8" }, 500);
    const user = userEvent.setup();
    renderPage(<Simulator />);
    await user.click(screen.getByRole("button", { name: "Run simulation" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("-X utf8");
  });

  it("helpers: estimates and validation", () => {
    expect(estimateSeconds("pre_tournament", 5000)).toBe(8);
    expect(estimateSeconds("current", 5000)).toBe(1);
    expect(validateInputs("1000", "")).toBeNull();
    expect(validateInputs("99", "")).not.toBeNull();
    expect(validateInputs("1000", "-1")).not.toBeNull();
    expect(validateInputs("1000", "2147483648")).not.toBeNull();
  });
});
