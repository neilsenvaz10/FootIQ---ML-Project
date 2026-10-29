// WCAG 2.x contrast arithmetic and a reader for the design tokens in src/index.css.
// Used by tests/design-tokens.test.jsx and the development-only design-system page; not part of the production bundle.

export function hexToRgb(h) {
  const s = h.replace("#", "");
  const full = s.length === 3 ? [...s].map((c) => c + c).join("") : s;
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
}

const linear = (c) => {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};

export const luminance = ([r, g, b]) => 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);

const rgbOf = (c) => (typeof c === "string" ? hexToRgb(c) : c);

export function contrastRatio(a, b) {
  const [x, y] = [luminance(rgbOf(a)), luminance(rgbOf(b))];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

// `fg` drawn at `alpha` over `bg` (what a class such as bg-ok/10 produces).
export const blend = (fg, bg, alpha) => rgbOf(fg).map((v, i) => v * alpha + rgbOf(bg)[i] * (1 - alpha));

// Colour tokens of the @theme block as { name: "#rrggbb" }; a token defined as a reference to another token is resolved.
export function colorTokens(css) {
  const block = css.match(/@theme[^{]*\{([\s\S]*?)\n\}/)?.[1] ?? "";
  const raw = {};
  for (const m of block.matchAll(/--color-([a-z0-9-]+):\s*([^;]+);/g)) raw[m[1]] = m[2].trim();
  const out = {};
  for (const [name, value] of Object.entries(raw)) {
    const ref = value.match(/^var\(--color-([a-z0-9-]+)\)$/);
    out[name] = ref ? raw[ref[1]] : value;
  }
  return out;
}

// HSL (degrees, percent, percent) to [r, g, b] in 0-255, for the generated team colours.
export function hslToRgb(h, s, l) {
  const sat = s / 100;
  const lig = l / 100;
  const k = (n) => (n + h / 30) % 12;
  const a = sat * Math.min(lig, 1 - lig);
  const f = (n) => lig - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0), f(8), f(4)].map((v) => Math.round(v * 255));
}
