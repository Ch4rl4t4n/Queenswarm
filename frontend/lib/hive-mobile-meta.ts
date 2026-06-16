/** Route labels used by compact mobile chrome (hive header + titles). */
import { AGENTIC_OS_PRODUCT_NAME } from "@/lib/cross-route-naming";
import { OPERATOR_CONTROL_PLANE_ENABLED, PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { hiveMissionControlPageTitle } from "@/lib/hive-home-route";

export interface MobileRouteMeta {
  kicker: string;
  pageTitleSuffix?: string;
  staticSubtitle?: string;
}

const AGENTIC_OS_ROUTE_META: MobileRouteMeta = {
  kicker: AGENTIC_OS_PRODUCT_NAME,
  staticSubtitle: "Operator control plane · now actions",
  pageTitleSuffix: AGENTIC_OS_PRODUCT_NAME,
};

function routeTable(consolidatedEnabled: boolean): { prefix: string; meta: MobileRouteMeta }[] {
  return [
    ...(consolidatedEnabled
      ? [
          ...(OPERATOR_CONTROL_PLANE_ENABLED
            ? [
                { prefix: "/agentic-os", meta: AGENTIC_OS_ROUTE_META },
                { prefix: "/cockpit", meta: AGENTIC_OS_ROUTE_META },
              ]
            : []),
          { prefix: "/dashboard", meta: { kicker: "Dashboard", staticSubtitle: "Overview · monitoring · costs", pageTitleSuffix: "Dashboard" } },
          { prefix: "/overview", meta: { kicker: "Dashboard", staticSubtitle: "Overview · monitoring · costs", pageTitleSuffix: "Dashboard" } },
          { prefix: "/execution", meta: { kicker: "Tasks", staticSubtitle: "Tasks · workflows · jobs · routines", pageTitleSuffix: "Tasks" } },
          { prefix: "/knowledge", meta: { kicker: "Knowledge", staticSubtitle: "HiveMind · outputs · recipes", pageTitleSuffix: "Knowledge" } },
          { prefix: "/hive-mind", meta: { kicker: "Knowledge", staticSubtitle: "HiveMind alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/outputs", meta: { kicker: "Knowledge", staticSubtitle: "Outputs alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/learning", meta: { kicker: "Knowledge", staticSubtitle: "Learning alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/recipes", meta: { kicker: "Knowledge", staticSubtitle: "Recipes alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/integrations", meta: { kicker: "Integrations", staticSubtitle: "Connectors · plugins · external apps", pageTitleSuffix: "Integrations" } },
          { prefix: "/apps-tools", meta: { kicker: "Apps & Tools", staticSubtitle: "Domain workspaces · factory · MCP", pageTitleSuffix: "Apps & Tools" } },
          { prefix: "/apps-tools/marketing-automation", meta: { kicker: "Apps & Tools", staticSubtitle: "Publish queue · social distribution", pageTitleSuffix: "Marketing Automation" } },
          { prefix: "/apps-tools/content-factory", meta: { kicker: "Apps & Tools", staticSubtitle: "Pack Factory · Research", pageTitleSuffix: "Apps & Tools" } },
          { prefix: "/apps-tools/trading-automation", meta: { kicker: "Apps & Tools", staticSubtitle: "Trading cockpit · live lane", pageTitleSuffix: "Trading Automation" } },
          { prefix: "/apps-tools/trading-journal", meta: { kicker: "Apps & Tools", staticSubtitle: "Studio settings · review cron", pageTitleSuffix: "Trading Journal" } },
          { prefix: "/apps-tools/browser-automation", meta: { kicker: "Apps & Tools", staticSubtitle: "Operator-approved browser harness", pageTitleSuffix: "Browser Automation" } },
          { prefix: "/apps-tools/research-workspace", meta: { kicker: "Apps & Tools", staticSubtitle: "Briefing-first research lane", pageTitleSuffix: "Research Workspace" } },
          { prefix: "/apps-tools/analytics", meta: { kicker: "Apps & Tools", staticSubtitle: "Decision-ready analytics reports", pageTitleSuffix: "Analytics Workspace" } },
          { prefix: "/apps-tools/mcp-ops-studio", meta: { kicker: "Apps & Tools", staticSubtitle: "MCP Ops · Catalog", pageTitleSuffix: "Apps & Tools" } },
          { prefix: "/manual", meta: { kicker: "Manual", staticSubtitle: "Operator docs · app functions", pageTitleSuffix: "Manual" } },
          { prefix: "/foragers", meta: { kicker: "Foragers", staticSubtitle: "Dynamic ingest workers · spawn flow", pageTitleSuffix: "Foragers" } },
          { prefix: "/routines", meta: { kicker: "Routines", staticSubtitle: "Supervisor schedules · webhooks · L3/L4", pageTitleSuffix: "Routines" } },
          { prefix: "/monitoring", meta: { kicker: "Monitoring", staticSubtitle: "Host pressure · queues · telemetry", pageTitleSuffix: "Monitoring" } },
          { prefix: "/factory", meta: { kicker: "Apps & Tools", staticSubtitle: "Simulate-first MVP blueprint lane", pageTitleSuffix: "Micro-SaaS Factory" } },
          { prefix: "/connectors", meta: { kicker: "Integrations", staticSubtitle: "Connector hub alias · consolidated view", pageTitleSuffix: "Integrations" } },
          { prefix: "/external-projects", meta: { kicker: "Integrations", staticSubtitle: "External apps alias · consolidated view", pageTitleSuffix: "Integrations" } },
          { prefix: "/plugins", meta: { kicker: "Integrations", staticSubtitle: "Plugin catalog alias · consolidated view", pageTitleSuffix: "Integrations" } },
        ]
      : []),
    { prefix: "/settings/security", meta: { kicker: "Settings", staticSubtitle: "Security · 2FA · passwords", pageTitleSuffix: "Security" } },
    { prefix: "/settings/billing", meta: { kicker: "Settings", staticSubtitle: "Legacy alias · redirects to Costs", pageTitleSuffix: "Costs" } },
    { prefix: "/settings/team", meta: { kicker: "Settings", staticSubtitle: "Members · roles · invites", pageTitleSuffix: "Team" } },
    { prefix: "/settings/audit", meta: { kicker: "Settings", staticSubtitle: "Admin actions · overrides · exports", pageTitleSuffix: "Audit log" } },
    { prefix: "/settings/sharing", meta: { kicker: "Settings", staticSubtitle: "Public links · embed · revoke", pageTitleSuffix: "Public sharing" } },
    { prefix: "/settings/enterprise", meta: { kicker: "Settings", staticSubtitle: "SSO · SCIM · workspace policy", pageTitleSuffix: "Enterprise" } },
    { prefix: "/settings/api-keys", meta: { kicker: "Settings", staticSubtitle: "Dashboard API keys", pageTitleSuffix: "API keys" } },
    { prefix: "/settings/llm-keys", meta: { kicker: "Settings", staticSubtitle: "LLM routing · Grok vault · voice", pageTitleSuffix: "LLM & Voice" } },
    { prefix: "/settings/notifications", meta: { kicker: "Settings", staticSubtitle: "Alerts · channels", pageTitleSuffix: "Notifications" } },
    { prefix: "/settings/capabilities", meta: { kicker: "Settings", staticSubtitle: "Features · architecture · roadmap", pageTitleSuffix: "Capabilities" } },
    { prefix: "/settings/harness", meta: { kicker: "Settings", staticSubtitle: "AI Layer · rules · skills · patterns", pageTitleSuffix: "Harness" } },
    { prefix: "/settings", meta: { kicker: "Settings", staticSubtitle: "Operator cockpit preferences", pageTitleSuffix: "Settings" } },
    { prefix: "/external-projects", meta: { kicker: "External", staticSubtitle: "MCP · REST · WebSocket bridges", pageTitleSuffix: "External projects" } },
    { prefix: "/connectors", meta: { kicker: "Connectors", staticSubtitle: "Phase 3 MCP · Gmail to TikTok · vault sync", pageTitleSuffix: "Connectors" } },
    { prefix: "/hive-mind", meta: { kicker: "HiveMind", staticSubtitle: "Shared constellation · embeddings", pageTitleSuffix: "HiveMind" } },
    { prefix: "/outputs", meta: { kicker: "Outputs", staticSubtitle: "Archived deliverables · semantic search", pageTitleSuffix: "Outputs" } },
    { prefix: "/learning", meta: { kicker: "Learning", staticSubtitle: "Pollen · imitation · reflections", pageTitleSuffix: "Learning" } },
    { prefix: "/jobs", meta: { kicker: "Jobs", staticSubtitle: "Celery · async workflow polling", pageTitleSuffix: "Jobs" } },
    { prefix: "/ballroom", meta: { kicker: "Ballroom", staticSubtitle: "Voice + chat", pageTitleSuffix: "Ballroom" } },
    { prefix: "/workflows", meta: { kicker: "Workflows", staticSubtitle: "DAG · pause · cancel", pageTitleSuffix: "Workflows" } },
    { prefix: "/tasks/new", meta: { kicker: hiveMissionControlPageTitle(), staticSubtitle: "Compose a new swarm mission", pageTitleSuffix: "New task" } },
    { prefix: "/tasks", meta: { kicker: hiveMissionControlPageTitle(), staticSubtitle: "Mission Kanban · backlog · assignments", pageTitleSuffix: hiveMissionControlPageTitle() } },
    { prefix: "/agents/new", meta: { kicker: "Agents", staticSubtitle: "Spawn a dynamic bee", pageTitleSuffix: "New agent" } },
    { prefix: "/agents", meta: { kicker: "Agents", staticSubtitle: "Sessions · roster · hierarchy", pageTitleSuffix: "Agents" } },
    { prefix: "/swarms/new", meta: { kicker: "Swarms", staticSubtitle: "Opinionated swarm templates", pageTitleSuffix: "Swarm Builder" } },
    { prefix: "/swarms", meta: { kicker: "Swarms", staticSubtitle: "Colonies · purposes · pollen", pageTitleSuffix: "Swarms" } },
    { prefix: "/hierarchy", meta: { kicker: "Agents", staticSubtitle: "Hierarchy alias · graph view", pageTitleSuffix: "Agents" } },
    { prefix: "/settings/costs", meta: { kicker: "Settings", staticSubtitle: "Costs · spend · models · caps", pageTitleSuffix: "Costs" } },
    { prefix: "/plugins", meta: { kicker: "Plugins", staticSubtitle: "Built-ins · operator uploads", pageTitleSuffix: "Plugins" } },
    { prefix: "/simulations", meta: { kicker: "Simulations", staticSubtitle: "Verified sandbox ledger", pageTitleSuffix: "Simulations" } },
    { prefix: "/recipes", meta: { kicker: "Recipes", staticSubtitle: "Library · semantic recall · tags", pageTitleSuffix: "Recipes" } },
    { prefix: "/design-system", meta: { kicker: "Design", staticSubtitle: "Neon-dark tokens preview", pageTitleSuffix: "Design system" } },
  ];
}

function longestPrefixMeta(pathname: string, consolidatedEnabled: boolean): MobileRouteMeta | null {
  let best: MobileRouteMeta | null = null;
  let bestLen = -1;
  for (const row of routeTable(consolidatedEnabled)) {
    if (pathname === row.prefix || pathname.startsWith(`${row.prefix}/`)) {
      if (row.prefix.length > bestLen) {
        bestLen = row.prefix.length;
        best = row.meta;
      }
    }
  }
  return best;
}

export function hiveMobileRouteMeta(pathname: string, consolidatedEnabled: boolean = PHASE70_CONSOLIDATED_NAV_ENABLED): MobileRouteMeta {
  if (pathname === "/") {
    if (OPERATOR_CONTROL_PLANE_ENABLED) {
      return AGENTIC_OS_ROUTE_META;
    }
    return { kicker: "Dashboard", staticSubtitle: "Live swarm roster", pageTitleSuffix: "Dashboard" };
  }

  const hit = longestPrefixMeta(pathname, consolidatedEnabled);
  if (hit) {
    return hit;
  }

  return { kicker: "QueenSwarm", staticSubtitle: "Agentic OS hub" };
}
