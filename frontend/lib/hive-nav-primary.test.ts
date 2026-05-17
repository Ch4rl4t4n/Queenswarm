import { describe, expect, it } from "vitest";

import {
  buildHiveNavGroups,
  buildHiveNavPrimary,
  HIVE_NAV_GROUPS,
  HIVE_NAV_PRIMARY,
  hiveBottomNavItems,
} from "./hive-nav-primary";

describe("hive-nav-primary", () => {
  it("lists consolidated primary section entries", () => {
    const hrefs = HIVE_NAV_PRIMARY.map((i) => i.href);
    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/agents");
    expect(hrefs).toContain("/tasks");
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

  it("buildHiveNavPrimary disables consolidated hubs when flag is false", () => {
    const nav = buildHiveNavPrimary(false).map((item) => item.href);
    expect(nav).toContain("/");
    expect(nav).toContain("/tasks");
    expect(nav).not.toContain("/dashboard");
  });

  it("buildHiveNavGroups omits hub links when consolidated mode is disabled", () => {
    const groups = buildHiveNavGroups(false);
    const hrefs = groups.flatMap((group) => group.items.map((item) => item.href));
    expect(hrefs).not.toContain("/dashboard");
    expect(hrefs).not.toContain("/knowledge");
    expect(hrefs).toContain("/hive-mind");
    expect(hrefs).toContain("/tasks");
  });
});
