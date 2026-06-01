/**
 * Whole-App UI Reorder — canonical information architecture (v1).
 * Single source of truth for primary sidebar order, zones, and More-menu coverage.
 */

import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Boxes,
  Brain,
  Briefcase,
  Cable,
  ClipboardList,
  Factory,
  FileText,
  FlaskConical,
  GitBranch,
  LayoutDashboardIcon,
  ListTodo,
  MicIcon,
  Puzzle,
  ScrollText,
  Settings,
  Share2,
  CircleHelp,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";

import { integrationsTabHref } from "@/lib/integrations-routes";
import { hiveOverviewHref } from "@/lib/hive-home-route";

/** IA version — bump when primary rail order or zones change. */
export const WHOLE_APP_IA_VERSION = "2026.05-v1";

export type HiveNavSection =
  | "overview"
  | "agents"
  | "execution"
  | "knowledge"
  | "integrations"
  | "ballroom"
  | "settings"
  | "manual";

/** Top-level product zones aligned with AGENTIC_OS_APPS_BLUEPRINT. */
export type HiveIaZone = "agentic_os" | "apps_tools" | "integrations" | "knowledge" | "ballroom";

export interface HiveIaPrimarySpec {
  href: string;
  label: string;
  Icon: LucideIcon;
  iaZone: HiveIaZone;
  bottomNav?: boolean;
  section: HiveNavSection;
  featureKey?: string;
}

export interface HiveIaNavItem {
  href: string;
  label: string;
  Icon: LucideIcon;
  bottomNav?: boolean;
  section?: HiveNavSection;
  featureKey?: string;
  iaZone?: HiveIaZone;
}

/** Operator Control Plane — canonical primary rail (9 items, 5 zones). */
export const CANONICAL_PRIMARY_CP: HiveIaPrimarySpec[] = [
  {
    href: "/agentic-os",
    label: "Agentic OS",
    Icon: Zap,
    iaZone: "agentic_os",
    bottomNav: true,
    section: "overview",
    featureKey: "operator_cockpit",
  },
  {
    href: "/swarms",
    label: "Swarms",
    Icon: Share2,
    iaZone: "agentic_os",
    section: "overview",
    featureKey: "swarms",
  },
  {
    href: "/tasks",
    label: "Tasks",
    Icon: ListTodo,
    iaZone: "agentic_os",
    bottomNav: true,
    section: "execution",
    featureKey: "tasks",
  },
  {
    href: "/agents",
    label: "Agents",
    Icon: Users,
    iaZone: "agentic_os",
    bottomNav: true,
    section: "agents",
    featureKey: "agents",
  },
  {
    href: "/foragers",
    label: "Foragers",
    Icon: Sparkles,
    iaZone: "agentic_os",
    section: "agents",
    featureKey: "foragers",
  },
  {
    href: "/apps-tools",
    label: "Apps & Tools",
    Icon: Boxes,
    iaZone: "apps_tools",
    section: "integrations",
    featureKey: "integrations",
  },
  {
    href: "/integrations",
    label: "Integrations",
    Icon: Cable,
    iaZone: "integrations",
    section: "integrations",
    featureKey: "integrations",
  },
  {
    href: "/knowledge",
    label: "Knowledge",
    Icon: Brain,
    iaZone: "knowledge",
    bottomNav: true,
    section: "knowledge",
    featureKey: "knowledge",
  },
  {
    href: "/ballroom",
    label: "Ballroom",
    Icon: MicIcon,
    iaZone: "ballroom",
    section: "ballroom",
    featureKey: "ballroom",
  },
];

/** Expected primary href order for regression tests. */
export const CANONICAL_PRIMARY_CP_HREFS: readonly string[] = CANONICAL_PRIMARY_CP.map((row) => row.href);

/** Routes that must appear in mobile More menu but not primary rail. */
export const CANONICAL_MORE_ONLY_HREFS: readonly string[] = [
  "/factory",
  "/apps-tools/content-factory",
  "/workflows",
  "/jobs",
  "/dashboard",
];

/** Map canonical spec → runtime nav item (adds iaZone for sidebar dividers). */
export function toHiveNavItems(specs: HiveIaPrimarySpec[]): HiveIaNavItem[] {
  return specs.map((row) => ({
    href: row.href,
    label: row.label,
    Icon: row.Icon,
    bottomNav: row.bottomNav,
    section: row.section,
    featureKey: row.featureKey,
    iaZone: row.iaZone,
  }));
}

