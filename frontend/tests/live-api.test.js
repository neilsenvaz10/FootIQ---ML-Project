// @vitest-environment node
// Contract test against a RUNNING backend. Skipped unless FOOTIQ_LIVE_API is set, e.g.
//   FOOTIQ_LIVE_API=http://127.0.0.1:8000 npm test
// It checks that every field the frontend reads actually exists in the real API responses (guards against API drift).
import { describe, expect, it } from "vitest";

const BASE = process.env.FOOTIQ_LIVE_API;
const live = BASE ? describe : describe.skip;
const get = async (path) => {
  const r = await fetch(`${BASE}${path}`, { headers: { Origin: "http://localhost:5173" } });
  return { status: r.status, body: await r.json(), cors: r.headers.get("access-control-allow-origin") };
};
const probs = (p) => {
  expect(Math.abs(p.home + p.draw + p.away - 1)).toBeLessThan(1e-6);
  expect(p.model).toBeTruthy();
};

live("live backend contract", () => {
  it("health, meta and CORS for the dev origin", async () => {
    const h = await get("/api/health");
    expect(h.cors).toBe("http://localhost:5173");
    expect(h.body).toMatchObject({ status: "ok" });
    expect(typeof h.body.club_prediction_ready).toBe("boolean");
    const m = (await get("/api/meta")).body;
    expect(m.attribution.length).toBeGreaterThan(2);
    expect(m.data_through).toHaveProperty("club_results");
    expect(m.data_through).toHaveProperty("international_ratings");
    expect(m.limitations.length).toBeGreaterThan(3);
  });

  it("competitions: 11 with the fields the overview reads", async () => {
    const c = (await get("/api/competitions")).body;
    expect(c).toHaveLength(11);
    for (const x of c) for (const k of ["key", "name", "group", "badge", "basis", "rows", "seasons", "first_date", "last_date", "sources", "licences"]) expect(x).toHaveProperty(k);
    expect(c.find((x) => x.key === "UCL").badge).toBe("Not validated (indicative only)");
  });

  it("dashboard, coverage, team and head-to-head shapes", async () => {
    const seasons = (await get("/api/competitions/EPL/seasons")).body;
    expect(seasons[0]).toMatch(/^\d{4}-\d{2}$/);
    const d = (await get(`/api/competitions/EPL/dashboard?season=${seasons[1]}`)).body;
    expect(d.standings).toHaveLength(20);
    for (const k of ["pos", "team", "played", "won", "drawn", "lost", "gf", "ga", "gd", "points"]) expect(d.standings[0]).toHaveProperty(k);
    for (const k of ["matches", "goals_per_match", "home_win_rate", "draw_rate", "away_win_rate", "outcome_basis", "first_date", "last_date"]) expect(d.summary).toHaveProperty(k);
    expect(d.results[0]).toHaveProperty("shootout_winner");
    expect((await get("/api/competitions/UCL/dashboard?season=2024-25")).body.standings).toBeNull();
    const cov = (await get("/api/competitions/EPL/coverage")).body;
    for (const k of ["season", "rows_in_dataset", "expected_matches", "coverage_pct", "note"]) expect(cov[0]).toHaveProperty(k);
    const t = (await get("/api/team?key=EPL&team=Arsenal%20FC&opponent=Chelsea%20FC")).body;
    expect(t.form.last[0]).toHaveProperty("result");
    for (const k of ["meetings", "a_wins", "b_wins", "draws", "last"]) expect(t.head_to_head).toHaveProperty(k);
    expect(t.head_to_head.a_wins + t.head_to_head.b_wins + t.head_to_head.draws).toBe(t.head_to_head.meetings);
  });

  it("predictions: club and international, probabilities sum to 1, badges", async () => {
    const club = (await get("/api/predict?key=EPL&home=Arsenal%20FC&away=Chelsea%20FC")).body;
    expect(club.validation_badge).toBe("Validated");
    probs(club.primary);
    probs(club.secondary);
    probs(club.elo_only);
    const ucl = (await get("/api/predict?key=UCL&home=Manchester%20City%20FC&away=Real%20Madrid%20CF")).body;
    expect(ucl.validation_badge).toBe("Not validated (indicative only)");
    expect(ucl.notes.join(" ")).toContain("NOT validated");
    const unl = (await get("/api/predict?key=UNL&home=Spain&away=France&venue=home")).body;
    expect(unl.validation_badge).toBe("Partially validated");
    probs(unl.primary);
    expect(unl.gate).toHaveProperty("public_pick");
  });

  it("team season filter and model performance", async () => {
    const all = (await get("/api/competitions/EPL/teams")).body;
    const cur = (await get("/api/competitions/EPL/teams?season=2026-27")).body;
    expect(cur).toHaveLength(20);
    expect(all.length).toBeGreaterThan(cur.length);
    expect((await get("/api/competitions/EPL/teams?season=1999-00")).status).toBe(404);
    const p = (await get("/api/models/performance")).body;
    for (const k of ["club_v1", "club_v2_r1", "international_v27", "worldcup", "uefa_club", "caveats", "sources"]) expect(p).toHaveProperty(k);
    expect(p.club_v1.evaluation[0].models.find((m) => m.model === "multinomial_logreg").n).toBe(15645);
    expect(p.club_v1.per_league).toHaveLength(5);
    expect(p.international_v27.models[0]).toHaveProperty("accuracy");
  });

  it("bracket, standings form and prediction inputs", async () => {
    const b = (await get("/api/worldcup/bracket")).body;
    expect(b.rounds.map((r) => r.matches.length)).toEqual([16, 8, 4, 2, 1]);
    expect(b.rounds[4].matches[0].status).toBe("result not in the dataset");
    expect(b.note).toContain("not a simulation");
    const d = (await get("/api/competitions/EPL/dashboard?season=2024-25")).body;
    expect(d.standings[0].form.length).toBe(5);
    const p = (await get("/api/predict?key=EPL&home=Arsenal%20FC&away=Chelsea%20FC")).body;
    for (const side of ["home", "away"]) for (const k of ["elo", "ppg5", "gd5", "days_rest", "prior_matches"]) expect(p.inputs[side]).toHaveProperty(k);
  });

  it("gameweek endpoints (read-only: the live suite never presses Predict gameweek)", async () => {
    const l = (await get("/api/gameweeks?key=EPL")).body;
    expect(l.gameweeks).toHaveLength(38);
    for (const k of ["matchday_no", "first_date", "last_date", "completed", "upcoming", "awaiting_result", "predictable", "order_issue", "rescheduled_fixtures", "saved_forecast_runs"]) expect(l.gameweeks[0]).toHaveProperty(k);
    expect(l).toHaveProperty("next_gameweek");
    const g = (await get(`/api/gameweek?key=EPL&matchday=${l.next_gameweek}`)).body;
    expect(g.fixtures.length).toBeGreaterThanOrEqual(9);
    for (const k of ["record_id", "date", "home", "away", "status", "predictable", "flags", "reasons", "reliability", "form", "forecast", "evaluation", "result"]) expect(g.fixtures[0]).toHaveProperty(k);
    expect(["scheduled", "awaiting_result", "completed"]).toContain(g.fixtures[0].status);
    expect(g.evaluation).toHaveProperty("caveat");
    expect((await get("/api/gameweeks?key=UCL")).status).toBe(422);
    expect((await get("/api/gameweek?key=EPL&matchday=50")).status).toBe(404);
    expect((await get("/api/sync/status")).body.competitions).toHaveLength(11);
  });

  it("featured fixture (Home): shape, stored values only, cache headers, 304, validation, latency, and nothing is written", async () => {
    const FIVE = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"];
    const hit = async (path, headers = {}) => {
      const t = performance.now();
      const r = await fetch(`${BASE}${path}`, { headers: { Origin: "http://localhost:5173", ...headers } });
      const text = await r.text();
      return { r, ms: performance.now() - t, text, body: text ? JSON.parse(text) : null };
    };
    const savedRuns = async () => {
      const total = [];
      for (const key of FIVE) total.push((await get(`/api/gameweeks?key=${key}`)).body.gameweeks.reduce((n, g) => n + g.saved_forecast_runs, 0));
      return total;
    };
    const before = await savedRuns();

    const first = await hit("/api/featured-fixture");
    expect(first.r.status).toBe(200);
    expect(first.r.headers.get("access-control-allow-origin")).toBe("http://localhost:5173");
    expect(first.r.headers.get("cache-control")).toBe("private, max-age=60");
    expect(first.r.headers.get("etag")).toMatch(/^"[0-9a-f]+"$/);
    expect(["hit", "miss"]).toContain(first.r.headers.get("x-footiq-cache"));
    expect(first.ms, "first request").toBeLessThan(2000); // /api/gameweek needs 3.7 s to 10.5 s; the Home banner must not

    const d = first.body;
    for (const k of ["generated_utc", "today_utc", "scope", "featured", "empty_state", "upcoming", "recent_results", "leagues", "freshness", "notes"]) expect(d).toHaveProperty(k);
    expect(d.scope.competitions).toEqual(FIVE);
    expect(Object.keys(d.freshness.competitions)).toEqual(FIVE);
    expect(d.leagues.map((l) => l.competition_key)).toEqual(FIVE);
    expect(d.freshness.live_enabled).toBe(false);
    expect(d.upcoming.length).toBeLessThanOrEqual(8);
    expect(d.recent_results.length).toBeLessThanOrEqual(8);

    // every kickoff is exactly what the store holds: a UTC time, a local time with no zone, or nothing
    const kickoff = (k) => {
      expect(["utc", "local_without_time_zone", "unknown"]).toContain(k.state);
      if (k.state === "utc") expect(k.utc).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/);
      if (k.state === "local_without_time_zone") {
        expect(k.utc).toBeNull();
        expect(k.local).toMatch(/^\d{2}:\d{2}/);
      }
      if (k.state === "unknown") expect([k.utc, k.local]).toEqual([null, null]);
    };
    for (const f of d.upcoming) {
      for (const k of ["record_id", "competition_key", "competition", "season", "date", "kickoff", "home", "away", "status", "source", "eligibility", "has_saved_forecast"]) expect(f).toHaveProperty(k);
      expect(FIVE).toContain(f.competition_key);
      expect(f.status).toBe("scheduled");
      expect(f.date >= d.today_utc).toBe(true);
      expect(typeof f.home.name).toBe("string");
      expect(typeof f.home.resolved).toBe("boolean");
      for (const k of ["eligible", "predictable", "reliability", "flags"]) expect(f.eligibility).toHaveProperty(k);
      kickoff(f.kickoff);
    }
    expect(d.upcoming.map((f) => f.date)).toEqual(d.upcoming.map((f) => f.date).sort());
    for (const r of d.recent_results) {
      expect(FIVE).toContain(r.competition_key);
      expect(["completed", "awarded"]).toContain(r.status);
      expect(Number.isInteger(r.home_goals) && Number.isInteger(r.away_goals)).toBe(true);
      expect(r.date <= d.today_utc).toBe(true);
    }
    expect(d.recent_results.map((r) => r.date)).toEqual(d.recent_results.map((r) => r.date).sort().reverse());

    if (d.featured) {
      const f = d.featured;
      expect(d.empty_state).toBeNull();
      expect(d.upcoming.some((u) => u.record_id === f.record_id)).toBe(false); // the list continues after the featured fixture
      expect(f.date >= d.today_utc).toBe(true); // a fresh league's fixture within three days may be featured ahead of a stale league's earlier one
      expect(f.home.resolved && f.away.resolved).toBe(true);
      expect(Array.isArray(f.eligibility.reasons)).toBe(true);
      expect(f.forecast === null || typeof f.forecast.predictions.primary.home === "number").toBe(true); // a forecast only if one was already saved
      expect(f.has_saved_forecast).toBe(f.forecast !== null);
      expect(f.matchday_label === null || typeof f.matchday_label === "string").toBe(true);
    } else {
      expect(["no_upcoming_fixture", "no_eligible_fixture"]).toContain(d.empty_state.code);
      expect(typeof d.empty_state.message).toBe("string");
    }
    for (const c of Object.values(d.freshness.competitions)) {
      for (const k of ["state", "state_reasons", "latest_result", "last_successful_sync_utc", "approved_sources", "awaiting_result", "scheduled"]) expect(c).toHaveProperty(k);
    }

    // repeated and conditional requests
    const again = await hit("/api/featured-fixture");
    expect(again.r.headers.get("x-footiq-cache")).toBe("hit");
    expect(again.r.headers.get("etag")).toBe(first.r.headers.get("etag"));
    expect(again.ms, "cached request").toBeLessThan(500);
    const cond = await hit("/api/featured-fixture", { "If-None-Match": first.r.headers.get("etag") });
    expect(cond.r.status).toBe(304);
    expect(cond.text).toBe("");

    // a single league, and the bounds
    const one = (await hit("/api/featured-fixture?comp=EPL&upcoming=3&results=2")).body;
    expect(one.scope.competitions).toEqual(["EPL"]);
    expect(one.upcoming.length).toBeLessThanOrEqual(3);
    expect(one.recent_results.length).toBeLessThanOrEqual(2);
    for (const x of [...one.upcoming, ...one.recent_results]) expect(x.competition_key).toBe("EPL");
    for (const bad of ["?comp=UCL", "?comp=WC", "?upcoming=0", "?upcoming=13", "?results=99"]) {
      const r = await hit(`/api/featured-fixture${bad}`);
      expect(r.r.status, bad).toBe(422);
      expect(r.body.detail, bad).toBeTruthy();
    }

    // reading the Home data never saves a forecast
    expect(await savedRuns()).toEqual(before);
  }, 60000);

  it("matches hub: bounded pages, counts that add up, keyset paging, stored kickoffs, cache, validation, latency, nothing written", async () => {
    const FIVE = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"];
    const hit = async (path, headers = {}) => {
      const t = performance.now();
      const r = await fetch(`${BASE}${path}`, { headers: { Origin: "http://localhost:5173", ...headers } });
      const text = await r.text();
      return { r, ms: performance.now() - t, body: text ? JSON.parse(text) : null };
    };
    const first = await hit("/api/matches?status=upcoming&limit=25");
    expect(first.r.status).toBe(200);
    expect(first.r.headers.get("cache-control")).toBe("private, max-age=60");
    expect(first.ms, "first request").toBeLessThan(2000);
    const d = first.body;
    for (const k of ["generated_utc", "today_utc", "scope", "counts", "items", "page", "facets", "freshness", "notes"]) expect(d).toHaveProperty(k);
    expect(d.scope.competitions).toEqual(FIVE);
    expect(d.items.length).toBeLessThanOrEqual(25);
    expect(d.counts.all).toBe(d.counts.upcoming + d.counts.awaiting_result + d.counts.completed + d.counts.other);
    for (const x of d.items) {
      expect(["scheduled"]).toContain(x.status);
      expect(x.date >= d.today_utc).toBe(true);
      expect(typeof x.kickoff.zone_verified).toBe("boolean");
      expect(x.kickoff.zone_verified).toBe(x.kickoff.state === "utc");
      if (x.kickoff.state !== "utc") expect(x.kickoff.utc).toBeNull();
      for (const k of ["timing", "eligibility", "source", "home", "away"]) expect(x).toHaveProperty(k);
    }
    // walk every upcoming match of one league a page at a time: no duplicates, in order, as many as the count says
    const seen = [];
    let cursor = null;
    let pages = 0;
    do {
      const p = (await hit(`/api/matches?comp=SERIEA&status=upcoming&limit=50${cursor ? `&cursor=${cursor}` : ""}`)).body;
      seen.push(...p.items.map((i) => `${i.date}|${i.kickoff.utc ?? ""}|${i.record_id}`));
      cursor = p.page.next_cursor;
      pages += 1;
      if (!cursor) expect(seen.length).toBe(p.counts.upcoming);
    } while (cursor && pages < 50);
    expect(new Set(seen).size).toBe(seen.length);
    expect(seen).toEqual([...seen].sort());
    const done = (await hit("/api/matches?comp=BUNDESLIGA&status=completed&limit=10")).body;
    for (const x of done.items) expect(Number.isInteger(x.result.home_goals) && Number.isInteger(x.result.away_goals)).toBe(true);
    expect(done.items.map((i) => i.date)).toEqual(done.items.map((i) => i.date).sort().reverse());
    const again = await hit("/api/matches?status=upcoming&limit=25");
    expect(again.r.headers.get("x-footiq-cache")).toBe("hit");
    expect(again.ms, "cached request").toBeLessThan(500);
    expect((await hit("/api/matches?status=upcoming&limit=25", { "If-None-Match": first.r.headers.get("etag") })).r.status).toBe(304);
    for (const bad of ["?comp=UCL", "?status=live", "?limit=0", "?limit=51", "?matchday=0", "?season=2026", "?cursor=garbage"]) expect((await hit(`/api/matches${bad}`)).r.status, bad).toBe(422);
    expect((await hit("/api/matches?comp=EPL&season=1999-00")).r.status).toBe(404);
  }, 60000);

  it("invalid inputs return {detail: string}", async () => {
    for (const path of [
      "/api/predict?key=EPL&home=Arsenal%20FC&away=Arsenal%20FC",
      "/api/predict?key=EPL&home=Arsenal%20FC&away=Chelsea%20FC&date=2020-01-01",
      "/api/predict?key=WC&home=Brazil&away=Argentina&date=2020-01-01",
      "/api/predict?key=EPL&home=Arsenal%20FC&away=Chelsea%20FC&date=notadate",
      "/api/team?key=EPL&team=Nobody%20FC",
      "/api/worldcup/simulate?simulations=5",
    ]) {
      const r = await get(path);
      expect([404, 422], path).toContain(r.status);
      expect(typeof r.body.detail).toBe("string");
    }
  });

  it("simulator: both modes, seeded and reproducible", async () => {
    const q = "simulations=200&seed=5";
    const a = (await get(`/api/worldcup/simulate?${q}&mode=pre_tournament`)).body;
    const b = (await get(`/api/worldcup/simulate?${q}&mode=pre_tournament`)).body;
    expect(a.title_odds).toEqual(b.title_odds);
    expect(a.group_tables).toBeNull();
    expect(a.title_odds[0]).toHaveProperty("champion_pct");
    const c = (await get(`/api/worldcup/simulate?${q}&mode=current`)).body;
    expect(Object.keys(c.group_tables)).toHaveLength(12);
    expect(c.seed).toBe(5);
  }, 60000);
});
