import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SyncStatus from "../src/components/SyncStatus.jsx";

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, statusText: "x", json: () => Promise.resolve(body) });
const comp = (over) => ({ competition_key: "EPL", state: "stale", state_reasons: [], latest_result: "2026-10-12", awaiting_result: 15, scheduled: 305, approved_sources: [], last_successful_sync_utc: null,
  last_successful_external_check_utc: null, last_successful_import_utc: "2026-10-25T09:07:13Z", last_attempted_sync_utc: null, imported_records: 299, quarantined_records: 33,
  provider_readiness: "prepared_offline", feed_lag: { lagging: true, message: "Results lagging: newest verified result 2026-10-12 (15 days ago); 20 fixture(s) past their date have no verified result (oldest 2026-10-17)." }, history_note: "A successful source check does not make the history complete: the fixtures above are past their date and have no verified result in the store.", ...over });
const SCHED = { live_enabled: true, status: "backing off after 2 failed cycle(s); next check 2026-11-02T06:00:00Z", next_scheduled_check_utc: "2026-11-02T06:00:00Z", consecutive_failed_cycles: 2 };
const QUAR = { needs_operator_review: 57, warning: "57 unresolved sync finding(s) need a human decision (55 date disagreement, 1 score conflict, 1 contradictory record). Nothing is applied automatically." };
const status = (competitions, extra = {}) => ({ live_enabled: false, periodic_minutes: 360, note: "Data is historical.", attribution: [], competitions, ...extra });

beforeEach(() => vi.stubGlobal("fetch", vi.fn(() => json(status([comp(), comp({ competition_key: "SERIEA", provider_readiness: "blocked_no_provider", last_successful_import_utc: null, imported_records: 0, quarantined_records: 0 })])))));
afterEach(() => vi.unstubAllGlobals());

describe("honest freshness indicators", () => {
  it("never calls an offline import a source check", async () => {
    render(<SyncStatus />);
    expect((await screen.findByText(/Last successful source check:/)).parentElement).toHaveTextContent("none yet");
    expect(screen.getByText(/Sync:/).parentElement).toHaveTextContent("off (cached data only)");
  });

  it("shows source check, import, attempt, counts and provider status separately per league", async () => {
    render(<SyncStatus />);
    await userEvent.click(await screen.findByRole("button", { name: /details/i }));
    expect(screen.getByRole("columnheader", { name: "Last source check" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Last import" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Last attempt" })).toBeInTheDocument();
    expect(screen.getByText("299 / 33")).toBeInTheDocument();
    expect(screen.getByText("2026-10-25 09:07:13 UTC")).toBeInTheDocument();
    expect(screen.getByText("Saved snapshots only; no live source approved")).toBeInTheDocument();
    expect(screen.getByText("No approved provider")).toBeInTheDocument();
    expect(screen.getAllByText(/does not make the history complete/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Results lagging: newest verified result 2026-10-12 \(15 days ago\)/).length).toBeGreaterThan(0);
  });

  it("shows the scheduler state, failed cycles, next check, last-check summary and the quarantine warning", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(status([comp({ last_check_summary: "Source checked successfully at 2026-11-01T06:00:03Z: reachable, and it returned no new results (the stored history is unchanged)." })], { live_enabled: true, scheduler: SCHED, quarantine: QUAR }))));
    render(<SyncStatus />);
    expect(await screen.findByRole("alert")).toHaveTextContent("57 unresolved sync finding(s) need a human decision");
    expect(screen.getByText(/Scheduler:/).parentElement).toHaveTextContent("backing off after 2 failed cycle(s)");
    expect(screen.getByText(/Failed cycles in a row:/).parentElement).toHaveTextContent("2");
    await userEvent.click(screen.getByRole("button", { name: /details/i }));
    expect(screen.getByText(/Next scheduled check:/).parentElement).toHaveTextContent("2026-11-02 06:00:00 UTC");
    expect(screen.getByText(/Quarantined findings needing review:/).parentElement).toHaveTextContent("57");
    expect(screen.getByText(/returned no new results/)).toBeInTheDocument();
  });

  it("shows Bundesliga and La Liga with their own next check and failure state", async () => {
    const leagues = {
      BUNDESLIGA: { next_check_utc: "2026-11-02T06:00:00Z", consecutive_failed_cycles: 0 },
      LALIGA: { next_check_utc: "2026-11-02T12:00:00Z", consecutive_failed_cycles: 1 },
    };
    const live = { provider_readiness: "approved_live_enabled", approved_sources: ["openligadb"], state: "fresh", last_successful_external_check_utc: "2026-11-01T06:00:03Z", feed_lag: null, history_note: null };
    vi.stubGlobal("fetch", vi.fn(() => json(status([comp({ competition_key: "BUNDESLIGA", ...live }), comp({ competition_key: "LALIGA", ...live })], { live_enabled: true, scheduler: { ...SCHED, consecutive_failed_cycles: 1, leagues }, quarantine: QUAR }))));
    render(<SyncStatus />);
    await userEvent.click(await screen.findByRole("button", { name: /details/i }));
    const row = (name) => screen.getByText(name, { selector: "td" }).closest("tr");
    expect(row("BUNDESLIGA")).toHaveTextContent("2026-11-02 06:00:00 UTC");
    expect(row("BUNDESLIGA")).not.toHaveTextContent("failed cycle(s) in a row");
    expect(row("LALIGA")).toHaveTextContent("2026-11-02 12:00:00 UTC");
    expect(row("LALIGA")).toHaveTextContent("1 failed cycle(s) in a row, backing off");
  });

  it("in startup mode shows one refresh per launch, no schedule, the last attempt and the error", async () => {
    const leagues = {
      BUNDESLIGA: { next_check_utc: null, consecutive_failed_cycles: 0, last_error: null },
      LALIGA: { next_check_utc: null, consecutive_failed_cycles: 2, last_error: { at_utc: "2026-11-02T08:00:00Z", error: "SourceUnavailable: HTTP 503" } },
    };
    const live = { provider_readiness: "approved_live_enabled", approved_sources: ["openligadb"], state: "fresh", last_successful_external_check_utc: "2026-11-01T06:00:03Z", feed_lag: null, history_note: null };
    const sched = { live_enabled: true, status: "startup refresh finished at 2026-11-02T08:00:09Z: errors in LALIGA", next_scheduled_check_utc: null, consecutive_failed_cycles: 2, leagues };
    vi.stubGlobal("fetch", vi.fn(() => json(status([comp({ competition_key: "BUNDESLIGA", ...live }), comp({ competition_key: "LALIGA", ...live })], { live_enabled: true, sync_mode: "startup", scheduler: sched, quarantine: QUAR }))));
    render(<SyncStatus />);
    expect(await screen.findByText(/refreshes once each time FootIQ starts/)).toBeInTheDocument();
    expect(screen.getByText(/Scheduler:/).parentElement).toHaveTextContent("startup refresh finished at 2026-11-02T08:00:09Z: errors in LALIGA");
    expect(screen.getByText(/Failed refreshes in a row:/).parentElement).toHaveTextContent("2");
    await userEvent.click(screen.getByRole("button", { name: /details/i }));
    expect(screen.getByText(/Next refresh:/).parentElement).toHaveTextContent("next time FootIQ starts");
    const row = (name) => screen.getByText(name, { selector: "td" }).closest("tr");
    expect(row("LALIGA")).toHaveTextContent("2 failed refresh(es) in a row; the stored data is unchanged");
    expect(row("LALIGA")).toHaveTextContent("SourceUnavailable: HTTP 503");
    expect(row("BUNDESLIGA")).not.toHaveTextContent("Last error");
  });
});
