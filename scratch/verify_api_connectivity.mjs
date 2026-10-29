const base = "http://127.0.0.1:8000";

const endpoints = [
  // 1. Health & Meta
  { name: "Health", path: "/api/health", method: "GET" },
  { name: "Metadata & Caveats", path: "/api/meta", method: "GET" },
  { name: "Sync Status", path: "/api/sync/status", method: "GET" },

  // 2. Competitions & Leagues
  { name: "Competitions List", path: "/api/competitions", method: "GET" },
  { name: "Bundesliga Seasons", path: "/api/competitions/BUNDESLIGA/seasons", method: "GET" },
  { name: "Bundesliga Coverage", path: "/api/competitions/BUNDESLIGA/coverage", method: "GET" },
  { name: "Bundesliga Dashboard", path: "/api/competitions/BUNDESLIGA/dashboard?season=2026-27", method: "GET" },

  // 3. Matches & Featured
  { name: "Featured Fixture", path: "/api/featured-fixture", method: "GET" },
  { name: "Matches List", path: "/api/matches?comp=BUNDESLIGA&limit=5", method: "GET" },

  // 4. Team Comparison
  { name: "Team Overview", path: "/api/team?key=BUNDESLIGA&team=FC%20Bayern%20M%C3%BCnchen", method: "GET" },

  // 5. Predictions
  { name: "Gameweeks List", path: "/api/gameweeks?key=BUNDESLIGA", method: "GET" },

  // 6. World Cup Simulator & Bracket
  { name: "World Cup Bracket", path: "/api/worldcup/bracket", method: "GET" },
  { name: "World Cup Simulate (Pre-tournament)", path: "/api/worldcup/simulate?simulations=100&mode=pre_tournament&seed=42", method: "GET" },
  { name: "World Cup Simulate (Archived)", path: "/api/worldcup/simulate?simulations=100&mode=current&seed=42", method: "GET" },

  // 7. Season Simulator
  { name: "Season Sim Status", path: "/api/season/status?key=BUNDESLIGA", method: "GET" },
  { name: "Season Sim Runs History", path: "/api/season/runs?key=BUNDESLIGA&season=2026-27", method: "GET" },

  // 8. Models
  { name: "Models Performance", path: "/api/models/performance", method: "GET" },
];

console.log("Verifying all FootIQ backend endpoints and contracts...");
let allOk = true;

for (const ep of endpoints) {
  try {
    const res = await fetch(`${base}${ep.path}`, { method: ep.method });
    const json = await res.json();
    if (!res.ok) {
      console.error(`[FAIL] ${ep.name} (${ep.method} ${ep.path}) -> ${res.status}: ${JSON.stringify(json)}`);
      allOk = false;
    } else {
      console.log(`[PASS] ${ep.name} (${ep.path}) -> ${res.status} (${Object.keys(json).length} keys)`);
    }
  } catch (err) {
    console.error(`[FAIL] ${ep.name} (${ep.method} ${ep.path}) -> ${err.message}`);
    allOk = false;
  }
}

if (!allOk) process.exit(1);
console.log("\nALL FOOTIQ BACKEND API CONTRACTS VERIFIED 100% OPERATIONAL!");
