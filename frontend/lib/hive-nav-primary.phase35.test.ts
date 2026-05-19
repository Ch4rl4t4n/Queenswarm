import { describe, expect, it } from "vitest";

import { HIVE_NAV_GROUPS, HIVE_NAV_PRIMARY } from "./hive-nav-primary";

/** Routes exercised by Phase 3.5 Playwright navigation smoke — IA regression guard. */
describe("hive-nav-primary Phase 3.5 IA coverage", () => {
  it("includes required cockpit destinations", () => {
    const consolidated = HIVE_NAV_PRIMARY.some((item) => item.href === "/integrations");
    const routeRequirements: readonly string[] = [
      consolidated ? "/integrations" : "/connectors",
      consolidated ? "/knowledge" : "/hive-mind",
      "/tasks",
      "/ballroom",
    ];
    const hrefs = new Set(HIVE_NAV_PRIMARY.map((i) => i.href));
    for (const href of routeRequirements) {
      expect(hrefs.has(href), `missing nav entry for ${href}`).toBe(true);
    }
  });

  it("groups integrations section contains canonical shortcuts", () => {
    const integrations = HIVE_NAV_GROUPS.find((g) => g.title === "Integrations");
    expect(integrations).toBeDefined();
    const hrefs = integrations!.items.map((i) => i.href);
    if (hrefs.some((href) => href.startsWith("/integrations"))) {
      expect(hrefs).toContain("/integrations");
      expect(hrefs).toContain("/integrations?tab=hub");
      expect(hrefs).toContain("/integrations?tab=external");
      expect(hrefs).toContain("/integrations?tab=plugins");
      return;
    }
    expect(hrefs).toContain("/connectors");
    expect(hrefs).toContain("/external-projects");
  });
});
