import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { launch, sleep } from "../data/supervised/phase4/p44/cdp_p44.mjs";

const root = "D:/Foot IQ";
const outDir = root + "/docs/mini-project/phase4/p4.6";
mkdirSync(outDir, { recursive: true });

const chrome = await launch({ port: 9346, profile: root + "/data/supervised/phase4/p46/chrome-profile-p46" });
const probe = readFileSync(root + "/data/supervised/phase4/tools/probe.js", "utf8");
const probeResults = {};

async function waitForText(text, tag = "button", maxMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const found = await chrome.eval(`(() => {
      const el = Array.from(document.querySelectorAll(${JSON.stringify(tag)})).find(b => b.textContent.includes(${JSON.stringify(text)}));
      return Boolean(el);
    })()`);
    if (found) return true;
    await sleep(400);
  }
  throw new Error(`Timeout waiting for element with tag ${tag} and text ${text}`);
}

async function clickByText(text, tag = "button") {
  await waitForText(text, tag);
  const box = await chrome.eval(`(() => {
    const el = Array.from(document.querySelectorAll(${JSON.stringify(tag)})).find(b => b.textContent.includes(${JSON.stringify(text)}));
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  })()`);
  if (!box) throw new Error(`no element found with tag ${tag} and text ${text}`);
  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
    await chrome.send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
  }
  await sleep(400);
}

try {
  console.log("Capturing 1440px Desktop screenshots...");
  await chrome.viewport(1440, 1000, 1, false);

  // 1. Home
  await chrome.go("http://127.0.0.1:5174/", 3000);
  probeResults["desktop_home"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/home-1440.png`, { fullPage: true });

  // 2. Matches
  await chrome.go("http://127.0.0.1:5174/matches?comp=BUNDESLIGA&season=2026-27&status=completed", 2500);
  probeResults["desktop_matches"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/matches-1440.png`, { fullPage: true });

  // 3. Leagues
  await chrome.go("http://127.0.0.1:5174/analytics?comp=BUNDESLIGA", 2500);
  probeResults["desktop_leagues"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/leagues-1440.png`, { fullPage: true });

  // 4. Compare
  await chrome.go("http://127.0.0.1:5174/compare?key=BUNDESLIGA&team=FC+Bayern+M%C3%BCnchen&opponent=Borussia+Dortmund", 2500);
  probeResults["desktop_compare"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/compare-1440.png`, { fullPage: true });

  // 5. Predictions
  await chrome.go("http://127.0.0.1:5174/predict?mode=gameweek&comp=BUNDESLIGA", 2500);
  probeResults["desktop_predictions"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/predictions-1440.png`, { fullPage: true });

  // 6. World Cup Simulator (Controls & Qualified Teams)
  await chrome.go("http://127.0.0.1:5174/simulations?tab=worldcup", 2500);
  await clickByText("View all 48 qualified teams");
  await sleep(600);
  probeResults["desktop_worldcup_controls"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-controls-1440.png`, { fullPage: true });

  // 7. World Cup Simulator Run
  await clickByText("Run simulation");
  for (let i = 0; i < 40; i++) {
    await sleep(500);
    const done = await chrome.eval(`Boolean(document.body.innerText.includes("Top five contenders"))`);
    if (done) break;
  }
  await sleep(1500);
  probeResults["desktop_worldcup_simulated"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-simulated-1440.png`, { fullPage: true });

  // 8. Season Simulator
  await chrome.go("http://127.0.0.1:5174/simulations?tab=season", 3000);
  await waitForText("Run points-only simulation");
  await clickByText("Run points-only simulation");
  for (let i = 0; i < 40; i++) {
    await sleep(500);
    const done = await chrome.eval(`Boolean(document.querySelector('[data-testid="points-result"]'))`);
    if (done) break;
  }
  await sleep(1500);
  probeResults["desktop_season_simulated"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/season-simulator-1440.png`, { fullPage: true });

  // 9. Models
  await chrome.go("http://127.0.0.1:5174/models", 2500);
  probeResults["desktop_models"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/models-1440.png`, { fullPage: true });

  // --- 820px Tablet ---
  console.log("Capturing 820px Tablet screenshots...");
  await chrome.viewport(820, 1180, 1, false);

  await chrome.go("http://127.0.0.1:5174/", 2500);
  probeResults["tablet_home"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/home-820.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/analytics?comp=BUNDESLIGA", 2500);
  probeResults["tablet_leagues"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/leagues-820.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/simulations?tab=worldcup", 2500);
  probeResults["tablet_worldcup"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-820.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/simulations?tab=season", 2500);
  probeResults["tablet_season"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/season-820.png`, { fullPage: true });

  // --- 375px Mobile ---
  console.log("Capturing 375px Mobile screenshots...");
  await chrome.viewport(375, 812, 1, true);

  await chrome.go("http://127.0.0.1:5174/", 2500);
  probeResults["mobile_home"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/home-375.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/analytics?comp=BUNDESLIGA", 2500);
  probeResults["mobile_leagues"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/leagues-375.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/simulations?tab=worldcup", 2500);
  probeResults["mobile_worldcup"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-375.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/simulations?tab=season", 2500);
  probeResults["mobile_season"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/season-375.png`, { fullPage: true });

  console.log("All P4.6 screenshots captured successfully!");
} finally {
  writeFileSync(`${outDir}/visual_probe_p46.json`, JSON.stringify(probeResults, null, 2));
  await chrome.close();
}
