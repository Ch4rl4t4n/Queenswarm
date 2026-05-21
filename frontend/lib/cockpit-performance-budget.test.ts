import { describe, expect, it } from "vitest";

import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { cockpitSwrKeys } from "@/lib/cockpit-swr-keys";

describe("cockpit-performance-budget", () => {
  it("dashboard agents limit is smaller than full roster", () => {
    expect(COCKPIT_PERF.dashboardAgentsLimit).toBeLessThan(COCKPIT_PERF.fullAgentsLimit);
  });

  it("telemetry poll respects minimum interval", () => {
    expect(COCKPIT_PERF.minTelemetryPollMs).toBeGreaterThanOrEqual(10_000);
  });

  it("ws connected poll is longer than base telemetry poll", () => {
    expect(COCKPIT_PERF.wsConnectedPollMs).toBeGreaterThan(COCKPIT_PERF.minTelemetryPollMs);
  });
});

describe("cockpit-swr-keys", () => {
  it("bundle key encodes payload limits", () => {
    expect(cockpitSwrKeys.bundle(96, 10)).toEqual(["cockpit", "bundle", 96, 10]);
  });

  it("uses distinct keys for dashboard vs full agents", () => {
    expect(cockpitSwrKeys.agentsDashboard()).not.toEqual(cockpitSwrKeys.agentsFull());
  });
});
