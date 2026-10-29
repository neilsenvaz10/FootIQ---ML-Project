import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";
import { Badge, Button, ButtonLink, Card, Chip, Empty, ErrorBox, Field, Icon, Input, Kpi, Notice, Pills, Select, Spinner, StatCard, TabPanel, Tabs, TeamCrest } from "../components/ui.jsx";
import { ICON_NAMES } from "../components/Icon.jsx";
import { contrastRatio, hexToRgb } from "../lib/contrast.js";
import { initials } from "../lib/team.js";

// Development-only sheet (route /design, absent from the production build): the tokens and shared components exactly as the app uses them.
// It contains no football data. The club names below are only inputs to the badge generator.

const GROUPS = {
  Surfaces: ["bg", "sidebar", "panel", "panel-2", "panel-3"],
  Text: ["ink", "ink-2", "mute", "mute-2"],
  Brand: ["accent", "accent-strong", "primary", "primary-hi", "primary-lo"],
  Status: ["ok", "warn", "bad", "info"],
  Outcomes: ["home", "draw", "away"],
  Borders: ["line", "line-strong"],
};
const CLUBS = ["Arsenal", "Manchester City", "Real Madrid", "1. FC Köln", "Bayer 04 Leverkusen", "Paris Saint-Germain", "Brighton & Hove Albion", "1. FSV Mainz 05"];

function useTokenValues() {
  const [values, setValues] = useState({});
  useEffect(() => {
    const style = getComputedStyle(document.documentElement);
    const out = {};
    for (const names of Object.values(GROUPS)) for (const n of names) out[n] = style.getPropertyValue(`--color-${n}`).trim();
    setValues(out);
  }, []);
  return values;
}

// Text tokens and the accent are judged as text on the panel surface; the solid primary fills as the background of white button text.
function Swatch({ name, value, panel }) {
  const asFill = name.startsWith("primary");
  const asText = ["ink", "ink-2", "mute", "mute-2", "accent", "accent-strong", "ok", "warn", "bad", "info"].includes(name);
  let note = "";
  if (value && panel && asText) note = ` · ${contrastRatio(hexToRgb(value), hexToRgb(panel)).toFixed(1)}:1 on panel`;
  if (value && asFill) note = ` · white text ${contrastRatio(hexToRgb(value), [255, 255, 255]).toFixed(1)}:1`;
  if (value && panel && name === "line-strong") note = ` · ${contrastRatio(hexToRgb(value), hexToRgb(panel)).toFixed(1)}:1 on panel`;
  return (
    <div className="min-w-0">
      <div className="h-14 rounded-xl border border-line-strong" style={{ background: `var(--color-${name})` }} />
      <p className="mt-1.5 truncate text-xs font-semibold text-ink">{name}</p>
      <p className="text-xs tabular-nums text-mute">
        {value || "…"}
        {note}
      </p>
    </div>
  );
}

// /design?only=<id> shows one section on its own (used to capture screenshots that fit one screen).
function Section({ id, title, children }) {
  const [params] = useSearchParams();
  const only = params.get("only");
  if (only && only !== id) return null;
  return (
    <section id={id} className="mb-8">
      <h2 className="mb-3 text-lg font-bold">{title}</h2>
      {children}
    </section>
  );
}

