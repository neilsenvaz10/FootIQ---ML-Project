// Recharts now take their colours from CSS variables (src/lib/chart.js). This captures every chart screen so that can be checked by eye.
import { launch, sleep } from "./cdp.mjs";

const BASE = process.env.BASE || "http://localhost:5173";
const OUT = process.env.OUT || "D:/Foot IQ/docs/mini-project/phase4/p4.1";
const chrome = await launch({ port: 9335 });
const unresolved = `(() => { const bad = []; let used = 0; for (const el of document.querySelectorAll('svg.recharts-surface [fill], svg.recharts-surface [stroke], .recharts-wrapper [style]')) { for (const a of ['fill', 'stroke']) { const v = el.getAttribute(a); if (v && v.startsWith('var(')) { used += 1; const c = getComputedStyle(el)[a]; if (!c || c === 'none' || c === 'rgba(0, 0, 0, 0)') bad.push(v); } } } return { cssVariableColoursUsed: used, notResolved: bad.length }; })()`;
const clickText = (selector, text) => `(() => { const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find((e) => e.textContent.trim().startsWith(${JSON.stringify(text)})); if (!el) return false; el.click(); return true; })()`;
try {
  await chrome.viewport(1440, 2300, 1, false);
  await chrome.go(`${BASE}/`, 5000);
  await chrome.shot(`${OUT}/charts-home.png`);
  console.log("home charts: svg", await chrome.eval(`document.querySelectorAll('svg.recharts-surface').length`), JSON.stringify(await chrome.eval(unresolved)));

  await chrome.go(`${BASE}/analytics`, 4000);
  console.log("click Stats:", await chrome.eval(clickText("[role=tab]", "Stats")));
  await sleep(3500);
  await chrome.shot(`${OUT}/charts-leagues-stats.png`);
  console.log("leagues charts: svg", await chrome.eval(`document.querySelectorAll('svg.recharts-surface').length`), JSON.stringify(await chrome.eval(unresolved)));

  await chrome.go(`${BASE}/models`, 5000);
  await chrome.shot(`${OUT}/charts-models.png`);
  console.log("models charts: svg", await chrome.eval(`document.querySelectorAll('svg.recharts-surface').length`), JSON.stringify(await chrome.eval(unresolved)));

  await chrome.go(`${BASE}/simulations`, 3000);
  console.log("click Run simulation:", await chrome.eval(clickText("button", "Run simulation")));
  await sleep(9000);
  await chrome.shot(`${OUT}/charts-simulator.png`);
  console.log("simulator charts: svg", await chrome.eval(`document.querySelectorAll('svg.recharts-surface').length`));
  console.log("simulator charts:", JSON.stringify(await chrome.eval(unresolved)));
} finally {
  await chrome.close();
}
