import { describe, expect, it } from "vitest";

import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";
import { hiveOverviewHref } from "@/lib/hive-home-route";
import { interpolateManualHomeTokens, manualSections } from "@/lib/manual-i18n";

describe("interpolateManualHomeTokens", () => {
  it("replaces home route and label placeholders", () => {
    const text = interpolateManualHomeTokens("Land on {HOME_ROUTE} — start in {HOME_LABEL}.");
    expect(text).toContain(hiveOverviewHref());
    expect(text).not.toContain("{HOME_ROUTE}");
    expect(text).not.toContain("{HOME_LABEL}");
  });
});

describe("manualSections", () => {
  it("uses CP-aware home route in quick-start checklist", () => {
    const section = manualSections("en").find((s) => s.id === "quick-start");
    expect(section?.checklist?.[0]).toContain(hiveOverviewHref());
    if (OPERATOR_CONTROL_PLANE_ENABLED) {
      expect(section?.checklist?.[0]).toContain("/cockpit");
    }
  });
});
