/** E2E mirror of production home routing (see middleware + hive-home-route). */

function cpEnabled(): boolean {
  // Local Playwright webServer sets CP enabled — align test expectations with next dev env.
  if (!process.env.PLAYWRIGHT_BASE_URL) {
    return true;
  }
  const raw = process.env.NEXT_PUBLIC_OPERATOR_CONTROL_PLANE_ENABLED;
  if (raw === undefined) {
    return true;
  }
  const norm = raw.trim().toLowerCase();
  if (["0", "false", "no", "off"].includes(norm)) {
    return false;
  }
  return true;
}

export function e2eHiveHomePath(): string {
  return cpEnabled() ? "/agentic-os" : "/dashboard";
}

export function e2eHiveHomeHeading(): RegExp {
  return cpEnabled() ? /Agentic OS/i : /^Dashboard$/i;
}

/** Advanced ColonyConsole — always `/dashboard`. */
export function e2eAdvancedDashboardPath(): string {
  return "/dashboard";
}
