import { describe, expect, it } from "vitest";

import { hiveOverviewHref, hiveOverviewLabel } from "./hive-home-route";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "./feature-flags";

describe("hive-home-route", () => {
  it("returns agentic-os when control plane enabled", () => {
    if (OPERATOR_CONTROL_PLANE_ENABLED) {
      expect(hiveOverviewHref()).toBe("/agentic-os");
      expect(hiveOverviewLabel()).toBe("Agentic OS");
      expect(hiveOverviewHref({ soloMode: true })).toBe("/tasks");
      expect(hiveOverviewLabel({ soloMode: true })).toBe("Mission Control");
    } else {
      expect(hiveOverviewHref()).toBe("/dashboard");
      expect(hiveOverviewLabel()).toBe("Dashboard");
    }
  });
});
