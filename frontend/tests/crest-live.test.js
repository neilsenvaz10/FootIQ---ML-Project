// @vitest-environment node
// Runs the badge generator over every team name the REAL backend serves. Skipped unless FOOTIQ_LIVE_API is set, like live-api.test.js:
//   FOOTIQ_LIVE_API=http://127.0.0.1:8000 npm test
// Read-only: it only issues GET requests.
import { describe, expect, it } from "vitest";
import { initials, significantWords } from "../src/lib/team.js";

const BASE = process.env.FOOTIQ_LIVE_API;
const live = BASE ? describe : describe.skip;
const get = async (path) => (await fetch(`${BASE}${path}`)).json();

live("team badges for the real team names", () => {
  it("every team in every competition gets a code made of letters only", async () => {
    const competitions = await get("/api/competitions");
    const names = new Set();
    for (const c of competitions) for (const t of await get(`/api/competitions/${c.key}/teams`)) names.add(t);
    expect(names.size).toBeGreaterThan(300);
    for (const n of names) {
      expect(significantWords(n).length, n).toBeGreaterThan(0);
      expect(initials(n), n).toMatch(/^\p{L}{2,3}$/u); // "AZ" is a two-letter club name; everything else gets three letters
      expect(initials(n, 2), n).toMatch(/^\p{L}{2}$/u);
    }
  });

  it("the teams of one domestic league in its newest season all get different three-letter codes", async () => {
    for (const key of ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]) {
      const [newest] = await get(`/api/competitions/${key}/seasons`);
      const teams = await get(`/api/competitions/${key}/teams?season=${newest}`);
      const codes = teams.map((t) => initials(t));
      expect(new Set(codes).size, `${key} ${newest}: ${codes.join(" ")}`).toBe(teams.length);
    }
  });
});