/** Legacy consolidated nav (non–control-plane). */
export function buildLegacyConsolidatedPrimary(): HiveIaNavItem[] {
  return [
    {
      href: hiveOverviewHref(),
      label: "Dashboard",
      Icon: LayoutDashboardIcon,
      bottomNav: true,
      section: "overview",
      featureKey: "dashboard",
      iaZone: "agentic_os",
    },
    {
      href: "/swarms",
      label: "Swarms",
      Icon: Share2,
      section: "overview",
      featureKey: "swarms",
      iaZone: "agentic_os",
    },
    {
      href: "/agents",
      label: "Agents",
      Icon: Users,
      bottomNav: true,
      section: "agents",
      featureKey: "agents",
      iaZone: "agentic_os",
    },
    {
      href: "/foragers",
      label: "Foragers",
      Icon: Sparkles,
      section: "agents",
      featureKey: "foragers",
      iaZone: "agentic_os",
    },
    {
      href: "/tasks",
      label: "Tasks",
      Icon: ListTodo,
      bottomNav: true,
      section: "execution",
      featureKey: "tasks",
      iaZone: "agentic_os",
    },
    {
      href: "/factory",
      label: "Factory",
      Icon: Factory,
      section: "execution",
      featureKey: "skills_export_factory",
      iaZone: "apps_tools",
    },
    {
      href: "/knowledge",
      label: "Knowledge",
      Icon: Brain,
      section: "knowledge",
      featureKey: "knowledge",
      iaZone: "knowledge",
    },
    {
      href: "/integrations",
      label: "Integrations",
      Icon: Cable,
      section: "integrations",
      featureKey: "integrations",
      iaZone: "integrations",
    },
    {
      href: "/ballroom",
      label: "Ballroom",
      Icon: MicIcon,
      bottomNav: true,
      section: "ballroom",
      featureKey: "ballroom",
      iaZone: "ballroom",
    },
  ];
}

export type HiveNavGroupSpec = { title: string; items: HiveIaNavItem[] };

