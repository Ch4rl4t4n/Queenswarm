/**
 * Frontend feature flags for progressive rollout.
 * Conservative defaults keep advanced modules hidden unless explicitly enabled.
 */

function parseBoolean(raw: string | undefined, fallback: boolean): boolean {
  if (raw === undefined) {
    return fallback;
  }
  const norm = raw.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(norm)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(norm)) {
    return false;
  }
  return fallback;
}

export function isFeatureEnabled(name: string, fallback: boolean): boolean {
  return parseBoolean(process.env[name], fallback);
}

export const PHASE70_CONSOLIDATED_NAV_ENABLED = isFeatureEnabled("NEXT_PUBLIC_PHASE70_CONSOLIDATED_NAV_ENABLED", true);
export const ADVANCED_MONITORING_ENABLED = isFeatureEnabled("NEXT_PUBLIC_ADVANCED_MONITORING_ENABLED", false);
export const SIMULATIONS_ENABLED = isFeatureEnabled("NEXT_PUBLIC_SIMULATIONS_ENABLED", false);
export const LEADERBOARD_ENABLED = isFeatureEnabled("NEXT_PUBLIC_LEADERBOARD_ENABLED", false);
export const RECIPES_ENABLED = isFeatureEnabled("NEXT_PUBLIC_RECIPES_ENABLED", false);
export const SECURITY_2FA_ADVANCED_ENABLED = isFeatureEnabled("NEXT_PUBLIC_SECURITY_2FA_ADVANCED_ENABLED", false);
export const API_KEY_MANAGEMENT_ENABLED = isFeatureEnabled("NEXT_PUBLIC_API_KEY_MANAGEMENT_ENABLED", false);
