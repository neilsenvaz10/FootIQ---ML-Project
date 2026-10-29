// @vitest-environment node
// Presentation helpers for the Home dashboard (src/lib/fixtures.js). They only format what the API returned: a time is never invented,
// a date never moves with the viewer's time zone, and a missing value is said to be missing.
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { compareLink, dayLabel, FLAG_LABELS, flagChips, freshnessText, fullDay, gameweekLink, groupByDate, isProvisional, kickoffOf, kickoffParts, kickoffShort, kickoffText, longDay, manualLink, MATCH_STATUS, SHORT_LEAGUE, shortDay, timingChip } from "../src/lib/fixtures.js";

const UTC = { state: "utc", utc: "2026-10-31T15:00:00Z", local: null };
const LOCAL = { state: "local_without_time_zone", utc: null, local: "18:30", zone_verified: false };
const UNKNOWN = { state: "unknown", utc: null, local: null };

describe("kickoff", () => {
  it("states a UTC time as UTC", () => {
    expect(kickoffText(UTC)).toBe("15:00 UTC");
    expect(kickoffShort(UTC)).toBe("15:00 UTC");
  });
  it("says that a published local time has an unconfirmed time zone, and does not convert it", () => {
    expect(kickoffText(LOCAL)).toBe("18:30 (time zone unconfirmed)");
    expect(kickoffShort(LOCAL)).toBe("18:30 local");
    expect(kickoffText(LOCAL)).not.toMatch(/UTC/);
  });
  it("says when there is no time, for an unknown state, a missing object or a UTC state without a value", () => {
    for (const k of [UNKNOWN, undefined, null, {}, { state: "utc", utc: null }, { state: "local_without_time_zone", local: null }]) {
      expect(kickoffText(k)).toBe("time not confirmed");
      expect(kickoffShort(k)).toBe("Time not confirmed");
    }
  });
});

describe("dates", () => {
  it("formats calendar dates in UTC, so the day never shifts with the viewer's time zone", () => {
    expect(shortDay("2026-10-31")).toBe("Sat 31 Oct");
    expect(longDay("2026-10-31")).toBe("Saturday 31 October 2026");
    expect(shortDay("2026-01-01")).toBe("Thu 1 Jan"); // the day a negative UTC offset would turn into 31 Dec
    expect(shortDay("2026-12-31")).toBe("Thu 31 Dec"); // and a positive one into 1 Jan
  });
  it("the formatters are pinned to UTC in the source", () => {
    const src = readFileSync(join(resolve(dirname(fileURLToPath(import.meta.url)), ".."), "src/lib/fixtures.js"), "utf8");
    expect(src.match(/timeZone: "UTC"/g)).toHaveLength(2);
    expect(src).toContain('T00:00:00Z');
  });
  it("calls the server's own date Today and the next day Tomorrow, across a month and a year end", () => {
    expect(dayLabel("2026-10-27", "2026-10-27")).toBe("Today");
    expect(dayLabel("2026-10-28", "2026-10-27")).toBe("Tomorrow");
    expect(dayLabel("2026-11-01", "2026-10-31")).toBe("Tomorrow");
    expect(dayLabel("2027-01-01", "2026-12-31")).toBe("Tomorrow");
    expect(dayLabel("2026-10-29", "2026-10-27")).toBe("Thu 29 Oct");
    expect(dayLabel("2026-10-26", "2026-10-27")).toBe("Mon 26 Oct"); // yesterday is just a date
  });
  it("falls back to the plain date without a server date, and to nothing without a date", () => {
    expect(dayLabel("2026-10-27")).toBe("Tue 27 Oct");
    expect(dayLabel("", "2026-10-27")).toBe("");
    expect(dayLabel(null, "2026-10-27")).toBe("");
  });
  it("groups consecutive items that share a date and keeps the order given", () => {
    const items = [
      { id: 1, date: "2026-10-27" },
      { id: 2, date: "2026-10-27" },
      { id: 3, date: "2026-10-28" },
      { id: 4, date: "2026-10-27" },
    ];
    expect(groupByDate(items).map((g) => [g.date, g.items.map((i) => i.id)])).toEqual([
      ["2026-10-27", [1, 2]],
      ["2026-10-28", [3]],
      ["2026-10-27", [4]],
    ]);
    expect(groupByDate([])).toEqual([]);
    expect(groupByDate()).toEqual([]);
  });
});

