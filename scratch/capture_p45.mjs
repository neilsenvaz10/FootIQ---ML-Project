import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { launch, sleep } from "../data/supervised/phase4/p44/cdp_p44.mjs";

const root = "D:/Foot IQ";
const outDir = root + "/docs/mini-project/phase4/p4.5";
mkdirSync(outDir, { recursive: true });

const chrome = await launch({ port: 9345, profile: root + "/data/supervised/phase4/p44/chrome-profile-p45" });
const probe = readFileSync(root + "/data/supervised/phase4/tools/probe.js", "utf8");
const probeResults = {};

async function clickByText(text, tag = "button") {
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
  await sleep(300);
}

try {
  // --- 1440px Desktop ---
  await chrome.viewport(1440, 1000, 1, false);

  // 1. World Cup Simulator Overview & Controls
  await chrome.go("http://127.0.0.1:5174/simulations?tab=worldcup", 3000);
  probeResults["desktop_worldcup_controls"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-controls-1440.png`, { fullPage: true });

  // 2. Expand all 48 qualified teams
  await clickByText("View all 48 qualified teams");
  await sleep(600);
  await chrome.shot(`${outDir}/worldcup-teams-1440.png`, { fullPage: true });

  // 3. Run Simulation (Pre-tournament or current)
  await clickByText("Run simulation");
  // Wait for results
  for (let i = 0; i < 40; i++) {
    await sleep(500);
    const done = await chrome.eval(`Boolean(document.body.innerText.includes("Top five contenders"))`);
    if (done) break;
  }
  await sleep(1500);
  probeResults["desktop_worldcup_simulated"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-simulated-1440.png`, { fullPage: true });

  // 4. Bracket Tab
  await clickByText("2026 bracket");
  await sleep(1000);
  await chrome.shot(`${outDir}/worldcup-bracket-1440.png`, { fullPage: true });

  // 5. Season Simulator Tab
  await chrome.go("http://127.0.0.1:5174/simulations?tab=season", 3000);
  probeResults["desktop_season"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/season-points-1440.png`, { fullPage: true });

  // --- 820px Tablet ---
  await chrome.viewport(820, 1180, 1, false);
  await chrome.go("http://127.0.0.1:5174/simulations?tab=worldcup", 2500);
  probeResults["tablet_worldcup"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-820.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/simulations?tab=season", 2500);
  probeResults["tablet_season"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/season-820.png`, { fullPage: true });

  // --- 375px Mobile ---
  await chrome.viewport(375, 812, 1, true);
  await chrome.go("http://127.0.0.1:5174/simulations?tab=worldcup", 2500);
  probeResults["mobile_worldcup"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/worldcup-375.png`, { fullPage: true });

  await chrome.go("http://127.0.0.1:5174/simulations?tab=season", 2500);
  probeResults["mobile_season"] = await chrome.eval(probe);
  await chrome.shot(`${outDir}/season-375.png`, { fullPage: true });

  console.log("Capture completed successfully!");
} finally {
  writeFileSync(`${outDir}/visual_probe_p45.json`, JSON.stringify(probeResults, null, 2));
  await chrome.close();
}
