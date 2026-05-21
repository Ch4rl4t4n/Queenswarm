import { describe, expect, it } from "vitest";

import { DASHBOARD_LAYOUT_DEFAULTS } from "@/lib/dashboard-layout-preferences";
import {
  dashboardSummaryPollEnabledFromLayout,
  dashboardTelemetryPollEnabledFromLayout,
} from "@/lib/hooks/use-dashboard-telemetry-poll-enabled";

describe("use-dashboard-telemetry-poll-enabled", () => {
  it("pauses telemetry when settings flyout is open", () => {
    expect(dashboardTelemetryPollEnabledFromLayout(DASHBOARD_LAYOUT_DEFAULTS, true)).toBe(false);
  });

  it("pauses telemetry when all live sections are hidden", () => {
    const hidden = {
      ...DASHBOARD_LAYOUT_DEFAULTS,
      agents: false,
      kpiStats: false,
      pollenCosts: false,
      taskQueue: false,
      recentTasks: false,
      queenMission: false,
      performanceTier: false,
      ballroomParticipants: false,
    };
    expect(dashboardTelemetryPollEnabledFromLayout(hidden, false)).toBe(false);
  });

  it("runs summary poll when KPI tiles visible", () => {
    expect(dashboardSummaryPollEnabledFromLayout(DASHBOARD_LAYOUT_DEFAULTS, false)).toBe(true);
  });
});
