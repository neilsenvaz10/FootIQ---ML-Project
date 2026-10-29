// Phase 4 / P4.2: screenshots and measurements of the redesigned Home page with headless Chrome (dev server on 5173, backend on 8000 with a private database copy).
//   node p42_capture.mjs shots [outdir]   Home at desktop, tablet and phone (above the fold and full page) plus focus and states
//   node p42_capture.mjs probe            contrast (gradient stops included), target sizes, overflow, headings on every route at 1440, 820 and 375 px
//   node p42_capture.mjs keys             drives the keyboard on Home: every Tab stop with its focus ring, the disclosure, the league pills, a fixture row
import { readFileSync, writeFileSync } from "node:fs";
import { launch, sleep } from "./cdp.mjs";

const BASE = process.env.BASE || "http://localhost:5173";
const OUT = process.env.OUT || "D:/Foot IQ/docs/mini-project/phase4/p4.2";
const mode = process.argv[2] || "shots";
const probe = readFileSync(new URL("./probe.js", import.meta.url), "utf8");
const ROUTES = ["/", "/matches", "/analytics", "/compare", "/predict", "/simulations", "/models"];
const VIEWPORTS = [
  { name: "desktop", w: 1440, h: 900, scale: 1, mobile: false },
  { name: "tablet", w: 820, h: 1180, scale: 1, mobile: false },
  { name: "mobile", w: 375, h: 812, scale: 2, mobile: true },
];

const chrome = await launch({ port: 9337 });
try {
  if (mode === "shots") {
    const full = async (vp, file, height, settle = 5000, path = "/") => {
      await chrome.viewport(vp.w, height, vp.scale, vp.mobile);
      await chrome.go(BASE + path, settle);
      await chrome.shot(`${OUT}/${file}`);
      console.log("saved", file);
    };
    for (const vp of VIEWPORTS) {
      await chrome.viewport(vp.w, vp.h, vp.scale, vp.mobile);
      await chrome.go(`${BASE}/`, 5500);
      await chrome.shot(`${OUT}/home-${vp.name}-fold.png`);
      console.log("saved", `home-${vp.name}-fold.png`);
    }
    await full(VIEWPORTS[0], "home-desktop-full.png", 1900);
    await full(VIEWPORTS[1], "home-tablet-full.png", 2700);
    await full({ ...VIEWPORTS[2] }, "home-mobile-full.png", 3300);
  }

  if (mode === "keys") {
    await chrome.viewport(1440, 900, 1, false);
    await chrome.go(`${BASE}/`, 5500);
    const describe = `(() => { const a = document.activeElement; if (!a || a === document.body) return null; const cs = getComputedStyle(a); const r = a.getBoundingClientRect();
      return { el: a.tagName.toLowerCase() + (a.getAttribute("role") ? "[" + a.getAttribute("role") + "]" : ""), text: (a.getAttribute("aria-label") || a.textContent || "").trim().slice(0, 46),
        ring: cs.outlineStyle + " " + cs.outlineWidth + " " + cs.outlineColor, h: Math.round(r.height), w: Math.round(r.width), inMain: !!a.closest("main"), top: Math.round(r.top) }; })()`;
    const stops = [];
    for (let i = 0; i < 40; i += 1) {
      await chrome.key("Tab");
      stops.push(await chrome.eval(describe));
    }
    const inMain = stops.filter((x) => x && x.inMain);
    console.log(`Tab stops (40 presses): ${stops.filter(Boolean).length} focused elements, ${inMain.length} inside <main>`);
    for (const x of inMain.slice(0, 30)) console.log(`  ${x.el.padEnd(14)} ${x.w}x${x.h}`.padEnd(30), x.ring.padEnd(34), JSON.stringify(x.text));
    const noRing = inMain.filter((x) => !/^solid 2px/.test(x.ring));
    console.log("main stops without a 2 px solid ring:", noRing.length, noRing.map((x) => x.text).join(" | "));

    // the notes disclosure: Enter and Space open and close it
    await chrome.eval(`document.querySelector("main details summary").focus(); 0`);
    await chrome.key("Enter");
    const opened = await chrome.eval(`document.querySelector("main details").open`);
    await chrome.key(" ");
    const closed = await chrome.eval(`document.querySelector("main details").open`);
    console.log("notes disclosure: Enter ->", opened ? "open" : "closed", "| Space ->", closed ? "open" : "closed");

    // league pills: arrow keys move the selection and the table follows
    await chrome.eval(`document.querySelector('[role=radiogroup][aria-label="League"] [aria-checked=true]').focus(); 0`);
    await chrome.key("ArrowRight");
    await sleep(2500);
    console.log("ArrowRight on the league pills:", await chrome.eval(`JSON.stringify({ selected: document.querySelector('[role=radiogroup][aria-label="League"] [aria-checked=true]').textContent, focus: document.activeElement.textContent, caption: (document.querySelector("main table caption")||{}).textContent })`));

    // a fixture row is a link: Enter goes to that gameweek (client-side navigation)
    const row = await chrome.eval(`(() => { const a = [...document.querySelectorAll("main section")].find((s) => s.querySelector("h2")?.textContent === "Next fixtures").querySelector("ul a"); a.focus(); return a.getAttribute("href"); })()`);
    await chrome.key("Enter");
    await sleep(1500);
    console.log("Enter on the first fixture row:", row, "->", await chrome.eval(`location.pathname + location.search`));
  }

  if (mode === "probe") {
    const all = {};
    for (const vp of VIEWPORTS) {
      await chrome.viewport(vp.w, vp.h, vp.scale, vp.mobile);
      await chrome.go(BASE + "/", 5500);
      all[vp.name] = [];
      for (const route of ROUTES) {
        if (route !== "/") await chrome.spa(route, route === "/predict" ? 9000 : 3500);
        const o = await chrome.eval(probe);
        all[vp.name].push(o);
        console.log([vp.name.padEnd(7), o.path.padEnd(12), o.title.padEnd(26), `ovf ${o.overflowX}`, `h1 ${o.h1.length}`, `contrast-fail ${o.text.contrastFailures}`, `(grad ${o.text.gradientBackgroundSkipped})`, `text<12 ${o.text.under12px}(+${o.text.decorativeUnder12px})`, `controls ${o.targets.controls}`, `<44 ${o.targets.below44}`, `<24 ${o.targets.below24}`].join(" | "));
        if (o.text.contrastFailures) console.log("    contrast samples:", JSON.stringify(o.text.failSamples));
        if (o.targets.below44) console.log("    <44 samples:", o.targets.below44Samples.join(" ; "));
      }
    }
    writeFileSync(`${OUT}/probe-${process.env.LABEL || "p42"}.json`, JSON.stringify(all, null, 1));
  }
} finally {
  await chrome.close();
}
