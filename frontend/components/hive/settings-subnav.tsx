"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { HiveSectionSubnav } from "@/components/hive/hive-section-subnav";
import { usePlatform } from "@/components/hive/platform-context";
import {
  filterSettingsNavGroups,
  filterSettingsNavSections,
  settingsNavGroupForHref,
} from "@/lib/settings-nav";
import {
  filterSettingsNavGroupsForDisclosure,
  isSettingsAdvancedGroup,
  settingsNavAdvancedOpenForPathname,
  settingsNavHasCollapsedAdvancedGroups,
  settingsNavInitialAdvancedOpen,
} from "@/lib/settings-nav-tiers";
import { isSettingsNavSectionActive } from "@/lib/settings-panel-registry";
import { cn } from "@/lib/utils";

/** Two-tier settings sub-nav with progressive disclosure for Advanced + Admin groups. */
export function SettingsSubnav() {
  const pathname = usePathname();
  const router = useRouter();
  const { features, isAdmin, platformMode, soloMode } = usePlatform();
  const platformOpts = { isAdmin, platformMode, soloMode };
  const groups = filterSettingsNavGroups(features, platformOpts);
  const sections = filterSettingsNavSections(features, platformOpts);

  const [advancedOpen, setAdvancedOpen] = useState(() =>
    settingsNavInitialAdvancedOpen(pathname, groups, sections, isSettingsNavSectionActive),
  );

  useEffect(() => {
    if (settingsNavAdvancedOpenForPathname(pathname, groups)) {
      setAdvancedOpen(true);
      return;
    }
    const groupId = settingsNavGroupForHref(
      sections.find((section) => isSettingsNavSectionActive(pathname, section.href))?.href ?? "",
      groups,
    );
    if (groupId && isSettingsAdvancedGroup(groupId)) {
      setAdvancedOpen(true);
    }
  }, [pathname, groups, sections]);

  const visibleGroups = useMemo(
    () => filterSettingsNavGroupsForDisclosure(groups, advancedOpen),
    [groups, advancedOpen],
  );

  const showExpandAdvanced = settingsNavHasCollapsedAdvancedGroups(groups, advancedOpen);

  const activeHref = useMemo(() => {
    const match = sections.find((section) => isSettingsNavSectionActive(pathname, section.href));
    return match?.href ?? sections[0]?.href ?? "/settings/security";
  }, [pathname, sections]);

  const activeGroupId =
    settingsNavGroupForHref(activeHref, visibleGroups) ??
    settingsNavGroupForHref(activeHref, groups) ??
    visibleGroups[0]?.id ??
    groups[0]?.id ??
    "essential";

  const groupItems = useMemo(
    () =>
      visibleGroups.map((group) => ({
        id: group.id,
        label: group.label,
        badge: group.sectionHrefs.length,
      })),
    [visibleGroups],
  );

  const sectionItems = useMemo(() => {
    const group = groups.find((g) => g.id === activeGroupId);
    if (!group) {
      return [];
    }
    return sections
      .filter((section) => group.sectionHrefs.includes(section.href))
      .map((section) => ({
        id: section.href,
        label: section.label,
        icon: section.icon,
        href: section.href,
      }));
  }, [activeGroupId, groups, sections]);

  function collapseAdvanced(): void {
    setAdvancedOpen(false);
    if (isSettingsAdvancedGroup(activeGroupId)) {
      router.push("/settings/security");
    }
  }

  return (
    <div className="settings-subnav-disclosure flex flex-col gap-3">
      <HiveSectionSubnav
        primary={groupItems}
        secondary={sectionItems}
        activePrimary={activeGroupId}
        activeSecondary={activeHref}
        onPrimaryChange={(id) => {
          const group = groups.find((g) => g.id === id);
          const firstHref = group?.sectionHrefs[0];
          if (firstHref) {
            router.push(firstHref);
          }
        }}
        onSecondaryChange={(id) => router.push(id)}
        primaryAriaLabel="Settings groups"
        secondaryAriaLabel="Settings sections"
        primaryMenuKey="settings-groups"
        secondaryMenuKey="settings-sections"
      />

      {showExpandAdvanced ? (
        <button
          type="button"
          className="settings-subnav-disclosure-toggle qs-btn qs-btn--ghost qs-btn--sm w-fit gap-1.5"
          aria-expanded={false}
          onClick={() => setAdvancedOpen(true)}
        >
          <ChevronDown className="size-4 shrink-0" aria-hidden />
          Show advanced settings
        </button>
      ) : null}

      {advancedOpen && groups.some((group) => isSettingsAdvancedGroup(group.id)) ? (
        <button
          type="button"
          className={cn(
            "settings-subnav-disclosure-toggle qs-btn qs-btn--ghost qs-btn--sm w-fit gap-1.5",
            !isSettingsAdvancedGroup(activeGroupId) && "text-(--qs-text-3)",
          )}
          aria-expanded={true}
          onClick={collapseAdvanced}
        >
          <ChevronUp className="size-4 shrink-0" aria-hidden />
          Show fewer settings
        </button>
      ) : null}
    </div>
  );
}
