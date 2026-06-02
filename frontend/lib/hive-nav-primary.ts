/**
 * Primary cockpit navigation — shared by desktop sidebar, mobile drawer, bottom nav, and More sheet.
 * Whole-App UI Reorder: order/zones from `hive-ia-canonical.ts`.
 */

import type { LucideIcon } from "lucide-react";
import {
  Brain,
  Cable,
  CircleHelp,
  LayoutDashboardIcon,
  ListTodo,
  MicIcon,
  Settings,
  Share2,
  Sparkles,
  Users,
} from "lucide-react";

import {
  ADVANCED_MONITORING_ENABLED,
  PHASE70_CONSOLIDATED_NAV_ENABLED,
  OPERATOR_CONTROL_PLANE_ENABLED,
  RECIPES_ENABLED,
  SIMULATIONS_ENABLED,
} from "@/lib/feature-flags";
import {
  buildCanonicalNavGroups,
  buildLegacyConsolidatedPrimary,
  CANONICAL_PRIMARY_CP,
  toHiveNavItems,
  type HiveIaZone,
} from "@/lib/hive-ia-canonical";
import { hiveOverviewHref } from "@/lib/hive-home-route";

export type { HiveIaZone };

export interface HiveNavItem {
  href: string;
  label: string;
  Icon: LucideIcon;
  /** Included in compact mobile bottom nav (first slots before “Menu”). */
  bottomNav?: boolean;
  section?: "overview" | "agents" | "execution" | "knowledge" | "integrations" | "ballroom" | "settings" | "manual";
  /** Platform feature key — filtered at runtime via PlatformProvider. */
  featureKey?: string;
  /** Whole-App IA zone — drives sidebar dividers between product layers. */
  iaZone?: HiveIaZone;
}

/** Lower sidebar rail — settings, manual. */
export function buildHiveSidebarSecondary(consolidatedEnabled: boolean): HiveNavItem[] {
  if (consolidatedEnabled && OPERATOR_CONTROL_PLANE_ENABLED) {
    return [
      { href: "/settings/security", label: "Settings", Icon: Settings, section: "settings", featureKey: "settings" },
      { href: "/manual", label: "Manual", Icon: CircleHelp, section: "manual", featureKey: "manual" },
    ];
  }
  return [
    { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboardIcon, section: "overview" },
    { href: "/settings/security", label: "Settings", Icon: Settings, section: "settings", featureKey: "settings" },
    { href: "/manual", label: "Manual", Icon: CircleHelp, section: "manual", featureKey: "manual" },
  ];
}

export const HIVE_SIDEBAR_SECONDARY: HiveNavItem[] = buildHiveSidebarSecondary(PHASE70_CONSOLIDATED_NAV_ENABLED);

function buildHiveNavPrimaryConsolidated(): HiveNavItem[] {
  if (OPERATOR_CONTROL_PLANE_ENABLED) {
    return toHiveNavItems(CANONICAL_PRIMARY_CP);
  }
  return buildLegacyConsolidatedPrimary();
}

/** Ordered rail — desktop shows full list (scroll); mobile drawer mirrors this. */
export function buildHiveNavPrimary(consolidatedEnabled: boolean): HiveNavItem[] {
  if (!consolidatedEnabled) {
    return [
      { href: hiveOverviewHref(), label: "Dashboard", Icon: LayoutDashboardIcon, bottomNav: true, section: "overview", iaZone: "agentic_os" },
      { href: "/swarms", label: "Swarms", Icon: Share2, section: "overview", iaZone: "agentic_os" },
      { href: "/agents", label: "Agents", Icon: Users, bottomNav: true, section: "agents", iaZone: "agentic_os" },
      { href: "/foragers", label: "Foragers", Icon: Sparkles, section: "agents", iaZone: "agentic_os" },
      { href: "/tasks", label: "Tasks", Icon: ListTodo, bottomNav: true, section: "execution", iaZone: "agentic_os" },
      { href: "/hive-mind", label: "HiveMind", Icon: Brain, section: "knowledge", iaZone: "knowledge" },
      { href: "/connectors", label: "Connectors", Icon: Cable, section: "integrations", iaZone: "integrations" },
      { href: "/ballroom", label: "Ballroom", Icon: MicIcon, bottomNav: true, section: "ballroom", iaZone: "ballroom" },
    ];
  }

  return buildHiveNavPrimaryConsolidated();
}

export const HIVE_NAV_PRIMARY: HiveNavItem[] = buildHiveNavPrimary(PHASE70_CONSOLIDATED_NAV_ENABLED);

/** Solo operator: promote Tasks to first rail slot as Mission Control (OW13). */
export function applySoloMissionControlNav(primary: HiveNavItem[], soloMode: boolean): HiveNavItem[] {
  if (!soloMode || !OPERATOR_CONTROL_PLANE_ENABLED) {
    return primary;
  }
  const tasksIdx = primary.findIndex((item) => item.href === "/tasks");
  if (tasksIdx < 0) {
    return primary;
  }
  const relabeled = primary.map((item) =>
    item.href === "/tasks" ? { ...item, label: "Mission Control", bottomNav: true } : item,
  );
  if (tasksIdx === 0) {
    return relabeled;
  }
  const copy = [...relabeled];
  const [tasks] = copy.splice(tasksIdx, 1);
  return [tasks, ...copy];
}

export function buildHiveNavPrimaryForContext(
  consolidatedEnabled: boolean,
  soloMode: boolean,
): HiveNavItem[] {
  return applySoloMissionControlNav(buildHiveNavPrimary(consolidatedEnabled), soloMode);
}

