import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";

/** Primary overview route — Cockpit when CP enabled, legacy dashboard otherwise. */
export function hiveOverviewHref(options?: { soloMode?: boolean }): string {
  if (options?.soloMode && OPERATOR_CONTROL_PLANE_ENABLED) {
    return "/tasks";
  }
  return OPERATOR_CONTROL_PLANE_ENABLED ? "/agentic-os" : "/dashboard";
}

/** Mission Control kanban — solo operator home when CP enabled. */
export function hiveMissionControlHref(): string {
  return "/tasks";
}

/** Sidebar / shortcut label for the overview route. */
export function hiveOverviewLabel(options?: { soloMode?: boolean }): string {
  if (options?.soloMode && OPERATOR_CONTROL_PLANE_ENABLED) {
    return "Mission Control";
  }
  return OPERATOR_CONTROL_PLANE_ENABLED ? "Agentic OS" : "Dashboard";
}