export default function DesignSystem() {
  const tokens = useTokenValues();
  const [pill, setPill] = useState("a");
  const [tab, setTab] = useState("one");
  const [size, setSize] = useState("32");
  return (
    <div>
      <PageHeader title="Design system">Tokens and shared components of the redesign (development only; not in the production build). No football data appears on this page.</PageHeader>

      <Section id="tokens" title="Colour tokens">
        {Object.entries(GROUPS).map(([group, names]) => (
          <div key={group} className="mb-5">
            <h3 className="mb-2 text-sm font-semibold text-mute">{group}</h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {names.map((n) => (
                <Swatch key={n} name={n} value={tokens[n]} panel={tokens.panel} />
              ))}
            </div>
          </div>
        ))}
      </Section>

      <Section id="type" title="Type (Inter, self-hosted)">
        <Card>
          <p className="text-[1.75rem] font-extrabold leading-tight tracking-tight sm:text-3xl">Page title, 28 to 30 px</p>
          <p className="mt-3 text-lg font-bold">Section title, 18 px</p>
          <p className="mt-3 text-base font-bold">Card title, 16 px</p>
          <p className="mt-3 text-sm text-ink-2">Body text, 14 px. Probabilities and counts use tabular figures: 0.1 1.1 2.2 3.3 4.4 5.5 6.6 7.7 8.8 9.9.</p>
          <p className="mt-3 text-xs text-mute">Small text, 12 px: the smallest size used in the app.</p>
          <p className="mt-3 text-2xl font-extrabold tabular-nums">12,345.6</p>
        </Card>
      </Section>

      <Section id="buttons" title="Buttons">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button disabled>Disabled</Button>
          <ButtonLink to="/">Link button</ButtonLink>
        </div>
        <p className="mt-2 text-xs text-mute">Every button is at least 44 px tall. Tab to see the focus ring.</p>
      </Section>

      <Section id="controls" title="Controls, filters and tabs">
        <Card>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Text input" hint="Hint text, 12 px">
              <Input placeholder="Placeholder" />
            </Field>
            <Field label="Select">
              <Select value="b" onChange={() => {}} options={[{ value: "a", label: "First option" }, { value: "b", label: "Second option" }]} />
            </Field>
          </div>
          <div className="mt-5">
            <Pills label="Example filter" value={pill} onChange={setPill} options={[{ value: "a", label: "All" }, { value: "b", label: "Finished" }, { value: "c", label: "Scheduled" }]} />
          </div>
          <div className="mt-5">
            <Tabs idBase="ds" label="Example tabs" value={tab} onChange={setTab} tabs={[{ value: "one", label: "First" }, { value: "two", label: "Second" }, { value: "three", label: "Third" }]} />
            <TabPanel idBase="ds" value={tab} className="pt-3 text-sm text-mute">
              Panel for the {tab} tab. Arrow keys move between tabs; Enter or Space opens one.
            </TabPanel>
          </div>
        </Card>
      </Section>

      <Section id="states" title="Badges, chips, notices and states">
        <div className="flex flex-wrap gap-2">
          <Badge badge="Validated" />
          <Badge badge="Partially validated" />
          <Badge badge="Not validated" />
          <Chip>Neutral</Chip>
          <Chip tone="info">Info</Chip>
          <Chip tone="ok">Ok</Chip>
          <Chip tone="warn">Warning</Chip>
          <Chip tone="bad">Problem</Chip>
        </div>
        <div className="mt-4 grid gap-3">
          <Notice tone="info" title="Info.">Neutral information, for example how a figure is computed.</Notice>
          <Notice tone="ok" title="Done.">Something worked.</Notice>
          <Notice tone="warn" title="Careful.">Data is stale or a result is provisional.</Notice>
          <Notice tone="bad" title="Problem.">Something failed or is not validated.</Notice>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Spinner label="Loading…" />
          <Empty>Nothing to show.</Empty>
          <ErrorBox error={new Error("Example error message")} onRetry={() => {}} />
        </div>
      </Section>

      <Section id="cards" title="Cards and numbers">
        <div className="grid gap-3 sm:grid-cols-3">
          <Kpi label="Kpi label" value="12.3%" hint="Hint" />
          <StatCard label="Stat card" value="4,567" />
          <Card title="Card title" subtitle="Card subtitle">
            <p className="text-sm text-mute">Card body.</p>
          </Card>
        </div>
      </Section>

      <Section id="badges" title="Team badges (generated; a licensed crest replaces one only via src/data/crests.json)">
        <Card>
          <Pills label="Badge size" value={size} onChange={setSize} options={["20", "24", "32", "48", "72"]} />
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {CLUBS.map((c) => (
              <li key={c} className="flex items-center gap-3">
                <TeamCrest name={c} size={Number(size)} />
                <span className="text-sm">
                  {c} <span className="text-mute">→ {initials(c)} / {initials(c, 2)}</span>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </Section>

      <Section id="icons" title="Icons">
        <div className="flex flex-wrap gap-4">
          {ICON_NAMES.map((n) => (
            <div key={n} className="flex w-16 flex-col items-center gap-1 text-xs text-mute">
              <Icon name={n} className="h-6 w-6 text-ink" />
              {n}
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
