import { launch } from "../data/supervised/phase4/p44/cdp_p44.mjs";

const chrome = await launch({ port: 9346 });
await chrome.viewport(375, 1000, 1, true);
await chrome.go("http://127.0.0.1:5174/analytics?comp=BUNDESLIGA", 3000);

// Click stats tab
await chrome.eval(`document.querySelector('[role="tab"]:nth-child(3)').click()`);
await new Promise((r) => setTimeout(r, 2000));

const html = await chrome.eval(`
  const card = document.querySelector('.recharts-wrapper');
  card ? card.outerHTML : 'no recharts-wrapper'
`);
console.log("RECHARTS HTML:", html);

await chrome.close();
