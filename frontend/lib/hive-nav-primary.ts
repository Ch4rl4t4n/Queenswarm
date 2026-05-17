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
  Coins,
  FileText,
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
} from "lucide-react";
import {
  ADVANCED_MONITORING_ENABLED,
  LEADERBOARD_ENABLED,
  PHASE70_CONSOLIDATED_NAV_ENABLED,
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
}

/** Ordered rail — desktop shows full list (scroll); mobile drawer mirrors this. */
export function buildHiveNavPrimary(consolidatedEnabled: boolean): HiveNavItem[] {
  if (!consolidatedEnabled) {
    return [
      { href: "/", label: "Dashboard", Icon: LayoutDashboardIcon, bottomNav: true, section: "overview" },
      { href: "/agents", label: "Agents", Icon: Users, bottomNav: true, section: "agents" },
      { href: "/tasks", label: "Tasks", Icon: ListTodo, bottomNav: true, section: "execution" },
      { href: "/hive-mind", label: "HiveMind", Icon: Brain, section: "knowledge" },
      { href: "/connectors", label: "Connectors", Icon: Cable, section: "integrations" },
      { href: "/ballroom", label: "Ballroom", Icon: MicIcon, bottomNav: true, section: "ballroom" },
      { href: "/settings/security", label: "Settings", Icon: Settings, section: "settings" },
      { href: "/manual", label: "Manual", Icon: CircleHelp, section: "manual" },
    ];
  }

  return [
    { href: "/", label: "Dashboard", Icon: LayoutDashboardIcon, bottomNav: true, section: "overview" },
    { href: "/agents", label: "Agents", Icon: Users, bottomNav: true, section: "agents" },
    { href: "/tasks", label: "Tasks", Icon: ListTodo, bottomNav: true, section: "execution" },
    { href: "/knowledge", label: "Knowledge", Icon: Brain, section: "knowledge" },
    { href: "/integrations", label: "Integrations", Icon: Cable, section: "integrations" },
    { href: "/ballroom", label: "Ballroom", Icon: MicIcon, bottomNav: true, section: "ballroom" },
    { href: "/settings/security", label: "Settings", Icon: Settings, section: "settings" },
    { href: "/manual", label: "Manual", Icon: CircleHelp, section: "manual" },
  ];
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
        { href: "/costs", label: "Costs", Icon: Coins, section: "overview" },
        { href: "/#hive-live-swarm", label: "Live network", Icon: Hexagon, section: "overview" },
        { href: "/swarms", label: "Swarms", Icon: Share2, section: "overview" },
      ],
    },
    {
      title: "Agents",
      items: [
        { href: "/agents", label: consolidatedEnabled ? "Agents hub" : "Agents", Icon: Users, section: "agents" },
        { href: "/agents/new", label: "Spawn agent", Icon: ClipboardList, section: "agents" },
        { href: "/agents#hierarchy", label: "Hierarchy", Icon: Share2, section: "agents" },
      ],
    },
    {
      title: "Execution",
      items: [
        ...(consolidatedEnabled
          ? [{ href: "/tasks", label: "Tasks hub", Icon: ListTodo, section: "execution" as const }]
          : []),
        { href: "/tasks/new", label: "New task", Icon: ClipboardList, section: "execution" },
        { href: "/tasks", label: "Tasks", Icon: ListTodo, section: "execution" },
        { href: "/workflows", label: "Workflows", Icon: GitBranch, section: "execution" },
        { href: "/jobs", label: "Async jobs", Icon: Briefcase, section: "execution" },
        ...(SIMULATIONS_ENABLED
          ? [{ href: "/simulations", label: "Simulations", Icon: FlaskConical, section: "execution" as const }]
          : []),
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
          href: consolidatedEnabled ? "/integrations#hub" : "/connectors",
          label: "Connectors",
          Icon: Cable,
          section: "integrations",
        },
        {
          href: consolidatedEnabled ? "/integrations#external" : "/external-projects",
          label: "External apps",
          Icon: Boxes,
          section: "integrations",
        },
        {
          href: consolidatedEnabled ? "/integrations#plugins" : "/plugins",
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

export function hiveBottomNavItems(): HiveNavItem[] {
  const flagged = HIVE_NAV_PRIMARY.filter((i) => i.bottomNav);
  return flagged.length ? flagged : HIVE_NAV_PRIMARY.slice(0, 3);
}

export function sectionForPath(pathname: string): string {
  const normalized = pathname === "" ? "/" : pathname;
  if (
    normalized === "/" ||
    normalized.startsWith("/dashboard") ||
    normalized.startsWith("/overview") ||
    normalized.startsWith("/monitoring") ||
    normalized.startsWith("/costs") ||
    normalized.startsWith("/swarms")
  ) {
    return "overview";
  }
  if (normalized.startsWith("/agents") || normalized.startsWith("/hierarchy")) {
    return "agents";
  }
  if (
    normalized.startsWith("/execution") ||
    normalized.startsWith("/tasks") ||
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

export function isNavItemActive(pathname: string, item: HiveNavItem): boolean {
  if (item.href.startsWith("/#")) {
    return pathname === "/";
  }
  if (item.href === "/") {
    return pathname === "/";
  }
  if (pathname === item.href || pathname.startsWith(`${item.href}/`)) {
    return true;
  }
  if (item.section) {
    return sectionForPath(pathname) === item.section;
  }
  return false;
}
