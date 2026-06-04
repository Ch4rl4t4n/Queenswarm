"use client";

import { Boxes, Sparkles } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useMemo } from "react";

import { HiveSectionSubnav } from "@/components/hive/hive-section-subnav";
import { usePlatform } from "@/components/hive/platform-context";
import { useSkillFactoryNav } from "@/components/apps-tools/skill-factory-nav-context";
import {
  APPS_TOOLS_MODULE_INDEX_HREF,
  appsToolsPrimaryFromPathname,
  navigateSkillFactoryTab,
  resolveSkillFactoryTab,
  skillFactoryTabHref,
  SKILL_FACTORY_TABS,
  type SkillFactoryTab,
} from "@/lib/apps-tools-routes";
import { useRouteHash } from "@/lib/hooks/use-route-hash";

/** Primary (Module index · Skill Factory) + secondary Skill Factory tabs. */
export function AppsToolsSubnav(): JSX.Element | null {
  const pathname = usePathname();
  const router = useRouter();
  const routeHash = useRouteHash();
  const { hasFeature } = usePlatform();
  const { queueBadge } = useSkillFactoryNav();

  const primarySection = appsToolsPrimaryFromPathname(pathname);
  const activePrimary =
    pathname.includes("/apps-tools/content-factory") ? "content_factory" : primarySection;
  const skillFactoryEnabled = hasFeature("skill_factory");

  const primaryItems = useMemo(() => {
    const rows = [
      { id: "module_index", label: "Module index", icon: Boxes, href: APPS_TOOLS_MODULE_INDEX_HREF },
    ];
    if (skillFactoryEnabled) {
      rows.push({
        id: "skill_factory",
        label: "Skill Factory",
        icon: Sparkles,
        href: skillFactoryTabHref("launch"),
      });
      rows.push({
        id: "content_factory",
        label: "Pack Factory",
        icon: Sparkles,
        href: "/apps-tools/content-factory?section=pack-factory#pack-factory",
      });
    }
    return rows;
  }, [skillFactoryEnabled]);

  const activeSkillFactoryTab = useMemo(
    () => resolveSkillFactoryTab({ hash: routeHash }),
    [routeHash],
  );

  const secondaryItems = useMemo(() => {
    if (primarySection !== "skill_factory" || !skillFactoryEnabled) {
      return [];
    }
    return SKILL_FACTORY_TABS.map((row) => ({
      id: row.id,
      label: row.label,
      badge: row.id === "queue" && queueBadge !== undefined && queueBadge > 0 ? queueBadge : undefined,
    }));
  }, [primarySection, queueBadge, skillFactoryEnabled]);

  const onPrimaryChange = useCallback(
    (id: string) => {
      if (id === "skill_factory") {
        router.push(skillFactoryTabHref("launch"));
        return;
      }
      if (id === "content_factory") {
        router.push("/apps-tools/content-factory?section=pack-factory#pack-factory");
        return;
      }
      router.push(APPS_TOOLS_MODULE_INDEX_HREF);
    },
    [router],
  );

  const onSecondaryChange = useCallback((id: string) => {
    navigateSkillFactoryTab(id as SkillFactoryTab);
  }, []);

  if (primaryItems.length === 0) {
    return null;
  }

  return (
    <HiveSectionSubnav
      primary={primaryItems}
      secondary={secondaryItems.length > 0 ? secondaryItems : undefined}
      activePrimary={activePrimary}
      activeSecondary={primarySection === "skill_factory" ? activeSkillFactoryTab : undefined}
      onPrimaryChange={onPrimaryChange}
      onSecondaryChange={secondaryItems.length > 0 ? onSecondaryChange : undefined}
      primaryAriaLabel="Apps & Tools sections"
      secondaryAriaLabel="Skill Factory sections"
      primaryMenuKey="apps-tools-primary"
      secondaryMenuKey="apps-tools-skill-factory"
    />
  );
}