/** Build grouped More-menu sections — deduped, blueprint-aligned. */
export function buildCanonicalNavGroups(options: {
  consolidatedEnabled: boolean;
  operatorControlPlane: boolean;
  advancedMonitoring: boolean;
  simulationsEnabled: boolean;
  recipesEnabled: boolean;
}): HiveNavGroupSpec[] {
  const { consolidatedEnabled, operatorControlPlane, advancedMonitoring, simulationsEnabled, recipesEnabled } =
    options;

  return [
    {
      title: "Agentic OS",
      items: [
        ...(operatorControlPlane && consolidatedEnabled
          ? [
              { href: "/agentic-os", label: "Agentic OS", Icon: Zap, section: "overview" as const, iaZone: "agentic_os" as const },
              { href: "/dashboard", label: "Advanced dashboard", Icon: LayoutDashboardIcon, section: "overview" as const, iaZone: "agentic_os" as const },
            ]
          : [{ href: hiveOverviewHref(), label: "Dashboard", Icon: LayoutDashboardIcon, section: "overview" as const, iaZone: "agentic_os" as const }]),
        ...(advancedMonitoring
          ? [{ href: "/monitoring", label: "Monitoring", Icon: Activity, section: "overview" as const, iaZone: "agentic_os" as const }]
          : []),
        { href: "/swarms", label: "Swarms", Icon: Share2, section: "overview" as const, iaZone: "agentic_os" as const },
      ],
    },
    {
      title: "Agents",
      items: [
        { href: "/agents", label: consolidatedEnabled ? "Agents hub" : "Agents", Icon: Users, section: "agents", iaZone: "agentic_os" },
        { href: "/agents/new", label: "Spawn agent", Icon: ClipboardList, section: "agents", iaZone: "agentic_os" },
        { href: "/foragers", label: "Foragers", Icon: Sparkles, section: "agents", iaZone: "agentic_os" },
        { href: "/agents#hierarchy", label: "Hierarchy", Icon: Share2, section: "agents", iaZone: "agentic_os" },
      ],
    },
    {
      title: "Execution",
      items: [
        { href: "/tasks", label: consolidatedEnabled ? "Tasks hub" : "Tasks", Icon: ListTodo, section: "execution", iaZone: "agentic_os" },
        { href: "/tasks/new", label: "New task", Icon: ClipboardList, section: "execution", iaZone: "agentic_os" },
        { href: "/workflows", label: "Workflows", Icon: GitBranch, section: "execution", iaZone: "agentic_os" },
        ...(simulationsEnabled
          ? [{ href: "/simulations", label: "Simulations", Icon: FlaskConical, section: "execution" as const, iaZone: "agentic_os" as const }]
          : []),
        { href: "/jobs", label: "Jobs", Icon: Briefcase, section: "execution", iaZone: "agentic_os" },
      ],
    },
    {
      title: "Knowledge",
      items: [
        ...(consolidatedEnabled
          ? [{ href: "/knowledge", label: "Knowledge hub", Icon: Brain, section: "knowledge" as const, iaZone: "knowledge" as const }]
          : []),
        {
          href: consolidatedEnabled ? "/knowledge#hivemind" : "/hive-mind",
          label: "HiveMind",
          Icon: Brain,
          section: "knowledge",
          iaZone: "knowledge",
        },
        {
          href: consolidatedEnabled ? "/knowledge#outputs" : "/outputs",
          label: "Outputs",
          Icon: FileText,
          section: "knowledge",
          iaZone: "knowledge",
        },
        ...(recipesEnabled
          ? [
              {
                href: consolidatedEnabled ? "/knowledge#recipes" : "/recipes",
                label: "Recipes",
                Icon: ScrollText,
                section: "knowledge" as const,
                iaZone: "knowledge" as const,
              },
            ]
          : []),
      ],
    },
    {
      title: "Apps & Tools",
      items: [
        { href: "/apps-tools", label: "Module index", Icon: Boxes, section: "integrations", iaZone: "apps_tools" },
        { href: "/apps-tools/marketing-automation", label: "Marketing Automation", Icon: Zap, section: "integrations", iaZone: "apps_tools" },
        { href: "/apps-tools/trading-automation", label: "Trading Automation", Icon: Activity, section: "integrations", iaZone: "apps_tools" },
        { href: "/apps-tools/content-factory", label: "Content Factory", Icon: Factory, section: "integrations", iaZone: "apps_tools" },
        { href: "/factory", label: "Micro-SaaS Factory", Icon: Factory, section: "execution", featureKey: "skills_export_factory", iaZone: "apps_tools" },
        { href: integrationsTabHref("studio"), label: "Legacy Execution Studio", Icon: Zap, section: "integrations", iaZone: "apps_tools" },
        { href: integrationsTabHref("marketplace"), label: "Tools marketplace", Icon: Boxes, section: "integrations", iaZone: "apps_tools" },
        { href: integrationsTabHref("skills"), label: "Skills export", Icon: ScrollText, section: "integrations", iaZone: "apps_tools" },
      ],
    },
    {
      title: "Integrations",
      items: [
        ...(consolidatedEnabled
          ? [{ href: "/integrations", label: "Integrations hub", Icon: Cable, section: "integrations" as const, iaZone: "integrations" as const }]
          : []),
        {
          href: consolidatedEnabled ? integrationsTabHref("hub") : "/connectors",
          label: "Connectors",
          Icon: Cable,
          section: "integrations",
          iaZone: "integrations",
        },
        {
          href: consolidatedEnabled ? integrationsTabHref("external") : "/external-projects",
          label: "External apps",
          Icon: Boxes,
          section: "integrations",
          iaZone: "integrations",
        },
        {
          href: consolidatedEnabled ? integrationsTabHref("plugins") : "/plugins",
          label: "Plugins",
          Icon: Puzzle,
          section: "integrations",
          iaZone: "integrations",
        },
      ],
    },
    {
      title: "Ballroom",
      items: [{ href: "/ballroom", label: "Realtime Ballroom", Icon: MicIcon, section: "ballroom", iaZone: "ballroom" }],
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

/** True when a subtle zone divider should render before this item. */
export function shouldRenderIaZoneDivider(items: HiveIaNavItem[], index: number): boolean {
  if (index <= 0) {
    return false;
  }
  const prev = items[index - 1]?.iaZone;
  const current = items[index]?.iaZone;
  return Boolean(prev && current && prev !== current);
}
