import { describe, expect, it } from "vitest";

import {
  appsToolsPrimaryFromPathname,
  appsToolsShellActiveForPathname,
  contentPackFactoryTabFromHash,
  contentPackFactoryTabHref,
  mcpOpsStudioTabFromHash,
  mcpOpsStudioTabHref,
  resolveContentPackFactoryTab,
  resolveMcpOpsStudioTab,
  filterSkillFactoryTabsForPersonalOs,
  PERSONAL_OS_HIDDEN_SKILL_FACTORY_TABS,
  SKILL_FACTORY_TABS,
  resolveSkillFactoryTab,
  skillFactoryTabFromHash,
  skillFactoryTabHref,
} from "@/lib/apps-tools-routes";

describe("apps-tools-routes", () => {
  it("detects shell routes", () => {
    expect(appsToolsShellActiveForPathname("/apps-tools")).toBe(true);
    expect(appsToolsShellActiveForPathname("/apps-tools/skill-factory")).toBe(true);
    expect(appsToolsShellActiveForPathname("/apps-tools/content-factory")).toBe(true);
    expect(appsToolsShellActiveForPathname("/apps-tools/mcp-ops-studio")).toBe(true);
    expect(appsToolsShellActiveForPathname("/apps-tools/marketing-automation")).toBe(false);
  });

  it("maps primary section from pathname", () => {
    expect(appsToolsPrimaryFromPathname("/apps-tools")).toBe("module_index");
    expect(appsToolsPrimaryFromPathname("/apps-tools/skill-factory")).toBe("skill_factory");
    expect(appsToolsPrimaryFromPathname("/apps-tools/content-factory")).toBe("content_factory");
    expect(appsToolsPrimaryFromPathname("/apps-tools/mcp-ops-studio")).toBe("mcp_ops_studio");
  });

  it("resolves skill factory tabs from hash", () => {
    expect(skillFactoryTabFromHash("#research")).toBe("research");
    expect(skillFactoryTabFromHash("#guide")).toBe("guide");
    expect(skillFactoryTabFromHash("")).toBeNull();
    expect(resolveSkillFactoryTab({ hash: "#library" })).toBe("library");
    expect(resolveSkillFactoryTab({ hash: "" })).toBe("research");
    expect(resolveSkillFactoryTab({ hash: "#launch", personalOsMode: true })).toBe("research");
    expect(resolveSkillFactoryTab({ hash: "#launch", personalOsMode: false })).toBe("launch");
    expect(skillFactoryTabHref("settings")).toBe("/apps-tools/skill-factory#settings");
  });

  it("filters launch tab in personal os mode", () => {
    const filtered = filterSkillFactoryTabsForPersonalOs(SKILL_FACTORY_TABS, true);
    expect(filtered.map((row) => row.id)).not.toContain("launch");
    expect(PERSONAL_OS_HIDDEN_SKILL_FACTORY_TABS.has("launch")).toBe(true);
    expect(filterSkillFactoryTabsForPersonalOs(SKILL_FACTORY_TABS, false)).toHaveLength(SKILL_FACTORY_TABS.length);
  });

  it("resolves content pack factory tabs from hash", () => {
    expect(contentPackFactoryTabFromHash("#research")).toBe("research");
    expect(contentPackFactoryTabFromHash("#pack-factory")).toBe("research");
    expect(contentPackFactoryTabFromHash("#pipeline")).toBe("research");
    expect(contentPackFactoryTabFromHash("#queue")).toBe("queue");
    expect(resolveContentPackFactoryTab({ hash: "" })).toBe("research");
    expect(contentPackFactoryTabHref("guide")).toBe("/apps-tools/content-factory#guide");
  });

  it("resolves mcp ops studio tabs from hash", () => {
    expect(mcpOpsStudioTabFromHash("#catalog")).toBe("catalog");
    expect(mcpOpsStudioTabFromHash("#mcp-catalog")).toBe("catalog");
    expect(mcpOpsStudioTabFromHash("#install")).toBe("install");
    expect(mcpOpsStudioTabFromHash("#health")).toBe("health");
    expect(resolveMcpOpsStudioTab({ hash: "" })).toBe("catalog");
    expect(mcpOpsStudioTabHref("health")).toBe("/apps-tools/mcp-ops-studio#health");
  });
});
