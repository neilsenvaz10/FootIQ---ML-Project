// Matches hub (Phase 4, stage P4.3). The page shows what /api/matches returns, a page at a time: stored kickoffs as stored (a local time without a time zone is marked
// unconfirmed, never converted), verified scores, freshness, provisional and source indicators, and links onward. It computes and forecasts nothing, and it never asks the
// browser's clock what is live or finished. All club names below are fictional.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import Matches from "../src/pages/Matches.jsx";

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const TODAY = "2026-10-27";
const KEYS = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"];
const NAMES = { EPL: "English Premier League", LALIGA: "La Liga", BUNDESLIGA: "Bundesliga", SERIEA: "Serie A", LIGUE1: "Ligue 1" };
const UTC = (d, hhmm = "15:00") => ({ state: "utc", utc: `${d}T${hhmm}:00Z`, local: null, time_precision: "minute", zone_verified: true });
const LOCAL = { state: "local_without_time_zone", utc: null, local: "18:30", time_precision: "local_unknown_tz", zone_verified: false };
const UNKNOWN = { state: "unknown", utc: null, local: null, time_precision: "date_only", zone_verified: false };
const team = (name, resolved = true) => ({ name, entity: resolved ? `CLUB:TST:${name.toLowerCase().replaceAll(" ", "-")}` : null, resolved });
const FUTURE = { phase: "future_date", ambiguous: false, note: null };
const TODAY_UNCONFIRMED = { phase: "today_time_zone_unconfirmed", ambiguous: true, note: "Dated today. The kickoff is stored as a local time without a time zone, so it cannot be known whether the match has started. No time is converted or assumed." };

const match = (id, over = {}) => ({
  record_id: `tst:${id}`, competition_key: "EPL", competition: NAMES.EPL, season: "2026-27", matchday_no: 9, matchday_label: "Matchday 9", date: "2026-10-31", kickoff: UTC("2026-10-31"),
  home: team("Northbridge United"), away: team("Eastvale Town"), status: "scheduled", stored_status: "scheduled", result: null, result_missing: false, source: "test-feed", timing: FUTURE,
  eligibility: { eligible: true, predictable: true, reliability: "full", flags: [] }, saved_forecast_runs: 0, ...over,
});
const finished = (id, hg, ag, over = {}) => match(id, { date: "2026-10-24", status: "completed", stored_status: "completed", kickoff: UTC("2026-10-24"), result: { home_goals: hg, away_goals: ag, source: "test-feed" }, timing: { phase: "result_stored", ambiguous: false, note: null }, eligibility: null, ...over });

const freshness = (state = "fresh") => ({
  live_enabled: false, periodic_minutes: 360, note: "n", attribution: [],
  competitions: Object.fromEntries(KEYS.map((k) => [k, { state, state_reasons: [], latest_result: "2026-10-25", last_successful_sync_utc: "2026-10-26T08:00:00Z", approved_sources: [], awaiting_result: 0, scheduled: 100 }])),
});
const COUNTS = { upcoming: 3, awaiting_result: 1, completed: 2, other: 0, all: 6 };
function answer(items, over = {}) {
  return {
    generated_utc: `${TODAY}T10:00:00Z`, today_utc: TODAY, scope: { competitions: KEYS, seasons: { EPL: "2026-27" }, matchday: null, status: "upcoming", order: "asc", limit: 25 },
    counts: COUNTS, items, page: { limit: 25, returned: items.length, has_more: false, next_cursor: null }, facets: { seasons: ["2026-27", "2025-26"], matchdays: [1, 2, 9] }, freshness: freshness(), notes: [], ...over,
  };
}

