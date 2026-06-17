/**
 * Personal OS mode — mirror of backend personal_os_mode.py preset lists.
 * Stacks on solo mode: daily operator stack without revenue/commercial noise.
 */

export const PERSONAL_OS_HIDDEN_FEATURES = new Set([
  "team_rbac",
  "enterprise_workspace",
  "accounts_admin",
  "skills_marketplace",
  "ugc_content_engine",
  "billing_settings",
  "sharing_settings",
  "product_mission",
  "self_extending_tool_marketplace",
  "bee_gamification",
  "leaderboard",
  "content_pack_factory",
  "skills_export_factory",
  "simulations",
  "jobs",
  "external_projects",
]);

export const PERSONAL_OS_CORE_FEATURES = new Set([
  "dashboard",
  "operator_cockpit",
  "swarms",
  "agents",
  "tasks",
  "workflows",
  "knowledge",
  "integrations",
  "connectors",
  "execution_studio",
  "ballroom",
  "recipes",
  "settings",
  "llm_keys_settings",
  "api_keys_settings",
  "ai_harness_dashboard",
  "pattern_explorer",
  "costs",
  "audit_settings",
  "platform_features_admin",
  "command_center_admin",
  "manual",
  "monitoring",
  "plugins",
  "free_first_routing",
  "sub_swarm_mind_ui",
  "dump_sleep",
  "overnight_voice_report",
  "auto_graphify",
  "selective_recall",
  "skill_factory",
  "design_system",
]);

export const PERSONAL_OS_OPTIONAL_FEATURES = new Set([
  "foragers",
  "episodic_memory",
  "slack_harness_trainer",
  "lsp_mcp_bridge",
  "rubric_templates",
  "venice_mcp_preset",
]);

/** Apps & Tools module keys hidden in Personal OS (frozen/commercial lanes). */
export const PERSONAL_OS_HIDDEN_APPS_TOOLS_MODULES = new Set([
  "content_factory",
  "mcp_ops_studio",
  "trading_automation",
  "browser_automation",
  "ecommerce_workspace",
  "research_workspace",
]);

/** More-menu hrefs stripped in Personal OS. */
export const PERSONAL_OS_MORE_HIDDEN_HREFS = new Set([
  "/factory",
  "/jobs",
  "/simulations",
  "/workflows",
]);

export function parsePersonalOsModeFlag(raw: string | undefined): boolean {
  if (raw === undefined) {
    return false;
  }
  const norm = raw.trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(norm);
}

/** Build-time hint — authoritative value comes from GET /auth/me ``personal_os_mode``. */
export const PERSONAL_OS_MODE_BUILD_HINT = parsePersonalOsModeFlag(
  process.env.NEXT_PUBLIC_PERSONAL_OS_MODE,
);

/** Apply Personal OS preset onto resolved platform features (client fallback only). */
export function applyPersonalOsModeOverrides(
  resolved: Record<string, boolean>,
  options: { isAdmin?: boolean } = {},
): Record<string, boolean> {
  const isAdmin = options.isAdmin ?? true;
  const out = { ...resolved };
  for (const key of PERSONAL_OS_HIDDEN_FEATURES) {
    out[key] = false;
  }
  for (const key of PERSONAL_OS_CORE_FEATURES) {
    out[key] = true;
  }
  for (const key of PERSONAL_OS_OPTIONAL_FEATURES) {
    out[key] = isAdmin;
  }
  out.platform_features_admin = isAdmin;
  out.accounts_admin = false;
  out.command_center_admin = isAdmin;
  return out;
}

export function filterAppsToolsModulesForPersonalOs<
  T extends { moduleKey: string },
>(modules: readonly T[], personalOsMode: boolean): T[] {
  if (!personalOsMode) {
    return [...modules];
  }
  return modules.filter((row) => !PERSONAL_OS_HIDDEN_APPS_TOOLS_MODULES.has(row.moduleKey));
}
