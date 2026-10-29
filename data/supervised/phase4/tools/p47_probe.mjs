// P4.7: every route at 1440, 820 and 375 px against the live backend: overflow, contrast, small text, targets, and any visible error banner.
import { readFileSync, writeFileSync } from "node:fs";
import { launch } from "./cdp.mjs";
const probe = readFileSync(new URL("./probe.js", import.meta.url), "utf8");
const ROUTES = ["/", "/matches", "/analytics", "/compare", "/predict", "/predict?mode=manual&comp=EPL", "/simulations", "/models"];
const VP = [{ n: "desktop", w: 1440, h: 900, s: 1, m: false }, { n: "tablet", w: 820, h: 1180, s: 1, m: false }, { n: "mobile", w: 375, h: 812, s: 2, m: true }];
const chrome = await launch({ port: 9347 });
const rows = [];
try {
  for (const vp of VP) {
    for (const r of ROUTES) {
      await chrome.viewport(vp.w, vp.h, vp.s, vp.m);
      await chrome.go("http://localhost:5173" + r, 7000);
      const o = await chrome.eval(probe);
      const banner = await chrome.eval(`(() => { const t = document.body.innerText; return { unreachable: /Cannot reach the backend/.test(t), wentWrong: /Something went wrong/.test(t) }; })()`);
      const row = { vp: vp.n, route: r, overflow: o.overflowX, h1: o.h1.length, contrastFail: o.text.contrastFailures, under12: o.text.under12px, below44: o.targets.below44, samples44: o.targets.below44Samples, ...banner };
      rows.push(row);
      console.log(`${vp.n.padEnd(7)} ${r.padEnd(32)} ovf ${row.overflow} h1 ${row.h1} contrast ${row.contrastFail} <12px ${row.under12} <44px ${row.below44} unreachable ${row.unreachable} error ${row.wentWrong}`);
    }
  }
  writeFileSync("D:/Foot IQ/data/supervised/phase4/p47_ui_probe.json", JSON.stringify(rows, null, 1));
} finally { await chrome.close(); }