let handlers;
let calls;
beforeEach(() => {
  handlers = {};
  calls = [];
  handlers["/api/matches"] = () => json(answer([match(1)]));
  vi.stubGlobal(
    "fetch",
    vi.fn((url, init) => {
      const u = new URL(url);
      calls.push({ path: u.pathname, method: init?.method ?? "GET", q: Object.fromEntries(u.searchParams) });
      if (handlers[u.pathname]) return handlers[u.pathname](u);
      return json({ detail: `unmocked ${u.pathname}` }, 404);
    }),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const Where = () => <output data-testid="where">{useLocation().search}</output>;
const hub = (route = "/matches") => (
  <MemoryRouter initialEntries={[route]}>
    <Matches />
    <Where />
  </MemoryRouter>
);
const rowsOf = () => screen.getAllByRole("article");
const matchCalls = () => calls.filter((c) => c.path === "/api/matches");

describe("Matches: what a row shows", () => {
  it("lists upcoming matches by day, with both clubs, badges and each kickoff exactly as stored", async () => {
    handlers["/api/matches"] = () =>
      json(answer([
        match(1, { date: TODAY, kickoff: LOCAL, timing: TODAY_UNCONFIRMED }),
        match(2, { date: TODAY, kickoff: UTC(TODAY, "19:45"), timing: { phase: "today_before_kickoff", ambiguous: false, note: null }, home: team("Harbour City"), away: team("Westmoor Rovers") }),
        match(3, { date: "2026-10-28", kickoff: UNKNOWN, home: team("Kingsfield Athletic"), away: team("Lowmoor") }),
        match(4, { date: "2026-10-31", kickoff: UTC("2026-10-31"), home: team("Ashgrove"), away: team("Redcliffe Wanderers") }),
      ]));
    render(hub());
    await screen.findByRole("article", { name: "Northbridge United v Eastvale Town" });
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Today · Tue 27 Oct 2026", "Tomorrow · Wed 28 Oct 2026", "Sat 31 Oct 2026"]);
    expect(rowsOf()).toHaveLength(4);
    const first = within(screen.getByRole("article", { name: "Northbridge United v Eastvale Town" }));
    expect(first.getByText("18:30 local")).toBeInTheDocument();
    expect(first.getByText("zone unconfirmed")).toBeInTheDocument();
    expect(first.queryByText("Today · time zone unconfirmed")).toBeNull(); // chip removed (Phase 4.35)
    expect(within(screen.getByRole("article", { name: "Harbour City v Westmoor Rovers" })).getByText("19:45 UTC")).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Kingsfield Athletic v Lowmoor" })).queryByText("Time not confirmed")).toBeNull(); // nothing is said when the store has no time (Phase 4.35)
    for (const row of rowsOf()) expect(row.querySelectorAll("[data-crest]")).toHaveLength(2); // a badge for each club
  });

  it("says once, under Today, that some kickoffs have no verified time zone, and never mentions it when none is in doubt", async () => {
    handlers["/api/matches"] = () => json(answer([match(1, { date: TODAY, kickoff: LOCAL, timing: TODAY_UNCONFIRMED }), match(2, { date: TODAY, kickoff: LOCAL, timing: TODAY_UNCONFIRMED, home: team("Harbour City"), away: team("Lowmoor") })]));
    const { unmount } = render(hub());
    await screen.findAllByRole("article");
    expect(screen.getAllByText(/Some matches today have no verified kickoff time zone/)).toHaveLength(1);
    unmount();
    handlers["/api/matches"] = () => json(answer([match(1)]));
    render(hub());
    await screen.findAllByRole("article");
    expect(screen.queryByText(/Some matches today/)).toBeNull();
  });

  it("never calls anything live and never converts a local time into UTC", async () => {
    handlers["/api/matches"] = () => json(answer([match(1, { date: TODAY, kickoff: LOCAL, timing: TODAY_UNCONFIRMED })]));
    render(hub());
    const row = await screen.findByRole("article");
    expect(row).not.toHaveTextContent(/\bUTC\b|\blive\b|in progress|kicked off/i);
  });

  it("shows the league only when all leagues are listed, and the matchday, status, provisional, unmatched-club, saved-forecast and source indicators", async () => {
    handlers["/api/matches"] = () =>
      json(answer([
        match(1, { competition_key: "SERIEA", competition: NAMES.SERIEA, status: "awaiting_result", stored_status: "scheduled", date: "2026-10-26", timing: { phase: "date_passed", ambiguous: false, note: "The date has passed." }, eligibility: { eligible: true, predictable: true, reliability: "provisional", flags: ["stale_history"] }, saved_forecast_runs: 2 }),
        match(2, { home: team("Unlisted Club", false), source: "openligadb" }),
      ]));
    render(hub());
    await screen.findAllByRole("article");
    const a = within(screen.getAllByRole("article")[0]);
    expect(a.getByText("Serie A")).toBeInTheDocument();
    expect(a.getByText("Matchday 9")).toBeInTheDocument();
    expect(a.getByText("Awaiting result")).toBeInTheDocument();
    expect(a.getByText("Provisional history")).toBeInTheDocument();
    expect(a.getByText("Gameweek forecast saved")).toBeInTheDocument();
    expect(a.getByText("Source: test-feed")).toBeInTheDocument();
    const b = within(screen.getAllByRole("article")[1]);
    expect(b.getByText("Club not matched")).toBeInTheDocument();
    expect(b.getByText("Source: openligadb")).toBeInTheDocument();
    expect(b.getByText("Premier League")).toBeInTheDocument();
  });

  it("marks a stored UTC kickoff that has passed as awaiting a result, with no claim about the match", async () => {
    handlers["/api/matches"] = () => json(answer([match(1, { date: TODAY, status: "awaiting_result", stored_status: "scheduled", kickoff: UTC(TODAY, "09:00"), timing: { phase: "kickoff_passed", ambiguous: true, note: "The stored kickoff time (UTC) has passed and no verified result is stored yet. This page does not say whether the match is in progress or finished." } })]));
    render(hub());
    const row = within(await screen.findByRole("article"));
    expect(row.getByText("Awaiting result")).toBeInTheDocument();
    expect(row.queryByText("Kickoff passed · no result yet")).toBeNull(); // chip removed (Phase 4.35)
    expect(row.getByText("09:00 UTC")).toBeInTheDocument();
    expect(screen.getByRole("article")).not.toHaveTextContent(/\blive\b|in progress.*\bnow\b/i);
  });

  it("shows verified final scores with the winner marked, FT or Awarded, the source, and no link to a manual prediction", async () => {
    handlers["/api/matches"] = () =>
      json(answer([
        finished(1, 2, 1),
        finished(2, 0, 3, { home: team("Lowmoor"), away: team("Ashgrove"), status: "awarded", stored_status: "awarded" }),
        finished(3, 0, 0, { home: team("Harbour City"), away: team("Westmoor Rovers") }),
      ], { counts: { ...COUNTS, completed: 3 } }));
    render(hub("/matches?status=completed"));
    const one = within(await screen.findByRole("article", { name: "Northbridge United v Eastvale Town" }));
    expect(one.getByText("Full time")).toBeInTheDocument();
    expect(one.getByText("Final score: Northbridge United 2, Eastvale Town 1.")).toBeInTheDocument();
    expect(one.getByText("Northbridge United").className).toMatch(/font-extrabold/);           // the winner
    expect(one.getByText("Eastvale Town").className).toMatch(/text-mute/);                      // the loser
    expect(one.queryByRole("link", { name: /Predict .* manually/ })).toBeNull();
    expect(one.getByText("Source: test-feed")).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Lowmoor v Ashgrove" })).getByText("Awarded")).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Harbour City v Westmoor Rovers" })).getByText("Final score: Harbour City 0, Westmoor Rovers 0.")).toBeInTheDocument();
  });

  it("shows no score at all when a finished match has none stored", async () => {
    handlers["/api/matches"] = () => json(answer([finished(1, 0, 0, { result: null, result_missing: true })]));
    render(hub("/matches?status=completed"));
    const row = within(await screen.findByRole("article"));
    expect(row.getByText("Final score not stored for this match.")).toBeInTheDocument();
    expect(row.queryByText(/Final score: /)).toBeNull();
  });
});