describe("reliability flags and freshness", () => {
  it("labels each distinct flag once and keeps unknown flags visible", () => {
    const chips = flagChips(["stale_history", "missing_results_home", "missing_results_away", "kickoff_timezone_unknown", "something_new"]);
    expect(chips.map(([label]) => label)).toEqual(["Stale history", "Missing earlier results", "Kickoff time zone unconfirmed", "something_new"]);
    expect(Object.fromEntries(chips)).toMatchObject({ "Stale history": "warn", "Kickoff time zone unconfirmed": "info", something_new: "info" });
    expect(flagChips()).toEqual([]);
    expect(flagChips([])).toEqual([]);
  });
  it("every flag the backend can raise has a label", () => {
    for (const flag of ["stale_history", "missing_results_home", "missing_results_away", "earlier_fixtures_unplayed_home", "earlier_fixtures_unplayed_away", "kickoff_time_unknown", "kickoff_timezone_unknown", "rescheduled_or_out_of_order", "low_history", "ratings_not_connected", "not_certainly_before_kickoff"]) {
      expect(FLAG_LABELS[flag], flag).toHaveLength(2);
    }
  });
  it("is provisional only when the backend says so", () => {
    expect(isProvisional({ eligibility: { reliability: "provisional" } })).toBe(true);
    expect(isProvisional({ eligibility: { reliability: "full" } })).toBe(false);
    expect(isProvisional({ eligibility: {} })).toBe(false);
    expect(isProvisional({})).toBe(false);
    expect(isProvisional(null)).toBe(false);
  });
  it("words the freshness of a competition's data without hiding the newest result", () => {
    expect(freshnessText({ state: "fresh", latest_result: "2026-10-25" })).toEqual({ tone: "ok", text: "Data fresh · newest verified result 2026-10-25" });
    expect(freshnessText({ state: "stale", latest_result: "2026-09-20" })).toEqual({ tone: "warn", text: "Data not fresh · newest verified result 2026-09-20" });
    expect(freshnessText({ state: "unknown", latest_result: null })).toEqual({ tone: "warn", text: "Data not fresh · no verified result stored" });
    expect(freshnessText(undefined)).toBeNull();
    expect(freshnessText(null)).toBeNull();
  });
});

describe("links and names", () => {
  it("links a fixture to its gameweek on the predictions page", () => {
    expect(gameweekLink({ competition_key: "EPL", matchday_no: 9 })).toBe("/predict?mode=gameweek&comp=EPL&gw=9");
    expect(gameweekLink({ competition_key: "SERIEA", matchday_no: null })).toBe("/predict?mode=gameweek&comp=SERIEA");
  });
  it("short league names cover exactly the five domestic leagues", () => {
    expect(Object.keys(SHORT_LEAGUE)).toEqual(["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]);
  });
});

describe("kickoff cells, links and statuses for the Matches hub (P4.3)", () => {
  it("splits a kickoff into the time as stored and what is unconfirmed about it", () => {
    expect(kickoffParts(UTC)).toEqual({ time: "15:00 UTC", note: null });
    expect(kickoffParts(LOCAL)).toEqual({ time: "18:30 local", note: "zone unconfirmed" });
    for (const k of [UNKNOWN, undefined, null, {}]) expect(kickoffParts(k)).toEqual({ time: "Time not confirmed", note: null });
  });
  it("reads the gameweek page's two kickoff fields in the same shape, without inventing a UTC time from a local one", () => {
    expect(kickoffOf({ kickoff_utc: "2026-10-31T15:00:00Z", kickoff_local: null })).toMatchObject({ state: "utc", utc: "2026-10-31T15:00:00Z" });
    expect(kickoffOf({ kickoff_utc: null, kickoff_local: "18:30" })).toEqual({ state: "local_without_time_zone", utc: null, local: "18:30" });
    expect(kickoffOf({ kickoff_utc: null, kickoff_local: null })).toEqual({ state: "unknown", utc: null, local: null });
  });
  it("links a match to its gameweek (with its season on request), to the manual predictor and to the comparison, with both clubs", () => {
    const f = { competition_key: "EPL", season: "2025-26", matchday_no: 12, home: { name: "Northbridge United" }, away: { name: "Eastvale Town" } };
    expect(gameweekLink(f)).toBe("/predict?mode=gameweek&comp=EPL&gw=12");
    expect(gameweekLink(f, { season: true })).toBe("/predict?mode=gameweek&comp=EPL&season=2025-26&gw=12");
    expect(manualLink(f)).toBe("/predict?mode=manual&comp=EPL&home=Northbridge+United&away=Eastvale+Town");
    expect(compareLink(f)).toBe("/compare?comp=EPL&a=Northbridge+United&b=Eastvale+Town");
  });
  it("labels every stored status and never has a live one", () => {
    expect(Object.keys(MATCH_STATUS)).toEqual(["scheduled", "awaiting_result", "completed", "awarded", "postponed", "cancelled", "abandoned"]);
    expect(Object.keys(MATCH_STATUS).some((k) => /live/i.test(k) || /live/i.test(MATCH_STATUS[k][0]))).toBe(false);
  });
  it("turns an unconfirmed same-day kickoff into a chip, and says nothing for the ordinary phases", () => {
    expect(timingChip({ phase: "today_time_zone_unconfirmed" })).toEqual(["Today · time zone unconfirmed", "info"]);
    expect(timingChip({ phase: "today_time_unknown" })).toEqual(["Today · time not stated", "info"]);
    expect(timingChip({ phase: "kickoff_passed" })).toEqual(["Kickoff passed · no result yet", "warn"]);
    for (const phase of ["future_date", "today_before_kickoff", "date_passed", "result_stored", "not_played"]) expect(timingChip({ phase })).toBeNull();
    expect(timingChip(undefined)).toBeNull();
  });
  it("heads a list day with the date and its year", () => {
    expect(fullDay("2026-10-31")).toBe("Sat 31 Oct 2026");
  });
});
