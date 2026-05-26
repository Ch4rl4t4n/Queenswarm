import { describe, expect, it } from "vitest";

import { hiveOverviewHref, hiveOverviewLabel } from "./hive-home-route";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "./feature-flags";

describe("hive-home-route", () => {
  it("returns cockpit when control plane enabled", () => {
    if (OPERATOR_CONTROL_PLANE_ENABLED) {
      expect(hiveOverviewHref()).toBe("/cockpit");
      expect(hiveOverviewLabel()).toBe("Cockpit");
    } else {
      expect(hiveOverviewHref()).toBe("/dashboard");
      expect(hiveOverviewLabel()).toBe("Dashboard");
    }
  });
});
