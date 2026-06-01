import { describe, expect, it } from "vitest";

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
  it("includes deep links on canonical workflow checklist steps", () => {
    const section = manualSections("en").find((s) => s.id === "canonical-workflow");
    expect(section?.checklist?.[0]?.href).toBe("/knowledge#memory");
    expect(section?.checklist?.[1]?.href).toBe("/agents#sessions");
  });
});
