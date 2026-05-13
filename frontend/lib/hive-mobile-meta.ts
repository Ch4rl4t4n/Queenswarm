/** Route labels used by compact mobile chrome (hive header + titles). */

export interface MobileRouteMeta {
  kicker: string;
  pageTitleSuffix?: string;
  staticSubtitle?: string;
}

export function hiveMobileRouteMeta(pathname: string): MobileRouteMeta {
  if (pathname.startsWith("/ballroom")) {
    return {
      kicker: "Ballroom",
      staticSubtitle: "Voice + chat",
      pageTitleSuffix: "Ballroom",
    };
  }
  if (pathname === "/") {
    return { kicker: "Queen Swarm", staticSubtitle: "Dashboard · live swarm roster" };
  }
  return { kicker: "QueenSwarm", staticSubtitle: "Hive cockpit" };
}
