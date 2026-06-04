import { describe, expect, it } from "vitest";

import {
  appsToolsPrimaryFromPathname,
  appsToolsShellActiveForPathname,
  contentPackFactoryTabFromHash,
  contentPackFactoryTabHref,
  resolveContentPackFactoryTab,
  resolveSkillFactoryTab,
  skillFactoryTabFromHash,
  skillFactoryTabHref,
} from "@/lib/apps-tools-routes";

describe("apps-tools-routes", () => {
  it("detects shell routes", () => {
    expect(appsToolsShellActiveForPathname("/apps-tools")).toBe(true);
    expect(appsToolsShellActiveForPathname("/apps-tools/skill-factory")).toBe(true);
    expect(appsToolsShellActiveForPathname("/apps-tools/content-factory")).toBe(true);
    expect(appsToolsShellActiveForPathname("/apps-tools/marketing-automation")).toBe(false);
  });

  it("maps primary section from pathname", () => {
    expect(appsToolsPrimaryFromPathname("/apps-tools")).toBe("module_index");
    expect(appsToolsPrimaryFromPathname("/apps-tools/skill-factory")).toBe("skill_factory");
    expect(appsToolsPrimaryFromPathname("/apps-tools/content-factory")).toBe("content_factory");
  });

  it("resolves skill factory tabs from hash", () => {
    expect(skillFactoryTabFromHash("#research")).toBe("research");
    expect(skillFactoryTabFromHash("#guide")).toBe("guide");
    expect(skillFactoryTabFromHash("")).toBeNull();
    expect(resolveSkillFactoryTab({ hash: "#library" })).toBe("library");
    expect(resolveSkillFactoryTab({ hash: "" })).toBe("research");
    expect(skillFactoryTabHref("settings")).toBe("/apps-tools/skill-factory#settings");
  });

  it("resolves content pack factory tabs from hash", () => {
    expect(contentPackFactoryTabFromHash("#research")).toBe("research");
    expect(contentPackFactoryTabFromHash("#pack-factory")).toBe("research");
    expect(contentPackFactoryTabFromHash("#pipeline")).toBe("research");
    expect(contentPackFactoryTabFromHash("#queue")).toBe("queue");
    expect(resolveContentPackFactoryTab({ hash: "" })).toBe("research");
    expect(contentPackFactoryTabHref("guide")).toBe("/apps-tools/content-factory#guide");
  });
});
