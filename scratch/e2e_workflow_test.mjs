// End-to-End Workflow & Integration Test Suite for FootIQ Phase 4.6
const base = "http://127.0.0.1:8000";

async function get(path) {
  const res = await fetch(`${base}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} returned ${res.status}: ${text}`);
  }
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} returned ${res.status}: ${text}`);
  }
  return res.json();
}

console.log("=================================================");
console.log("Starting FootIQ Phase 4.6 End-to-End Verifications");
console.log("=================================================\n");

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failed++;
  }
}

// 1. Home Dashboard & Freshness
console.log("1. Testing Home Dashboard & Data Freshness...");
try {
  const feat = await get("/api/featured-fixture");
  assert(feat.featured !== undefined, "Featured fixture returned");
  assert(Array.isArray(feat.recent_results), `Recent results list returned (${feat.recent_results.length} results)`);

  const sync = await get("/api/sync/status");
  assert(sync.competitions !== undefined, "Sync status has competitions map");
  assert(sync.live_enabled === false, "Live sync is disabled (safety safeguard preserved)");

  const meta = await get("/api/meta");
  assert(Array.isArray(meta.limitations), "Metadata disclaimers and limitations returned");
} catch (e) {
  console.error("  Error in Home/Freshness:", e.message);
  failed++;
}

// 2. Matches Filtering & Fixtures
console.log("\n2. Testing Matches Filtering & Queries...");
try {
  const matches = await get("/api/matches?comp=BUNDESLIGA&status=completed&limit=5");
  assert(Array.isArray(matches.items) && matches.items.length > 0, `Matches query returns items (${matches.items.length} items)`);
  assert(matches.counts && matches.counts.all > 0, `Total matches count is ${matches.counts.all}`);

  const upcoming = await get("/api/matches?comp=BUNDESLIGA&status=upcoming&limit=5");
  assert(Array.isArray(upcoming.items), "Upcoming fixtures query succeeds");
} catch (e) {
  console.error("  Error in Matches:", e.message);
  failed++;
}

// 3. Leagues & Standings
console.log("\n3. Testing Leagues, Standings & Dashboards...");
try {
  const dash = await get("/api/competitions/BUNDESLIGA/dashboard?season=2026-27");
  assert(dash.standings && dash.standings.length > 0, "Bundesliga standings returned");
  const first = dash.standings[0];
  assert(first.team && first.points !== undefined, `Leader: ${first.team} (${first.points} pts)`);
  assert(Array.isArray(first.form), "Form dots present for teams");

  const cov = await get("/api/competitions/BUNDESLIGA/coverage");
  assert(Array.isArray(cov) && cov.length > 0, `Bundesliga seasons coverage reported (${cov.length} seasons)`);
} catch (e) {
  console.error("  Error in Leagues:", e.message);
  failed++;
}

// 4. Team Comparison
console.log("\n4. Testing Team Comparison (H2H)...");
try {
  const h2h = await get("/api/team?key=BUNDESLIGA&team=FC%20Bayern%20M%C3%BCnchen&opponent=Borussia%20Dortmund");
  assert(h2h.form !== undefined, "Team form history returned");
  assert(h2h.head_to_head !== undefined, "Head-to-head comparison records computed");
} catch (e) {
  console.error("  Error in Team Comparison:", e.message);
  failed++;
}

// 5 & 6. Predictions & Gameweek
console.log("\n5 & 6. Testing Gameweek Fixtures & Predictions Setup...");
try {
  const gws = await get("/api/gameweeks?key=BUNDESLIGA");
  assert(Array.isArray(gws.seasons) && gws.seasons.length > 0, "Gameweek seasons listed");
  assert(gws.next_gameweek !== undefined, `Next gameweek: ${gws.next_gameweek}`);

  const gwMatches = await get(`/api/gameweek?key=BUNDESLIGA&season=${gws.season}&matchday=${gws.next_gameweek}`);
  assert(Array.isArray(gwMatches.fixtures), "Gameweek fixtures returned");
} catch (e) {
  console.error("  Error in Gameweek:", e.message);
  failed++;
}

// 7. World Cup Pre-Tournament Simulation & Determinism
console.log("\n7. Testing World Cup Pre-Tournament Simulation (Determinism & Odds)...");
try {
  const sim1 = await get("/api/worldcup/simulate?simulations=500&mode=pre_tournament&seed=9999");
  const sim2 = await get("/api/worldcup/simulate?simulations=500&mode=pre_tournament&seed=9999");
  assert(sim1.simulations === 500, "Simulation ran 500 tournaments");
  assert(sim1.title_odds.length === 48, "All 48 national teams present in odds");
  assert(sim1.title_odds[0].qualify_knockout_pct !== undefined, "qualify_knockout_pct present");

  // Determinism check
  const champ1 = sim1.title_odds[0].champion_pct;
  const champ2 = sim2.title_odds[0].champion_pct;
  assert(champ1 === champ2, `Deterministic results verified: seed 9999 gave ${champ1}% both times`);
} catch (e) {
  console.error("  Error in World Cup Pre-Tournament:", e.message);
  failed++;
}

// 8. World Cup Archived-State Simulation & Real Bracket
console.log("\n8. Testing World Cup Archived-State Simulation & Bracket...");
try {
  const simArch = await get("/api/worldcup/simulate?simulations=500&mode=current&seed=123");
  assert(simArch.group_tables !== null, "Archived mode returned locked group tables");
  assert(Object.keys(simArch.group_tables).length === 12, "12 groups locked in archived state");

  const bracket = await get("/api/worldcup/bracket");
  assert(Array.isArray(bracket.rounds), "Real 2026 bracket returned");
  const r32 = bracket.rounds.find((r) => r.name === "Round of 32");
  assert(r32 && r32.matches.length > 0, "Round of 32 matches present");
} catch (e) {
  console.error("  Error in World Cup Archived & Bracket:", e.message);
  failed++;
}

// 9. Domestic League Points-Only Season Simulation
console.log("\n9. Testing Domestic League Season Simulator (Points-Only & Bounds)...");
try {
  const st = await get("/api/season/status?key=BUNDESLIGA");
  assert(st.can_simulate === false, "Final-position simulation is safely blocked (predeclared criteria)");
  assert(st.points_only && st.points_only.can_run === true, "Points-only simulation is eligible");

  // Run points simulation
  const ptsRun = await post("/api/season/points", {
    key: "BUNDESLIGA",
    season: st.season,
    user_action: "simulate_points_button",
    simulations: 1000,
    seed: 777,
  });

  assert(ptsRun.result && ptsRun.result.summary.teams.length > 0, "Points simulation returned club summaries");
  const bayer = ptsRun.result.summary.teams.find((t) => t.name.includes("Bayern"));
  assert(bayer && bayer.expected_points > 0, `Expected points for Bayern: ${bayer?.expected_points}`);

  if (ptsRun.result.position_bounds && ptsRun.result.position_bounds.status === "available") {
    assert(ptsRun.result.position_bounds.clubs.length > 0, "Position ranges (bounds) computed");
  }
} catch (e) {
  console.error("  Error in Season Simulator:", e.message);
  failed++;
}

// 10. Models & Provenance Information
console.log("\n10. Testing Models & Performance Metrics...");
try {
  const models = await get("/api/models/performance");
  assert(models.club_v1 !== undefined, "Club v1 model metrics present");
  assert(models.worldcup !== undefined, "World Cup tournament model metrics present");
  assert(models.caveats && models.caveats.length > 0, "Model caveats and historical disclaimers present");
} catch (e) {
  console.error("  Error in Models:", e.message);
  failed++;
}

console.log("\n=================================================");
console.log(`End-to-End Test Summary: ${passed} PASSED, ${failed} FAILED`);
console.log("=================================================");

if (failed > 0) process.exit(1);
