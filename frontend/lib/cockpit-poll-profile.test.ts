import { describe, expect, it } from "vitest";

import {
  COCKPIT_POLL_AGENTS_TASKS_MS,
  COCKPIT_POLL_BOARD_MS,
  COCKPIT_POLL_COLONY_TELEMETRY_MS,
  COCKPIT_POLL_EXTERNAL_METRICS_MS,
  COCKPIT_POLL_SYSTEM_STATUS_MS,
} from "./cockpit-poll-profile";

describe("cockpit-poll-profile Phase 3.6", () => {
  it("exports positive poll intervals (built from NEXT_PUBLIC_QS_POLL_PROFILE at bundle time)", () => {
    expect(COCKPIT_POLL_AGENTS_TASKS_MS).toBeGreaterThanOrEqual(5000);
    expect(COCKPIT_POLL_BOARD_MS).toBeGreaterThanOrEqual(8000);
    expect(COCKPIT_POLL_COLONY_TELEMETRY_MS).toBeGreaterThanOrEqual(8000);
    expect(COCKPIT_POLL_SYSTEM_STATUS_MS).toBeGreaterThanOrEqual(12000);
    expect(COCKPIT_POLL_EXTERNAL_METRICS_MS).toBeGreaterThanOrEqual(25_000);
  });
});
