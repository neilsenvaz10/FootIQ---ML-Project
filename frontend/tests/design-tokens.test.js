// @vitest-environment node
// Design tokens (Phase 4, stage P4.1): every colour pair the app uses for text or for the edge of a control is checked against WCAG 2.2 AA,
// the tokens are read from src/index.css itself, and nothing may reach for an external font or a colour that is not a token.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { blend, colorTokens, contrastRatio } from "../src/lib/contrast.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (rel) => readFileSync(join(ROOT, rel), "utf8");
const T = colorTokens(read("src/index.css"));
const SURFACES = ["bg", "sidebar", "panel", "panel-2", "panel-3"];

const walk = (dir) =>
  readdirSync(join(ROOT, dir), { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name).replaceAll("\\", "/")]));
const SOURCE_FILES = walk("src").filter((f) => /\.(jsx?|css)$/.test(f));

describe("contrast arithmetic", () => {
  it("reproduces the published WCAG values", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrastRatio("#767676", "#ffffff")).toBeCloseTo(4.54, 2);
    expect(contrastRatio("#ffffff", "#ffffff")).toBe(1);
  });
});

describe("tokens", () => {
  it("are read from the @theme block of src/index.css", () => {
    for (const name of ["bg", "sidebar", "panel", "panel-2", "panel-3", "line", "line-strong", "ink", "ink-2", "mute", "mute-2", "accent", "primary", "primary-hi", "primary-lo", "ok", "warn", "bad", "info"]) {
      expect(T[name], name).toMatch(/^#[0-9a-f]{6}$/i);
    }
    expect(T.pitch).toBe(T.accent); // the legacy name still resolves to the new accent
  });

  it.each(["ink", "ink-2", "mute", "mute-2", "accent"].flatMap((t) => SURFACES.map((s) => [t, s])))("%s text on %s is at least 4.5:1", (text, surface) => {
    expect(contrastRatio(T[text], T[surface])).toBeGreaterThanOrEqual(4.5);
  });

  it.each(["ok", "warn", "bad", "info"].flatMap((t) => ["bg", "panel", "panel-2"].map((s) => [t, s])))("%s status text on %s is at least 4.5:1", (tone, surface) => {
    expect(contrastRatio(T[tone], T[surface])).toBeGreaterThanOrEqual(4.5);
  });

  it.each(["ok", "warn", "bad", "info"].flatMap((t) => [0.1, 0.15].map((a) => [t, a])))("%s text on its own %d tint over a card is at least 4.5:1", (tone, alpha) => {
    for (const surface of ["panel", "panel-2"]) {
      expect(contrastRatio(T[tone], blend(T[tone], T[surface], alpha))).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("white text on the primary button is at least 4.5:1 at both ends of its gradient (it was 3.86 and 3.22 before P4.1)", () => {
    for (const name of ["primary", "primary-hi", "primary-lo"]) expect(contrastRatio("#ffffff", T[name]), name).toBeGreaterThanOrEqual(4.5);
  });

  it("disabled button text and placeholders keep 4.5:1 on the control fill", () => {
    expect(contrastRatio(T["mute-2"], T["panel-2"])).toBeGreaterThanOrEqual(4.5);
  });

  it.each(SURFACES)("the edge of a control (line-strong) is at least 3:1 against %s", (surface) => {
    expect(contrastRatio(T["line-strong"], T[surface])).toBeGreaterThanOrEqual(3);
  });

  it.each(SURFACES)("the keyboard focus ring (accent) is at least 3:1 against %s", (surface) => {
    expect(contrastRatio(T.accent, T[surface])).toBeGreaterThanOrEqual(3);
  });

  it("the active navigation item (accent on a 15% accent tint) is at least 4.5:1 in the sidebar and in the More sheet", () => {
    for (const surface of ["sidebar", "panel"]) expect(contrastRatio(T.accent, blend(T.accent, T[surface], 0.15))).toBeGreaterThanOrEqual(4.5);
  });

  it("quiet chips (mute on a 5% white tint) and black form letters on the win and loss colours are at least 4.5:1", () => {
    expect(contrastRatio(T.mute, blend("#ffffff", T.panel, 0.05))).toBeGreaterThanOrEqual(4.5);
    for (const name of ["ok", "bad", "ink-2"]) expect(contrastRatio("#000000", T[name]), name).toBeGreaterThanOrEqual(4.5);
  });

  it("every var(--color-...) used anywhere in src is a defined token", () => {
    const used = new Set();
    for (const file of SOURCE_FILES) for (const m of read(file).matchAll(/var\(--color-([a-z0-9-]+)\)/g)) used.add(m[1]);
    const undefinedTokens = [...used].filter((name) => !(name in T));
    expect(undefinedTokens).toEqual([]);
    expect(used.size).toBeGreaterThan(5);
  });
});

describe("shared components and the shell", () => {
  const SHARED = ["ui.jsx", "Layout.jsx", "Sidebar.jsx", "MobileNav.jsx", "SyncStatus.jsx", "Brand.jsx", "Icon.jsx", "PageHeader.jsx", "FixtureCard.jsx", "ProbBar.jsx", "SourceDetails.jsx", "Bracket.jsx"].map((f) => `src/components/${f}`);

  it("use no text smaller than 12 px", () => {
    for (const file of SHARED) expect(read(file), file).not.toMatch(/text-\[(?:[0-9]|1[01])(?:\.\d+)?px\]/);
  });

  it("use no hard-coded hex colour in the redesigned components (colours come from the tokens)", () => {
    for (const file of ["ui.jsx", "Layout.jsx", "Sidebar.jsx", "MobileNav.jsx", "SyncStatus.jsx", "Brand.jsx", "Icon.jsx", "TeamCrest.jsx"].map((f) => `src/components/${f}`)) {
      expect(read(file), file).not.toMatch(/#[0-9a-fA-F]{6}\b/);
    }
  });

  it("make every interactive shared control at least 44 px tall", () => {
    const ui = read("src/components/ui.jsx");
    expect(ui.match(/min-h-11/g).length).toBeGreaterThanOrEqual(6); // buttons (shared base), Select/Input, Pills, Tabs, ErrorBox retry, MatchRow
    for (const file of ["Sidebar.jsx", "MobileNav.jsx", "SyncStatus.jsx"].map((f) => `src/components/${f}`)) expect(read(file), file).toMatch(/min-h-(?:11|12|14)|h-16|h-11/);
  });
});

describe("Home dashboard (P4.2): the featured match on the hero gradient", () => {
  const STOPS = ["hero-from", "hero-via", "panel"]; // the three colour stops of .hero, lightest first
  const hero = read("src/index.css").match(/\.hero\s*\{([\s\S]*?)\}/)?.[1] ?? "";
  const glass = (stop, alpha) => blend("#000000", T[stop], alpha); // what a bg-black/NN fill makes of a stop

  it("is painted from tokens only, in the order the tests below assume", () => {
    const at = (name) => hero.indexOf(`var(--color-${name})`);
    expect(at("hero-from")).toBeGreaterThanOrEqual(0);
    expect(at("hero-from")).toBeLessThan(at("hero-via"));
    expect(at("hero-via")).toBeLessThan(at("panel"));
    expect(hero).not.toMatch(/#[0-9a-fA-F]{3,8}/);
    for (const name of STOPS) expect(T[name], name).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it.each(["ink", "ink-2"].flatMap((t) => STOPS.map((s) => [t, s])))("%s text on the hero stop %s is at least 4.5:1", (text, stop) => {
    expect(contrastRatio(T[text], T[stop])).toBeGreaterThanOrEqual(4.5);
  });

  it.each(STOPS)("text on darkened glass (chips, forecast strip, notes, glass buttons) is at least 4.5:1 over the stop %s", (stop) => {
    for (const alpha of [0.2, 0.25, 0.3, 0.45]) {
      for (const text of ["ink", "ink-2"]) expect(contrastRatio(T[text], glass(stop, alpha)), `${text} on black/${alpha * 100}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it.each(["ok", "warn"].flatMap((t) => STOPS.map((s) => [t, s])))("a %s chip (its colour on its own 10%% tint) is at least 4.5:1 over the stop %s", (tone, stop) => {
    expect(contrastRatio(T[tone], blend(T[tone], T[stop], 0.1))).toBeGreaterThanOrEqual(4.5);
  });

  it("the light call-to-action (page colour on ink, or on white when hovered) is at least 7:1", () => {
    expect(contrastRatio(T.bg, T.ink)).toBeGreaterThanOrEqual(7);
    expect(contrastRatio(T.bg, "#ffffff")).toBeGreaterThanOrEqual(7);
  });

  it.each(STOPS)("the edge of a glass button (white at 50%% over black/30, or black/45 when hovered) is at least 3:1 against the stop %s", (stop) => {
    for (const fill of [0.3, 0.45]) expect(contrastRatio(blend("#ffffff", glass(stop, fill), 0.5), T[stop]), `black/${fill * 100}`).toBeGreaterThanOrEqual(3);
  });

  it.each(STOPS)("the keyboard focus ring (accent) is at least 3:1 against the stop %s", (stop) => {
    expect(contrastRatio(T.accent, T[stop])).toBeGreaterThanOrEqual(3);
  });

  it("the buttons really use the classes this test models", () => {
    const ui = read("src/components/ui.jsx");
    expect(ui).toContain('BUTTON_STYLES.light = "bg-ink text-bg ');
    expect(ui).toContain('BUTTON_STYLES.glass = "border border-white/50 bg-black/30 text-ink hover:bg-black/45 ');
    expect(ui).toContain('hero: "text-ink border-white/20 bg-black/25"');
  });
});

describe("Home dashboard (P4.2): sources", () => {
  const HOME = ["FeaturedMatch.jsx", "FixtureLists.jsx", "LeagueOverview.jsx", "QuickActions.jsx"].map((f) => `src/components/home/${f}`);

  it("use no text under 12 px and no hard-coded colour", () => {
    for (const file of [...HOME, "src/lib/fixtures.js", "src/pages/Overview.jsx"]) {
      expect(read(file), file).not.toMatch(/text-\[(?:[0-9]|1[01])(?:\.\d+)?px\]/);
      expect(read(file), file).not.toMatch(/#[0-9a-fA-F]{6}/);
    }
  });

  it("make every link and button at least 44 px tall (min-h-11 or taller) unless it is a plain inline link", () => {
    for (const file of HOME.filter((f) => !f.endsWith("FeaturedMatch.jsx"))) expect(read(file), file).toMatch(/min-h-(?:11|12|14|\[4\.5rem\])/);
    const banner = read("src/components/home/FeaturedMatch.jsx");
    expect(banner).toMatch(/<Summary onHero/); // the notes disclosure (its summary is 44 px tall, below); the three actions are ButtonLinks (min-h-11 in BUTTON_BASE)
    expect(banner).not.toMatch(/<a |<summary/);
    expect(read("src/components/ui.jsx")).toMatch(/export function Summary[\s\S]*?min-h-11/);
  });

  it("do not call a forecast-creating endpoint or any other write: Home only reads", () => {
    for (const file of [...HOME, "src/pages/Overview.jsx"]) {
      const src = read(file);
      expect(src, file).not.toMatch(/method:\s*["']POST/i);
      expect(src, file).not.toMatch(/\/api\/gameweek(?!s)/); // the full gameweek page is never requested by Home
      expect(src, file).not.toMatch(/api\/gameweek\/(?:forecast|predict)|api\/forecast/);
    }
  });
});

describe("fonts", () => {
  it("Inter is self-hosted from the npm package and no stylesheet, script or page asks an external host for a font", () => {
    expect(read("src/main.jsx")).toContain('import "@fontsource-variable/inter/wght.css"');
    expect(JSON.parse(read("package.json")).dependencies).toHaveProperty("@fontsource-variable/inter");
    expect(read("src/index.css")).toMatch(/--font-sans:\s*"Inter Variable"/);
    for (const file of ["index.html", ...SOURCE_FILES]) {
      expect(read(file), file).not.toMatch(/fonts\.googleapis|fonts\.gstatic|use\.typekit|cdnjs|jsdelivr|unpkg|@import\s+url\(/i);
    }
  });

  it("the font's licence (SIL OFL 1.1) is present in the installed package", () => {
    const licence = join(ROOT, "node_modules/@fontsource-variable/inter/LICENSE");
    expect(existsSync(licence)).toBe(true);
    expect(readFileSync(licence, "utf8")).toContain("SIL OPEN FONT LICENSE Version 1.1");
  });
});

describe("Matches and Predictions (P4.3): sources", () => {
  const FILES = ["src/pages/Matches.jsx", "src/components/matches/MatchCard.jsx", "src/components/matches/MatchFilters.jsx", "src/components/Kickoff.jsx", "src/pages/Predict.jsx", "src/pages/GameweekPredict.jsx", "src/pages/Predictions.jsx", "src/pages/TeamComparison.jsx", "src/components/FixtureCard.jsx", "src/components/ProbBar.jsx"];

  it("use no text under 12 px (the two undersized Compare texts and the Predictions labels are fixed)", () => {
    for (const file of FILES) expect(read(file), file).not.toMatch(/text-\[(?:[0-9]|1[01])(?:\.\d+)?px\]/);
  });

  it("make the Matches links and controls at least 44 px tall", () => {
    expect(read("src/components/matches/MatchCard.jsx")).toMatch(/min-h-11/);
    expect(read("src/components/FixtureCard.jsx")).toMatch(/min-h-11/);
  });

  it("the Matches and Home sources never write, and the Matches page never requests the gameweek page or a forecast", () => {
    for (const file of FILES.slice(0, 5).filter((f) => !f.includes("Predict"))) {
      expect(read(file), file).not.toMatch(/method:\s*["']POST|\/api\/gameweek|\/api\/predict/);
    }
  });
});
