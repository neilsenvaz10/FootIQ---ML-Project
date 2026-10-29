// Which font files does the browser actually request? (Inter ships as 7 unicode-range subsets; only the ones a page needs are downloaded.)
import { launch } from "./cdp.mjs";

const BASE = process.env.BASE || "http://localhost:5173";
const chrome = await launch({ port: 9336 });
try {
  await chrome.viewport(1440, 900, 1, false);
  for (const path of ["/", "/analytics?comp=LALIGA", "/analytics?comp=UEL", "/models"]) {
    await chrome.go(BASE + path, 4000);
    const files = await chrome.eval(`performance.getEntriesByType('resource').filter((r) => /\\.woff2/.test(r.name)).map((r) => r.name.split('/').pop().split('?')[0] + ' ' + Math.round(r.transferSize || r.encodedBodySize) + ' B')`);
    const hosts = await chrome.eval(`[...new Set(performance.getEntriesByType('resource').map((r) => new URL(r.name).host))]`);
    console.log(path.padEnd(28), "font files:", JSON.stringify(files), "| hosts contacted:", JSON.stringify(hosts));
  }
} finally {
  await chrome.close();
}
