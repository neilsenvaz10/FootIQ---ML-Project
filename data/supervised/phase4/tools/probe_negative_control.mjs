// Negative control for probe.js: the probe must report a low-contrast element placed on the hero gradient, and must not report a high-contrast one.
import { readFileSync } from "node:fs";
import { launch } from "./cdp.mjs";

const probe = readFileSync(new URL("./probe.js", import.meta.url), "utf8");
const chrome = await launch({ port: 9338 });
try {
  await chrome.viewport(1440, 900, 1, false);
  await chrome.go("http://localhost:5173/", 5500);
  const base = await chrome.eval(probe);
  console.log("real page: gradient backgrounds checked", base.text.gradientBackgroundsChecked, "| skipped", base.text.gradientBackgroundSkipped, "| failures", base.text.contrastFailures);
  await chrome.eval(`(() => {
    const hero = document.querySelector("section.hero");
    const mk = (cls, text) => { const p = document.createElement("p"); p.className = cls; p.textContent = text; hero.appendChild(p); };
    mk("text-mute", "NEGATIVE CONTROL mute on the lightest stop");
    mk("text-ink-2", "POSITIVE CONTROL ink-2 on the hero");
    const chip = document.createElement("span"); chip.className = "text-mute border border-line bg-white/5"; chip.textContent = "NEGATIVE CONTROL quiet chip on the hero"; hero.appendChild(chip);
    return true;
  })()`);
  const after = await chrome.eval(probe);
  const names = after.text.failSamples.map((f) => `${f.t} (${f.r}:1 ${f.fg} on ${f.bg})`);
  console.log("after planting: failures", after.text.contrastFailures);
  for (const n of names) console.log("  ", n);
} finally {
  await chrome.close();
}
