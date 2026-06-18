import { describe, expect, it } from "vitest";

import {
  PERSONAL_OS_MORE_HIDDEN_HREFS,
  applyPersonalOsModeOverrides,
  filterAppsToolsModulesForPersonalOs,
  isPersonalOsArchivedPage,
  parsePersonalOsModeFlag,
} from "@/lib/personal-os-mode";

describe("personal-os-mode", () => {
  it("parses truthy env flags", () => {
    expect(parsePersonalOsModeFlag("true")).toBe(true);
    expect(parsePersonalOsModeFlag("1")).toBe(true);
    expect(parsePersonalOsModeFlag("false")).toBe(false);
  });

  it("hides commercial more-menu hrefs including factory", () => {
    expect(PERSONAL_OS_MORE_HIDDEN_HREFS.has("/factory")).toBe(true);
  });

  it("detects archived Personal OS page paths", () => {
    expect(isPersonalOsArchivedPage("/factory")).toBe(true);
    expect(isPersonalOsArchivedPage("/apps-tools/trading-automation")).toBe(true);
    expect(isPersonalOsArchivedPage("/tasks")).toBe(false);
  });

  it("filters commercial apps-tools modules", () => {
    const modules = [
      { moduleKey: "marketing_team", label: "Marketing Team" },
      { moduleKey: "trading_automation", label: "Trading" },
    ];
    const filtered = filterAppsToolsModulesForPersonalOs(modules, true);
    expect(filtered.map((row) => row.moduleKey)).toEqual(["marketing_team"]);
  });

  it("applyPersonalOsModeOverrides disables skills_export_factory", () => {
    const out = applyPersonalOsModeOverrides({ skills_export_factory: true }, { isAdmin: true });
    expect(out.skills_export_factory).toBe(false);
    expect(out.tasks).toBe(true);
  });
});
