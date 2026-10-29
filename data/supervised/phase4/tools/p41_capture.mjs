// Phase 4 / P4.1: screenshots and measurements with headless Chrome against the dev server (and the backend on a private database copy).
//   node p41_capture.mjs shots     writes the checkpoint screenshots into docs/mini-project/phase4/p4.1/
//   node p41_capture.mjs probe     measures contrast, target sizes, overflow, headings and titles on every route at 1440, 820 and 375 px
//   node p41_capture.mjs keys      drives the keyboard (skip link, tab order, More sheet) in a real browser and prints what happened
import { readFileSync, writeFileSync } from "node:fs";
import { launch, sleep } from "./cdp.mjs";

const BASE = process.env.BASE || "http://localhost:5173";
const OUT = process.env.OUT || "D:/Foot IQ/docs/mini-project/phase4/p4.1";
const probe = readFileSync(new URL("./probe.js", import.meta.url), "utf8");
const mode = process.argv[2] || "shots";
const ROUTES = ["/", "/matches", "/analytics", "/compare", "/predict", "/simulations", "/models"];
const VIEWPORTS = [
  { name: "desktop", w: 1440, h: 900, scale: 1, mobile: false },
  { name: "tablet", w: 820, h: 1180, scale: 1, mobile: false },
  { name: "mobile", w: 375, h: 812, scale: 2, mobile: true },
];
const SETTLE = { "/predict": 9000, "/": 4000, "/analytics": 4000, "/models": 4000, "/simulations": 4000 };

