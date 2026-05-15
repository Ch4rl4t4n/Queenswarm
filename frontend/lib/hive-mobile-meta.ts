/** Route labels used by compact mobile chrome (hive header + titles). */

export interface MobileRouteMeta {
  kicker: string;
  pageTitleSuffix?: string;
  staticSubtitle?: string;
}

const ROUTE_TABLE: { prefix: string; meta: MobileRouteMeta }[] = [
  { prefix: "/overview", meta: { kicker: "Overview", staticSubtitle: "Dashboard · monitoring · costs", pageTitleSuffix: "Overview" } },
  { prefix: "/execution", meta: { kicker: "Execution", staticSubtitle: "Tasks · workflows · jobs · routines", pageTitleSuffix: "Execution" } },
  { prefix: "/knowledge", meta: { kicker: "Knowledge", staticSubtitle: "HiveMind · outputs · recipes", pageTitleSuffix: "Knowledge" } },
  { prefix: "/integrations", meta: { kicker: "Integrations", staticSubtitle: "Connectors · plugins · external apps", pageTitleSuffix: "Integrations" } },
  { prefix: "/settings/security", meta: { kicker: "Settings", staticSubtitle: "Security · 2FA · passwords", pageTitleSuffix: "Security" } },
  { prefix: "/settings/api-keys", meta: { kicker: "Settings", staticSubtitle: "Dashboard API keys", pageTitleSuffix: "API keys" } },
  { prefix: "/settings/llm-keys", meta: { kicker: "Settings", staticSubtitle: "LLM vault · routing", pageTitleSuffix: "LLM keys" } },
  { prefix: "/settings/notifications", meta: { kicker: "Settings", staticSubtitle: "Alerts · channels", pageTitleSuffix: "Notifications" } },
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
  { prefix: "/agents", meta: { kicker: "Agents", staticSubtitle: "Roster · run · configure", pageTitleSuffix: "Agents" } },
  { prefix: "/swarms", meta: { kicker: "Swarms", staticSubtitle: "Colonies · purposes · pollen", pageTitleSuffix: "Swarms" } },
  { prefix: "/hierarchy", meta: { kicker: "Hierarchy", staticSubtitle: "Swarm layout · bees", pageTitleSuffix: "Hierarchy" } },
  { prefix: "/costs", meta: { kicker: "Costs", staticSubtitle: "Spend · models · caps", pageTitleSuffix: "Costs" } },
  { prefix: "/leaderboard", meta: { kicker: "Leaderboard", staticSubtitle: "Pollen prestige · colonies · recipes", pageTitleSuffix: "Leaderboard" } },
  { prefix: "/plugins", meta: { kicker: "Plugins", staticSubtitle: "Built-ins · operator uploads", pageTitleSuffix: "Plugins" } },
  { prefix: "/simulations", meta: { kicker: "Simulations", staticSubtitle: "Verified sandbox ledger", pageTitleSuffix: "Simulations" } },
  { prefix: "/recipes", meta: { kicker: "Recipes", staticSubtitle: "Library · semantic recall · tags", pageTitleSuffix: "Recipes" } },
  { prefix: "/design-system", meta: { kicker: "Design", staticSubtitle: "Neon-dark tokens preview", pageTitleSuffix: "Design system" } },
];

function longestPrefixMeta(pathname: string): MobileRouteMeta | null {
  let best: MobileRouteMeta | null = null;
  let bestLen = -1;
  for (const row of ROUTE_TABLE) {
    if (pathname === row.prefix || pathname.startsWith(`${row.prefix}/`)) {
      if (row.prefix.length > bestLen) {
        bestLen = row.prefix.length;
        best = row.meta;
      }
    }
  }
  return best;
}

export function hiveMobileRouteMeta(pathname: string): MobileRouteMeta {
  if (pathname === "/") {
    return { kicker: "Overview", staticSubtitle: "Dashboard · live swarm roster", pageTitleSuffix: "Overview" };
  }

  const hit = longestPrefixMeta(pathname);
  if (hit) {
    return hit;
  }

  return { kicker: "QueenSwarm", staticSubtitle: "Hive cockpit" };
}