/** Grouped shortcuts for the mobile More sheet (dense overview). */
export function buildHiveNavGroups(consolidatedEnabled: boolean): { title: string; items: HiveNavItem[] }[] {
  return buildCanonicalNavGroups({
    consolidatedEnabled,
    operatorControlPlane: OPERATOR_CONTROL_PLANE_ENABLED,
    advancedMonitoring: ADVANCED_MONITORING_ENABLED,
    simulationsEnabled: SIMULATIONS_ENABLED,
    recipesEnabled: RECIPES_ENABLED,
  });
}

export const HIVE_NAV_GROUPS: { title: string; items: HiveNavItem[] }[] = buildHiveNavGroups(PHASE70_CONSOLIDATED_NAV_ENABLED);

export function hiveBottomNavItems(primary: HiveNavItem[] = HIVE_NAV_PRIMARY): HiveNavItem[] {
  const flagged = primary.filter((i) => i.bottomNav);
  return flagged.length ? flagged : primary.slice(0, 3);
}

export function sectionForPath(pathname: string): string {
  const normalized = pathname === "" ? "/" : pathname;
  if (
    normalized === "/" ||
    normalized.startsWith("/agentic-os") ||
    normalized.startsWith("/dashboard") ||
    normalized.startsWith("/cockpit") ||
    normalized.startsWith("/oracle") ||
    normalized.startsWith("/overview") ||
    normalized.startsWith("/monitoring") ||
    normalized.startsWith("/swarms")
  ) {
    return "overview";
  }
  if (normalized.startsWith("/agents") || normalized.startsWith("/foragers") || normalized.startsWith("/hierarchy")) {
    return "agents";
  }
  if (
    normalized.startsWith("/execution") ||
    normalized.startsWith("/tasks") ||
    normalized.startsWith("/factory") ||
    normalized.startsWith("/workflows") ||
    normalized.startsWith("/jobs") ||
    normalized.startsWith("/simulations")
  ) {
    return "execution";
  }
  if (
    normalized.startsWith("/knowledge") ||
    normalized.startsWith("/hive-mind") ||
    normalized.startsWith("/outputs") ||
    normalized.startsWith("/learning") ||
    normalized.startsWith("/recipes")
  ) {
    return "knowledge";
  }
  if (
    normalized.startsWith("/apps-tools") ||
    normalized.startsWith("/integrations") ||
    normalized.startsWith("/connectors") ||
    normalized.startsWith("/external-projects") ||
    normalized.startsWith("/plugins")
  ) {
    return "integrations";
  }
  if (normalized.startsWith("/ballroom")) {
    return "ballroom";
  }
  if (normalized.startsWith("/settings")) {
    return "settings";
  }
  if (normalized.startsWith("/manual")) {
    return "manual";
  }
  return "unknown";
}

export interface NavActiveContext {
  /** Current URL hash including leading `#`. */
  hash?: string;
  /** Peer nav items — used to pick the most specific active match. */
  candidates?: HiveNavItem[];
}

function splitNavHref(href: string): { path: string; hash: string } {
  const hashIdx = href.indexOf("#");
  const pathWithQuery = hashIdx === -1 ? href : href.slice(0, hashIdx);
  const hash = hashIdx === -1 ? "" : href.slice(hashIdx);
  const queryIdx = pathWithQuery.indexOf("?");
  const path = queryIdx === -1 ? pathWithQuery : pathWithQuery.slice(0, queryIdx);
  if (hashIdx === -1) {
    return { path: path || "/", hash: "" };
  }
  return {
    path: path || "/",
    hash,
  };
}

/** True when this nav item should render as the sole active route in a group. */
export function isNavItemActive(pathname: string, item: HiveNavItem, ctx?: NavActiveContext): boolean {
  const normalizedPath = pathname === "" ? "/" : (pathname.split("#")[0] ?? pathname);
  const currentHash = ctx?.hash ?? "";
  const { path: itemPath, hash: itemHash } = splitNavHref(item.href);
  const candidates = ctx?.candidates ?? [];

  if (itemHash) {
    if (normalizedPath !== itemPath) {
      return false;
    }
    return currentHash === itemHash;
  }

  if (itemPath === "/" || itemPath === "/agentic-os" || itemPath === "/cockpit" || itemPath === "/dashboard") {
    if (itemPath === "/agentic-os") {
      return (normalizedPath === "/agentic-os" || normalizedPath === "/cockpit") && !currentHash;
    }
    return normalizedPath === itemPath && !currentHash;
  }

  if (normalizedPath === itemPath) {
    if (currentHash) {
      const hashTargetsSibling = candidates.some((other) => {
        const { path: otherPath, hash: otherHash } = splitNavHref(other.href);
        return otherPath === itemPath && otherHash && currentHash === otherHash;
      });
      if (hashTargetsSibling) {
        return false;
      }
    }
    return true;
  }

  if (itemPath.startsWith("/settings") && normalizedPath.startsWith("/settings")) {
    return itemPath === "/settings/security";
  }

  if (!normalizedPath.startsWith(`${itemPath}/`)) {
    return false;
  }

  const moreSpecificMatch = candidates.some((other) => {
    if (other.href === item.href) {
      return false;
    }
    const { path: otherPath, hash: otherHash } = splitNavHref(other.href);
    if (otherHash) {
      return false;
    }
    if (otherPath.length <= itemPath.length) {
      return false;
    }
    return normalizedPath === otherPath || normalizedPath.startsWith(`${otherPath}/`);
  });

  return !moreSpecificMatch;
}
