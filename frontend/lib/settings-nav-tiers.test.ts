import { Shield } from "lucide-react";
import { describe, expect, it } from "vitest";

import { SETTINGS_NAV_GROUPS } from "@/lib/settings-nav";
import {
  filterSettingsNavGroupsForDisclosure,
  isSettingsAdvancedGroup,
  settingsNavAdvancedOpenForPathname,
  settingsNavHasCollapsedAdvancedGroups,
  settingsNavInitialAdvancedOpen,
  settingsNavTierForHref,
} from "@/lib/settings-nav-tiers";

describe("settings-nav-tiers", () => {
  it("defines three canonical tiers in group order", () => {
    expect(SETTINGS_NAV_GROUPS.map((g) => g.id)).toEqual(["essential", "operator", "admin"]);
    expect(SETTINGS_NAV_GROUPS[0]?.label).toBe("Essentials");
    expect(SETTINGS_NAV_GROUPS[1]?.label).toBe("Advanced");
  });

  it("collapses advanced groups when disclosure is closed", () => {
    const collapsed = filterSettingsNavGroupsForDisclosure(SETTINGS_NAV_GROUPS, false);
    expect(collapsed).toHaveLength(1);
    expect(collapsed[0]?.id).toBe("essential");
    expect(settingsNavHasCollapsedAdvancedGroups(SETTINGS_NAV_GROUPS, false)).toBe(true);
  });

  it("shows all groups when disclosure is open", () => {
    const open = filterSettingsNavGroupsForDisclosure(SETTINGS_NAV_GROUPS, true);
    expect(open).toHaveLength(3);
    expect(settingsNavHasCollapsedAdvancedGroups(SETTINGS_NAV_GROUPS, true)).toBe(false);
  });

  it("resolves tier from href", () => {
    expect(settingsNavTierForHref("/settings/security", SETTINGS_NAV_GROUPS)).toBe("essential");
    expect(settingsNavTierForHref("/settings/harness", SETTINGS_NAV_GROUPS)).toBe("operator");
    expect(settingsNavTierForHref("/settings/command-center", SETTINGS_NAV_GROUPS)).toBe("admin");
  });

  it("opens disclosure initially on advanced routes", () => {
    expect(
      settingsNavInitialAdvancedOpen(
        "/settings/harness",
        SETTINGS_NAV_GROUPS,
        [{ href: "/settings/harness", label: "Harness", icon: Shield }],
        (path, href) => path === href,
      ),
    ).toBe(true);
    expect(
      settingsNavInitialAdvancedOpen(
        "/settings/security",
        SETTINGS_NAV_GROUPS,
        [{ href: "/settings/security", label: "Security", icon: Shield }],
        (path, href) => path === href,
      ),
    ).toBe(false);
  });

  it("opens disclosure from pathname even without hydrated sections", () => {
    expect(settingsNavAdvancedOpenForPathname("/settings/harness", SETTINGS_NAV_GROUPS)).toBe(true);
    expect(settingsNavAdvancedOpenForPathname("/settings/security", SETTINGS_NAV_GROUPS)).toBe(false);
  });
});
