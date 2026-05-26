"use client";

import { usePathname } from "next/navigation";
import type { SWRConfiguration } from "swr";

import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";

/** Return true when the active pathname matches a dashboard route prefix. */
export function pathnameMatchesRoute(pathname: string, route: string): boolean {
  const norm = (pathname.split("#")[0] ?? "/").replace(/\/$/, "") || "/";
  const base = route.replace(/\/$/, "") || "/";
  if (base === "/") {
    return norm === "/" || norm === "/dashboard" || norm === "/overview";
  }
  return norm === base || norm.startsWith(`${base}/`);
}

/**
 * SWR poll options that run only while the operator is on ``activeRoute``.
 * Stops background polling when navigating away (e.g. dashboard telemetry off /agents).
 */
export function useRouteScopedPollOptions(
  refreshMs: number,
  activeRoute: string,
): Pick<SWRConfiguration, "refreshInterval" | "revalidateOnFocus" | "dedupingInterval" | "focusThrottleInterval"> {
  const pathname = usePathname() ?? "/";
  const active = pathnameMatchesRoute(pathname, activeRoute);
  return useSwrVisiblePollOptions(active ? refreshMs : 0);
}