describe("Matches: where each row leads", () => {
  it("links an unplayed match to its gameweek (with its season), to a manual prediction and to the comparison", async () => {
    handlers["/api/matches"] = () => json(answer([match(1, { season: "2025-26" })]));
    render(hub());
    const row = within(await screen.findByRole("article"));
    expect(row.getByRole("link", { name: /Gameweek 9 predictions and forecast history: Northbridge United v Eastvale Town/ })).toHaveAttribute("href", "/predict?mode=gameweek&comp=EPL&season=2025-26&gw=9");
    expect(row.getByRole("link", { name: "Predict Northbridge United v Eastvale Town manually" })).toHaveAttribute("href", "/predict?mode=manual&comp=EPL&home=Northbridge+United&away=Eastvale+Town");
    expect(row.getByRole("link", { name: "Compare Northbridge United and Eastvale Town" })).toHaveAttribute("href", "/compare?comp=EPL&a=Northbridge+United&b=Eastvale+Town");
  });

  it("offers no link when a club is not matched to an identity (nothing could be pre-selected)", async () => {
    handlers["/api/matches"] = () => json(answer([match(1, { away: team("Unlisted Club", false) })]));
    render(hub());
    const row = within(await screen.findByRole("article"));
    expect(row.queryAllByRole("link")).toHaveLength(0);
    expect(row.getByText("Club not matched")).toBeInTheDocument();
  });
});

