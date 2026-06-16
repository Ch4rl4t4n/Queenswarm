import { describe, expect, it } from "vitest";

import { APPS_TOOLS_MODULES, APPS_TOOLS_MODULES_CORE } from "@/lib/apps-tools-modules";

describe("apps-tools-modules analytics workspace", () => {
  it("includes analytics workspace as core beta module", () => {
    const mod = APPS_TOOLS_MODULES.find((row) => row.moduleKey === "analytics_workspace");
    expect(mod).toBeDefined();
    expect(mod?.href).toBe("/apps-tools/analytics");
    expect(mod?.capabilityKeys).toContain("apps.analytics.decision_report.v1");
    expect(APPS_TOOLS_MODULES_CORE.some((row) => row.moduleKey === "analytics_workspace")).toBe(true);
  });
});
