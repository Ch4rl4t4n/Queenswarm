import { describe, expect, it } from "vitest";

import {
  buildHiveNavGroups,
  buildHiveNavPrimary,
  HIVE_NAV_GROUPS,
  HIVE_NAV_PRIMARY,
  HIVE_SIDEBAR_SECONDARY,
  hiveBottomNavItems,
  isNavItemActive,
} from "./hive-nav-primary";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "./feature-flags";

describe("hive-nav-primary", () => {
  const overviewHref = OPERATOR_CONTROL_PLANE_ENABLED ? "/cockpit" : "/dashboard";

  it("lists consolidated primary section entries", () => {
    const hrefs = HIVE_NAV_PRIMARY.map((i) => i.href);
    expect(hrefs).toContain("/agents");
    expect(hrefs).toContain("/knowledge");
    expect(hrefs).toContain("/integrations");
    expect(hrefs).toContain("/ballroom");
    expect(hrefs).toContain(overviewHref);
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
    expect(nav).toContain(overviewHref);
    expect(nav).toContain("/tasks");
    expect(nav).not.toContain("/knowledge");
  });

  it("buildHiveNavGroups omits hub links when consolidated mode is disabled", () => {
    const groups = buildHiveNavGroups(false);
    const hrefs = groups.flatMap((group) => group.items.map((item) => item.href));
    expect(hrefs).not.toContain("/knowledge");
    expect(hrefs).toContain(overviewHref);
    if (OPERATOR_CONTROL_PLANE_ENABLED) {
      expect(hrefs).not.toContain("/dashboard");
    } else {
      expect(hrefs).not.toContain("/cockpit");
    }
    expect(hrefs).toContain("/hive-mind");
    expect(hrefs).toContain("/tasks");
  });

  it("isNavItemActive highlights only the matching route, not whole section", () => {
    const overview = HIVE_NAV_PRIMARY.find((i) => i.href === overviewHref)!;
    const swarms = HIVE_NAV_PRIMARY.find((i) => i.href === "/swarms")!;
    const agents = HIVE_NAV_PRIMARY.find((i) => i.href === "/agents")!;
    const agentsGroup = HIVE_NAV_GROUPS.find((g) => g.title === "Agents")!.items;
    const foragers = agentsGroup.find((i) => i.href === "/foragers")!;
    const executionItems = HIVE_NAV_GROUPS.find((g) => g.title === "Execution")!.items;

    expect(isNavItemActive(overviewHref, overview)).toBe(true);
    expect(isNavItemActive(overviewHref, swarms)).toBe(false);
    expect(
      isNavItemActive(overviewHref, overview, {
        hash: "#hive-live-swarm",
        candidates: HIVE_NAV_GROUPS[0]!.items,
      }),
    ).toBe(false);

    expect(isNavItemActive("/agents", agents)).toBe(true);
    expect(isNavItemActive("/agents", foragers)).toBe(false);

    expect(isNavItemActive("/foragers", foragers)).toBe(true);
    expect(isNavItemActive("/foragers", agents)).toBe(false);

    expect(
      isNavItemActive("/tasks/new", executionItems.find((i) => i.href === "/tasks/new")!, {
        candidates: executionItems,
      }),
    ).toBe(true);
    expect(
      isNavItemActive("/tasks/new", executionItems.find((i) => i.href === "/tasks")!, {
        candidates: executionItems,
      }),
    ).toBe(false);

    expect(isNavItemActive("/settings/billing", HIVE_SIDEBAR_SECONDARY.find((i) => i.label === "Settings")!)).toBe(
      true,
    );
  });
});
