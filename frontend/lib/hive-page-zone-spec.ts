/**
 * Whole-App UI Reorder — canonical page shell metadata per IA zone route.
 * Used by E2E smoke tests and docs; keep in sync with `hive-ia-canonical.ts`.
 */

import type { HivePageHintKey } from "@/lib/hive-page-hints";

export const HIVE_PAGE_SHELL_VERSION = "2026.05-v1";

export interface HivePageZoneSpec {
  path: string;
  title: string;
  hintKey: HivePageHintKey;
  /** Minimum expected h1 test id chain: shell → header h1 */
  hasSubnav?: boolean;
}

/** Top-level zone index routes — each must render HivePageShell with matching title. */
export const HIVE_PAGE_ZONE_SPECS: HivePageZoneSpec[] = [
  { path: "/agentic-os", title: "Agentic OS", hintKey: "cockpit", hasSubnav: true },
  { path: "/swarms", title: "Swarms", hintKey: "swarms", hasSubnav: false },
  { path: "/tasks", title: "Tasks", hintKey: "tasks", hasSubnav: false },
  { path: "/routines", title: "Routines", hintKey: "routines", hasSubnav: false },
  { path: "/agents", title: "Agents", hintKey: "agents", hasSubnav: true },
  { path: "/apps-tools", title: "Apps & Tools", hintKey: "appsTools", hasSubnav: false },
  { path: "/integrations", title: "Integrations", hintKey: "integrations", hasSubnav: true },
  { path: "/knowledge", title: "Knowledge", hintKey: "knowledge", hasSubnav: true },
  { path: "/ballroom", title: "Ballroom", hintKey: "ballroom", hasSubnav: false },
];

export function hivePageZoneSpecForPath(pathname: string): HivePageZoneSpec | undefined {
  const normalized = pathname.replace(/\/$/, "") || "/";
  return HIVE_PAGE_ZONE_SPECS.find((spec) => spec.path === normalized);
}