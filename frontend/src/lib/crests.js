// Licensed local crests, by manifest only (src/data/crests.json + src/assets/crests/). Nothing is fetched at run time and nothing is hotlinked.
import manifest from "../data/crests.json";
import { significantWords } from "./team.js";

// Every file in src/assets/crests/ (empty today), as { "../assets/crests/arsenal.svg": "/assets/arsenal-1a2b3c.svg" }.
const FILES = import.meta.glob("../assets/crests/*.{svg,png,webp}", { eager: true, query: "?url", import: "default" });

// Key of a team in the manifest: its significant words, lower-case and accent-free ("Arsenal FC" and "ARSENAL" -> "arsenal").
export const crestKey = (name) => significantWords(name).join(" ");

const REQUIRED = ["file", "licence", "source"];

// Entries that are complete and whose file exists; `problems` lists every entry that was rejected and why.
export function resolveManifest(man = manifest, files = FILES) {
  const byName = Object.fromEntries(Object.entries(files).map(([path, url]) => [path.split("/").pop(), url]));
  const crests = {};
  const problems = [];
  if (man?.schema !== 1) problems.push(`unsupported manifest schema: ${man?.schema}`);
  for (const [key, e] of Object.entries(man?.crests ?? {})) {
    const missing = REQUIRED.filter((f) => typeof e?.[f] !== "string" || !e[f].trim());
    if (missing.length) problems.push(`${key}: missing ${missing.join(", ")}`);
    else if (!byName[e.file]) problems.push(`${key}: file ${e.file} is not in src/assets/crests/`);
    else if (crestKey(key) !== key) problems.push(`${key}: the key must be written as "${crestKey(key)}" (lower-case, no accents or punctuation, no club prefixes)`);
    else crests[key] = { url: byName[e.file], licence: e.licence, source: e.source, attribution: e.attribution ?? null };
  }
  return { crests, problems };
}

const RESOLVED = resolveManifest();

export function crestFor(name, resolved = RESOLVED) {
  return resolved.crests[crestKey(name)] ?? null;
}

// Text a licence asks to be shown with the crests that are actually in use.
export function crestAttributions(resolved = RESOLVED) {
  return [...new Set(Object.values(resolved.crests).map((c) => c.attribution).filter(Boolean))];
}

export const crestProblems = RESOLVED.problems;
