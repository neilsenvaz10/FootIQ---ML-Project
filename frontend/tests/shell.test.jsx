import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import App from "../src/App.jsx";
import Layout from "../src/components/Layout.jsx";
import { MetaProvider } from "../src/components/MetaContext.jsx";
import { Button, DataTable, Pills, TabPanel, Tabs } from "../src/components/ui.jsx";
import { MORE, NAV, PRIMARY, documentTitle, isActive, pageTitle } from "../src/lib/nav.js";

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const META = { attribution: [], data_through: { club_results: "2026-10-24", international_ratings: "2026-06-02" }, limitations: [] };

beforeEach(() => {
  window.scrollTo = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn((url) => {
      const u = new URL(url);
      if (u.pathname === "/api/meta") return json(META);
      if (u.pathname === "/api/sync/status") return json({ detail: "store not built" }, 503);
      if (u.pathname === "/api/health") return json({ status: "ok", club_prediction_ready: true });
      return json({ detail: `unmocked ${u.pathname}` }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const Echo = () => <p data-testid="page">page at {useLocation().pathname}</p>;
const Probe = () => {
  const l = useLocation();
  return <output data-testid="where">{l.pathname + l.search}</output>;
};

// The real shell (sidebar, top bar, bottom bar, skip link) around a trivial page, so these tests stay fast and exact.
const shell = (route = "/") =>
  render(
    <MemoryRouter initialEntries={[route]}>
      <MetaProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="*" element={<Echo />} />
          </Route>
        </Routes>
      </MetaProvider>
    </MemoryRouter>,
  );

const sidebar = () => within(screen.getByRole("navigation", { name: "Main" }));
const bottomBar = () => within(screen.getByRole("navigation", { name: "Main mobile" }));

describe("navigation model", () => {
  it("has seven destinations: Predict is now Predictions, five are primary and two sit behind More", () => {
    expect(NAV.map((n) => n.label)).toEqual(["Home", "Matches", "Leagues", "Compare", "Predictions", "Simulations", "Models"]);
    expect(PRIMARY.map((n) => n.label)).toEqual(["Home", "Matches", "Leagues", "Predictions", "Simulations"]);
    expect(MORE.map((n) => n.label)).toEqual(["Compare", "Models"]);
    expect(PRIMARY.length + MORE.length).toBe(NAV.length);
  });

  it("keeps every existing address", () => {
    const byLabel = Object.fromEntries(NAV.map((n) => [n.label, n.to]));
    expect(byLabel).toMatchObject({ Home: "/", Leagues: "/analytics", Compare: "/compare", Predictions: "/predict", Simulations: "/simulations", Models: "/models", Matches: "/matches" });
    expect(isActive(NAV.find((n) => n.label === "Predictions"), "/predictions")).toBe(true); // renamed address
    expect(isActive(NAV.find((n) => n.label === "Simulations"), "/worldcup")).toBe(false); // the World Cup left the scope: its old address is gone
  });

  it("marks only the current destination, including sub-paths and a trailing slash", () => {
    const active = (path) => NAV.filter((n) => isActive(n, path)).map((n) => n.label);
    expect(active("/")).toEqual(["Home"]);
    expect(active("/analytics")).toEqual(["Leagues"]);
    expect(active("/analytics/")).toEqual(["Leagues"]);
    expect(active("/predict")).toEqual(["Predictions"]);
    expect(active("/worldcup")).toEqual([]);
    expect(active("/nowhere")).toEqual([]);
  });

  it("titles every page and the unknown page", () => {
    expect(pageTitle("/predict")).toBe("Predictions");
    expect(documentTitle("/worldcup")).toBe("Page not found · FootIQ");
    expect(documentTitle("/nowhere")).toBe("Page not found · FootIQ");
  });
});

describe("sidebar (tablet and desktop)", () => {
  it("lists all seven destinations with their addresses and marks the current page", () => {
    shell("/models");
    const links = sidebar().getAllByRole("link");
    expect(links.map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      ["Home", "/"],
      ["Matches", "/matches"],
      ["Leagues", "/analytics"],
      ["Compare", "/compare"],
      ["Predictions", "/predict"],
      ["Simulations", "/simulations"],
      ["Models", "/models"],
    ]);
    expect(links.filter((a) => a.getAttribute("aria-current") === "page").map((a) => a.textContent)).toEqual(["Models"]);
    expect(sidebar().queryByRole("link", { name: "Predict" })).toBeNull();
  });

  it("highlights Simulations on /simulations", () => {
    shell("/simulations");
    expect(sidebar().getByRole("link", { name: "Simulations" })).toHaveAttribute("aria-current", "page");
  });
});

describe("bottom bar and the More menu (phones)", () => {
  it("shows five primary links and a More button; More opens the other two destinations", async () => {
    const user = userEvent.setup();
    shell("/");
    expect(bottomBar().getAllByRole("link").map((a) => a.textContent)).toEqual(["Home", "Matches", "Leagues", "Predictions", "Simulations"]);
    const more = bottomBar().getByRole("button", { name: "More" });
    expect(more).toHaveAttribute("aria-expanded", "false");
    await user.click(more);
    const dialog = screen.getByRole("dialog", { name: "More" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(more).toHaveAttribute("aria-expanded", "true");
    expect(within(dialog).getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      ["Compare", "/compare"],
      ["Models", "/models"],
    ]);
  });

  it("makes all seven destinations reachable on a phone (bar plus More)", async () => {
    const user = userEvent.setup();
    shell("/");
    await user.click(bottomBar().getByRole("button", { name: "More" }));
    const reachable = [...bottomBar().getAllByRole("link"), ...within(screen.getByRole("dialog")).getAllByRole("link")].map((a) => a.getAttribute("href"));
    expect(reachable.sort()).toEqual(NAV.map((n) => n.to).sort());
  });

  it("highlights More while a destination inside it is the current page", () => {
    shell("/compare");
    expect(bottomBar().getByRole("button", { name: "More" }).className).toContain("text-accent");
  });

  it("closes with Escape and gives focus back to the More button", async () => {
    const user = userEvent.setup();
    shell("/");
    const more = bottomBar().getByRole("button", { name: "More" });
    await user.click(more);
    expect(within(screen.getByRole("dialog")).getByRole("button", { name: "Close menu" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(more).toHaveFocus();
    expect(document.body.classList.contains("overflow-hidden")).toBe(false);
  });

  it("keeps Tab inside the open sheet, in both directions", async () => {
    const user = userEvent.setup();
    shell("/");
    await user.click(bottomBar().getByRole("button", { name: "More" }));
    const dialog = within(screen.getByRole("dialog"));
    const close = dialog.getByRole("button", { name: "Close menu" });
    const compare = dialog.getByRole("link", { name: /Compare/ });
    const models = dialog.getByRole("link", { name: /Models/ });
    expect(close).toHaveFocus();
    await user.tab();
    expect(compare).toHaveFocus();
    await user.tab();
    expect(models).toHaveFocus();
    await user.tab(); // past the last control: back to the first
    expect(close).toHaveFocus();
    await user.tab({ shift: true }); // before the first control: on to the last
    expect(models).toHaveFocus();
  });

  it("closes when a destination is chosen and shows that page", async () => {
    const user = userEvent.setup();
    shell("/");
    await user.click(bottomBar().getByRole("button", { name: "More" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("link", { name: /Compare/ }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByTestId("page")).toHaveTextContent("page at /compare");
  });

  it("also closes from the close button and from the backdrop", async () => {
    const user = userEvent.setup();
    shell("/");
    const more = bottomBar().getByRole("button", { name: "More" });
    await user.click(more);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Close menu" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    await user.click(more);
    await user.click(screen.getByRole("dialog").previousSibling); // the backdrop
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("page titles, skip link and focus", () => {
  it.each([
    ["/", "Home"],
    ["/matches", "Matches"],
    ["/analytics", "Leagues"],
    ["/compare", "Compare"],
    ["/predict", "Predictions"],
    ["/predictions", "Predictions"],
    ["/worldcup", "Page not found"],
    ["/simulations", "Simulations"],
    ["/models", "Models"],
    ["/nowhere", "Page not found"],
  ])("%s has the document title '%s · FootIQ'", (route, name) => {
    shell(route);
    expect(document.title).toBe(`${name} · FootIQ`);
  });

  it("offers 'Skip to main content' as the very first Tab stop, and it focuses the page area", async () => {
    const user = userEvent.setup();
    shell("/");
    await user.tab();
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip).toHaveFocus();
    await user.keyboard("{Enter}");
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main");
    expect(main).toHaveFocus();
  });

  it("changes the title, announces the page, scrolls to the top and moves focus to the page area after a navigation", async () => {
    const user = userEvent.setup();
    shell("/");
    expect(screen.getByRole("status").textContent).toBe(""); // nothing is announced for the first page
    await user.click(sidebar().getByRole("link", { name: "Leagues" }));
    expect(document.title).toBe("Leagues · FootIQ");
    expect(screen.getByRole("status")).toHaveTextContent("Leagues");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(screen.getByRole("main")).toHaveFocus();
  });

  it("does not move focus on the first render", () => {
    shell("/models");
    expect(screen.getByRole("main")).not.toHaveFocus();
  });
});

describe("routes", () => {
  const LAZY = { timeout: 10000 }; // the first import of a route that pulls in Recharts takes over a second on a cold start
  // Every page is a lazy chunk. Importing them once here keeps the module start-up (several seconds the first time, while the test workers are busy)
  // out of the tests, which are about routing. It says nothing about how fast a page loads for a user; the build reports the real chunk sizes.
  beforeAll(async () => {
    await Promise.all([
      import("../src/pages/Overview.jsx"),
      import("../src/pages/Matches.jsx"),
      import("../src/pages/Analytics.jsx"),
      import("../src/pages/TeamComparison.jsx"),
      import("../src/pages/Predictions.jsx"),
      import("../src/pages/Simulations.jsx"),
      import("../src/pages/Models.jsx"),
      import("../src/pages/DesignSystem.jsx"),
    ]);
  }, 60000);
  const app = (route) =>
    render(
      <MemoryRouter initialEntries={[route]}>
        <App />
        <Probe />
      </MemoryRouter>,
    );

  it("redirects /predictions to /predict and keeps the query string of the link", async () => {
    app("/predictions?comp=EPL&mode=manual");
    await screen.findByRole("heading", { level: 1, name: "Predictions" }, LAZY);
    expect(screen.getByTestId("where")).toHaveTextContent("/predict?comp=EPL&mode=manual");
  });

  it("serves the season simulator on /simulations", async () => {
    app("/simulations");
    expect(await screen.findByRole("heading", { name: "Season simulator" }, LAZY)).toBeInTheDocument();
    expect(screen.getByTestId("where")).toHaveTextContent("/simulations");
  });

  it("links the Predictions tabs to their panel, which has its own name (so it does not repeat the 'Gameweek' control inside it)", async () => {
    app("/predict?mode=manual");
    const tab = await screen.findByRole("tab", { name: "Manual head-to-head" }, LAZY);
    const panel = screen.getByRole("tabpanel", { name: "Manual head-to-head prediction" });
    expect(tab).toHaveAttribute("aria-controls", panel.id);
  });

  it("has no World Cup tab: the Simulations page is the season simulator only", async () => {
    app("/simulations");
    await screen.findByRole("heading", { name: "Season simulator" }, LAZY);
    expect(screen.queryByRole("tab", { name: "World Cup" })).toBeNull();
  });

  it("Matches is the hub since P4.3: its filters are there, and with the backend refusing it shows the error and no match at all (never a placeholder one)", async () => {
    app("/matches");
    expect(await screen.findByRole("heading", { level: 1, name: "Matches" }, LAZY)).toBeInTheDocument();
    const page = screen.getByRole("main");
    expect(within(page).getByRole("radiogroup", { name: "League" })).toBeInTheDocument();
    expect(within(page).getByRole("radiogroup", { name: "Status" })).toBeInTheDocument();
    expect(await within(page).findByRole("alert")).toHaveTextContent("unmocked /api/matches");
    expect(within(page).queryAllByRole("article")).toHaveLength(0);
    expect(screen.queryByText("Not built yet.")).toBeNull();
  });

  it("an unknown address says so and offers the way home", async () => {
    app("/nowhere");
    expect(await screen.findByRole("heading", { level: 1, name: "Page not found" }, LAZY)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Home" })).toHaveAttribute("href", "/");
  });

  it("serves the design-system sheet in development builds (the production build leaves it out)", async () => {
    app("/design");
    expect(await screen.findByRole("heading", { level: 1, name: "Design system" }, LAZY)).toBeInTheDocument(); // tests run in development mode
  });
});

describe("keyboard use of tabs and filters", () => {
  const TABS = [
    { value: "one", label: "One" },
    { value: "two", label: "Two" },
    { value: "three", label: "Three" },
  ];
  function TabsHarness() {
    const [v, setV] = useState("one");
    return (
      <>
        <Tabs idBase="t" label="Demo" value={v} onChange={setV} tabs={TABS} />
        <TabPanel idBase="t" value={v}>
          panel {v}
        </TabPanel>
      </>
    );
  }

  it("tabs: only the selected tab is a Tab stop, arrow keys move focus, Enter activates", async () => {
    const user = userEvent.setup();
    render(<TabsHarness />);
    const [one, two, three] = ["One", "Two", "Three"].map((n) => screen.getByRole("tab", { name: n }));
    expect([one, two, three].map((t) => t.tabIndex)).toEqual([0, -1, -1]);
    await user.tab();
    expect(one).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(two).toHaveFocus();
    expect(one).toHaveAttribute("aria-selected", "true"); // moving focus does not load another panel
    await user.keyboard("{End}");
    expect(three).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(one).toHaveFocus(); // wraps
    await user.keyboard("{ArrowLeft}");
    expect(three).toHaveFocus();
    await user.keyboard("{Home}");
    expect(one).toHaveFocus();
    await user.keyboard("{ArrowRight}{Enter}");
    expect(two).toHaveAttribute("aria-selected", "true");
    expect([one, two, three].map((t) => t.tabIndex)).toEqual([-1, 0, -1]);
    expect(screen.getByRole("tabpanel")).toHaveTextContent("panel two");
  });

  it("tabs: each tab points at its panel and the panel names its tab", () => {
    render(<TabsHarness />);
    const tab = screen.getByRole("tab", { name: "One" });
    const panel = screen.getByRole("tabpanel");
    expect(tab).toHaveAttribute("aria-controls", "t-panel-one");
    expect(panel).toHaveAttribute("id", "t-panel-one");
    expect(panel).toHaveAttribute("aria-labelledby", tab.id);
  });

  it("tabs without idBase still get ids and no dangling aria-controls", () => {
    render(<Tabs label="Solo" value="a" onChange={() => {}} tabs={["a", "b"]} />);
    for (const t of screen.getAllByRole("tab")) {
      expect(t.id).toBeTruthy();
      expect(t).not.toHaveAttribute("aria-controls");
    }
  });

  function PillsHarness({ start = "a" }) {
    const [v, setV] = useState(start);
    return <Pills label="Demo" value={v} onChange={setV} options={["a", "b", "c"]} />;
  }

  it("filters: the checked pill is the only Tab stop; arrows select and focus, wrapping at the ends", async () => {
    const user = userEvent.setup();
    render(<PillsHarness />);
    const radios = screen.getAllByRole("radio");
    expect(radios.map((r) => r.tabIndex)).toEqual([0, -1, -1]);
    await user.tab();
    expect(radios[0]).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(radios[1]).toHaveFocus();
    expect(radios[1]).toHaveAttribute("aria-checked", "true");
    await user.keyboard("{End}");
    expect(radios[2]).toHaveAttribute("aria-checked", "true");
    await user.keyboard("{ArrowRight}");
    expect(radios[0]).toHaveFocus();
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
    await user.keyboard("{ArrowUp}");
    expect(radios[2]).toHaveAttribute("aria-checked", "true");
    expect(radios.map((r) => r.tabIndex)).toEqual([-1, -1, 0]);
  });

  it("filters: when nothing is selected the first pill is reachable", () => {
    render(<PillsHarness start="zzz" />);
    expect(screen.getAllByRole("radio").map((r) => r.tabIndex)).toEqual([0, -1, -1]);
  });
});

describe("other shared pieces", () => {
  it("DataTable tolerates two columns with the same header (no duplicate-key warning)", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <DataTable
        columns={[
          { header: "Model", key: "model" },
          { header: "Acc.", key: "a1", num: true },
          { header: "Acc.", key: "a2", num: true },
        ]}
        rows={[{ model: "m", a1: 1, a2: 2 }]}
      />,
    );
    expect(spy).not.toHaveBeenCalled();
    expect(screen.getAllByRole("columnheader", { name: "Acc." })).toHaveLength(2);
    spy.mockRestore();
  });

  it("buttons never submit a form by accident and are at least 44 px tall", () => {
    render(<Button>Go</Button>);
    const b = screen.getByRole("button", { name: "Go" });
    expect(b).toHaveAttribute("type", "button");
    expect(b.className).toContain("min-h-11");
  });
});
