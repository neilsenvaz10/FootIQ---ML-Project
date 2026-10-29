// P4.3: screenshots and probes of Matches, Predictions, Compare and the refined Home (headless Chrome; dev server on 5173, backend on 8000 with a private copy).
//   node p43_capture.mjs shots    node p43_capture.mjs probe
import { readFileSync, writeFileSync } from "node:fs";
import { launch } from "./cdp.mjs";

const BASE = "http://localhost:5173";
const OUT = "D:/Foot IQ/docs/mini-project/phase4/p4.3";
const probe = readFileSync(new URL("./probe.js", import.meta.url), "utf8");
const VP = [
  { name: "desktop", w: 1440, h: 900, scale: 1, mobile: false },
  { name: "tablet", w: 820, h: 1180, scale: 1, mobile: false },
  { name: "mobile", w: 375, h: 812, scale: 2, mobile: true },
];
const PAGES = {
  "matches-upcoming": "/matches",
  "matches-completed": "/matches?comp=BUNDESLIGA&status=completed",
  "predictions-gameweek": "/predict?mode=gameweek&comp=EPL",
  "predictions-manual": "/predict?mode=manual&comp=EPL&home=Arsenal%20FC&away=Chelsea%20FC",
  compare: "/compare?comp=EPL&a=Arsenal%20FC&b=Chelsea%20FC",
  home: "/",
};
const mode = process.argv[2] || "shots";
const chrome = await launch({ port: 9341 });
try {
  if (mode === "shots") {
    for (const vp of VP) {
      for (const [name, path] of Object.entries(PAGES)) {
        await chrome.viewport(vp.w, vp.h, vp.scale, vp.mobile);
        await chrome.go(BASE + path, 6500);
        await chrome.shot(`${OUT}/${name}-${vp.name}-fold.png`);
        if (name.startsWith("matches") || name.startsWith("predictions")) {
          await chrome.viewport(vp.w, vp.name === "mobile" ? 3200 : 2200, vp.scale, vp.mobile);
          await chrome.go(BASE + path, 6500);
          await chrome.shot(`${OUT}/${name}-${vp.name}-full.png`);
        }
        console.log("saved", name, vp.name);
      }
    }
  }
  if (mode === "probe") {
    const all = {};
    for (const vp of VP) {
      all[vp.name] = [];
      for (const [name, path] of Object.entries(PAGES)) {
        await chrome.viewport(vp.w, vp.h, vp.scale, vp.mobile);
        await chrome.go(BASE + path, 6500);
        const o = await chrome.eval(probe);
        all[vp.name].push({ name, ...o });
        console.log([vp.name.padEnd(7), name.padEnd(22), `ovf ${o.overflowX}`, `h1 ${o.h1.length}`, `contrast-fail ${o.text.contrastFailures}`, `text<12 ${o.text.under12px}`, `controls ${o.targets.controls}`, `<44 ${o.targets.below44}`].join(" | "));
        if (o.text.contrastFailures) console.log("   contrast:", JSON.stringify(o.text.failSamples));
        if (o.targets.below44) console.log("   <44:", o.targets.below44Samples.join(" ; "));
        if (o.text.under12px) console.log("   <12px:", JSON.stringify(o.text.smallSamples));
      }
    }
    writeFileSync(`${OUT}/probe-p43.json`, JSON.stringify(all, null, 1));
  }
} finally {
  await chrome.close();
}
