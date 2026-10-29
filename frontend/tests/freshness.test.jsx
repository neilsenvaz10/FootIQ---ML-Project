import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import CompetitionFreshness, { FreshnessTable } from "../src/components/CompetitionFreshness.jsx";

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const rec = (over) => ({ key: "BUNDESLIGA", name: "Bundesliga", group: "Domestic league", latest_result: "2026-10-25", days_since_latest_result: 3, data_status: "startup_updated", data_status_label: "Updated when FootIQ starts",
  update_note: "Refreshed once each time FootIQ starts from openligadb; not a live feed.", last_successful_refresh_utc: "2026-10-28T01:52:38Z", sync_mode: "startup", has_warnings: false, warnings: [], ...over });
const DATA = [
  rec(),
  rec({ key: "UNL", name: "UEFA Nations League", group: "International", latest_result: "2025-06-08", days_since_latest_result: 507, data_status: "historical_only", data_status_label: "Historical only: no automatic updates",
    update_note: "No update source is approved for this competition; the data is a saved snapshot.", last_successful_refresh_utc: null, sync_mode: null, has_warnings: true,
    warnings: [{ level: "warning", text: "No matches of the 2026-27 edition are in the data." }, { level: "info", text: "Team ratings used for predictions end on 2026-06-02." }] }),
  rec({ key: "WC", name: "FIFA World Cup", group: "International", latest_result: "2026-07-18", days_since_latest_result: 102, data_status: "historical_only", data_status_label: "Historical only: no automatic updates",
    update_note: "No update source is approved for this competition; the data is a saved snapshot.", last_successful_refresh_utc: null, sync_mode: null, has_warnings: true,
    warnings: [{ level: "warning", text: "2026: 103 of 104 matches are in the data (the final is not among them)." }] }),
];
afterEach(() => vi.unstubAllGlobals());

describe("competition data freshness", () => {
  it("shows an updated-at-start competition with its latest result and last successful refresh", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(DATA)));
    render(<CompetitionFreshness compKey="BUNDESLIGA" />);
    const box = await screen.findByRole("group", { name: /Data freshness: Bundesliga/ });
    expect(box).toHaveTextContent("Updated when FootIQ starts");
    expect(box).toHaveTextContent("Latest result: 2026-10-25 (3 days ago)");
    expect(box).toHaveTextContent("Last successful refresh: 2026-10-28 01:52:38 UTC");
    expect(box).not.toHaveTextContent("Missing coverage");
  });

  it("labels a historical-only competition as historical, with no refresh time and the missing-coverage warning", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(DATA)));
    render(<CompetitionFreshness compKey="UNL" />);
    const box = await screen.findByRole("group", { name: /Data freshness: UEFA Nations League/ });
    expect(box).toHaveTextContent("Historical only: no automatic updates");
    expect(box).toHaveTextContent("Latest result: 2025-06-08 (507 days ago)");
    expect(box).not.toHaveTextContent("Last successful refresh");
    expect(box).toHaveTextContent("Missing coverage: No matches of the 2026-27 edition are in the data.");
    expect(box).toHaveTextContent("Team ratings used for predictions end on 2026-06-02.");
  });

  it("never calls any competition live, and shows the World Cup's missing final", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(DATA)));
    const { container } = render(<FreshnessTable />);
    await screen.findByText(/Every competition/);
    expect(container.textContent).toMatch(/103 of 104 matches are in the data \(the final is not among them\)/);
    expect(container.textContent.replace(/not a live feed/g, "")).not.toMatch(/\blive\b/i);
    expect(container.querySelectorAll("[data-competition]").length).toBe(3);
  });

  it("renders nothing when the backend does not answer, so a page never breaks because of it", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json({ detail: "down" }, 503)));
    const { container } = render(<CompetitionFreshness compKey="BUNDESLIGA" />);
    await new Promise((r) => setTimeout(r, 50));
    expect(container).toBeEmptyDOMElement();
  });
});
