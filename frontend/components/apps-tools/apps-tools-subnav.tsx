"use client";

import { Boxes, Cable, Package, Sparkles } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useMemo } from "react";

import { HiveSectionSubnav } from "@/components/hive/hive-section-subnav";
import { usePlatform } from "@/components/hive/platform-context";
import { useSkillFactoryNav } from "@/components/apps-tools/skill-factory-nav-context";
import {
  APPS_TOOLS_MODULE_INDEX_HREF,
  appsToolsPrimaryFromPathname,
  CONTENT_PACK_FACTORY_TABS,
  contentPackFactoryTabHref,
  MCP_OPS_STUDIO_TABS,
  mcpOpsStudioTabHref,
  navigateContentPackFactoryTab,
  navigateMcpOpsStudioTab,
  navigateSkillFactoryTab,
  resolveContentPackFactoryTab,
  resolveMcpOpsStudioTab,
  resolveSkillFactoryTab,
  skillFactoryTabHref,
  SKILL_FACTORY_TABS,
  type ContentPackFactoryTab,
  type McpOpsStudioTab,
  type SkillFactoryTab,
} from "@/lib/apps-tools-routes";
import { useRouteHash } from "@/lib/hooks/use-route-hash";

/** Primary (Module index · factories · MCP Ops) + secondary section tabs. */
export function AppsToolsSubnav(): JSX.Element | null {
  const pathname = usePathname();
  const router = useRouter();
  const routeHash = useRouteHash();
  const { hasFeature } = usePlatform();
  const { queueBadge, packQueueBadge } = useSkillFactoryNav();

  const primarySection = appsToolsPrimaryFromPathname(pathname);
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
        icon: Package,
        href: contentPackFactoryTabHref("research"),
      });
    }
    rows.push({
      id: "mcp_ops_studio",
      label: "MCP Ops",
      icon: Cable,
      href: mcpOpsStudioTabHref("catalog"),
    });
    return rows;
  }, [skillFactoryEnabled]);

  const activeSkillFactoryTab = useMemo(
    () => resolveSkillFactoryTab({ hash: routeHash }),
    [routeHash],
  );

  const activeContentFactoryTab = useMemo(
    () => resolveContentPackFactoryTab({ hash: routeHash }),
    [routeHash],
  );

  const activeMcpOpsTab = useMemo(() => resolveMcpOpsStudioTab({ hash: routeHash }), [routeHash]);

  const secondaryItems = useMemo(() => {
    if (primarySection === "skill_factory" && skillFactoryEnabled) {
      return SKILL_FACTORY_TABS.map((row) => ({
        id: row.id,
        label: row.label,
        badge: row.id === "queue" && queueBadge !== undefined && queueBadge > 0 ? queueBadge : undefined,
      }));
    }
    if (primarySection === "content_factory" && skillFactoryEnabled) {
      return CONTENT_PACK_FACTORY_TABS.map((row) => ({
        id: row.id,
        label: row.label,
        badge:
          row.id === "queue" && packQueueBadge !== undefined && packQueueBadge > 0 ? packQueueBadge : undefined,
      }));
    }
    if (primarySection === "mcp_ops_studio") {
      return MCP_OPS_STUDIO_TABS.map((row) => ({ id: row.id, label: row.label }));
    }
    return [];
  }, [packQueueBadge, primarySection, queueBadge, skillFactoryEnabled]);

  const onPrimaryChange = useCallback(
    (id: string) => {
      if (id === "skill_factory") {
        router.push(skillFactoryTabHref("launch"));
        return;
      }
      if (id === "content_factory") {
        router.push(contentPackFactoryTabHref("research"));
        return;
      }
      if (id === "mcp_ops_studio") {
        router.push(mcpOpsStudioTabHref("catalog"));
        return;
      }
      router.push(APPS_TOOLS_MODULE_INDEX_HREF);
    },
    [router],
  );

  const onSecondaryChange = useCallback(
    (id: string) => {
      if (primarySection === "skill_factory") {
        navigateSkillFactoryTab(id as SkillFactoryTab);
        return;
      }
      if (primarySection === "content_factory") {
        navigateContentPackFactoryTab(id as ContentPackFactoryTab);
        return;
      }
      if (primarySection === "mcp_ops_studio") {
        navigateMcpOpsStudioTab(id as McpOpsStudioTab);
      }
    },
    [primarySection],
  );

  const secondaryAriaLabel =
    primarySection === "content_factory"
      ? "Content Pack Factory sections"
      : primarySection === "mcp_ops_studio"
        ? "MCP Ops Studio sections"
        : "Skill Factory sections";

  const secondaryMenuKey =
    primarySection === "content_factory"
      ? "apps-tools-content-factory"
      : primarySection === "mcp_ops_studio"
        ? "apps-tools-mcp-ops-studio"
        : "apps-tools-skill-factory";

  if (primaryItems.length === 0) {
    return null;
  }

  return (
    <HiveSectionSubnav
      primary={primaryItems}
      secondary={secondaryItems.length > 0 ? secondaryItems : undefined}
      activePrimary={primarySection}
      activeSecondary={
        primarySection === "skill_factory"
          ? activeSkillFactoryTab
          : primarySection === "content_factory"
            ? activeContentFactoryTab
            : primarySection === "mcp_ops_studio"
              ? activeMcpOpsTab
              : undefined
      }
      onPrimaryChange={onPrimaryChange}
      onSecondaryChange={secondaryItems.length > 0 ? onSecondaryChange : undefined}
      primaryAriaLabel="Apps & Tools sections"
      secondaryAriaLabel={secondaryAriaLabel}
      primaryMenuKey="apps-tools-primary"
      secondaryMenuKey={secondaryMenuKey}
    />
  );
}
