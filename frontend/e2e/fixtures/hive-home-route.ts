/** E2E mirror of production home routing (see middleware + hive-home-route). */

import { hiveMissionControlPageTitle, hiveOverviewHref, hiveOverviewLabel } from "@/lib/hive-home-route";

export function e2eHiveHomePath(): string {
  return hiveOverviewHref();
}

export function e2eHiveHomeHeading(): RegExp {
  const label = hiveOverviewLabel();
  return new RegExp(`^${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "i");
}

/** Tasks hub page title when solo Mission Control is home. */
export function e2eTasksHubHeading(): RegExp {
  const label = hiveMissionControlPageTitle();
  return new RegExp(`^${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "i");
}

/** Advanced ColonyConsole — always `/dashboard`. */
export function e2eAdvancedDashboardPath(): string {
  return "/dashboard";
}
