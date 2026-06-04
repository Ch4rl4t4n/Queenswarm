/**
 * Whole-App UI Reorder — mobile/tablet QA route matrix (Phase 6).
 * Primary zone routes + secondary More-menu / settings / apps-tools modules.
 */

import { HIVE_PAGE_ZONE_SPECS } from "@/lib/hive-page-zone-spec";

/** Sticky mobile header brand — home link on all routes (see HiveMobileHeader). */
export const MOBILE_HEADER_HOME_BRAND = "QueenSwarm";

export interface MobileTabletRouteSpec {
  path: string;
  /** @deprecated Header shows MOBILE_HEADER_HOME_BRAND; kept for route docs / legacy tests. */
  mobileTitle: string;
  /** Expected hive-page-shell h1 when route uses HivePageShell. */
  shellTitle?: string;
  /** Expected panel h2 inside nested shell content (e.g. Settings → Costs). */
  panelHeading?: string | RegExp;
  /** Fallback heading when page uses HivePageHeader only (legacy). */
  contentHeading?: string | RegExp;
  /** Requires operator control plane feature flag. */
  requiresCp?: boolean;
}

/** Top-level IA zone routes — each must render HivePageShell with matching title. */
export const MOBILE_TABLET_ZONE_ROUTE_SPECS: MobileTabletRouteSpec[] = [
  ...HIVE_PAGE_ZONE_SPECS.map((spec) => ({
    path: spec.path,
    mobileTitle: spec.title,
    shellTitle: spec.title,
    requiresCp: spec.path === "/agentic-os",
  })),
  { path: "/settings/security", mobileTitle: "Settings", shellTitle: "Settings" },
  { path: "/manual", mobileTitle: "Manual", shellTitle: "Manual" },
];

/**
 * Secondary routes — More menu, execution hub, settings panels, Apps & Tools modules.
 * Phase 6.2 mobile/tablet pass.
 */
export const MOBILE_TABLET_SECONDARY_ROUTE_SPECS: MobileTabletRouteSpec[] = [
  { path: "/foragers", mobileTitle: "Foragers", shellTitle: "Foragers" },
  { path: "/routines", mobileTitle: "Routines", shellTitle: "Routines" },
  { path: "/factory", mobileTitle: "Micro-SaaS Factory", shellTitle: "Micro-SaaS Factory" },
  { path: "/jobs", mobileTitle: "Jobs", shellTitle: "Async workflow jobs" },
  { path: "/workflows", mobileTitle: "Workflows", shellTitle: "Workflows" },
  { path: "/monitoring", mobileTitle: "Monitoring", shellTitle: "Monitoring" },
  { path: "/simulations", mobileTitle: "Simulations", shellTitle: "Simulations" },
  { path: "/tasks/new", mobileTitle: "New task", shellTitle: "New task" },
  { path: "/agents/new", mobileTitle: "New agent", shellTitle: "New agent" },
  { path: "/settings/costs", mobileTitle: "Costs", shellTitle: "Settings", panelHeading: /^Costs$/ },
  { path: "/settings/team", mobileTitle: "Team", shellTitle: "Settings" },
  { path: "/settings/enterprise", mobileTitle: "Enterprise", shellTitle: "Settings" },
  { path: "/settings/harness", mobileTitle: "Harness", shellTitle: "Settings" },
  { path: "/settings/capabilities", mobileTitle: "Capabilities", shellTitle: "Settings" },
  { path: "/settings/llm-keys", mobileTitle: "LLM & Voice", shellTitle: "Settings", panelHeading: /Grok \(xAI\)/i },
  { path: "/settings/notifications", mobileTitle: "Notifications", shellTitle: "Settings", panelHeading: /^Email$/ },
  { path: "/settings/api-keys", mobileTitle: "API keys", shellTitle: "Settings", panelHeading: /External data APIs/i },
  { path: "/settings/audit", mobileTitle: "Audit log", shellTitle: "Settings", panelHeading: /^Audit log$/ },
  { path: "/settings/sharing", mobileTitle: "Public sharing", shellTitle: "Settings", panelHeading: /^Public sharing$/ },
  { path: "/apps-tools/marketing-automation", mobileTitle: "Marketing Automation", shellTitle: "Marketing Automation" },
  { path: "/apps-tools/content-factory", mobileTitle: "Pack Factory", shellTitle: "Apps & Tools" },
  { path: "/apps-tools/trading-automation", mobileTitle: "Trading Automation", shellTitle: "Trading Automation" },
  { path: "/apps-tools/browser-automation", mobileTitle: "Browser Automation", shellTitle: "Browser Automation" },
  { path: "/apps-tools/research-workspace", mobileTitle: "Research Workspace", shellTitle: "Research Workspace" },
  { path: "/apps-tools/mcp-ops-studio", mobileTitle: "MCP Ops", shellTitle: "Apps & Tools" },
];

/** Full mobile/tablet regression matrix (zones + secondary). */
export const MOBILE_TABLET_ROUTE_SPECS: MobileTabletRouteSpec[] = [
  ...MOBILE_TABLET_ZONE_ROUTE_SPECS,
  ...MOBILE_TABLET_SECONDARY_ROUTE_SPECS,
];

export function mobileTabletRouteSpecCount(): number {
  return MOBILE_TABLET_ROUTE_SPECS.length;
}
