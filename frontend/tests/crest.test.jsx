import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import TeamCrest from "../src/components/TeamCrest.jsx";
import { TeamAvatar } from "../src/components/ui.jsx";
import { contrastRatio, hslToRgb } from "../src/lib/contrast.js";
import manifest from "../src/data/crests.json";
import { crestAttributions, crestFor, crestKey, crestProblems, resolveManifest } from "../src/lib/crests.js";
import { CREST_HUES, CREST_STYLE, crestColors, crestHue, initials, significantWords } from "../src/lib/team.js";

afterEach(() => vi.unstubAllGlobals());

describe("initials", () => {
  // [name, three-letter code, two-letter code]
  const CASES = [
    ["Arsenal", "ARS", "AR"],
    ["Arsenal FC", "ARS", "AR"],
    ["Manchester City", "MCI", "MC"],
    ["Manchester United FC", "MUN", "MU"],
    ["Real Madrid", "RMA", "RM"],
    ["Atlético Madrid", "AMA", "AM"],
    ["Paris Saint-Germain", "PSG", "PS"],
    ["Brighton & Hove Albion", "BHA", "BH"],
    ["West Ham United", "WHU", "WH"],
    ["AS Roma", "ROM", "RO"],
    ["RC Celta de Vigo", "CVI", "CV"],
    ["Côte d'Ivoire", "CIV", "CI"],
    ["Borussia Mönchengladbach", "BMO", "BM"],
    ["FC St. Pauli", "SPA", "SP"],
    // names that produced "1K", "B0", "P0", "1M" and similar before: digits and punctuation never reach the badge
    ["1. FC Köln", "KOL", "KO"],
    ["1. FSV Mainz 05", "MAI", "MA"],
    ["Bayer 04 Leverkusen", "BLE", "BL"],
    ["TSG 1899 Hoffenheim", "HOF", "HO"],
    ["Paderborn 07", "PAD", "PA"],
    ["Hannover 96", "HAN", "HA"],
    ["TSV 1860 München", "MUN", "MU"],
    ["1. FC Union Berlin", "UBE", "UB"],
    ["VfB Stuttgart", "STU", "ST"],
  ];
  it.each(CASES)("%s -> %s (%s in small badges)", (name, three, two) => {
    expect(initials(name)).toBe(three);
    expect(initials(name, 3)).toBe(three);
    expect(initials(name, 2)).toBe(two);
  });

  it("is always letters only, upper case, and the length that was asked for", () => {
    for (const [name] of CASES) {
      expect(initials(name)).toMatch(/^\p{Lu}{3}$/u);
      expect(initials(name, 2)).toMatch(/^\p{Lu}{2}$/u);
    }
  });

  it("does not depend on accents, case, club prefixes or punctuation", () => {
    expect(initials("Atletico Madrid")).toBe(initials("Atlético Madrid"));
    expect(initials("ARSENAL")).toBe(initials("arsenal fc"));
    expect(initials("FC Arsenal")).toBe(initials("Arsenal"));
    expect(initials("Brighton and Hove Albion")).toBe(initials("Brighton & Hove Albion"));
    expect(significantWords("1. FC Köln")).toEqual(["koln"]);
  });

  it("copes with empty and symbol-only input", () => {
    expect(initials("")).toBe("?");
    expect(initials()).toBe("?");
    expect(initials(null)).toBe("?");
    expect(initials("1.")).toBe("?");
    expect(initials("FC")).toBe("FC"); // only a prefix: use it rather than show nothing
  });
});

describe("generated colours", () => {
  it("are the same for every way of writing the team and never change between calls", () => {
    expect(crestColors("Arsenal")).toEqual(crestColors("Arsenal FC"));
    expect(crestColors("Arsenal")).toEqual(crestColors("ARSENAL"));
    expect(crestColors("Atlético Madrid")).toEqual(crestColors("Atletico Madrid"));
    expect(crestHue("Chelsea")).toBe(crestHue("Chelsea"));
    expect(crestHue("1. FC Köln")).toBe(crestHue("Köln"));
  });

  it("use 24 evenly spaced hues and spread teams across them", () => {
    const names = ["Arsenal", "Chelsea", "Liverpool", "Everton", "Fulham", "Brentford", "Burnley", "Leeds United", "Sunderland", "Wolverhampton Wanderers", "Real Madrid", "Barcelona", "Sevilla", "Valencia", "Villarreal", "Getafe", "Osasuna", "Girona", "Mallorca", "Alaves", "Bayern Munich", "Dortmund", "Leverkusen", "Freiburg", "Mainz", "Augsburg", "Bochum", "Hamburg", "Juventus", "Napoli", "Lazio", "Torino"];
    const hues = new Set(names.map(crestHue));
    for (const h of hues) expect((h * CREST_HUES) % 360).toBe(0);
    expect(hues.size).toBeGreaterThan(12);
  });

  it("give every one of the 24 hues at least 4.5:1 between the letters and the badge", () => {
    for (let i = 0; i < CREST_HUES; i += 1) {
      const h = i * (360 / CREST_HUES);
      const bg = hslToRgb(h, CREST_STYLE.background.s, CREST_STYLE.background.l);
      const fg = hslToRgb(h, CREST_STYLE.text.s, CREST_STYLE.text.l);
      expect(contrastRatio(fg, bg), `hue ${h}`).toBeGreaterThanOrEqual(4.5);
    }
  });
});

