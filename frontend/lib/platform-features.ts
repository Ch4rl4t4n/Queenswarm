/**
 * Platform feature catalog — keep in sync with backend platform_features.py.
 */

export type PlatformMode = "internal" | "commercial";

export type FeatureRule = boolean | "admin";

export interface FeatureSpec {
  internal: FeatureRule;
  commercial: FeatureRule;
  minTier?: "free" | "pro" | "enterprise";
}

export const PLATFORM_FEATURE_CATALOG: Record<string, FeatureSpec> = {
  dashboard: { internal: true, commercial: true },
  swarms: { internal: true, commercial: true },
  agents: { internal: true, commercial: true },
  foragers: { internal: true, commercial: true, minTier: "pro" },
  tasks: { internal: true, commercial: true },
  knowledge: { internal: true, commercial: true },
  integrations: { internal: true, commercial: true },
  ballroom: { internal: true, commercial: true, minTier: "pro" },
  costs: { internal: true, commercial: true },
  leaderboard: { internal: true, commercial: true, minTier: "pro" },
  manual: { internal: true, commercial: true },
  settings: { internal: true, commercial: true },
  monitoring: { internal: "admin", commercial: false },
  workflows: { internal: true, commercial: true },
  jobs: { internal: true, commercial: false },
  simulations: { internal: true, commercial: false },
  recipes: { internal: true, commercial: true, minTier: "pro" },
  external_projects: { internal: true, commercial: true, minTier: "pro" },
  plugins: { internal: true, commercial: true },
  connectors: { internal: true, commercial: true },
  skills_marketplace: { internal: true, commercial: true, minTier: "pro" },
  skills_export_factory: { internal: true, commercial: false },
  product_mission: { internal: true, commercial: false },
  ugc_content_engine: { internal: true, commercial: true, minTier: "pro" },
  sub_swarm_mind_ui: { internal: true, commercial: true },
  bee_gamification: { internal: true, commercial: true, minTier: "pro" },
  dump_sleep: { internal: true, commercial: true, minTier: "pro" },
  free_first_routing: { internal: true, commercial: true },
  auto_graphify: { internal: true, commercial: true, minTier: "pro" },
  selective_recall: { internal: true, commercial: true, minTier: "pro" },
  venice_mcp_preset: { internal: true, commercial: true, minTier: "pro" },
  team_rbac: { internal: false, commercial: true },
  billing_settings: { internal: false, commercial: true },
  sharing_settings: { internal: false, commercial: true },
  llm_keys_settings: { internal: true, commercial: true },
  api_keys_settings: { internal: true, commercial: true },
  audit_settings: { internal: "admin", commercial: true },
  enterprise_workspace: { internal: true, commercial: true, minTier: "enterprise" },
  design_system: { internal: "admin", commercial: false },
  platform_features_admin: { internal: "admin", commercial: false },
  accounts_admin: { internal: "admin", commercial: false },
  command_center_admin: { internal: "admin", commercial: false },
};

const TIER_RANK: Record<string, number> = {
  free: 0,
  pro: 1,
  enterprise: 2,
};

export const ROUTE_FEATURE_KEYS: Record<string, string> = {
  "/": "dashboard",
  "/swarms": "swarms",
  "/agents": "agents",
  "/foragers": "foragers",
  "/tasks": "tasks",
  "/knowledge": "knowledge",
  "/integrations": "integrations",
  "/ballroom": "ballroom",
  "/costs": "costs",
  "/leaderboard": "leaderboard",
  "/manual": "manual",
  "/monitoring": "monitoring",
  "/workflows": "workflows",
  "/jobs": "jobs",
  "/simulations": "simulations",
  "/recipes": "recipes",
  "/external-projects": "external_projects",
  "/plugins": "plugins",
  "/connectors": "connectors",
  "/hive-mind": "knowledge",
  "/outputs": "knowledge",
  "/learning": "knowledge",
  "/settings/billing": "billing_settings",
  "/settings/team": "team_rbac",
  "/settings/sharing": "sharing_settings",
  "/settings/llm-keys": "llm_keys_settings",
  "/settings/api-keys": "api_keys_settings",
  "/settings/audit": "audit_settings",
  "/settings/enterprise": "enterprise_workspace",
  "/settings/platform": "platform_features_admin",
  "/settings/accounts": "accounts_admin",
  "/settings/command-center": "command_center_admin",
  "/settings/capabilities": "settings",
  "/design-system": "design_system",
};

