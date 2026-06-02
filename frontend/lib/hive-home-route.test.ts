import { describe, expect, it } from "vitest";

import {
  hiveMissionControlPageTitle,
  hiveOverviewHref,
  hiveOverviewLabel,
  soloOperatorHomePreferred,
} from "./hive-home-route";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "./feature-flags";

describe("hive-home-route", () => {
  it("returns agentic-os when control plane enabled without solo preset", () => {
    if (OPERATOR_CONTROL_PLANE_ENABLED && !soloOperatorHomePreferred()) {
      expect(hiveOverviewHref()).toBe("/agentic-os");
      expect(hiveOverviewLabel()).toBe("Agentic OS");
      expect(hiveMissionControlPageTitle()).toBe("Tasks");
    } else if (OPERATOR_CONTROL_PLANE_ENABLED) {
      expect(hiveOverviewHref()).toBe("/tasks");
      expect(hiveOverviewLabel()).toBe("Mission Control");
      expect(hiveMissionControlPageTitle()).toBe("Mission Control");
      expect(hiveOverviewHref({ soloMode: true })).toBe("/tasks");
      expect(hiveOverviewLabel({ soloMode: true })).toBe("Mission Control");
    } else {
      expect(hiveOverviewHref()).toBe("/dashboard");
      expect(hiveOverviewLabel()).toBe("Dashboard");
    }
  });
});
