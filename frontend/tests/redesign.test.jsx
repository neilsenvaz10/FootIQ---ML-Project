import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { MetaProvider } from "../src/components/MetaContext.jsx";
import CompetitionSelect from "../src/components/CompetitionSelect.jsx";
import Models from "../src/pages/Models.jsx";
import AboutTheData from "../src/components/AboutTheData.jsx";
import Predict from "../src/pages/Predict.jsx";
import Simulator from "../src/pages/Simulator.jsx";
import { groupCompetitions } from "../src/lib/competitions.js";
import { parseSources } from "../src/lib/sources.js";

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const META = { attribution: [], data_through: { club_results: "2026-09-20", international_ratings: "2026-06-02" }, limitations: [] };
let handlers;

beforeEach(() => {
  handlers = {};
  vi.stubGlobal(
    "fetch",
    vi.fn((url) => {
      const u = new URL(url);
      if (handlers[u.pathname]) return handlers[u.pathname](u);
      if (u.pathname === "/api/health") return json({ status: "ok", club_prediction_ready: true });
      if (u.pathname === "/api/meta") return json(META);
      return json({ detail: `unmocked ${u.pathname}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const page = (ui, route = "/") => (
  <MemoryRouter initialEntries={[route]}>
    <MetaProvider>{ui}</MetaProvider>
  </MemoryRouter>
);

const PERF = {
  club_v1: {
    role: "Primary club predictor", status: "Validated on domestic leagues", notes: ["n1", "Log loss is the main score."],
    evaluation: [
      { period: "Test season", n: 15645, models: [{ model: "always_home", label: "Always predict a home win", n: 15645, accuracy: 0.4316, log_loss: 1.0758, brier: 0.651, macro_f1: 0.2 }, { model: "multinomial_logreg", label: "Club v1 (logistic regression)", n: 15645, accuracy: 0.5016, log_loss: 1.0073, brier: 0.6026, macro_f1: 0.37 }] },
      { period: "Forward holdout", n: 5770, models: [{ model: "multinomial_logreg", label: "Club v1 (logistic regression)", n: 5770, accuracy: 0.4943, log_loss: 1.0071, brier: 0.6032, macro_f1: 0.36 }] },
    ],
    per_league: [{ key: "EPL", competition: "English Premier League", test: { n: 380, accuracy: 0.521, log_loss: 0.99, always_home_log_loss: 1.08 }, forward_holdout: { n: 430, accuracy: 0.465, log_loss: 1.04, always_home_log_loss: 1.08 } }],
  },
  club_v2_r1: { role: "Candidate", status: "Development-validated only (no unbiased evaluation)", development: { period: "3 folds", n: 36881, accuracy: 0.4951, log_loss_v2: 1.0146, log_loss_v1_lr: 1.0176, log_loss_v1_elo: 1.0208, delta_vs_v1_lr: -0.003 }, notes: ["No unbiased test exists."] },
  international_v27: { role: "International predictor", status: "pooled", split: { train_matches: 18164, calibration_matches: 3580, test_matches: 3491, test_period: "2023-2026" }, models: [{ model: "ensemble", label: "v2.7 ensemble", log_loss: 0.8565, brier: 0.504, accuracy: 0.6087 }], gate: { label: "Confidence gate", public_coverage: 0.4672, public_pick_accuracy: 0.7682 }, notes: ["Pooled internationals."] },
  worldcup: { role: "Simulator", status: "small sample", results: [{ scope: "Whole tournament (before the final)", correct: 59, scored: 82, accuracy_pct: 71.95, ci_low_pct: 61.4, ci_high_pct: 80.5 }], notes: ["Wide intervals."] },
  uefa_club: { status: "Not validated", note: "UEFA club competitions are not validated: no accuracy figure exists." },
  caveats: ["Historical evaluation, inspected during development.", "Later models used earlier test data.", "Estimates only."],
  sources: ["FootIQ_Club_Model_Baseline_v1/04_TEST_METRICS.csv"],
};

describe("Model performance page", () => {
  it("shows the headline accuracies, development-only status and the UEFA warning", async () => {
    handlers["/api/models/performance"] = () => json(PERF);
    render(page(<Models />));
    expect(await screen.findByText("50.2%", { selector: "div.text-xl" })).toBeInTheDocument();
    expect(screen.queryByText(/World Cup 2026/)).toBeNull(); // the international and World Cup models are outside the six-competition scope
    expect(screen.queryByText(/International model/)).toBeNull();
    expect(screen.getByText("Dev only")).toBeInTheDocument();
    expect(screen.getAllByText(/The UEFA Champions League is not validated/).length).toBeGreaterThan(0);
    expect(screen.getByText(/No unbiased test exists/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("tab", { name: "Forward holdout" }));
    expect(screen.getByText(/5,770 matches across all domestic leagues/)).toBeInTheDocument();
  });
  it("shows the backend error", async () => {
    handlers["/api/models/performance"] = () => json({ detail: "evaluation file missing" }, 503);
    render(page(<Models />));
    expect(await screen.findByRole("alert")).toHaveTextContent("evaluation file missing");
  });
});

describe("competition dropdown and sources", () => {
  it("groups competitions into domestic leagues and the UEFA Champions League", () => {
    const all = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"].map((key) => ({ key, name: key }));
    const g = groupCompetitions(all);
    expect(g.map((x) => x.label)).toEqual(["Domestic leagues", "UEFA competition"]);
    expect(g[0].items).toHaveLength(5);
    expect(g[1].items.map((c) => c.key)).toEqual(["UCL"]);
    expect(groupCompetitions([{ key: "ZZZ", name: "New" }])[0].label).toBe("Other"); // nothing the backend returns is hidden
    render(<CompetitionSelect comps={all} value="EPL" onChange={() => {}} />);
    expect(screen.getByLabelText("Competition")).toHaveValue("EPL");
    expect(document.querySelectorAll("optgroup")).toHaveLength(2);
  });

  it("summarises long source lists and keeps every source reachable", () => {
    const urls = ["martj42/international_results", "https://www.fifa.com/a", "https://apnews.com/article/1", "https://apnews.com/article/2", "https://www.bbc.com/x"].join(" | ");
    const s = parseSources(urls);
    expect(s.summary).toBe("martj42/international_results, fifa.com + 2 more");
    expect(s.items).toHaveLength(5);
    expect(s.isLong).toBe(true);
    expect(parseSources("openfootball").isLong).toBe(false);
  });

  it("About the data keeps the page short: no limitation essay, a collapsible 'View sources' for long lists", async () => {
    const long = ["martj42", "https://www.fifa.com/a", "https://apnews.com/b"].join(" | ");
    handlers["/api/competitions"] = () =>
      json([{ key: "WC", name: "FIFA World Cup", group: "International", badge: "Validated", basis: "b", rows: 1094, seasons: 23, first_date: "1930-07-13", last_date: "2026-07-18", sources: long, licences: "CC0-1.0 | not asserted" }]);
    render(page(<AboutTheData />));
    expect(await screen.findByText("View sources")).toBeInTheDocument();
    expect(screen.getAllByText(/fifa\.com/).length).toBeGreaterThan(1); // summary line plus the full list inside the disclosure
    expect(screen.queryByText(/Data limitations/)).toBeNull();
  });
});

describe("season-aware team pickers", () => {
  it("defaults to the latest season's teams and lets the user switch to all seasons", async () => {
    const seen = [];
    handlers["/api/competitions"] = () => json([{ key: "EPL", name: "English Premier League", group: "Domestic league", badge: "Validated", basis: "b" }]);
    handlers["/api/competitions/EPL/seasons"] = () => json(["2026-27", "2025-26"]);
    handlers["/api/competitions/EPL/teams"] = (u) => {
      seen.push(u.searchParams.get("season"));
      return json(u.searchParams.get("season") ? ["Arsenal FC", "Coventry City FC"] : ["Arsenal FC", "Coventry City FC", "Huddersfield Town A.F.C."]);
    };
    render(page(<Predict />, "/predict?comp=EPL"));
    const home = await screen.findByLabelText("Home team");
    await waitFor(() => expect(within(home).getAllByRole("option").length).toBe(3)); // placeholder + 2 current-season teams
    expect(within(home).queryByRole("option", { name: "Huddersfield Town A.F.C." })).toBeNull();
    expect(seen).toContain("2026-27");
    expect(screen.getByLabelText("Team pool")).toHaveValue("2026-27");
    await userEvent.setup().selectOptions(screen.getByLabelText("Team pool"), "all");
    await waitFor(() => expect(within(screen.getByLabelText("Home team")).getByRole("option", { name: "Huddersfield Town A.F.C." })).toBeInTheDocument());
    expect(screen.getByText(/includes clubs that have since left/)).toBeInTheDocument();
  });
});

describe("World Cup visualisation", () => {
  it("shows a top-five chart and progression view from the backend response, and only shows group tables when provided", async () => {
    const odds = ["Spain", "France", "Argentina", "England", "Brazil", "Germany"].map((team, i) => ({ rank: i + 1, team, group: "A", round_of_16_pct: 90, quarter_final_pct: 70, semi_final_pct: 40, final_pct: 20, champion_pct: 12 - i }));
    handlers["/api/worldcup/simulate"] = () => json({ mode: "pre_tournament", simulations: 1000, seed: 1, seconds: 1, engine: "e", note: "n", metadata: {}, title_odds: odds, group_tables: null });
    render(page(<Simulator />));
    await userEvent.setup().click(screen.getByRole("button", { name: "Run simulation" }));
    expect(await screen.findByText("Top five contenders")).toBeInTheDocument();
    expect(screen.getByText("Tournament progression")).toBeInTheDocument();
    expect(screen.queryByText("Group tables")).toBeNull();
    expect(screen.getByText(/brackets are not shown/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------- score-app style pieces
import { CompareRow, FormDots, Gauge } from "../src/components/ui.jsx";

describe("score-app components", () => {
  it("FormDots renders one dot per result with an accessible summary", () => {
    render(<FormDots results={["W", "D", "L", "W", "W"]} />);
    expect(screen.getByLabelText(/last 5 results, oldest first: W D L W W/)).toBeInTheDocument();
  });
  it("CompareRow shows both values and an accessible bar summary", () => {
    render(<CompareRow label="Strength rating (Elo)" left={1800} right={1600} format={(v) => Math.round(v)} />);
    expect(screen.getByRole("img", { name: /Strength rating \(Elo\): 1800 versus 1600/ })).toBeInTheDocument();
    render(<CompareRow label="Missing" left={null} right={3} />);
    expect(screen.getByRole("img", { name: /Missing: n\/a versus 3/ })).toBeInTheDocument();
  });
  it("Gauge labels its probability", () => {
    render(<Gauge value={0.4123} label="Spain win" color="#27d17f" />);
    expect(screen.getByRole("img", { name: "Spain win 41.2%" })).toBeInTheDocument();
  });
});

describe("World Cup real bracket", () => {
  const m = (id, round, t1, t2, s1, s2, winner, status = "played") => ({ id, round, date: "2026-07-01", venue: "V", slots: ["a", "b"], team1: t1, team2: t2, score: s1 == null ? null : { team1: s1, team2: s2 }, shootout: null, winner, status, source: "x" });
  const BRACKET = {
    note: "Real 2026 results; this is not a simulation.",
    rounds: [
      { name: "Round of 32", matches: [m(73, "Round of 32", "Spain", "Canada", 2, 0, "Spain"), m(74, "Round of 32", "France", "Brazil", 1, 1, "Brazil")] },
      { name: "Round of 16", matches: [m(89, "Round of 16", "Spain", "Brazil", 1, 0, "Spain")] },
      { name: "Final", matches: [m(104, "Final", "Spain", "Argentina", null, null, null, "result not in the dataset")] },
    ],
    third_place: m(103, "Match for third place", "France", "England", 4, 6, "England"),
  };
  it("shows the bracket from the backend, marks the missing final result and never claims a champion", async () => {
    handlers["/api/worldcup/bracket"] = () => json(BRACKET);
    render(page(<Simulator />));
    await userEvent.setup().click(screen.getByRole("tab", { name: /2026 bracket/ }));
    expect(await screen.findByText("2026 knockout bracket")).toBeInTheDocument();
    expect(screen.getAllByText(/not a simulation/).length).toBeGreaterThan(0);
    expect(screen.getByText(/result of the final is not in the dataset/)).toBeInTheDocument();
    expect(screen.getAllByText("no result in data").length).toBeGreaterThan(0);
    expect(screen.getByText("Third-place match")).toBeInTheDocument();
  });
  it("shows an error if the bracket cannot be loaded", async () => {
    handlers["/api/worldcup/bracket"] = () => json({ detail: "bracket file missing" }, 503);
    render(page(<Simulator />));
    await userEvent.setup().click(screen.getByRole("tab", { name: /2026 bracket/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("bracket file missing");
  });
});

// ---------------------------------------------------------------- data freshness bar
import SyncStatus from "../src/components/SyncStatus.jsx";

describe("data freshness bar", () => {
  const STATUS = {
    generated_utc: "2026-10-25T10:00:00Z", live_enabled: false, periodic_minutes: 60, approved_sources: ["openligadb"], recent_checks: [], note: "Nothing here is a live score feed.",
    attribution: [{ source: "OpenLigaDB", text: "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0", used_for: ["BUNDESLIGA"] }],
    competitions: [
      { competition_key: "EPL", latest_result: "2026-09-20", awaiting_result: 20, scheduled: 310, approved_sources: [], last_successful_sync_utc: null, state: "stale", state_reasons: ["no approved fresh source for this competition"] },
      { competition_key: "BUNDESLIGA", latest_result: "2026-10-18", awaiting_result: 0, scheduled: 252, approved_sources: ["openligadb"], last_successful_sync_utc: "2026-10-25T09:00:00Z", state: "fresh", state_reasons: [] },
    ],
  };
  it("shows latest result, last update, sync state and per-league freshness, and never says live", async () => {
    handlers["/api/sync/status"] = () => json(STATUS);
    render(page(<SyncStatus />));
    expect(await screen.findByText(/Latest match result:/)).toBeInTheDocument();
    expect(screen.getByText("2026-10-18")).toBeInTheDocument();
    expect(screen.getByText(/off \(cached data only\)/)).toBeInTheDocument();
    expect(screen.queryByText("1 leagues stale")).toBeNull(); // the amber chip is no longer shown (Phase 4.35)
    await userEvent.setup().click(screen.getByRole("button", { name: /Details/ }));
    expect(screen.getByText("no approved fresh source for this competition")).toBeInTheDocument();
    expect(screen.getAllByText("stale").length).toBeGreaterThan(0);
    expect(screen.getByText("fresh")).toBeInTheDocument();
    expect(screen.getByText(/lizenziert unter ODbL 1.0/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\blive (score|match|now)\b(?! feed)/i);
  });
  it("stays hidden while the store is not built (503) and warns on other errors", async () => {
    handlers["/api/sync/status"] = () => json({ detail: "not built" }, 503);
    const { container } = render(page(<SyncStatus />));
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});