export function normalizePlatformMode(raw: string | null | undefined): PlatformMode {
  const key = String(raw ?? "internal").trim().toLowerCase();
  return key === "commercial" ? "commercial" : "internal";
}

/** Map tenant mode + tier to platform feature matrix column key. */
export function profileKeyFor(platformMode: string, subscriptionTier: string): string {
  const mode = normalizePlatformMode(platformMode);
  const tier = String(subscriptionTier ?? "free").trim().toLowerCase();
  if (mode === "internal") {
    return "internal";
  }
  if (tier === "enterprise") {
    return "commercial_enterprise";
  }
  if (tier === "pro") {
    return "commercial_pro";
  }
  return "commercial_free";
}

function tierAtLeast(current: string, required: string): boolean {
  return (TIER_RANK[current] ?? 0) >= (TIER_RANK[required] ?? 0);
}

function ruleForMode(rule: FeatureRule, isAdmin: boolean): boolean {
  if (rule === "admin") {
    return isAdmin;
  }
  return Boolean(rule);
}

/** Client-side fallback when API features are not yet loaded. */
export function resolvePlatformFeaturesFallback(input: {
  platformMode: PlatformMode;
  isAdmin: boolean;
  subscriptionTier?: string;
}): Record<string, boolean> {
  const tier = String(input.subscriptionTier ?? "free").trim().toLowerCase();
  const resolved: Record<string, boolean> = {};

  for (const [key, spec] of Object.entries(PLATFORM_FEATURE_CATALOG)) {
    const rule = input.platformMode === "commercial" ? spec.commercial : spec.internal;
    let enabled = ruleForMode(rule, input.isAdmin);
    if (
      enabled &&
      input.platformMode === "commercial" &&
      spec.minTier &&
      !tierAtLeast(tier, spec.minTier)
    ) {
      enabled = false;
    }
    resolved[key] = enabled;
  }

  resolved.platform_features_admin = input.platformMode === "internal" && input.isAdmin;
  resolved.accounts_admin = input.platformMode === "internal" && input.isAdmin;
  resolved.command_center_admin = input.platformMode === "internal" && input.isAdmin;
  return resolved;
}

export function routeFeatureKey(pathname: string): string | null {
  const normalized = (pathname || "/").split("#")[0] ?? "/";
  if (ROUTE_FEATURE_KEYS[normalized]) {
    return ROUTE_FEATURE_KEYS[normalized];
  }
  const prefixes = Object.keys(ROUTE_FEATURE_KEYS).sort((a, b) => b.length - a.length);
  for (const prefix of prefixes) {
    if (prefix !== "/" && (normalized === prefix || normalized.startsWith(`${prefix}/`))) {
      return ROUTE_FEATURE_KEYS[prefix] ?? null;
    }
  }
  if (normalized.startsWith("/settings")) {
    return "settings";
  }
  return null;
}

export function isRouteAllowed(pathname: string, features: Record<string, boolean>): boolean {
  const key = routeFeatureKey(pathname);
  if (!key) {
    return true;
  }
  return Boolean(features[key]);
}

export function isFeatureEnabled(features: Record<string, boolean>, key: string): boolean {
  return Boolean(features[key]);
}

export interface NavFeatureItem {
  href: string;
  featureKey?: string;
}

export function filterNavByFeatures<T extends NavFeatureItem>(
  items: T[],
  features: Record<string, boolean>,
): T[] {
  return items.filter((item) => {
    if (!item.featureKey) {
      const inferred = routeFeatureKey(item.href);
      if (!inferred) {
        return true;
      }
      return Boolean(features[inferred]);
    }
    return Boolean(features[item.featureKey]);
  });
}

export function filterNavGroupsByFeatures<T extends NavFeatureItem>(
  groups: { title: string; items: T[] }[],
  features: Record<string, boolean>,
): { title: string; items: T[] }[] {
  return groups
    .map((group) => ({
      ...group,
      items: filterNavByFeatures(group.items, features),
    }))
    .filter((group) => group.items.length > 0);
}
