/** Route labels used by compact mobile chrome (hive header + titles). */
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";

export interface MobileRouteMeta {
  kicker: string;
  pageTitleSuffix?: string;
  staticSubtitle?: string;
}

function routeTable(consolidatedEnabled: boolean): { prefix: string; meta: MobileRouteMeta }[] {
  return [
    ...(consolidatedEnabled
      ? [
          { prefix: "/dashboard", meta: { kicker: "Dashboard", staticSubtitle: "Overview · monitoring · costs", pageTitleSuffix: "Dashboard" } },
          { prefix: "/overview", meta: { kicker: "Dashboard", staticSubtitle: "Overview · monitoring · costs", pageTitleSuffix: "Dashboard" } },
          { prefix: "/execution", meta: { kicker: "Tasks", staticSubtitle: "Tasks · workflows · jobs · routines", pageTitleSuffix: "Tasks" } },
          { prefix: "/knowledge", meta: { kicker: "Knowledge", staticSubtitle: "HiveMind · outputs · recipes", pageTitleSuffix: "Knowledge" } },
          { prefix: "/hive-mind", meta: { kicker: "Knowledge", staticSubtitle: "HiveMind alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/outputs", meta: { kicker: "Knowledge", staticSubtitle: "Outputs alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/learning", meta: { kicker: "Knowledge", staticSubtitle: "Learning alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/recipes", meta: { kicker: "Knowledge", staticSubtitle: "Recipes alias · consolidated view", pageTitleSuffix: "Knowledge" } },
          { prefix: "/integrations", meta: { kicker: "Integrations", staticSubtitle: "Connectors · plugins · external apps", pageTitleSuffix: "Integrations" } },
          { prefix: "/connectors", meta: { kicker: "Integrations", staticSubtitle: "Connector hub alias · consolidated view", pageTitleSuffix: "Integrations" } },
          { prefix: "/external-projects", meta: { kicker: "Integrations", staticSubtitle: "External apps alias · consolidated view", pageTitleSuffix: "Integrations" } },
          { prefix: "/plugins", meta: { kicker: "Integrations", staticSubtitle: "Plugin catalog alias · consolidated view", pageTitleSuffix: "Integrations" } },
        ]
      : []),
    { prefix: "/settings/security", meta: { kicker: "Settings", staticSubtitle: "Security · 2FA · passwords", pageTitleSuffix: "Security" } },
    { prefix: "/settings/api-keys", meta: { kicker: "Settings", staticSubtitle: "Dashboard API keys", pageTitleSuffix: "API keys" } },
    { prefix: "/settings/llm-keys", meta: { kicker: "Settings", staticSubtitle: "LLM vault · routing", pageTitleSuffix: "LLM keys" } },
    { prefix: "/settings/notifications", meta: { kicker: "Settings", staticSubtitle: "Alerts · channels", pageTitleSuffix: "Notifications" } },
    { prefix: "/settings/capabilities", meta: { kicker: "Settings", staticSubtitle: "Features · architecture · roadmap", pageTitleSuffix: "Capabilities" } },
    { prefix: "/settings", meta: { kicker: "Settings", staticSubtitle: "Operator cockpit preferences", pageTitleSuffix: "Settings" } },
    { prefix: "/external-projects", meta: { kicker: "External", staticSubtitle: "MCP · REST · WebSocket bridges", pageTitleSuffix: "External projects" } },
    { prefix: "/connectors", meta: { kicker: "Connectors", staticSubtitle: "Phase 3 MCP · Gmail to Stripe · vault sync", pageTitleSuffix: "Connectors" } },
    { prefix: "/hive-mind", meta: { kicker: "HiveMind", staticSubtitle: "Shared constellation · embeddings", pageTitleSuffix: "HiveMind" } },
    { prefix: "/outputs", meta: { kicker: "Outputs", staticSubtitle: "Archived deliverables · semantic search", pageTitleSuffix: "Outputs" } },
    { prefix: "/learning", meta: { kicker: "Learning", staticSubtitle: "Pollen · imitation · reflections", pageTitleSuffix: "Learning" } },
    { prefix: "/jobs", meta: { kicker: "Jobs", staticSubtitle: "Celery · async workflow polling", pageTitleSuffix: "Async jobs" } },
    { prefix: "/ballroom", meta: { kicker: "Ballroom", staticSubtitle: "Voice + chat", pageTitleSuffix: "Ballroom" } },
    { prefix: "/workflows", meta: { kicker: "Workflows", staticSubtitle: "DAG · pause · cancel", pageTitleSuffix: "Workflows" } },
    { prefix: "/tasks/new", meta: { kicker: "Tasks", staticSubtitle: "Compose a new swarm mission", pageTitleSuffix: "New task" } },
    { prefix: "/tasks", meta: { kicker: "Tasks", staticSubtitle: "Backlog · assignments", pageTitleSuffix: "Tasks" } },
    { prefix: "/agents/new", meta: { kicker: "Agents", staticSubtitle: "Spawn a dynamic bee", pageTitleSuffix: "New agent" } },
    { prefix: "/agents", meta: { kicker: "Agents", staticSubtitle: "Sessions · roster · hierarchy", pageTitleSuffix: "Agents" } },
    { prefix: "/swarms/new", meta: { kicker: "Swarms", staticSubtitle: "Opinionated swarm templates", pageTitleSuffix: "Swarm Builder" } },
    { prefix: "/swarms", meta: { kicker: "Swarms", staticSubtitle: "Colonies · purposes · pollen", pageTitleSuffix: "Swarms" } },
    { prefix: "/hierarchy", meta: { kicker: "Agents", staticSubtitle: "Hierarchy alias · graph view", pageTitleSuffix: "Agents" } },
    { prefix: "/costs", meta: { kicker: "Costs", staticSubtitle: "Spend · models · caps", pageTitleSuffix: "Costs" } },
    { prefix: "/leaderboard", meta: { kicker: "Leaderboard", staticSubtitle: "Pollen prestige · colonies · recipes", pageTitleSuffix: "Leaderboard" } },
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
    return consolidatedEnabled
      ? { kicker: "Dashboard", staticSubtitle: "Live swarm roster", pageTitleSuffix: "Dashboard" }
      : { kicker: "Dashboard", staticSubtitle: "Live swarm roster", pageTitleSuffix: "Dashboard" };
  }

  const hit = longestPrefixMeta(pathname, consolidatedEnabled);
  if (hit) {
    return hit;
  }

  return { kicker: "QueenSwarm", staticSubtitle: "Hive cockpit" };
}
