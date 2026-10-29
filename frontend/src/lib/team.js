// Decorative helpers only: no football data is created here.

// Club-form prefixes and particles that carry no identity ("1. FC Köln" is Köln, "AS Roma" is Roma, "Celta de Vigo" is Celta Vigo).
const NOISE = new Set(["fc", "cf", "afc", "ac", "sc", "sv", "as", "us", "rc", "cd", "ud", "ss", "ssc", "bv", "vfb", "vfl", "fsv", "tsg", "tsv", "rcd", "sd", "fk", "sk", "nk", "kv", "krc", "ogc", "hsc", "ssv"]);
const PARTICLES = new Set(["de", "del", "della", "di", "da", "do", "dos", "das", "du", "des", "la", "le", "les", "los", "las", "el", "al", "von", "van", "der", "den", "ten", "ter", "of", "the", "and", "e", "y", "d", "l"]);

// Lower-case, accent-free words of a name; punctuation and symbols (".", "&", apostrophes) never survive.
function words(name) {
  return String(name ?? "")
    .normalize("NFD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .filter(Boolean);
}

const letters = (w) => Array.from(w).filter((ch) => /\p{L}/u.test(ch));

// The words that identify the team: no club prefixes, no particles, no purely numeric words ("05", "1860", "96").
export function significantWords(name) {
  const all = words(name);
  const kept = all.filter((w) => !NOISE.has(w) && !PARTICLES.has(w) && letters(w).length > 0);
  return kept.length ? kept : all.filter((w) => letters(w).length > 0);
}

// Three-letter code, always letters (never digits or punctuation), always upper case:
//   one word -> its first three letters (Arsenal -> ARS); two words -> first letter + first two letters of the second (Manchester City -> MCI);
//   three or more -> the first letters of the first three (Paris Saint-Germain -> PSG).
// `length` 2 gives the compact form used in small circles (MC, ARS -> AR).
export function initials(name = "", length = 3) {
  const ws = significantWords(name);
  if (!ws.length) return "?";
  let code;
  if (length <= 2) code = ws.length >= 2 ? letters(ws[0])[0] + letters(ws[1])[0] : letters(ws[0]).slice(0, 2).join("");
  else if (ws.length >= 3) code = ws.slice(0, 3).map((w) => letters(w)[0]).join("");
  else if (ws.length === 2) code = letters(ws[0])[0] + letters(ws[1]).slice(0, 2).join("");
  else code = letters(ws[0]).slice(0, 3).join("");
  return code.toUpperCase().slice(0, length);
}

// Deterministic fallback colours: the same team always gets the same colour, written in any form ("Arsenal", "Arsenal FC", "ARSENAL").
// 24 evenly spaced hues at fixed saturation and lightness; tests/crest.test.jsx checks every one for 4.5:1 text contrast.
export const CREST_HUES = 24;
export const CREST_STYLE = { background: { s: 42, l: 26 }, text: { s: 90, l: 90 } }; // saturation and lightness in percent

export function fnv1a(text) {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

export function crestHue(name = "") {
  return (fnv1a(significantWords(name).join(" ")) % CREST_HUES) * (360 / CREST_HUES);
}

export function crestColors(name = "") {
  const h = crestHue(name);
  const { background: bg, text } = CREST_STYLE;
  return { hue: h, background: `hsl(${h}, ${bg.s}%, ${bg.l}%)`, color: `hsl(${h}, ${text.s}%, ${text.l}%)` };
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function shortDate(iso = "") {
  const [y, m, d] = iso.split("-");
  if (!y || !m || !d) return { day: iso, year: "" };
  return { day: `${Number(d)} ${MONTHS[Number(m) - 1]}`, year: y };
}
