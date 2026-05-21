import { describe, expect, it } from "vitest";

import { mapCockpitSystemLiteToStatus } from "@/lib/cockpit-bundle";

describe("mapCockpitSystemLiteToStatus", () => {
  it("maps lite gauges into chrome-compatible system status", () => {
    const status = mapCockpitSystemLiteToStatus({
      agents_total: 12,
      agents_running: 3,
      tasks_running: 2,
      tasks_pending: 5,
      llm_grok: true,
      llm_anthropic: false,
    });
    expect(status.agents_total).toBe(12);
    expect(status.tasks_pending).toBe(5);
    expect(status.llm_ok).toBe(true);
    expect(status.llm_grok).toBe(true);
    expect(status.llm_anthropic).toBe(false);
  });
});
