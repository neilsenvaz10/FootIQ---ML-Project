// Home dashboard (Phase 4, stage P4.2). The page shows what /api/featured-fixture returns and nothing else: no fixture, score or kickoff time is made up,
// no forecast is calculated or saved, and one failing part never takes the others down. All club names below are fictional.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Overview from "../src/pages/Overview.jsx";
import { pct } from "../src/lib/format.js";

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const TODAY = "2026-10-27";
const KEYS = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"];
const UTC = { state: "utc", utc: "2026-10-31T15:00:00Z", local: null, time_precision: "minute", zone_verified: true };
const LOCAL = { state: "local_without_time_zone", utc: null, local: "18:30", time_precision: "local_unknown_tz", zone_verified: false };
const UNKNOWN = { state: "unknown", utc: null, local: null, time_precision: "none", zone_verified: false };

const team = (name, resolved = true) => ({ name, entity: resolved ? `CLUB:TST:${name.toLowerCase().replaceAll(" ", "-")}` : null, resolved });
const eligibility = (over = {}) => ({ eligible: true, predictable: true, reliability: "full", flags: [], ...over });
const fixture = (id, over = {}) => ({
  record_id: `tst:epl:2026-27:L${id}`, competition_key: "EPL", competition: "English Premier League", season: "2026-27", matchday_no: 9, matchday_label: "Matchday 9",
  date: "2026-10-31", kickoff: UTC, home: team("Northbridge United"), away: team("Eastvale Town"), status: "scheduled", source: "test-feed",
  eligibility: eligibility(), has_saved_forecast: false, ...over,
});
const FUTURE = { phase: "future_date", ambiguous: false, note: null };
const featured = (over = {}) => ({ ...fixture(1), eligibility: eligibility({ reasons: [], stale_days: 0 }), forecast: null, timing: FUTURE, ...over });
const result = (id, over = {}) => ({
  record_id: `tst:res:${id}`, competition_key: "EPL", competition: "English Premier League", season: "2026-27", matchday_no: 8, date: "2026-10-24",
  home: team("Harbour City"), away: team("Westmoor Rovers"), home_goals: 2, away_goals: 1, status: "completed", source: "test-feed", ...over,
});
const freshness = (state = "fresh", staleKeys = KEYS) => ({
  live_enabled: false, periodic_minutes: 360, note: "n", attribution: [],
  competitions: Object.fromEntries(
    KEYS.map((k) => [k, { state: state === "fresh" || !staleKeys.includes(k) ? "fresh" : state, state_reasons: [], latest_result: "2026-10-25", last_successful_sync_utc: "2026-10-26T08:00:00Z", approved_sources: [], awaiting_result: 0, scheduled: 100 }]),
  ),
});
function payload(over = {}) {
  const f = featured();
  return { generated_utc: `${TODAY}T10:00:00Z`, today_utc: TODAY, scope: { competitions: KEYS, rule: "r" }, featured: f, empty_state: null, upcoming: [fixture(2, { date: "2026-11-01", home: team("Harbour City"), away: team("Westmoor Rovers") })], recent_results: [result(1)], leagues: [], freshness: freshness(), notes: [], ...over };
}

const CLUBS = ["Harbour City", "Northbridge United", "Eastvale Town", "Westmoor Rovers", "Kingsfield Athletic", "Redcliffe Wanderers", "Lowmoor", "Ashgrove"];
const standings = (clubs = CLUBS) => clubs.map((t, i) => ({ pos: i + 1, team: t, played: 9, won: 7 - i, drawn: 1, lost: 1, gf: 20 - i, ga: 8 + i, gd: 12 - 2 * i, points: 22 - 2 * i, form: ["W", "W", "D", "W", "L"] }));
function league(handlers, key = "EPL", over = {}) {
  const { seasons = ["2026-27", "2025-26"], table = standings(), partial = true } = over;
  handlers[`/api/competitions/${key}/seasons`] = () => json(seasons);
  handlers[`/api/competitions/${key}/coverage`] = () =>
    json([{ season: seasons[0], rows_in_dataset: partial ? 70 : 380, expected_matches: 380, coverage_pct: partial ? 18.4 : 100, note: partial ? "incomplete or in progress" : "complete" }]);
  handlers[`/api/competitions/${key}/dashboard`] = () => json({ standings: table, summary: { matches: partial ? 70 : 380, goals_per_match: 2.7 }, results: [] });
}