const chrome = await launch();
try {
  if (mode === "shots") {
    const page = async (vp, path, file, settle) => {
      await chrome.viewport(vp.w, vp.h, vp.scale, vp.mobile);
      await chrome.go(BASE + path, settle);
      await chrome.shot(`${OUT}/${file}`);
      console.log("saved", file);
    };
    const [desktop, tablet, mobile] = VIEWPORTS;
    await page(desktop, "/", "desktop-home.png", 4000);
    await page(desktop, "/matches", "desktop-matches.png", 2500);
    await page(desktop, "/analytics", "desktop-leagues-table.png", 4000);
    await page(desktop, "/compare", "desktop-compare.png", 3000);
    await page(desktop, "/predict", "desktop-predictions.png", 9000);
    await page(desktop, "/simulations", "desktop-simulations.png", 4000);
    await page(desktop, "/models", "desktop-models.png", 4000);
    await page(tablet, "/", "tablet-home.png", 4000);
    await page(tablet, "/analytics", "tablet-leagues-table.png", 4000);
    await page(tablet, "/predict", "tablet-predictions.png", 9000);
    await page(mobile, "/", "mobile-home.png", 4000);
    await page(mobile, "/predict", "mobile-predictions.png", 9000);
    await page(mobile, "/models", "mobile-models.png", 4000);
    for (const only of ["tokens", "controls", "states", "badges"]) await page(desktop, `/design?only=${only}`, `design-${only}.png`, 2000);

    // keyboard states, with real key events
    await chrome.viewport(1440, 900, 1, false);
    await chrome.go(`${BASE}/`, 4000);
    await chrome.key("Tab");
    await chrome.shot(`${OUT}/keyboard-skip-link.png`);
    for (let i = 0; i < 4; i += 1) await chrome.key("Tab");
    await chrome.shot(`${OUT}/keyboard-focus-ring-sidebar.png`);
    console.log("saved keyboard states");

    // phone: the More sheet, opened by tapping the button
    await chrome.viewport(375, 812, 2, true);
    await chrome.go(`${BASE}/models`, 4000);
    await chrome.click('nav[aria-label="Main mobile"] button');
    await sleep(500);
    await chrome.shot(`${OUT}/mobile-more-sheet.png`);
    console.log("saved mobile-more-sheet.png");
  }

  if (mode === "probe") {
    const all = {};
    for (const vp of VIEWPORTS) {
      await chrome.viewport(vp.w, vp.h, vp.scale, vp.mobile);
      await chrome.go(BASE + "/", 4000);
      all[vp.name] = [];
      for (const route of ROUTES) {
        if (route !== "/") await chrome.spa(route, SETTLE[route] || 3000);
        const o = await chrome.eval(probe);
        all[vp.name].push(o);
        console.log(
          [vp.name.padEnd(7), o.path.padEnd(12), o.title.padEnd(28), `ovf ${o.overflowX}`, `h1 ${o.h1.length}`, `contrast-fail ${o.text.contrastFailures}`, `text<12 ${o.text.under12px}(+${o.text.decorativeUnder12px} decor)`, `controls ${o.targets.controls}`, `<44 ${o.targets.below44}`, `<24 ${o.targets.below24}`, `inter ${o.interFaces.length}`].join(" | "),
        );
      }
    }
    writeFileSync(`${OUT}/probe-${process.env.LABEL || "p41"}.json`, JSON.stringify(all, null, 1));
    console.log("wrote", `${OUT}/probe-${process.env.LABEL || "p41"}.json`);
  }

  if (mode === "keys") {
    await chrome.viewport(1440, 900, 1, false);
    await chrome.go(`${BASE}/`, 4000);
    const describe = `(() => { const a = document.activeElement; return a ? (a.tagName.toLowerCase() + (a.getAttribute("aria-label") ? '[' + a.getAttribute("aria-label") + ']' : '') + ' "' + (a.textContent || '').trim().slice(0, 28) + '"') : null; })()`;
    const order = [];
    for (let i = 0; i < 12; i += 1) {
      await chrome.key("Tab");
      order.push(await chrome.eval(describe));
    }
    console.log("first 12 Tab stops on Home (desktop):\n  " + order.join("\n  "));
    // skip link: Enter moves focus to the page area
    await chrome.go(`${BASE}/models`, 3500);
    await chrome.key("Tab");
    const skipVisible = await chrome.eval(`(() => { const r = document.activeElement.getBoundingClientRect(); return { text: document.activeElement.textContent.trim(), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }; })()`);
    await chrome.key("Enter");
    const afterSkip = await chrome.eval(`({ focus: document.activeElement.tagName.toLowerCase() + '#' + document.activeElement.id, url: location.pathname + location.hash })`);
    console.log("skip link when focused:", JSON.stringify(skipVisible), "| after Enter:", JSON.stringify(afterSkip));
    // phone: More sheet by keyboard
    await chrome.viewport(375, 812, 2, true);
    await chrome.go(`${BASE}/`, 3500);
    await chrome.eval(`document.querySelector('nav[aria-label="Main mobile"] button').focus(); 0`);
    await chrome.key("Enter");
    await sleep(300);
    const sheet = await chrome.eval(`({ open: !!document.querySelector('[role=dialog]'), focus: ${describe}, expanded: document.querySelector('nav[aria-label="Main mobile"] button').getAttribute('aria-expanded') })`);
    await chrome.key("Escape");
    await sleep(300);
    const closed = await chrome.eval(`({ open: !!document.querySelector('[role=dialog]'), focus: ${describe} })`);
    console.log("More sheet after Enter:", JSON.stringify(sheet), "| after Escape:", JSON.stringify(closed));
    // route change: title and focus
    await chrome.viewport(1440, 900, 1, false);
    await chrome.go(`${BASE}/`, 3500);
    await chrome.click('nav[aria-label="Main"] a[href="/analytics"]');
    await sleep(1500);
    console.log("after clicking Leagues:", await chrome.eval(`JSON.stringify({ title: document.title, focus: document.activeElement.tagName.toLowerCase() + '#' + document.activeElement.id, announced: [...document.querySelectorAll('[role=status]')].map((e) => e.textContent.trim().slice(0, 30)) })`));
  }
} finally {
  await chrome.close();
}
