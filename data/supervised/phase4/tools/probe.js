// Accessibility and layout probe evaluated inside a page (read-only: it measures, it never clicks or types).
// Reports: horizontal overflow, document title, landmarks, h1 count, whether Inter is loaded, text contrast (WCAG 1.4.3),
// text under 12 px (split into text people read and decorative aria-hidden glyphs such as badge letters), and the size of every operable control.
(() => {
  const cv = document.createElement("canvas");
  cv.width = cv.height = 1;
  const cx = cv.getContext("2d", { willReadFrequently: true });
  const BASE = "#0a0a1a";
  const px = () => Array.from(cx.getImageData(0, 0, 1, 1).data.slice(0, 3));
  const lin = (c) => { const s = c / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; };
  const lum = (r) => 0.2126 * lin(r[0]) + 0.7152 * lin(r[1]) + 0.0722 * lin(r[2]);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const hex = (r) => "#" + r.map((v) => v.toString(16).padStart(2, "0")).join("");
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none"; };

  // Colour stops of a gradient background (any CSS colour syntax is converted by the canvas); null when none can be read
  function gradientStops(image) {
    const found = image.match(/(?:rgba?|color|oklab|oklch|lab|lch|hsla?)\([^()]*\)/g) || [];
    const out = [];
    for (const c of found) {
      cx.globalAlpha = 1;
      cx.fillStyle = BASE;
      cx.fillRect(0, 0, 1, 1);
      cx.fillStyle = c;
      cx.fillRect(0, 0, 1, 1);
      out.push(px());
    }
    return out.length ? out : null;
  }

  // alpha (0-1) of any CSS colour: draw it on a transparent pixel and read the alpha channel back
  function alphaOf(color) {
    cx.globalAlpha = 1;
    cx.clearRect(0, 0, 1, 1);
    cx.fillStyle = color;
    cx.fillRect(0, 0, 1, 1);
    return cx.getImageData(0, 0, 1, 1).data[3] / 255;
  }

  // The surface behind an element: its own and its ancestors' fills stacked on the page colour. A translucent fill (bg-black/25, bg-white/5)
  // is composited over whatever lies beneath it; when a gradient lies beneath, each colour stop is a possible backdrop and the worst one decides.
  // (The page's own radial glow on <body> is not treated as a gradient: it is a faint tint on the page colour.)
  function background(el) {
    const layers = []; // innermost first
    let stops = null;
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (n !== document.body && n !== document.documentElement && cs.backgroundImage.includes("gradient")) {
        stops = gradientStops(cs.backgroundImage);
        if (stops) break;
      }
      const a = alphaOf(cs.backgroundColor);
      if (a > 0) layers.push(cs.backgroundColor);
      if (a >= 1) break;
    }
    const over = (base) => {
      cx.globalAlpha = 1;
      cx.fillStyle = BASE;
      cx.fillRect(0, 0, 1, 1);
      if (base) { cx.fillStyle = hex(base); cx.fillRect(0, 0, 1, 1); }
      for (const l of layers.slice().reverse()) { cx.fillStyle = l; cx.fillRect(0, 0, 1, 1); }
      return px();
    };
    return stops ? { gradient: true, stops: stops.map(over), rgb: null } : { gradient: false, stops: null, rgb: over(null) };
  }
  function opacityOf(el) { let o = 1; for (let n = el; n; n = n.parentElement) o *= Number(getComputedStyle(n).opacity); return o; }

  const out = { path: location.pathname, vw: innerWidth, overflowX: document.documentElement.scrollWidth - innerWidth, title: document.title };
  out.landmarks = { header: document.querySelectorAll("body > div > header, body > header").length, nav: document.querySelectorAll("nav").length, main: document.querySelectorAll("main").length, footer: document.querySelectorAll("footer").length, aside: document.querySelectorAll("aside").length };
  out.h1 = [...document.querySelectorAll("h1")].filter(visible).map((h) => h.textContent.trim().slice(0, 40));
  out.interFaces = [...document.fonts].filter((f) => f.family.replace(/"/g, "").includes("Inter") && f.status === "loaded").map((f) => f.family.replace(/"/g, ""));

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let total = 0, unknown = 0, gradientChecked = 0;
  const fails = [], small = [], decor = [];
  const seen = new Set();
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.textContent.replace(/\s+/g, " ").trim();
    if (!text) continue;
    const el = n.parentElement;
    if (!el || el.closest("script, style, noscript, svg")) continue;
    const range = document.createRange();
    range.selectNodeContents(n);
    const rect = range.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0 || !visible(el)) continue;
    if (el.closest(".sr-only")) continue;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    const weight = Number(cs.fontWeight);
    total += 1;
    if (fs < 12 && !seen.has("s" + text)) { seen.add("s" + text); (el.closest('[aria-hidden="true"]') ? decor : small).push({ t: text.slice(0, 24), fs }); }
    const bg = background(el);
    const textOn = (rgb) => {
      cx.globalAlpha = 1;
      cx.fillStyle = hex(rgb);
      cx.fillRect(0, 0, 1, 1);
      cx.globalAlpha = Math.max(0, Math.min(1, opacityOf(el)));
      cx.fillStyle = cs.color;
      cx.fillRect(0, 0, 1, 1);
      const fg = px();
      cx.globalAlpha = 1;
      return fg;
    };
    // on a gradient the worst of its colour stops decides; a gradient whose stops cannot be read is counted as unknown
    const backgrounds = bg.gradient ? bg.stops : [bg.rgb];
    if (!backgrounds) { unknown += 1; continue; }
    const large = fs >= 24 || (fs >= 18.66 && weight >= 700);
    let worst = Infinity, worstFg = null, worstBg = null;
    for (const b of backgrounds) {
      const fg = textOn(b);
      const r = ratio(fg, b);
      if (r < worst) { worst = r; worstFg = fg; worstBg = b; }
    }
    if (bg.gradient) gradientChecked += 1;
    if (worst < (large ? 3 : 4.5) && !seen.has(text)) { seen.add(text); fails.push({ t: text.slice(0, 28), r: +worst.toFixed(2), fs, fg: hex(worstFg), bg: hex(worstBg), gradient: bg.gradient }); }
  }
  out.text = { nodes: total, gradientBackgroundSkipped: unknown, gradientBackgroundsChecked: gradientChecked, contrastFailures: fails.length, failSamples: fails.slice(0, 8), under12px: small.length, smallSamples: small.slice(0, 8), decorativeUnder12px: decor.length };

  const SEL = "a[href], button, input:not([type=hidden]), select, textarea, [role=tab], [role=radio], [role=button], summary";
  const targets = [...document.querySelectorAll(SEL)].filter(visible).filter((el) => !el.closest(".sr-only"));
  const name = (el) => (el.getAttribute("aria-label") || el.textContent || el.getAttribute("placeholder") || el.tagName).replace(/\s+/g, " ").trim().slice(0, 26);
  const inlineLink = (el) => el.tagName === "A" && getComputedStyle(el).display === "inline" && el.parentElement && /^(P|LI|SPAN|DIV|TD|STRONG)$/.test(el.parentElement.tagName) && el.parentElement.textContent.trim().length > el.textContent.trim().length + 12;
  const rows = targets.map((el) => { const r = el.getBoundingClientRect(); return { n: name(el), w: Math.round(r.width), h: Math.round(r.height), inline: inlineLink(el), tag: el.tagName.toLowerCase() + (el.getAttribute("role") ? "[" + el.getAttribute("role") + "]" : "") }; });
  const ctl = rows.filter((r) => !r.inline);
  const lt44 = ctl.filter((r) => Math.min(r.w, r.h) < 44);
  out.targets = { controls: ctl.length, inlineTextLinks: rows.length - ctl.length, below44: lt44.length, below24: ctl.filter((r) => Math.min(r.w, r.h) < 24).length, below44Samples: lt44.slice(0, 12).map((r) => r.tag + ' "' + r.n + '" ' + r.w + "x" + r.h) };
  return out;
})()
