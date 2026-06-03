/**
 * Solo operator mode — mirror of backend solo_mode.py preset lists.
 * Solo = one admin operator with full revenue stack; multi-tenant B2B hidden only.
 */

export const SOLO_HIDDEN_FEATURES = new Set([
  "team_rbac",
  "enterprise_workspace",
  "accounts_admin",
  "skills_marketplace",
  "ugc_content_engine",
]);

export const SOLO_CORE_FEATURES = new Set([
  "dashboard",
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
  "skills_export_factory",
  "skill_factory",
  "billing_settings",
  "sharing_settings",
  "product_mission",
  "self_extending_tool_marketplace",
  "bee_gamification",
  "design_system",
]);

export const SOLO_OPTIONAL_FEATURES = new Set([
  "foragers",
  "simulations",
  "jobs",
  "external_projects",
  "episodic_memory",
  "slack_harness_trainer",
  "lsp_mcp_bridge",
  "rubric_templates",
  "venice_mcp_preset",
]);

export function parseSoloModeFlag(raw: string | undefined): boolean {
  if (raw === undefined) {
    return false;
  }
  const norm = raw.trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(norm);
}

/** Build-time hint — authoritative value comes from GET /auth/me ``solo_mode``. */
export const SOLO_MODE_BUILD_HINT = parseSoloModeFlag(process.env.NEXT_PUBLIC_SOLO_MODE);

/** Apply solo preset onto a resolved platform feature map (client fallback only). */
export function applySoloModeOverrides(
  resolved: Record<string, boolean>,
  options: { isAdmin?: boolean } = {},
): Record<string, boolean> {
  const isAdmin = options.isAdmin ?? true;
  const out = { ...resolved };
  for (const key of SOLO_HIDDEN_FEATURES) {
    out[key] = false;
  }
  for (const key of SOLO_CORE_FEATURES) {
    out[key] = true;
  }
  for (const key of SOLO_OPTIONAL_FEATURES) {
    out[key] = isAdmin;
  }
  out.platform_features_admin = isAdmin;
  out.accounts_admin = false;
  out.command_center_admin = isAdmin;
  return out;
}
