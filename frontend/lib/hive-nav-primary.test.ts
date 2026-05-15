import { describe, expect, it } from "vitest";

import { HIVE_NAV_GROUPS, HIVE_NAV_PRIMARY, hiveBottomNavItems } from "./hive-nav-primary";

describe("hive-nav-primary", () => {
  it("lists consolidated primary section entries", () => {
    const hrefs = HIVE_NAV_PRIMARY.map((i) => i.href);
    expect(hrefs).toContain("/overview");
    expect(hrefs).toContain("/agents");
    expect(hrefs).toContain("/execution");
    expect(hrefs).toContain("/knowledge");
    expect(hrefs).toContain("/integrations");
    expect(hrefs).toContain("/ballroom");
  });

  it("groups include every primary route at least once", () => {
    const seen = new Set<string>();
    for (const g of HIVE_NAV_GROUPS) {
      for (const item of g.items) {
        seen.add(item.href);
      }
    }
    for (const primary of HIVE_NAV_PRIMARY) {
      expect(seen.has(primary.href)).toBe(true);
    }
  });

  it("hiveBottomNavItems marks primary thumb routes", () => {
    const nav = hiveBottomNavItems();
    expect(nav.length).toBeGreaterThan(0);
    expect(nav.every((i) => i.bottomNav)).toBe(true);
  });
});