let handlers;
let calls;
beforeEach(() => {
  handlers = {};
  calls = [];
  handlers["/api/featured-fixture"] = () => json(payload());
  league(handlers, "EPL");
  vi.stubGlobal(
    "fetch",
    vi.fn((url, init) => {
      const u = new URL(url);
      calls.push({ path: u.pathname, search: u.search, method: init?.method ?? "GET" });
      if (handlers[u.pathname]) return handlers[u.pathname](u);
      return json({ detail: `unmocked ${u.pathname}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const home = () => (
  <MemoryRouter initialEntries={["/"]}>
    <Overview />
  </MemoryRouter>
);
// The loading placeholder is also a region named "Next match" (aria-busy), so wait until it has been replaced.
const banner = async () => {
  await waitFor(() => expect(screen.getByRole("region", { name: "Next match" })).not.toHaveAttribute("aria-busy"));
  return screen.getByRole("region", { name: "Next match" });
};
const cardOf = (title) => screen.getByRole("heading", { level: 2, name: title }).closest("section");

describe("Home: the featured match", () => {
  it("is the focal point: both clubs, competition, matchday, day and the verified kickoff", async () => {
    render(home());
    const b = await banner();
    for (const text of ["Northbridge United", "Eastvale Town", "English Premier League", "Matchday 9", "Sat 31 Oct", "15:00 UTC", "Home", "Away"]) {
      expect(within(b).getByText(text), text).toBeInTheDocument();
    }
    expect(within(b).getByRole("heading", { level: 2, name: "Next match" })).toBeInTheDocument();
    expect(b.querySelectorAll("[data-crest]")).toHaveLength(2); // a badge for each club, decorative because the names are written
    expect(b.querySelectorAll("[data-crest][aria-hidden=true]")).toHaveLength(2);
    expect(within(b).getByText(/Fixture source: test-feed/)).toBeInTheDocument();
    expect(within(b).getByText(/Historical and periodically synchronised data, not live/)).toBeInTheDocument();
  });

  it.each([
    [TODAY, "Today", "Tue 27 Oct"],
    ["2026-10-28", "Tomorrow", "Wed 28 Oct"],
  ])("calls %s %s and keeps the date underneath", async (date, word, written) => {
    handlers["/api/featured-fixture"] = () => json(payload({ featured: featured({ date }) }));
    render(home());
    const b = await banner();
    expect(within(b).getByText(word)).toBeInTheDocument();
    expect(within(b).getByText(written)).toBeInTheDocument();
  });

  it.each([
    ["a local time without a zone", LOCAL, "18:30 (time zone unconfirmed)"],
    ["no time at all", UNKNOWN, ""],
  ])("does not invent a kickoff time: %s is said as it is", async (_name, kickoff, written) => {
    handlers["/api/featured-fixture"] = () => json(payload({ featured: featured({ kickoff }) }));
    render(home());
    const b = await banner();
    if (written) expect(within(b).getByText(written)).toBeInTheDocument();
    else expect(b).not.toHaveTextContent(/time not confirmed/i);
    expect(b).not.toHaveTextContent(/\bUTC\b/);
  });

  it("explains a same-day kickoff whose time zone is unconfirmed, and never converts, assumes or calls it live", async () => {
    const timing = { phase: "today_time_zone_unconfirmed", ambiguous: true, note: "Dated today. The kickoff is stored as a local time without a time zone, so it cannot be known whether the match has started. No time is converted or assumed." };
    handlers["/api/featured-fixture"] = () => json(payload({ featured: featured({ date: TODAY, kickoff: LOCAL, timing }) }));
    render(home());
    const b = await banner();
    expect(within(b).queryByText("Today · time zone unconfirmed")).toBeNull(); // chip removed (Phase 4.35)
    expect(within(b).getByText(timing.note)).toBeInTheDocument();
    expect(within(b).getByText("18:30 (time zone unconfirmed)")).toBeInTheDocument();
    expect(b).not.toHaveTextContent(/\bUTC\b|(?<!not )\blive\b|in progress|kicked off|full time/i); // the footnote's "not live" is the one allowed mention
  });

  it("shows stale data and a provisional history as such", async () => {
    const reasons = ["The newest result in this competition is 2026-09-20, 37 days before this fixture."];
    handlers["/api/featured-fixture"] = () =>
      json(payload({ featured: featured({ eligibility: eligibility({ reliability: "provisional", flags: ["stale_history"], reasons, stale_days: 37 }) }), freshness: freshness("stale") }));
    render(home());
    const b = await banner();
    expect(within(b).queryByText("Data not fresh · newest verified result 2026-10-25")).toBeNull(); // warning chips removed (Phase 4.35)
    expect(within(b).queryByText("Provisional history")).toBeNull();
    expect(within(b).queryByText("Fully supported history")).toBeNull();
  });

  it("shows fresh data and a fully supported history as such, with no notes to open", async () => {
    render(home());
    const b = await banner();
    expect(within(b).getByText("Data fresh · newest verified result 2026-10-25")).toBeInTheDocument();
    expect(within(b).getByText("Fully supported history")).toBeInTheDocument();
    expect(within(b).queryByText(/Notes on this fixture/)).toBeNull();
  });

  it("lists the reliability flags once each and the reasons in a disclosure", async () => {
    const reasons = ["Northbridge United has 3 earlier matches without a verified result.", "Eastvale Town has 3 earlier matches without a verified result."];
    handlers["/api/featured-fixture"] = () =>
      json(payload({ featured: featured({ eligibility: eligibility({ reliability: "provisional", flags: ["missing_results_home", "missing_results_away", "kickoff_timezone_unknown"], reasons, stale_days: 0 }) }) }));
    render(home());
    const b = await banner();
    const summary = within(b).getByText("Notes on this fixture's data (2)");
    expect(summary.tagName).toBe("SUMMARY");
    expect(summary.closest("details")).not.toHaveAttribute("open");
    for (const r of reasons) expect(within(b).getByText(r)).toBeInTheDocument();
    expect(within(b).getAllByText("Missing earlier results")).toHaveLength(1); // two flags, one label
    expect(within(b).getByText("Kickoff time zone unconfirmed")).toBeInTheDocument();
    await userEvent.setup().click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
  });

  it("links to the fixture's gameweek, to a manual prediction on its league and to the team comparison", async () => {
    render(home());
    const b = await banner();
    expect(within(b).getByRole("link", { name: "Open gameweek predictions" })).toHaveAttribute("href", "/predict?mode=gameweek&comp=EPL&gw=9");
    expect(within(b).getByRole("link", { name: "Predict a match" })).toHaveAttribute("href", "/predict?mode=manual&comp=EPL");
    expect(within(b).getByRole("link", { name: "Compare teams" })).toHaveAttribute("href", "/compare");
  });

  it("says that no forecast is saved and does not make one: only four read requests are sent", async () => {
    render(home());
    const b = await banner();
    expect(within(b).getByText(/No forecast is saved for this fixture/)).toBeInTheDocument();
    expect(within(b).queryByText(/Saved forecast/)).toBeNull();
    await screen.findByRole("table");
    expect(calls.every((c) => c.method === "GET")).toBe(true);
    expect(calls.map((c) => c.path).sort()).toEqual(["/api/competitions/EPL/coverage", "/api/competitions/EPL/dashboard", "/api/competitions/EPL/seasons", "/api/featured-fixture"]);
    expect(calls.some((c) => /^\/api\/(predict|forecast|gameweek(?!s))/.test(c.path))).toBe(false); // no prediction, no gameweek page, nothing that saves
  });

  it("asks for the featured fixture once, with no parameters", async () => {
    render(home());
    await banner();
    const featuredCalls = calls.filter((c) => c.path === "/api/featured-fixture");
    expect(featuredCalls).toHaveLength(1);
    expect(featuredCalls[0].search).toBe("");
  });

  it.each([
    ["yes", "saved before kickoff"],
    ["no", "saved after kickoff"],
    ["unknown", "kickoff timing unknown"],
  ])("shows a forecast that was already saved, with team names (never 1 and 2); made_before_kickoff=%s", async (flag, written) => {
    const forecast = { created_utc: "2026-10-26T09:15:00Z", data_cutoff_date: "2026-10-25", made_before_kickoff: flag, predictions: { primary: { home: 0.48, draw: 0.27, away: 0.25 } } };
    handlers["/api/featured-fixture"] = () => json(payload({ featured: featured({ forecast, has_saved_forecast: true }) }));
    render(home());
    const b = await banner();
    const strip = within(b).getByRole("img", { name: `Saved forecast: Northbridge United win ${pct(0.48)}, Draw ${pct(0.27)}, Eastvale Town win ${pct(0.25)}` });
    expect(strip).toBeInTheDocument();
    expect(within(b).getByText("Saved forecast · club v1")).toBeInTheDocument();
    expect(within(b).getByText(new RegExp(`Saved 2026-10-26 09:15:00 UTC · history through 2026-10-25 · ${written}`))).toBeInTheDocument();
    expect(within(b).getByText("Northbridge United win")).toBeInTheDocument();
    expect(within(b).getByText("Eastvale Town win")).toBeInTheDocument();
    for (const bare of ["1", "2", "X"]) expect(within(b).queryByText(bare)).toBeNull();
    expect(within(b).queryByText(/No forecast is saved/)).toBeNull();
  });

  it("shows a loading state while the fixture is fetched", async () => {
    handlers["/api/featured-fixture"] = () => new Promise(() => {});
    render(home());
    const b = await screen.findByRole("region", { name: "Next match" });
    expect(b).toHaveAttribute("aria-busy", "true");
    expect(within(b).getByRole("status")).toHaveTextContent("Loading the next fixture…");
  });
});

describe("Home: when nothing can be featured", () => {
  const empty = { code: "no_upcoming_fixture", message: "No scheduled fixture dated 2026-10-27 or later is stored for the five domestic leagues." };

  it("says so in the banner, with the backend's reason, and does not make up a fixture", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ featured: null, upcoming: [], empty_state: empty, freshness: freshness("stale", ["EPL", "SERIEA"]) }));
    render(home());
    const b = await banner();
    expect(within(b).getByText("No upcoming fixture to feature")).toBeInTheDocument();
    expect(within(b).getByText(empty.message)).toBeInTheDocument();
    expect(within(b).getByText("2 of the five leagues do not have fresh data, so the stored schedule may be out of date.")).toBeInTheDocument();
    expect(within(b).getByRole("link", { name: "Browse leagues" })).toHaveAttribute("href", "/analytics");
    expect(within(b).getByRole("link", { name: "Gameweek predictions" })).toHaveAttribute("href", "/predict?mode=gameweek");
    expect(within(b).queryByRole("link", { name: "Open gameweek predictions" })).toBeNull();
    expect(within(cardOf("Next fixtures")).getByText("No further scheduled fixtures are stored.")).toBeInTheDocument();
  });

  it("does not talk about stale data when every league is fresh", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ featured: null, upcoming: [], empty_state: empty }));
    render(home());
    expect(await banner()).not.toHaveTextContent(/do not have fresh data/);
  });
});

describe("Home: failures stay where they happen", () => {
  it("shows the backend's message in the banner, keeps the rest of the page, and fetches again on request", async () => {
    let n = 0;
    handlers["/api/featured-fixture"] = () => (++n === 1 ? json({ detail: "The results store is not available." }, 503) : json(payload()));
    render(home());
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The results store is not available.");
    expect(await screen.findByRole("table")).toBeInTheDocument(); // the league table does not depend on the featured fixture
    expect(screen.getByRole("region", { name: "Quick access" })).toBeInTheDocument();
    await userEvent.setup().click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await banner()).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(n).toBe(2);
  });

  it("keeps the banner when only the league table fails", async () => {
    handlers["/api/competitions/EPL/dashboard"] = () => json({ detail: "dashboard unavailable" }, 500);
    render(home());
    const b = await banner();
    expect(within(b).getByText("Northbridge United")).toBeInTheDocument();
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("dashboard unavailable");
    expect(within(cardOf("League overview")).getByRole("alert")).toBe(alert);
  });
});

describe("Home: next fixtures", () => {
  const fixtures = () => [
    fixture(1, { date: TODAY, kickoff: LOCAL, home: team("Harbour City"), away: team("Westmoor Rovers") }),
    fixture(2, { date: "2026-10-28", kickoff: { ...UTC, utc: "2026-10-28T12:00:00Z" }, home: team("Kingsfield Athletic"), away: team("Lowmoor") }),
    fixture(3, { date: "2026-10-28", kickoff: UNKNOWN, home: team("Ashgrove"), away: team("Redcliffe Wanderers") }),
    fixture(4, { date: "2026-10-31", kickoff: UTC, competition_key: "SERIEA", competition: "Serie A", home: team("Northbridge United"), away: team("Unlisted Club", false) }),
  ];

  it("groups fixtures by day, with the day named, and shows each kickoff as the store has it", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ upcoming: fixtures() }));
    render(home());
    await banner();
    const card = cardOf("Next fixtures");
    expect(within(card).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Today", "Tomorrow", "Sat 31 Oct"]);
    expect(within(card).getByText("18:30 local")).toBeInTheDocument();
    expect(within(card).getByText("12:00 UTC")).toBeInTheDocument();
    expect(within(card).getByText("15:00 UTC")).toBeInTheDocument();
    expect(within(card).queryByText("Time not confirmed")).toBeNull(); // nothing is said when the store has no time (Phase 4.35)
    expect(within(card).getByText("Serie A")).toBeInTheDocument();
    expect(within(card).getAllByText("Premier League")).toHaveLength(3);
  });

  it("makes each row a link to that fixture's gameweek, named with both clubs", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ upcoming: fixtures() }));
    render(home());
    await banner();
    const card = cardOf("Next fixtures");
    // (jsdom joins the inline pieces of a name without spaces; a browser separates them, hence \s*)
    expect(within(card).getByRole("link", { name: /Harbour City\s*versus\s*Westmoor Rovers/ })).toHaveAttribute("href", "/predict?mode=gameweek&comp=EPL&gw=9");
    expect(within(card).getByRole("link", { name: /Northbridge United\s*versus\s*Unlisted Club/ })).toHaveAttribute("href", "/predict?mode=gameweek&comp=SERIEA&gw=9");
    expect(within(card).getByRole("link", { name: "Gameweek predictions →" })).toHaveAttribute("href", "/predict?mode=gameweek&comp=EPL&gw=9");
  });

  it("marks a club that is not matched to an identity", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ upcoming: fixtures() }));
    render(home());
    await banner();
    expect(within(cardOf("Next fixtures")).getAllByText("Club not matched")).toHaveLength(1);
  });

  it("shows at most six fixtures", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ upcoming: Array.from({ length: 8 }, (_, i) => fixture(i + 1, { home: team(`Home ${i + 1}`), away: team(`Away ${i + 1}`) })) }));
    render(home());
    await banner();
    const links = within(cardOf("Next fixtures")).getAllByRole("link");
    expect(links).toHaveLength(6 + 1); // six rows and the header link
  });

  it("says once that every fixture is provisional, instead of on every row", async () => {
    const provisional = eligibility({ reliability: "provisional", flags: ["stale_history"] });
    handlers["/api/featured-fixture"] = () => json(payload({ upcoming: fixtures().map((f) => ({ ...f, eligibility: provisional })) }));
    render(home());
    await banner();
    const card = cardOf("Next fixtures");
    expect(within(card).getByRole("note")).toHaveTextContent(/Provisional\.\s*The stored history behind every fixture below is stale or has gaps/);
    expect(within(card).queryByText("Provisional")).toBeNull();
  });

  it("marks only the provisional rows when some are fully supported", async () => {
    const list = fixtures();
    list[1] = { ...list[1], eligibility: eligibility({ reliability: "provisional", flags: ["missing_results_home"] }) };
    handlers["/api/featured-fixture"] = () => json(payload({ upcoming: list }));
    render(home());
    await banner();
    const card = cardOf("Next fixtures");
    expect(within(card).queryByRole("note")).toBeNull();
    expect(within(card).getAllByText("Provisional")).toHaveLength(1);
  });
});

describe("Home: latest verified results", () => {
  it("shows each final score with the clubs named, the league, and FT or AWD", async () => {
    handlers["/api/featured-fixture"] = () =>
      json(payload({ recent_results: [result(1), result(2, { home: team("Lowmoor"), away: team("Ashgrove"), home_goals: 0, away_goals: 3, status: "awarded", competition_key: "LIGUE1", competition: "Ligue 1" })] }));
    render(home());
    await banner();
    const card = cardOf("Latest verified results");
    expect(within(card).getByRole("group", { name: "Harbour City 2, Westmoor Rovers 1" })).toBeInTheDocument();
    expect(within(card).getByRole("group", { name: "Lowmoor 0, Ashgrove 3" })).toBeInTheDocument();
    expect(within(card).getByText("FT")).toBeInTheDocument();
    expect(within(card).getByText("AWD")).toBeInTheDocument();
    expect(within(card).getByText("Premier League")).toBeInTheDocument();
    expect(within(card).getByText("Ligue 1")).toBeInTheDocument();
    expect(within(card).getAllByText("24 Oct")).toHaveLength(2);
  });

  it("shows at most six results", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ recent_results: Array.from({ length: 8 }, (_, i) => result(i + 1, { home: team(`Home ${i + 1}`), away: team(`Away ${i + 1}`) })) }));
    render(home());
    await banner();
    expect(within(cardOf("Latest verified results")).getAllByRole("group")).toHaveLength(6);
  });

  it("says when no result is stored", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ recent_results: [] }));
    render(home());
    await banner();
    expect(within(cardOf("Latest verified results")).getByText("No verified results are stored for these leagues yet.")).toBeInTheDocument();
  });
});

describe("Home: league overview", () => {
  it("shows the newest season's top six, labelled as partial, with the data's freshness", async () => {
    handlers["/api/featured-fixture"] = () => json(payload({ freshness: freshness("stale") }));
    render(home());
    const table = await screen.findByRole("table", { name: /Premier League 2026-27: the top 6 clubs by points/ });
    const card = cardOf("League overview");
    expect(within(card).getByText("Premier League 2026-27: newest season in the data")).toBeInTheDocument();
    expect(within(card).queryByText("Partial season: 70 of 380 matches in the data")).toBeNull(); // chip removed (Phase 4.35)
    expect(within(card).queryByText("Data not fresh · newest verified result 2026-10-25")).toBeNull();
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["#", "Club", "P", "GD", "Pts", "Form"]);
    expect(within(table).getAllByRole("row")).toHaveLength(1 + 6);
    expect(within(table).getByText("Harbour City")).toBeInTheDocument();
    expect(within(table).queryByText("Ashgrove")).toBeNull(); // seventh and eighth are not shown
    expect(within(card).getByText("Computed from the 70 matches in the data, 3 points for a win and 1 for a draw.")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "Full table →" })).toHaveAttribute("href", "/analytics?comp=EPL");
  });

  it("does not call a finished season partial", async () => {
    league(handlers, "EPL", { partial: false });
    render(home());
    await screen.findByRole("table");
    expect(within(cardOf("League overview")).queryByText(/Partial season/)).toBeNull();
  });

  it("switches league and then shows that league's newest season", async () => {
    league(handlers, "SERIEA", { seasons: ["2026-27"], table: standings(["Dunmore", "Falcon Park", "Greyfriars", "Hollin", "Ivybridge", "Jarrow Town"]) });
    render(home());
    await screen.findByRole("table");
    await userEvent.setup().click(screen.getByRole("radio", { name: "Serie A" }));
    expect(await screen.findByRole("table", { name: /Serie A 2026-27/ })).toBeInTheDocument();
    expect(within(cardOf("League overview")).getByText("Dunmore")).toBeInTheDocument();
    expect(calls.map((c) => c.path)).toContain("/api/competitions/SERIEA/dashboard");
    expect(calls.find((c) => c.path === "/api/competitions/SERIEA/dashboard").search).toBe("?season=2026-27");
  });

  it("offers exactly the five domestic leagues, with one pill selected", async () => {
    render(home());
    await screen.findByRole("table");
    const group = screen.getByRole("radiogroup", { name: "League" });
    expect(within(group).getAllByRole("radio").map((r) => r.textContent)).toEqual(["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]);
    expect(within(group).getAllByRole("radio").filter((r) => r.getAttribute("aria-checked") === "true")).toHaveLength(1);
  });

  it("says when a league has no stored season, or no result in it yet", async () => {
    league(handlers, "LALIGA", { seasons: [] });
    league(handlers, "BUNDESLIGA", { table: null });
    render(home());
    await screen.findByRole("table");
    const user = userEvent.setup();
    await user.click(screen.getByRole("radio", { name: "La Liga" }));
    expect(await screen.findByText("No season is stored for this league.")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Bundesliga" }));
    expect(await screen.findByText("No results are stored for this season yet.")).toBeInTheDocument();
  });

  it("shows a failure on the card and fetches the table again on request", async () => {
    let n = 0;
    handlers["/api/competitions/EPL/dashboard"] = () => (++n === 1 ? json({ detail: "dashboard unavailable" }, 500) : json({ standings: standings(), summary: { matches: 70 }, results: [] }));
    render(home());
    const alert = await within(cardOf("League overview")).findByRole("alert");
    expect(alert).toHaveTextContent("dashboard unavailable");
    await userEvent.setup().click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(n).toBe(2);
  });
});

describe("Home: quick access and structure", () => {
  it("links to match predictions, gameweek predictions, team comparison and simulations", async () => {
    render(home());
    const quick = screen.getByRole("region", { name: "Quick access" });
    expect(within(quick).getAllByRole("link").map((a) => a.getAttribute("href"))).toEqual(["/predict?mode=manual", "/predict?mode=gameweek", "/compare", "/simulations"]);
    for (const name of ["Match predictions", "Gameweek predictions", "Compare teams", "Simulations"]) expect(within(quick).getByText(name)).toBeInTheDocument();
    await banner();
  });

  it("has one h1 and puts the featured match before everything else", async () => {
    render(home());
    const b = await banner();
    await screen.findByRole("table");
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual(["Home"]);
    const order = [b, screen.getByRole("region", { name: "Quick access" }), cardOf("Next fixtures"), cardOf("League overview"), cardOf("Latest verified results")];
    for (let i = 1; i < order.length; i++) expect(order[i - 1].compareDocumentPosition(order[i]) & Node.DOCUMENT_POSITION_FOLLOWING, `section ${i}`).toBeTruthy();
  });

  it("no longer carries the old report: no coverage charts, no validation donut, no competition catalogue request", async () => {
    render(home());
    await banner();
    await screen.findByRole("table");
    for (const gone of ["Matches by competition", "Prediction validation", "Data limitations", "About the data"]) expect(screen.queryByText(gone), gone).toBeNull();
    expect(calls.some((c) => c.path === "/api/competitions" || c.path === "/api/models/performance" || c.path === "/api/meta")).toBe(false);
  });

  it("gives every link and button a name", async () => {
    render(home());
    await banner();
    await screen.findByRole("table");
    const controls = [...screen.getAllByRole("link"), ...screen.getAllByRole("radio"), ...screen.queryAllByRole("button")];
    expect(controls.length).toBeGreaterThan(12);
    for (const el of controls) expect(el).toHaveAccessibleName();
  });
});
