/** Host detection for letagentscook.org marketing domain. */

const MARKETING_HOSTS = new Set(["letagentscook.org", "www.letagentscook.org"]);

export function marketingPublicOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_MARKETING_PUBLIC_ORIGIN?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "https://letagentscook.org";
}

export function appPublicOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_APP_PUBLIC_ORIGIN?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "https://queenswarm.love";
}

export function isMarketingHost(host: string | null | undefined): boolean {
  if (!host) {
    return false;
  }
  const normalized = host.split(":")[0]?.trim().toLowerCase() ?? "";
  return MARKETING_HOSTS.has(normalized);
}

export function isAppDashboardPath(pathname: string): boolean {
  const blockedPrefixes = [
    "/cockpit",
    "/dashboard",
    "/agents",
    "/tasks",
    "/settings",
    "/integrations",
    "/knowledge",
    "/ballroom",
    "/factory",
    "/apps-tools",
    "/agentic-os",
    "/workflows",
    "/swarms",
    "/foragers",
    "/routines",
    "/monitoring",
    "/oracle",
    "/plugins",
    "/recipes",
    "/execution",
    "/overview",
    "/hierarchy",
    "/costs",
    "/manual",
    "/simulations",
  ];
  return blockedPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}
