/**
 * Primary cockpit navigation — shared by desktop sidebar, mobile drawer, bottom nav, and More sheet.
 * Phase 2.6: single source of truth for IA consistency.
 */

import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Boxes,
  Brain,
  Briefcase,
  Cable,
  ClipboardList,
  FileText,
  Eye,
  Factory,
  FlaskConical,
  GitBranch,
  Hexagon,
  LayoutDashboardIcon,
  ListTodo,
  MicIcon,
  Puzzle,
  ScrollText,
  Settings,
  Share2,
  CircleHelp,
  Sparkles,
  Trophy,
  Users,
  Zap,
} from "lucide-react";

import { integrationsTabHref } from "@/lib/integrations-routes";
import {
  ADVANCED_MONITORING_ENABLED,
  LEADERBOARD_ENABLED,
  PHASE70_CONSOLIDATED_NAV_ENABLED,
  OPERATOR_CONTROL_PLANE_ENABLED,
  RECIPES_ENABLED,
  SIMULATIONS_ENABLED,
} from "@/lib/feature-flags";

export interface HiveNavItem {
  href: string;
  label: string;
  Icon: LucideIcon;
  /** Included in compact mobile bottom nav (first slots before “Menu”). */
  bottomNav?: boolean;
  section?: "overview" | "agents" | "execution" | "knowledge" | "integrations" | "ballroom" | "settings" | "manual";
  /** Platform feature key — filtered at runtime via PlatformProvider. */
  featureKey?: string;
}

/** Lower sidebar rail — costs, leaderboard, settings, manual. */
export function buildHiveSidebarSecondary(_consolidatedEnabled: boolean): HiveNavItem[] {
  return [
    ...(LEADERBOARD_ENABLED
      ? [{ href: "/leaderboard", label: "Leaderboard", Icon: Trophy, section: "knowledge" as const, featureKey: "leaderboard" as const }]
      : []),
    { href: "/settings/security", label: "Settings", Icon: Settings, section: "settings", featureKey: "settings" },
    { href: "/manual", label: "Manual", Icon: CircleHelp, section: "manual", featureKey: "manual" },
  ];
}

export const HIVE_SIDEBAR_SECONDARY: HiveNavItem[] = buildHiveSidebarSecondary(PHASE70_CONSOLIDATED_NAV_ENABLED);

function buildHiveNavPrimaryConsolidated(): HiveNavItem[] {
  const items: HiveNavItem[] = [];
  if (OPERATOR_CONTROL_PLANE_ENABLED) {
    items.push({
      href: "/cockpit",
      label: "Cockpit",
      Icon: Zap,
      bottomNav: true,
      section: "overview",
      featureKey: "operator_cockpit",
    });
    items.push({
      href: "/oracle",
      label: "Oracle",
      Icon: Eye,
      section: "overview",
      featureKey: "operator_cockpit",
    });
  }
  items.push(
    { href: "/", label: "Dashboard", Icon: LayoutDashboardIcon, bottomNav: !OPERATOR_CONTROL_PLANE_ENABLED, section: "overview", featureKey: "dashboard" },
    { href: "/swarms", label: "Swarms", Icon: Share2, section: "overview", featureKey: "swarms" },
    { href: "/agents", label: "Agents", Icon: Users, bottomNav: true, section: "agents", featureKey: "agents" },
    { href: "/foragers", label: "Foragers", Icon: Sparkles, section: "agents", featureKey: "foragers" },
    { href: "/tasks", label: "Tasks", Icon: ListTodo, bottomNav: true, section: "execution", featureKey: "tasks" },
    { href: "/factory", label: "Factory", Icon: Factory, section: "execution", featureKey: "skills_export_factory" },
    { href: "/knowledge", label: "Knowledge", Icon: Brain, section: "knowledge", featureKey: "knowledge" },
    { href: "/integrations", label: "Integrations", Icon: Cable, section: "integrations", featureKey: "integrations" },
    { href: "/ballroom", label: "Ballroom", Icon: MicIcon, bottomNav: true, section: "ballroom", featureKey: "ballroom" },
  );
  return items;
}

/** Ordered rail — desktop shows full list (scroll); mobile drawer mirrors this. */
export function buildHiveNavPrimary(consolidatedEnabled: boolean): HiveNavItem[] {
  if (!consolidatedEnabled) {
    return [
      { href: "/", label: "Dashboard", Icon: LayoutDashboardIcon, bottomNav: true, section: "overview" },
      { href: "/swarms", label: "Swarms", Icon: Share2, section: "overview" },
      { href: "/agents", label: "Agents", Icon: Users, bottomNav: true, section: "agents" },
      { href: "/foragers", label: "Foragers", Icon: Sparkles, section: "agents" },
      { href: "/tasks", label: "Tasks", Icon: ListTodo, bottomNav: true, section: "execution" },
      { href: "/hive-mind", label: "HiveMind", Icon: Brain, section: "knowledge" },
      { href: "/connectors", label: "Connectors", Icon: Cable, section: "integrations" },
      { href: "/ballroom", label: "Ballroom", Icon: MicIcon, bottomNav: true, section: "ballroom" },
    ];
  }

  return buildHiveNavPrimaryConsolidated();
}