describe("TeamCrest", () => {
  it("draws a generated badge: letters only, hidden from assistive technology because the name is written next to it", () => {
    const { container } = render(<TeamCrest name="1. FC Köln" size={48} />);
    const badge = container.querySelector("[data-crest]");
    expect(badge).toHaveAttribute("data-crest", "generated");
    expect(badge).toHaveAttribute("aria-hidden", "true");
    expect(badge).toHaveTextContent("KOL");
    expect(badge.style.width).toBe("48px");
    expect(badge.style.background).toMatch(/hsl|rgb/);
  });

  it("uses two letters in small badges and three in larger ones", () => {
    const { container, rerender } = render(<TeamCrest name="Manchester City" size={24} />);
    expect(container.querySelector("[data-crest]")).toHaveTextContent(/^MC$/);
    rerender(<TeamCrest name="Manchester City" size={34} />);
    expect(container.querySelector("[data-crest]")).toHaveTextContent(/^MCI$/);
  });

  it("can stand alone as a named image when the team name is not written beside it", () => {
    render(<TeamCrest name="Arsenal" decorative={false} />);
    expect(screen.getByRole("img", { name: "Arsenal badge" })).toBeInTheDocument();
  });

  it("TeamAvatar (the name older screens use) is the same component", () => {
    const { container } = render(<TeamAvatar name="Chelsea" size={30} />);
    expect(container.querySelector("[data-crest]")).toHaveTextContent("CHE");
  });

  it("shows a licensed crest only when it is given, as a decorative image, and falls back to the generated badge if the file fails to load", () => {
    const { container } = render(<TeamCrest name="Arsenal" crest={{ url: "/crests/arsenal.svg", licence: "test licence", source: "test supplier" }} />);
    const licensed = container.querySelector("[data-crest]");
    expect(licensed).toHaveAttribute("data-crest", "licensed");
    const img = licensed.querySelector("img");
    expect(img).toHaveAttribute("src", "/crests/arsenal.svg");
    expect(img).toHaveAttribute("alt", "");
    fireEvent.error(img);
    expect(container.querySelector("[data-crest]")).toHaveAttribute("data-crest", "generated");
  });

  it("never requests anything from the network", () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const { container } = render(
      <>
        <TeamCrest name="Arsenal" />
        <TeamCrest name="Bayern Munich" size={40} />
      </>,
    );
    expect(container.querySelectorAll("img")).toHaveLength(0); // the shipped manifest is empty: no image is bundled
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe("licensed crest manifest", () => {
  const files = { "../assets/crests/arsenal.svg": "/assets/arsenal-abc123.svg" };
  const good = { file: "arsenal.svg", licence: "Licence held by the project", source: "Supplier name", attribution: "Crests: supplier" };

  it("ships empty: no crest image is bundled, downloaded or hotlinked", () => {
    expect(manifest.schema).toBe(1);
    expect(manifest.crests).toEqual({});
    expect(crestProblems).toEqual([]);
    expect(crestFor("Arsenal")).toBeNull();
    expect(crestAttributions()).toEqual([]);
  });

  it("accepts an entry that names its file, licence and source, and finds it however the team is written", () => {
    const resolved = resolveManifest({ schema: 1, crests: { arsenal: good } }, files);
    expect(resolved.problems).toEqual([]);
    expect(crestFor("Arsenal FC", resolved)).toMatchObject({ url: "/assets/arsenal-abc123.svg", licence: "Licence held by the project", source: "Supplier name" });
    expect(crestFor("ARSENAL", resolved)).not.toBeNull();
    expect(crestFor("Chelsea", resolved)).toBeNull();
    expect(crestAttributions(resolved)).toEqual(["Crests: supplier"]);
  });

  it.each([
    ["licence", { file: "arsenal.svg", source: "Supplier name" }],
    ["source", { file: "arsenal.svg", licence: "Licence held by the project" }],
    ["file", { licence: "Licence held by the project", source: "Supplier name" }],
  ])("ignores an entry without its %s", (missing, entry) => {
    const resolved = resolveManifest({ schema: 1, crests: { arsenal: entry } }, files);
    expect(resolved.crests).toEqual({});
    expect(resolved.problems[0]).toContain(`missing ${missing}`);
  });

  it("ignores an entry whose licence is blank, whose file is not in src/assets/crests, or whose key is not in canonical form", () => {
    expect(resolveManifest({ schema: 1, crests: { arsenal: { ...good, licence: "  " } } }, files).crests).toEqual({});
    const missingFile = resolveManifest({ schema: 1, crests: { arsenal: { ...good, file: "nope.svg" } } }, files);
    expect(missingFile.crests).toEqual({});
    expect(missingFile.problems[0]).toContain("not in src/assets/crests");
    const badKey = resolveManifest({ schema: 1, crests: { "Atlético FC": good } }, files);
    expect(badKey.crests).toEqual({});
    expect(badKey.problems[0]).toContain('must be written as "atletico"');
  });

  it("rejects an unknown manifest version", () => {
    expect(resolveManifest({ schema: 2, crests: {} }, files).problems[0]).toContain("unsupported manifest schema");
  });

  it("keys teams the way the badge generator reads them", () => {
    expect(crestKey("1. FC Köln")).toBe("koln");
    expect(crestKey("Brighton & Hove Albion")).toBe("brighton hove albion");
  });
});
