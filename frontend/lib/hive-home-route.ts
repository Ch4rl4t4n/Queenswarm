import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";

/** Primary overview route — Cockpit when CP enabled, legacy dashboard otherwise. */
export function hiveOverviewHref(): string {
  return OPERATOR_CONTROL_PLANE_ENABLED ? "/agentic-os" : "/dashboard";
}

/** Sidebar / shortcut label for the overview route. */
export function hiveOverviewLabel(): string {
  return OPERATOR_CONTROL_PLANE_ENABLED ? "Agentic OS" : "Dashboard";
}