export const HIVE_NAV_PRIMARY: HiveNavItem[] = buildHiveNavPrimary(PHASE70_CONSOLIDATED_NAV_ENABLED);

/** Grouped shortcuts for the mobile More sheet (dense overview). */
export function buildHiveNavGroups(consolidatedEnabled: boolean): { title: string; items: HiveNavItem[] }[] {
  return [
    {
      title: "Overview",
      items: [
        { href: "/", label: "Dashboard", Icon: LayoutDashboardIcon, section: "overview" },
        ...(ADVANCED_MONITORING_ENABLED
          ? [{ href: "/monitoring", label: "Monitoring", Icon: Activity, section: "overview" as const }]
          : []),
        { href: "/#hive-live-swarm", label: "Live network", Icon: Hexagon, section: "overview" },
        { href: "/swarms", label: "Swarms", Icon: Share2, section: "overview" },
      ],
    },
    {
      title: "Agents",
      items: [
        { href: "/agents", label: consolidatedEnabled ? "Agents hub" : "Agents", Icon: Users, section: "agents" },
        { href: "/agents/new", label: "Spawn agent", Icon: ClipboardList, section: "agents" },
        { href: "/foragers", label: "Foragers", Icon: Sparkles, section: "agents" },
        { href: "/agents#hierarchy", label: "Hierarchy", Icon: Share2, section: "agents" },
      ],
    },
    {
      title: "Execution",
      items: [
        ...(consolidatedEnabled
          ? [{ href: "/tasks", label: "Tasks hub", Icon: ListTodo, section: "execution" as const }]
          : [{ href: "/tasks", label: "Tasks", Icon: ListTodo, section: "execution" as const }]),
        { href: "/tasks/new", label: "New task", Icon: ClipboardList, section: "execution" },
        { href: "/workflows", label: "Workflows", Icon: GitBranch, section: "execution" },
        { href: "/jobs", label: "Async jobs", Icon: Briefcase, section: "execution" },
        ...(SIMULATIONS_ENABLED
          ? [{ href: "/simulations", label: "Simulations", Icon: FlaskConical, section: "execution" as const }]
          : []),
        { href: "/factory", label: "Micro-SaaS Factory", Icon: Factory, section: "execution" as const, featureKey: "skills_export_factory" as const },
      ],
    },
    {
      title: "Knowledge",
      items: [
        ...(consolidatedEnabled
          ? [{ href: "/knowledge", label: "Knowledge hub", Icon: Brain, section: "knowledge" as const }]
          : []),
        {
          href: consolidatedEnabled ? "/knowledge#hivemind" : "/hive-mind",
          label: "HiveMind",
          Icon: Brain,
          section: "knowledge",
        },
        {
          href: consolidatedEnabled ? "/knowledge#outputs" : "/outputs",
          label: "Outputs",
          Icon: FileText,
          section: "knowledge",
        },
        {
          href: consolidatedEnabled ? "/knowledge#recipes" : "/learning",
          label: "Learning",
          Icon: Sparkles,
          section: "knowledge",
        },
        ...(RECIPES_ENABLED
          ? [
              {
                href: consolidatedEnabled ? "/knowledge#recipes" : "/recipes",
                label: "Recipes",
                Icon: ScrollText,
                section: "knowledge" as const,
              },
            ]
          : []),
        ...(LEADERBOARD_ENABLED
          ? [{ href: "/leaderboard", label: "Leaderboard", Icon: Trophy, section: "knowledge" as const }]
          : []),
      ],
    },
    {
      title: "Integrations",
      items: [
        ...(consolidatedEnabled
          ? [{ href: "/integrations", label: "Integrations hub", Icon: Cable, section: "integrations" as const }]
          : []),
        {
          href: consolidatedEnabled ? integrationsTabHref("hub") : "/connectors",
          label: "Connectors",
          Icon: Cable,
          section: "integrations",
        },
        {
          href: consolidatedEnabled ? integrationsTabHref("external") : "/external-projects",
          label: "External apps",
          Icon: Boxes,
          section: "integrations",
        },
        {
          href: consolidatedEnabled ? integrationsTabHref("plugins") : "/plugins",
          label: "Plugins",
          Icon: Puzzle,
          section: "integrations",
        },
      ],
    },
    {
      title: "Ballroom",
      items: [{ href: "/ballroom", label: "Realtime Ballroom", Icon: MicIcon, section: "ballroom" }],
    },
    {
      title: "Settings",
      items: [{ href: "/settings/security", label: "Settings", Icon: Settings, section: "settings" }],
    },
    {
      title: "Manual",
      items: [{ href: "/manual", label: "Manual", Icon: CircleHelp, section: "manual" }],
    },
  ];
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
    normalized.startsWith("/dashboard") ||
    normalized.startsWith("/cockpit") ||
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
    normalized.startsWith("/recipes") ||
    normalized.startsWith("/leaderboard")
  ) {
    return "knowledge";
  }
  if (
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
  if (hashIdx === -1) {
    return { path: href || "/", hash: "" };
  }
  return {
    path: href.slice(0, hashIdx) || "/",
    hash: href.slice(hashIdx),
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

  if (itemPath === "/") {
    return normalizedPath === "/" && !currentHash;
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
