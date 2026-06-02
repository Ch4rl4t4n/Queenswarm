import { OPERATOR_CONTROL_PLANE_ENABLED, SINGLE_ADMIN_MODE } from "@/lib/feature-flags";
import { SOLO_MODE_BUILD_HINT } from "@/lib/solo-mode";

/** Solo operator home — Mission Control kanban when CP + solo preset. */
export function soloOperatorHomePreferred(options?: { soloMode?: boolean }): boolean {
  const solo = options?.soloMode ?? (SINGLE_ADMIN_MODE || SOLO_MODE_BUILD_HINT);
  return Boolean(solo && OPERATOR_CONTROL_PLANE_ENABLED);
}

/** Primary overview route — Mission Control for solo operators, else Agentic OS / dashboard. */
export function hiveOverviewHref(options?: { soloMode?: boolean }): string {
  if (soloOperatorHomePreferred(options)) {
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
  if (soloOperatorHomePreferred(options)) {
    return "Mission Control";
  }
  return OPERATOR_CONTROL_PLANE_ENABLED ? "Agentic OS" : "Dashboard";
}

/** Page title for `/tasks` when solo Mission Control is the operator home. */
export function hiveMissionControlPageTitle(options?: { soloMode?: boolean }): string {
  return soloOperatorHomePreferred(options) ? "Mission Control" : "Tasks";
}
