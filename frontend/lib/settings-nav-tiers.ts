/**
 * Whole-App UI Reorder — Settings tier model (progressive disclosure).
 * Essentials visible by default; Advanced + Admin expand on demand or when deep-linked.
 */

import type { SettingsNavGroup, SettingsNavGroupId, SettingsNavSection } from "@/lib/settings-nav";

export type SettingsNavTier = "essential" | "operator" | "admin";

/** Group ids that stay collapsed until the operator expands advanced settings. */
export const SETTINGS_ADVANCED_GROUP_IDS: ReadonlySet<SettingsNavGroupId> = new Set(["operator", "admin"]);

export function isSettingsAdvancedGroup(groupId: SettingsNavGroupId): boolean {
  return SETTINGS_ADVANCED_GROUP_IDS.has(groupId);
}

/** Groups visible in the primary row when advanced settings are collapsed. */
export function filterSettingsNavGroupsForDisclosure(
  groups: SettingsNavGroup[],
  advancedOpen: boolean,
): SettingsNavGroup[] {
  if (advancedOpen) {
    return groups;
  }
  return groups.filter((group) => group.id === "essential");
}

/** Whether any advanced/admin group exists but is currently hidden. */
export function settingsNavHasCollapsedAdvancedGroups(
  groups: SettingsNavGroup[],
  advancedOpen: boolean,
): boolean {
  if (advancedOpen) {
    return false;
  }
  return groups.some((group) => isSettingsAdvancedGroup(group.id));
}

export function settingsNavTierForHref(
  href: string,
  groups: SettingsNavGroup[],
): SettingsNavTier {
  if (groups.find((g) => g.id === "admin")?.sectionHrefs.includes(href)) {
    return "admin";
  }
  if (groups.find((g) => g.id === "operator")?.sectionHrefs.includes(href)) {
    return "operator";
  }
  return "essential";
}

export function settingsNavGroupForHrefInGroups(
  href: string,
  groups: SettingsNavGroup[],
): SettingsNavGroupId | null {
  const match = groups.find((group) => group.sectionHrefs.includes(href));
  return match?.id ?? null;
}

/** Initial disclosure state — open when landing on an advanced/admin route. */
export function settingsNavInitialAdvancedOpen(
  pathname: string,
  groups: SettingsNavGroup[],
  sections: SettingsNavSection[],
  isActive: (pathname: string, href: string) => boolean,
): boolean {
  if (settingsNavAdvancedOpenForPathname(pathname, groups)) {
    return true;
  }
  const active = sections.find((section) => isActive(pathname, section.href));
  if (!active) {
    return false;
  }
  const groupId = settingsNavGroupForHrefInGroups(active.href, groups);
  return groupId ? isSettingsAdvancedGroup(groupId) : false;
}

/** True when pathname targets any advanced/admin settings route (works before panel hydration). */
export function settingsNavAdvancedOpenForPathname(pathname: string, groups: SettingsNavGroup[]): boolean {
  const normalized = pathname.replace(/\/$/, "") || "/";
  for (const group of groups) {
    if (!isSettingsAdvancedGroup(group.id)) {
      continue;
    }
    if (group.sectionHrefs.some((href) => normalized === href || normalized.startsWith(`${href}/`))) {
      return true;
    }
  }
  return false;
}