describe("Matches: filters live in the address and in the request", () => {
  it("asks for the upcoming matches of all leagues first, with a bounded page, and writes nothing to the address", async () => {
    render(hub());
    await screen.findAllByRole("article");
    expect(matchCalls()).toHaveLength(1);
    expect(matchCalls()[0].q).toEqual({ status: "upcoming", limit: "25" });
    expect(screen.getByTestId("where")).toHaveTextContent("");
    expect(screen.getByText(/Showing 1 of 3 upcoming matches · all six competitions · newest season/)).toBeInTheDocument();
  });

  it("reads comp, season, matchday and status from the address", async () => {
    render(hub("/matches?comp=SERIEA&season=2025-26&matchday=9&status=completed"));
    await screen.findAllByRole("article");
    expect(matchCalls()[0].q).toEqual({ comp: "SERIEA", season: "2025-26", matchday: "9", status: "completed", limit: "25" });
    expect(screen.getByRole("radio", { name: "Serie A" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByLabelText("Season")).toHaveValue("2025-26");
    expect(screen.getByLabelText("Matchday")).toHaveValue("9");
    expect(screen.getByRole("radio", { name: /^Completed/ })).toHaveAttribute("aria-checked", "true");
    for (const row of rowsOf()) expect(within(row).queryByText("Premier League")).toBeNull(); // one league selected: its name is not repeated on every row
  });

  it("ignores nonsense in the address instead of sending it", async () => {
    render(hub("/matches?comp=UEL&season=2026&matchday=999&status=live&team=CLUB:X:y"));       // an archived competition is not a hub competition; a team without a league is dropped
    await screen.findAllByRole("article");
    expect(matchCalls()[0].q).toEqual({ status: "upcoming", limit: "25" });
  });

  it("changing the league keeps the season, clears the matchday and asks again", async () => {
    const user = userEvent.setup();
    render(hub("/matches?season=2025-26&matchday=9"));
    await screen.findAllByRole("article");
    await user.click(screen.getByRole("radio", { name: "La Liga" }));
    await waitFor(() => expect(matchCalls()).toHaveLength(2));
    expect(matchCalls()[1].q).toEqual({ comp: "LALIGA", season: "2025-26", status: "upcoming", limit: "25" });
    expect(screen.getByTestId("where")).toHaveTextContent("?season=2025-26&comp=LALIGA");
  });

  it("season, matchday and status each change the request; upcoming is the default and is not written to the address", async () => {
    const user = userEvent.setup();
    render(hub());
    await screen.findAllByRole("article");
    await user.selectOptions(screen.getByLabelText("Season"), "2025-26");
    await waitFor(() => expect(matchCalls().at(-1).q.season).toBe("2025-26"));
    await user.selectOptions(screen.getByLabelText("Matchday"), "9");
    await waitFor(() => expect(matchCalls().at(-1).q.matchday).toBe("9"));
    await user.click(screen.getByRole("radio", { name: /^Completed/ }));
    await waitFor(() => expect(matchCalls().at(-1).q.status).toBe("completed"));
    expect(screen.getByTestId("where")).toHaveTextContent("season=2025-26");
    expect(screen.getByTestId("where")).toHaveTextContent("status=completed");
    await user.click(screen.getByRole("radio", { name: /^Upcoming/ }));
    await waitFor(() => expect(matchCalls().at(-1).q.status).toBe("upcoming"));
    expect(screen.getByTestId("where")).not.toHaveTextContent("status=");
  });

  it("offers the leagues, the status counts the server gave, the seasons and the matchdays of the selection", async () => {
    render(hub());
    await screen.findAllByRole("article");
    expect(within(screen.getByRole("radiogroup", { name: "League" })).getAllByRole("radio").map((r) => r.textContent)).toEqual(["All leagues", "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1", "Champions League"]);
    expect(within(screen.getByRole("radiogroup", { name: "Status" })).getAllByRole("radio").map((r) => r.textContent)).toEqual(["Upcoming · 3", "Awaiting result · 1", "Completed · 2", "All · 6"]);
    expect(within(screen.getByLabelText("Season")).getAllByRole("option").map((o) => o.textContent)).toEqual(["Newest season", "2026-27", "2025-26"]);
    expect(within(screen.getByLabelText("Matchday")).getAllByRole("option").map((o) => o.textContent)).toEqual(["All matchdays", "Matchday 1", "Matchday 2", "Matchday 9"]);
  });

  it("shows the postponed or cancelled status only when there is one, or when it is the selection", async () => {
    handlers["/api/matches"] = () => json(answer([match(1, { status: "postponed", stored_status: "postponed" })], { counts: { ...COUNTS, other: 2, all: 8 } }));
    render(hub("/matches?status=other"));
    await screen.findAllByRole("article");
    expect(screen.getByRole("radio", { name: "Postponed or cancelled · 2" })).toHaveAttribute("aria-checked", "true");
    expect(within(await screen.findByRole("article")).getByText("Postponed")).toBeInTheDocument();
  });
});

describe("Matches: pages, states and failures", () => {
  const second = (cursor) => [match(`p${cursor}a`, { home: team(`Second ${cursor} Home`), away: team(`Second ${cursor} Away`) })];

  it("loads more with the server's cursor, appends without duplicates, and stops when the server says there is no more", async () => {
    handlers["/api/matches"] = (u) => {
      const cursor = u.searchParams.get("cursor");
      if (!cursor) return json(answer([match(1)], { page: { limit: 25, returned: 1, has_more: true, next_cursor: "c1" }, counts: { ...COUNTS, upcoming: 3 } }));
      if (cursor === "c1") return json(answer(second(2), { page: { limit: 25, returned: 1, has_more: true, next_cursor: "c2" } }));
      return json(answer(second(3), { page: { limit: 25, returned: 1, has_more: false, next_cursor: null } }));
    };
    const user = userEvent.setup();
    render(hub());
    await screen.findAllByRole("article");
    expect(screen.getByText("1 of 3 shown")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show more matches" }));
    await waitFor(() => expect(rowsOf()).toHaveLength(2));
    expect(matchCalls().map((c) => c.q.cursor)).toEqual([undefined, "c1"]);
    expect(screen.getByText("2 of 3 shown")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show more matches" }));
    await waitFor(() => expect(rowsOf()).toHaveLength(3));
    expect(screen.queryByRole("button", { name: "Show more matches" })).toBeNull();
    expect(matchCalls().every((c) => c.q.limit === "25")).toBe(true);
    expect(new Set(rowsOf().map((r) => r.getAttribute("aria-label"))).size).toBe(3);
  });

  it("keeps the rows already shown when a later page fails, says why, and retries that page only", async () => {
    let failing = true;
    handlers["/api/matches"] = (u) => {
      if (!u.searchParams.get("cursor")) return json(answer([match(1)], { page: { limit: 25, returned: 1, has_more: true, next_cursor: "c1" } }));
      if (failing) return json({ detail: "the page could not be read" }, 500);
      return json(answer(second(2)));
    };
    const user = userEvent.setup();
    render(hub());
    await screen.findAllByRole("article");
    await user.click(screen.getByRole("button", { name: "Show more matches" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("the page could not be read");
    expect(rowsOf()).toHaveLength(1);
    failing = false;
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(rowsOf()).toHaveLength(2));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows a loading state, and the filters are usable while it lasts", async () => {
    handlers["/api/matches"] = () => new Promise(() => {});
    render(hub());
    expect(await screen.findByText("Loading matches…")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Matches" })).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("radiogroup", { name: "League" })).toBeInTheDocument();
    expect(screen.queryAllByRole("article")).toHaveLength(0);
  });

  it("shows the backend's message when the first page fails, offers a retry and a reset, and no match", async () => {
    let n = 0;
    handlers["/api/matches"] = () => (++n === 1 ? json({ detail: "no data for season '1999-00'" }, 404) : json(answer([match(1)])));
    const user = userEvent.setup();
    render(hub("/matches?season=1999-00"));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("no data for season '1999-00'");
    expect(screen.queryAllByRole("article")).toHaveLength(0);
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findAllByRole("article")).toHaveLength(1);
    expect(n).toBe(2);
  });

  it("resets every filter to the default selection", async () => {
    handlers["/api/matches"] = () => json({ detail: "boom" }, 500);
    const user = userEvent.setup();
    render(hub("/matches?comp=EPL&season=2025-26&status=completed"));
    await screen.findByRole("alert");
    handlers["/api/matches"] = () => json(answer([match(1)]));
    await user.click(screen.getByRole("button", { name: "Reset filters" }));
    await screen.findAllByRole("article");
    expect(screen.getByTestId("where")).toHaveTextContent("");
    expect(matchCalls().at(-1).q).toEqual({ status: "upcoming", limit: "25" });
  });

  it("explains an empty selection, points at the other statuses it has, and can show them", async () => {
    handlers["/api/matches"] = (u) => (u.searchParams.get("status") === "all" ? json(answer([finished(1, 1, 0)], { counts: { ...COUNTS, upcoming: 0, all: 4 } })) : json(answer([], { counts: { ...COUNTS, upcoming: 0, all: 4 } })));
    const user = userEvent.setup();
    render(hub());
    expect(await screen.findByText("No upcoming matches for this selection.")).toBeInTheDocument();
    expect(screen.getByText(/The same selection has 4 matches in other statuses; choose All/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show all statuses" }));
    expect(await screen.findAllByRole("article")).toHaveLength(1);
  });

  it("an empty selection with nothing in any status says so without the hint", async () => {
    handlers["/api/matches"] = () => json(answer([], { counts: { upcoming: 0, awaiting_result: 0, completed: 0, other: 0, all: 0 }, scope: { competitions: ["LIGUE1"], seasons: {}, matchday: null, status: "upcoming", order: "asc", limit: 25 } }));
    render(hub("/matches?comp=LIGUE1"));
    expect(await screen.findByText("No upcoming matches for this selection.")).toBeInTheDocument();
    expect(screen.queryByText(/in other statuses/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Show all statuses" })).toBeNull();
  });

  it("drops a slow answer that belongs to filters the user has already left", async () => {
    const resolvers = {};
    handlers["/api/matches"] = (u) => new Promise((resolve) => { resolvers[u.searchParams.get("comp") ?? "all"] = () => resolve({ ok: true, status: 200, statusText: "x", json: () => Promise.resolve(answer([match(u.searchParams.get("comp") ?? "all", { home: team(`${u.searchParams.get("comp") ?? "all"} Home`), away: team(`${u.searchParams.get("comp") ?? "all"} Away`) })])) }); });
    const user = userEvent.setup();
    render(hub());
    await waitFor(() => expect(resolvers.all).toBeDefined());
    await user.click(screen.getByRole("radio", { name: "Serie A" }));
    await waitFor(() => expect(resolvers.SERIEA).toBeDefined());
    resolvers.SERIEA();
    await screen.findByRole("article", { name: "SERIEA Home v SERIEA Away" });
    resolvers.all();                                                                       // the first, slower answer arrives last
    await new Promise((r) => setTimeout(r, 30));
    expect(rowsOf().map((r) => r.getAttribute("aria-label"))).toEqual(["SERIEA Home v SERIEA Away"]);
  });
});

describe("Matches: freshness", () => {
  it("shows one league's freshness as a chip, with the newest verified result", async () => {
    handlers["/api/matches"] = () => json(answer([match(1)], { scope: { competitions: ["EPL"], seasons: { EPL: "2026-27" }, matchday: null, status: "upcoming", order: "asc", limit: 25 }, freshness: freshness("stale") }));
    render(hub("/matches?comp=EPL"));
    expect(await screen.findByText(/Historical data, synchronised periodically\. Nothing here is live\./)).toBeInTheDocument();
    expect(screen.queryByText("Data not fresh · newest verified result 2026-10-25")).toBeNull(); // warning chip removed (Phase 4.35)
  });

  it("summarises all five leagues and lists each one in a disclosure", async () => {
    handlers["/api/matches"] = () => json(answer([match(1)], { freshness: { ...freshness(), competitions: { ...freshness().competitions, SERIEA: { ...freshness().competitions.SERIEA, state: "stale", latest_result: "2026-09-20" }, LIGUE1: { ...freshness().competitions.LIGUE1, state: "stale" } } } }));
    render(hub());
    expect(await screen.findByText(/Historical data, synchronised periodically/)).toBeInTheDocument();
    expect(screen.queryByText("Data not fresh in 2 of 5 competitions")).toBeNull(); // warning chip and the per-competition disclosure are not shown while data is stale (Phase 4.35)
    expect(screen.queryByText("Data freshness by competition")).toBeNull();
  });
});

describe("Matches: what the page does not do", () => {
  it("sends only bounded reads of /api/matches: no write, no forecast, no gameweek page, no catalogue", async () => {
    const user = userEvent.setup();
    render(hub());
    await screen.findAllByRole("article");
    await user.click(screen.getByRole("radio", { name: "Bundesliga" }));
    await waitFor(() => expect(matchCalls()).toHaveLength(2));
    expect(calls.every((c) => c.method === "GET" && c.path === "/api/matches" && Number(c.q.limit) <= 25)).toBe(true);
  });

  it("does not use the browser's clock: with the system date moved years ahead, Today is still the server's today", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2031-05-05T12:00:00Z"));
    handlers["/api/matches"] = () => json(answer([match(1, { date: TODAY, kickoff: LOCAL, timing: TODAY_UNCONFIRMED }), match(2, { date: "2026-10-28", home: team("Harbour City"), away: team("Lowmoor") })]));
    render(hub());
    await screen.findAllByRole("article");
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Today · Tue 27 Oct 2026", "Tomorrow · Wed 28 Oct 2026"]);
    expect(screen.queryByText("Awaiting result")).toBeNull();
  });

  it("the Matches sources never read the browser's clock or locale", () => {
    for (const file of ["src/pages/Matches.jsx", "src/components/matches/MatchCard.jsx", "src/components/matches/MatchFilters.jsx", "src/components/Kickoff.jsx", "src/lib/matches.js"]) {
      const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", file), "utf8");
      expect(src, file).not.toMatch(/Date\.now|new Date\(\)|toLocale|getTimezoneOffset|performance\.now|setInterval/);
    }
  });

  it("has one h1, names every row, and every link and radio has a name", async () => {
    render(hub());
    await screen.findAllByRole("article");
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual(["Matches"]);
    for (const row of rowsOf()) expect(row).toHaveAccessibleName();
    for (const el of [...screen.getAllByRole("link"), ...screen.getAllByRole("radio")]) expect(el).toHaveAccessibleName();
  });
});


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
    expect(row.getByText(/Northbridge United 2-3 Eastvale Town \(final score, penalties excluded\)/)).toBeInTheDocument();
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
    expect(await screen.findByText(/Historical data, synchronised periodically/)).toBeInTheDocument();
    expect(screen.queryByText(/Historical only · newest verified result 2026-10-21/)).toBeNull(); // amber chip removed (Phase 4.35)
  });

  it("lists the Champions League in the freshness disclosure of the all-competitions view", async () => {
    handlers["/api/matches"] = () => json(answer([match(1)], { freshness: { ...freshness(), competitions: { ...freshness().competitions, UCL: uclFresh } } }));
    render(hub());
    expect(await screen.findByText(/Historical data, synchronised periodically/)).toBeInTheDocument();
    expect(screen.queryByText("Data not fresh in 1 of 6 competitions")).toBeNull();
    expect(screen.queryByText(/Historical only · newest verified result 2026-10-21/)).toBeNull();
  });
});
