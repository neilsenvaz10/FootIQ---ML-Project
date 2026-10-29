// Minimal Chrome DevTools Protocol driver (Node 22+ built-ins only, no packages): launches a headless Chrome with a throw-away profile,
// then navigates, emulates a viewport, presses keys, evaluates scripts and takes screenshots. Used for Phase 4 screenshots and measurements.
import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function launch({ port = 9333, profile } = {}) {
  const dir = profile || `${process.env.TEMP || "."}/footiq_cdp_profile_${port}`;
  rmSync(dir, { recursive: true, force: true });
  const proc = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "--disable-extensions", `--user-data-dir=${dir}`, `--remote-debugging-port=${port}`, "about:blank"], { stdio: "ignore" });
  let target;
  for (let i = 0; i < 60 && !target; i += 1) {
    try {
      target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page");
    } catch {
      /* not up yet */
    }
    if (!target) await sleep(250);
  }
  if (!target) throw new Error("Chrome did not start");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.addEventListener("open", res, { once: true });
    ws.addEventListener("error", rej, { once: true });
  });
  let id = 0;
  const pending = new Map();
  const events = [];
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) pending.get(m.id)(m);
    else events.push(m);
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const i = (id += 1);
      pending.set(i, (m) => (m.error ? reject(new Error(`${method}: ${JSON.stringify(m.error)}`)) : resolve(m.result)));
      ws.send(JSON.stringify({ id: i, method, params }));
    });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setFocusEmulationEnabled", { enabled: true });

  const api = {
    send,
    // CSS-pixel viewport; `mobile` also turns on touch emulation and the mobile viewport rules
    async viewport(width, height, scale = 1, mobile = false) {
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: scale, mobile });
      await send("Emulation.setTouchEmulationEnabled", { enabled: mobile });
    },
    async go(url, settleMs = 2500) {
      events.length = 0;
      await send("Page.navigate", { url });
      for (let i = 0; i < 80; i += 1) {
        if (events.some((e) => e.method === "Page.loadEventFired")) break;
        await sleep(100);
      }
      await sleep(settleMs);
    },
    // in-app navigation without a reload (keeps scripts and focus state of the page)
    async spa(path, settleMs = 2500) {
      await api.eval(`history.pushState({}, "", ${JSON.stringify(path)}); window.dispatchEvent(new PopStateEvent("popstate")); 0`);
      await sleep(settleMs);
    },
    async eval(expression) {
      const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(`eval failed: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
      return r.result.value;
    },
    async key(name, { shift = false } = {}) {
      const map = { Tab: [9, "Tab"], Enter: [13, "Enter"], Escape: [27, "Escape"], ArrowRight: [39, "ArrowRight"], ArrowLeft: [37, "ArrowLeft"], ArrowDown: [40, "ArrowDown"], ArrowUp: [38, "ArrowUp"], Home: [36, "Home"], End: [35, "End"], " ": [32, "Space"] };
      const [vk, code] = map[name];
      const base = { key: name, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers: shift ? 8 : 0 };
      // Enter and Space need a text-producing keyDown so the page also sees a keypress (that is what activates a <button>)
      const text = name === "Enter" ? "\r" : name === " " ? " " : undefined;
      await send("Input.dispatchKeyEvent", text ? { type: "keyDown", ...base, text } : { type: "rawKeyDown", ...base });
      await send("Input.dispatchKeyEvent", { type: "keyUp", ...base });
      await sleep(120);
    },
    async click(selector) {
      const box = await api.eval(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
      if (!box) throw new Error(`no element for ${selector}`);
      for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
      await sleep(250);
    },
    async shot(path, { fullPage = false } = {}) {
      mkdirSync(dirname(path), { recursive: true });
      const r = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: fullPage });
      writeFileSync(path, Buffer.from(r.data, "base64"));
    },
    async close() {
      try {
        await send("Browser.close");
      } catch {
        /* already closing */
      }
      ws.close();
      proc.kill();
    },
  };
  return api;
}
