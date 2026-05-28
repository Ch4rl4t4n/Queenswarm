/**
 * Whole-App UI Reorder v2.1 — production-authenticated journey matrix.
 * Aligns with `HIVE_CRITICAL_JOURNEY_SPECS` but uses real hive (no API mocks).
 */

import { HIVE_PAGE_ZONE_SPECS } from "@/lib/hive-page-zone-spec";

export const HIVE_PROD_JOURNEY_VERSION = "2026.05-v1";

/** Required env vars for prod journey Playwright runs. */
export const HIVE_PROD_JOURNEY_ENV = {
  enabled: "E2E_PROD_AUTHENTICATED",
  token: "OPERATOR_USER_BEARER_TOKEN",
  baseUrl: "PLAYWRIGHT_BASE_URL",
} as const;

export interface HiveProdJourneyRouteSpec {
  path: string;
  /** Expected hive-page-shell h1 when route uses HivePageShell. */
  shellTitle?: string;
  /** Fallback heading match when page uses legacy header only. */
  heading?: string;
  requiresCp?: boolean;
}

/** Canonical zone index routes — must load on production with operator JWT. */
export const HIVE_PROD_JOURNEY_ZONE_ROUTES: HiveProdJourneyRouteSpec[] = HIVE_PAGE_ZONE_SPECS.map(
  (spec) => ({
    path: spec.path,
    shellTitle: spec.title,
    requiresCp: spec.path === "/agentic-os",
  }),
);

/** Secondary routes from critical journeys (settings, modules, execution). */
export const HIVE_PROD_JOURNEY_SECONDARY_ROUTES: HiveProdJourneyRouteSpec[] = [
  { path: "/settings/security", shellTitle: "Settings" },
  { path: "/settings/harness", shellTitle: "Settings" },
  { path: "/apps-tools/marketing-automation", shellTitle: "Marketing Automation" },
  { path: "/foragers", shellTitle: "Foragers" },
  { path: "/tasks/new", heading: "New task" },
  { path: "/swarms/new", heading: "New swarm" },
];

export const HIVE_PROD_JOURNEY_ROUTES: HiveProdJourneyRouteSpec[] = [
  ...HIVE_PROD_JOURNEY_ZONE_ROUTES,
  ...HIVE_PROD_JOURNEY_SECONDARY_ROUTES,
];

export function hiveProdJourneyRouteCount(): number {
  return HIVE_PROD_JOURNEY_ROUTES.length;
}

export function hiveProdJourneyEnabled(): boolean {
  if (process.env.E2E_PROD_AUTHENTICATED !== "1") {
    return false;
  }
  return Boolean(process.env.OPERATOR_USER_BEARER_TOKEN?.trim());
}
