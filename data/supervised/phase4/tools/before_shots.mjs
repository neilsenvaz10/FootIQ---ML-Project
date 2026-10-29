// Screenshots of the untouched baseline frontend (served separately on the dev port) at the same viewports as the P4.1 shots.
import { launch } from "./cdp.mjs";

const BASE = process.env.BASE || "http://localhost:5173";
const OUT = process.env.OUT || "D:/Foot IQ/docs/mini-project/phase4/p4.1/before";
const chrome = await launch({ port: 9334 });
try {
  const shots = [
    [{ w: 1440, h: 900, s: 1, m: false }, "/", "desktop-home.png", 4000],
    [{ w: 1440, h: 900, s: 1, m: false }, "/analytics", "desktop-leagues-table.png", 4000],
    [{ w: 1440, h: 900, s: 1, m: false }, "/predict", "desktop-predictions.png", 9000],
    [{ w: 1440, h: 900, s: 1, m: false }, "/models", "desktop-models.png", 4000],
    [{ w: 820, h: 1180, s: 1, m: false }, "/", "tablet-home.png", 4000],
    [{ w: 375, h: 812, s: 2, m: true }, "/", "mobile-home.png", 4000],
    [{ w: 375, h: 812, s: 2, m: true }, "/predict", "mobile-predictions.png", 9000],
  ];
  for (const [vp, path, file, settle] of shots) {
    await chrome.viewport(vp.w, vp.h, vp.s, vp.m);
    await chrome.go(BASE + path, settle);
    await chrome.shot(`${OUT}/${file}`);
    console.log("saved", file);
  }
} finally {
  await chrome.close();
}
