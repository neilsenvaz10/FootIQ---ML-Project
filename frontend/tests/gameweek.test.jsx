import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { MetaProvider } from "../src/components/MetaContext.jsx";
import Predictions from "../src/pages/Predictions.jsx";
import FixtureCard from "../src/components/FixtureCard.jsx";
import { EXPLICIT_ACTION } from "../src/pages/GameweekPredict.jsx";

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const COMPS = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"].map((key) => ({ key, name: key === "EPL" ? "English Premier League" : key, group: key === "UCL" ? "Continental club" : "Domestic league", badge: key === "UCL" ? "Not validated (indicative only)" : "Validated", basis: "b", rows: 1, seasons: 1, first_date: "2018-01-01", last_date: "2026-09-20", sources: "s", licences: "l" }));
const META = { attribution: [], data_through: { club_results: "2026-09-20", international_ratings: "2026-06-02" }, limitations: [] };

const LIST = {
  competition_key: "EPL", season: "2026-27", seasons: ["2026-27", "2025-26"], next_gameweek: 8, latest_result: "2026-09-20", today_utc: "2026-10-25",
  gameweeks: [
    { matchday_no: 7, fixtures: 10, first_date: "2026-10-17", last_date: "2026-10-19", completed: 0, upcoming: 0, awaiting_result: 10, predictable: 10, order_issue: false, rescheduled_fixtures: 0 },
    { matchday_no: 8, fixtures: 10, first_date: "2026-10-23", last_date: "2026-10-25", completed: 0, upcoming: 5, awaiting_result: 5, predictable: 10, order_issue: false, rescheduled_fixtures: 0 },
    { matchday_no: 9, fixtures: 10, first_date: "2026-10-31", last_date: "2026-11-02", completed: 0, upcoming: 10, awaiting_result: 0, predictable: 10, order_issue: true, rescheduled_fixtures: 1 },
  ],
};
const fixture = (over = {}) => ({
  record_id: "r1", matchday_no: 8, date: "2026-10-24", kickoff_utc: null, kickoff_local: null, home: "Arsenal FC", away: "Chelsea FC", stored_status: "scheduled", status: "awaiting_result", predictable: true, result: null,
  flags: ["kickoff_time_unknown", "stale_history", "missing_results_home"], reasons: ["The newest result in this competition is 2026-09-20."], reliability: "provisional", stale_days: 34,
  form: { home: [{ date: "2026-09-20", opponent: "X", venue: "H", gf: 2, ga: 1, result: "W" }], away: [] }, forecast: null, evaluation: null, ...over,
});
const FORECAST = { forecast_run_id: 3, created_utc: "2026-10-25T09:00:00Z", data_cutoff_date: "2026-09-20", data_cutoff_note: "n", made_before_kickoff: "unknown", reliability: "provisional", flags: [], models: { club_v1: "club_v1 frozen", club_v2_r1: "club_v2 v2-r1" }, artifact_sha256: {}, feature_sha256: "x",
  predictions: { primary: { home: 0.6, draw: 0.25, away: 0.15 }, secondary: { home: 0.55, draw: 0.25, away: 0.2 }, elo_only: { home: 0.5, draw: 0.3, away: 0.2 } } };
