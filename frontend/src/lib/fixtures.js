// Presentation helpers for fixtures and results (Home dashboard, gameweek cards). Nothing here creates football data: every value shown comes from the API.

// Reliability flags (see gameweeks.py) -> [label, tone]. The tone names are the ones Chip understands.
export const FLAG_LABELS = {
  stale_history: ["Stale history", "warn"],
  missing_results_home: ["Missing earlier results", "warn"],
  missing_results_away: ["Missing earlier results", "warn"],
  earlier_fixtures_unplayed_home: ["Earlier fixtures unplayed", "info"],
  earlier_fixtures_unplayed_away: ["Earlier fixtures unplayed", "info"],
  kickoff_time_unknown: ["Kickoff time unknown", "info"],
  kickoff_timezone_unknown: ["Kickoff time zone unconfirmed", "info"],
  rescheduled_or_out_of_order: ["Rescheduled?", "warn"],
  low_history: ["Little history", "warn"],
  ratings_not_connected: ["Ratings less comparable", "warn"],
  not_certainly_before_kickoff: ["Saved after kickoff window opened", "warn"],
};

// Each distinct label once, in the order the flags arrived.
export function flagChips(flags = []) {
  return [...new Map(flags.map((x) => [FLAG_LABELS[x]?.[0] ?? x, FLAG_LABELS[x]?.[1] ?? "info"])).entries()];
}

// The kickoff exactly as the store knows it: a UTC time, a local time whose zone is unconfirmed, or nothing. A local time is shown as stored and is never converted.
export function kickoffText(k) {
  if (k?.state === "utc" && k.utc) return `${k.utc.slice(11, 16)} UTC`;
  if (k?.state === "local_without_time_zone" && k.local) return `${k.local} (time zone unconfirmed)`;
  return "";
}

// Short form for list rows.
export function kickoffShort(k) {
  if (k?.state === "utc" && k.utc) return `${k.utc.slice(11, 16)} UTC`;
  if (k?.state === "local_without_time_zone" && k.local) return `${k.local} local`;
  return "";
}

// Two lines for a list cell: the time, and what is unconfirmed about it.
export function kickoffParts(k) {
  if (k?.state === "utc" && k.utc) return { time: `${k.utc.slice(11, 16)} UTC`, note: null };
  if (k?.state === "local_without_time_zone" && k.local) return { time: `${k.local} local`, note: "zone unconfirmed" };
  return { time: "", note: null };
}

// A gameweek fixture of the gameweek page (kickoff_utc and kickoff_local as plain fields) in the same shape.
export const kickoffOf = (f) => ({ state: f.kickoff_utc ? "utc" : f.kickoff_local ? "local_without_time_zone" : "unknown", utc: f.kickoff_utc ?? null, local: f.kickoff_local ?? null });

// Dates are calendar dates ("2026-10-31"); they are always formatted in UTC so the day never shifts with the viewer's time zone.
const SHORT = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
const LONG = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const asDate = (iso) => new Date(`${iso}T00:00:00Z`);

export const shortDay = (iso) => SHORT.format(asDate(iso)).replace(",", "");
export const longDay = (iso) => LONG.format(asDate(iso)).replace(",", "");

// "Today" and "Tomorrow" are relative to the server's UTC date (today_utc in the payload), otherwise "Fri 31 Oct".
export function dayLabel(iso, todayIso) {
  if (!iso) return "";
  if (iso === todayIso) return "Today";
  if (todayIso && Math.round((asDate(iso) - asDate(todayIso)) / 86400000) === 1) return "Tomorrow";
  return shortDay(iso);
}

// Consecutive items with the same date, in the order given: [{ date, items }].
export function groupByDate(items = []) {
  const out = [];
  for (const it of items) {
    const last = out.at(-1);
    if (last && last.date === it.date) last.items.push(it);
    else out.push({ date: it.date, items: [it] });
  }
  return out;
}

export const isProvisional = (f) => f?.eligibility?.reliability === "provisional";

// What to say about the freshness of a competition's data (from /api/featured-fixture -> freshness.competitions[key]).
export function freshnessText(fresh) {
  if (!fresh) return null;
  const latest = fresh.latest_result ? `newest verified result ${fresh.latest_result}` : "no verified result stored";
  return fresh.state === "fresh" ? { tone: "ok", text: `Data fresh · ${latest}` } : null; // a "Data not fresh" warning chip is no longer shown (Phase 4.35)
}

// Where a fixture's gameweek is shown: the Predictions page in gameweek mode, on that league and matchday (and season, when asked: the Matches page lists any season).
export function gameweekLink(f, { season = false } = {}) {
  const q = new URLSearchParams({ mode: "gameweek", comp: f.competition_key });
  if (season && f.season) q.set("season", f.season);
  if (f.matchday_no) q.set("gw", String(f.matchday_no));
  return `/predict?${q.toString()}`;
}

// The same two clubs in the manual head-to-head predictor and in the team comparison (both pages only pre-select them; nothing is computed until the user asks).
export const manualLink = (f) => `/predict?${new URLSearchParams({ mode: "manual", comp: f.competition_key, home: f.home.name, away: f.away.name }).toString()}`;
export const compareLink = (f) => `/compare?${new URLSearchParams({ comp: f.competition_key, a: f.home.name, b: f.away.name }).toString()}`;

// Match status (effective, from /api/matches) -> [label, chip tone].
export const MATCH_STATUS = {
  scheduled: ["Upcoming", "info"],
  awaiting_result: ["Awaiting result", "warn"],
  completed: ["Full time", "ok"],
  awarded: ["Awarded", "info"],
  postponed: ["Postponed", "warn"],
  cancelled: ["Cancelled", "bad"],
  abandoned: ["Abandoned", "bad"],
};

// What cannot be known about a fixture dated today, as a chip ([label, tone]) or null. Never "live": the page has no live data.
export function timingChip(timing) {
  void timing;                                    // the "time not stated" / "kickoff passed" chips are no longer shown (owner request, Phase 4.35)
  return null;
}

// "Sat 31 Oct 2026" for a list heading that is not today or tomorrow.
export const fullDay = (iso) => `${shortDay(iso)} ${iso.slice(0, 4)}`;

export const SHORT_LEAGUE = { EPL: "Premier League", LALIGA: "La Liga", BUNDESLIGA: "Bundesliga", SERIEA: "Serie A", LIGUE1: "Ligue 1" };
// The Matches hub also lists the Champions League (Phase 4.20); the other pages keep the five domestic leagues above.
export const HUB_LEAGUE = { ...SHORT_LEAGUE, UCL: "Champions League" };

// Freshness chip text for one competition of the hub. The Champions League has no automatic update source: it is "historical only" and changes only through approved imports.
export function competitionFreshness(key, fresh) {
  if (!fresh) return null;
  if (key === "UCL") return null;                    // the amber "Historical only" chip is no longer shown (Phase 4.35)
  return freshnessText(fresh);
}
