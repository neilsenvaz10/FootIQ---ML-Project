// Prints the accessible names Chrome computes for the Home page's links, groups, regions and tables (CDP Accessibility.getFullAXTree).
import { launch } from "./cdp.mjs";

const chrome = await launch({ port: 9339 });
try {
  await chrome.viewport(1440, 900, 1, false);
  await chrome.go("http://localhost:5173/", 5500);
  await chrome.send("Accessibility.enable");
  const { nodes } = await chrome.send("Accessibility.getFullAXTree");
  const show = (n) => `${n.role?.value}: ${JSON.stringify((n.name?.value || "").slice(0, 110))}`;
  const want = new Set(["link", "group", "region", "table", "radiogroup", "radio", "heading", "img"]);
  const rows = nodes.filter((n) => !n.ignored && want.has(n.role?.value) && (n.name?.value || n.role?.value === "table"));
  for (const n of rows) console.log(show(n));
} finally {
  await chrome.close();
}