const GW8 = (fixtures, extra = {}) => ({ competition_key: "EPL", season: "2026-27", matchday_no: 8, label: "Matchday 8", today_utc: "2026-10-25", latest_result: "2026-09-20", fixtures, evaluation: { finished_with_forecast: 0, counted: 0, excluded: 0, correct: 0, accuracy: null, mean_log_loss: null, caveat: "Application forecast history. Not the official prospective evaluation." }, runs: [], ...extra });

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
      if (u.pathname === "/api/health") return json({ status: "ok", club_prediction_ready: true });
      if (u.pathname === "/api/meta") return json(META);
      if (u.pathname === "/api/competitions") return json(COMPS);
      if (u.pathname === "/api/gameweeks") return json(LIST);
      if (u.pathname === "/api/gameweek") return json(GW8([fixture()]));
      if (u.pathname === "/api/sync/status") return json({ competitions: [{ competition_key: "EPL", state: "stale", latest_result: "2026-09-20", awaiting_result: 20 }] });
      if (u.pathname === "/api/competitions/EPL/teams") return json(["Arsenal FC", "Chelsea FC"]);
      if (u.pathname === "/api/competitions/EPL/seasons") return json(["2026-27"]);
      return json({ detail: `unmocked ${u.pathname}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const page = (route = "/predict") =>
  render(
    <MemoryRouter initialEntries={[route]}>
      <MetaProvider>
        <Predictions />
      </MetaProvider>
    </MemoryRouter>,
  );

describe("gameweek predictions page", () => {
  it("opens on the next gameweek, shows every fixture with its status and reliability flags, and computes nothing", async () => {
    page();
    expect(await screen.findByText("Arsenal FC")).toBeInTheDocument();
    expect(screen.getByLabelText("Gameweek")).toHaveValue("8");
    expect(screen.getByText(/next gameweek/)).toBeInTheDocument();
    expect(screen.getByText("Awaiting verified result")).toBeInTheDocument();
    expect(screen.queryByText("Provisional history")).toBeNull(); // chip removed (Phase 4.35)
    expect(screen.getByText("Stale history")).toBeInTheDocument();
    expect(screen.getByText("Missing earlier results")).toBeInTheDocument();
    expect(screen.getByText("Kickoff time unknown")).toBeInTheDocument();
    expect(screen.queryByText(/EPL results are stale/)).toBeNull(); // the amber stale notice is no longer shown (Phase 4.35)
    expect(screen.getByText(/only when you press Predict gameweek/)).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);                  // looking never saves
    expect(screen.getByText("No forecast saved for this gameweek yet.", { exact: false })).toBeInTheDocument();
  });

  it("saves a forecast only when Predict gameweek is pressed, then shows the saved probabilities, timestamp and models", async () => {
    let saved = false;
    handlers["/api/gameweek"] = () => json(GW8([fixture(saved ? { forecast: FORECAST } : {})], saved ? { runs: [{ forecast_run_id: 3, created_utc: "2026-10-25T09:00:00Z", data_cutoff_date: "2026-09-20", fixtures: 1 }] } : {}));
    handlers["/api/gameweek/predict"] = (u, init) => {
      saved = true;
      return json({ forecast_run_id: 3, created_utc: "2026-10-25T09:00:00Z", competition_key: "EPL", season: "2026-27", matchday_no: 8, data_cutoff_date: "2026-09-20", models: { club_v1: "club_v1 frozen" }, saved_fixtures: 1, skipped: [], note: "n", forecasts: [] });
    };
    const user = userEvent.setup();
    page();
    const btn = await screen.findByRole("button", { name: "Predict gameweek" });
    await waitFor(() => expect(btn).toBeEnabled());
    await user.click(btn);
    expect(await screen.findByText(/Saved\./)).toBeInTheDocument();
    const post = calls.filter((c) => c.method === "POST");
    expect(post).toHaveLength(1);
    expect(post[0].body).toEqual({ key: "EPL", season: "2026-27", matchday: 8, user_action: EXPLICIT_ACTION });
    expect(await screen.findByText(/Saved 2026-10-25 09:00:00 UTC/)).toBeInTheDocument();
    expect(screen.getAllByText("Run #3", { exact: false }).length).toBeGreaterThan(0);        // in the save notice and in the run history
    expect(screen.getByRole("img", { name: /Arsenal FC win 60.0%, Draw 25.0%, Chelsea FC win 15.0%/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Details" }));
    expect(screen.getByText(/experimental, development-validated only/)).toBeInTheDocument();
    expect(screen.getByText(/Saved before kickoff:/)).toBeInTheDocument();
  });

  it("keeps the button disabled until the club models are ready", async () => {
    let ready = false;
    handlers["/api/health"] = () => json({ status: "ok", club_prediction_ready: ready });
    page();
    const btn = await screen.findByRole("button", { name: "Predict gameweek" });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/Club models are warming up/)).toBeInTheDocument();
    ready = true;
    await waitFor(() => expect(btn).toBeEnabled(), { timeout: 5000 });
  }, 10000);

  it("shows predicted versus actual for finished fixtures and says which forecasts are not counted", async () => {
    handlers["/api/gameweek"] = () =>
      json(
        GW8(
          [
            fixture({ status: "completed", predictable: false, result: { home: 2, away: 1, source: "openligadb" }, forecast: { ...FORECAST, made_before_kickoff: "yes" }, evaluation: { actual: "H", predicted: "H", correct: true, p_actual: 0.6, log_loss: 0.51, made_before_kickoff: "yes", counted: true, note: null } }),
            fixture({ record_id: "r2", home: "Everton FC", away: "Fulham FC", status: "completed", predictable: false, result: { home: 0, away: 0, source: "openligadb" }, forecast: FORECAST, evaluation: { actual: "D", predicted: "H", correct: false, p_actual: 0.25, log_loss: 1.38, made_before_kickoff: "unknown", counted: false, note: "Saved after kickoff or with an unknown kickoff relative to the saving time: shown, but not counted in the summary." } }),
          ],
          { evaluation: { finished_with_forecast: 2, counted: 1, excluded: 1, correct: 1, accuracy: 1, mean_log_loss: 0.51, caveat: "Application forecast history. Not the official prospective evaluation; small samples." } },
        ),
      );
    page();
    expect(await screen.findByText("Predicted versus actual")).toBeInTheDocument();
    expect(screen.getByText(/called correctly \(100%\)/)).toBeInTheDocument();
    expect(screen.getByText(/1 finished fixture\(s\) with a forecast are shown but not counted/)).toBeInTheDocument();
    expect(screen.getAllByText(/Not the official prospective evaluation/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Predicted home win, actual home win ✓/)).toBeInTheDocument();
    expect(screen.getByText(/Predicted home win, actual draw ✗/)).toBeInTheDocument();
  });

  it("flags rescheduled gameweeks, lets the user move between gameweeks and offers the manual head-to-head mode", async () => {
    const user = userEvent.setup();
    page();
    await screen.findByText("Arsenal FC");
    await user.click(screen.getByRole("button", { name: "Next gameweek" }));
    await waitFor(() => expect(calls.some((c) => c.path === "/api/gameweek" && c.q.matchday === "9")).toBe(true));
    expect(within(screen.getByLabelText("Gameweek")).getByRole("option", { name: /GW 9 .*dates out of order/ })).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Manual head-to-head" }));
    expect(await screen.findByText(/Nothing is saved\./)).toBeInTheDocument();
    expect(screen.getByLabelText("Home team")).toBeInTheDocument();
  });

  it("shows the server's message when saving fails and handles a gameweek with nothing to forecast", async () => {
    handlers["/api/gameweek/predict"] = () => json({ detail: "Matchday 8 has no unplayed fixtures to forecast" }, 422);
    const user = userEvent.setup();
    page();
    const btn = await screen.findByRole("button", { name: "Predict gameweek" });
    await waitFor(() => expect(btn).toBeEnabled());
    await user.click(btn);
    expect(await screen.findByRole("alert")).toHaveTextContent("no unplayed fixtures to forecast");
  });

  it("only the five domestic leagues appear in the gameweek mode", async () => {
    page("/predict?mode=gameweek");
    const select = await screen.findByLabelText("Competition");
    await waitFor(() => expect(within(select).getAllByRole("option").length).toBe(5));
    expect(within(select).queryByRole("option", { name: "UCL" })).toBeNull();
  });
});

describe("fixture card", () => {
  it("never claims a kickoff time it does not have and labels a known one in UTC", () => {
    const { rerender } = render(<FixtureCard f={fixture()} />);
    expect(screen.queryByText("time not confirmed")).toBeNull(); // nothing is said when the store has no time (Phase 4.35)
    rerender(<FixtureCard f={fixture({ kickoff_utc: "2026-10-24T14:00:00Z", flags: [], reliability: "full", status: "scheduled" })} />);
    expect(screen.getByText("14:00 UTC")).toBeInTheDocument();
    expect(screen.getByText("Fully supported history")).toBeInTheDocument();
  });
});
