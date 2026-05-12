/** Route labels used by compact mobile chrome (hive header + titles). */

export interface MobileRouteMeta {
  /** Small label next to hive hex (breadcrumb pill). */
  kicker: string;
  /** Main H1-ish line rendered on the dashboard page header (optional duplication avoided). */
  pageTitleSuffix?: string;
  /** Fallback static subtitle when live summary lacks data. */
  staticSubtitle?: string;
}

export function hiveMobileRouteMeta(pathname: string): MobileRouteMeta {
  if (pathname.startsWith("/settings")) {
    return { kicker: "Settings", staticSubtitle: "Hive configuration · 7 sections" };
  }
  if (pathname.startsWith("/agents")) {
    return {
      kicker: "Agents",
      staticSubtitle: "Live scouts · imitate neighbors",
      pageTitleSuffix: "Agents",
    };
  }
  if (pathname.startsWith("/swarms")) {
    return { kicker: "Sub-Swarms", staticSubtitle: "4 decentralized roves · global sync · 5 min" };
  }
  if (pathname.startsWith("/tasks")) {
    return { kicker: "Task Queue", staticSubtitle: "Rapid Celery lane · swarm pickup" };
  }
  if (pathname.startsWith("/workflows")) {
    return { kicker: "Workflows", staticSubtitle: "DAG executions · decomposed guards" };
  }
  if (pathname.startsWith("/recipes")) {
    return { kicker: "Recipe Library", staticSubtitle: "Battle-tested verified flows · 0.85 cosine" };
  }
  if (pathname.startsWith("/leaderboard")) {
    return { kicker: "Leaderboard", staticSubtitle: "Top performers · imitation graph" };
  }
  if (pathname.startsWith("/ballroom")) {
    return {
      kicker: "Ballroom",
      staticSubtitle: "Voice rooms · WebRTC · transcripts",
      pageTitleSuffix: "Ballroom",
    };
  }
  if (pathname.startsWith("/costs")) {
    return { kicker: "Costs", staticSubtitle: "Per LLM · per agent · per swarm" };
  }
  if (
    pathname.startsWith("/simulations") ||
    pathname.startsWith("/plugins") ||
    pathname.startsWith("/design-system")
  ) {
    return { kicker: "Labs", staticSubtitle: "Tokens · components · plugins & simulations" };
  }
  /* Dashboard root */
  if (pathname === "/") {
    return { kicker: "Dashboard", staticSubtitle: "Decentralized swarms · verified loop" };
  }
  return { kicker: "QueenSwarm", staticSubtitle: "Hive cockpit" };
}
