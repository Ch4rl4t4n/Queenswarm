import { describe, expect, it } from "vitest";

import { filterSettingsNavGroups, filterSettingsNavSections } from "@/lib/settings-nav";
import { applySoloModeOverrides } from "@/lib/solo-mode";
import { resolvePlatformFeaturesFallback } from "@/lib/platform-features";

describe("settings-nav", () => {
  it("shows command center and platform for solo admin on internal tenant", () => {
    const features = applySoloModeOverrides(
      resolvePlatformFeaturesFallback({
        platformMode: "internal",
        isAdmin: true,
        subscriptionTier: "free",
      }),
      { isAdmin: true },
    );
    const opts = { isAdmin: true, platformMode: "internal", soloMode: true };
    const sections = filterSettingsNavSections(features, opts);
    const hrefs = sections.map((s) => s.href);
    expect(hrefs).toContain("/settings/command-center");
    expect(hrefs).toContain("/settings/platform");
    expect(hrefs).not.toContain("/settings/team");
    expect(hrefs).not.toContain("/settings/accounts");
  });

  it("includes Admin group when command center is visible", () => {
    const features = applySoloModeOverrides(
      resolvePlatformFeaturesFallback({
        platformMode: "internal",
        isAdmin: true,
        subscriptionTier: "free",
      }),
      { isAdmin: true },
    );
    const opts = { isAdmin: true, platformMode: "internal", soloMode: true };
    const groups = filterSettingsNavGroups(features, opts);
    const adminGroup = groups.find((g) => g.id === "admin");
    expect(adminGroup).toBeDefined();
    expect(adminGroup?.sectionHrefs).toContain("/settings/command-center");
    expect(adminGroup?.label).toBe("Admin");
  });

  it("keeps essentials separate from advanced operator lanes", () => {
    const features = applySoloModeOverrides(
      resolvePlatformFeaturesFallback({
        platformMode: "internal",
        isAdmin: true,
        subscriptionTier: "free",
      }),
      { isAdmin: true },
    );
    const opts = { isAdmin: true, platformMode: "internal", soloMode: true };
    const groups = filterSettingsNavGroups(features, opts);
    const essential = groups.find((g) => g.id === "essential");
    const operator = groups.find((g) => g.id === "operator");
    expect(essential?.sectionHrefs).toEqual([
      "/settings/security",
      "/settings/notifications",
      "/settings/llm-keys",
    ]);
    expect(operator?.sectionHrefs).toContain("/settings/harness");
    expect(operator?.sectionHrefs).toContain("/settings/costs");
    expect(operator?.sectionHrefs).not.toContain("/settings/security");
  });
});
