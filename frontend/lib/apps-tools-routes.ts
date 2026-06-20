/** Apps & Tools section routing — primary areas + factory hash tabs. */

export type AppsToolsPrimarySection = "module_index" | "skill_factory" | "content_factory" | "mcp_ops_studio";

export type SkillFactoryTab = "research" | "queue" | "library" | "settings" | "guide";

export type ContentPackFactoryTab = "research" | "queue" | "library" | "settings" | "guide";

export type McpOpsStudioTab = "catalog" | "install" | "health";

export const APPS_TOOLS_MODULE_INDEX_HREF = "/apps-tools";

export const APPS_TOOLS_SKILL_FACTORY_HREF = "/apps-tools/skill-factory";

export const APPS_TOOLS_CONTENT_FACTORY_HREF = "/apps-tools/content-factory";

export const APPS_TOOLS_MCP_OPS_STUDIO_HREF = "/apps-tools/mcp-ops-studio";

export const SKILL_FACTORY_TABS: { id: SkillFactoryTab; label: string }[] = [
  { id: "research", label: "Research" },
  { id: "queue", label: "Queue" },
  { id: "library", label: "Library" },
  { id: "settings", label: "Settings" },
  { id: "guide", label: "Guide" },
];

export function filterSkillFactoryTabsForPersonalOs(
  tabs: readonly { id: SkillFactoryTab; label: string }[],
  _personalOsMode: boolean,
): { id: SkillFactoryTab; label: string }[] {
  return [...tabs];
}

export const CONTENT_PACK_FACTORY_TABS: { id: ContentPackFactoryTab; label: string }[] = [
  { id: "research", label: "Research" },
  { id: "queue", label: "Queue" },
  { id: "library", label: "Library" },
  { id: "settings", label: "Settings" },
  { id: "guide", label: "Guide" },
];

export const MCP_OPS_STUDIO_TABS: { id: McpOpsStudioTab; label: string }[] = [
  { id: "catalog", label: "Catalog" },
  { id: "install", label: "Install queue" },
  { id: "health", label: "Health checks" },
];

const SKILL_FACTORY_TAB_IDS = new Set<string>(SKILL_FACTORY_TABS.map((row) => row.id));

/** Deep-link anchors on the Library tab (not tab ids). */
export const SKILL_FACTORY_LIBRARY_ANCHOR_HASHES = new Set<string>(["skill-factory-library"]);
const CONTENT_PACK_FACTORY_TAB_IDS = new Set<string>(CONTENT_PACK_FACTORY_TABS.map((row) => row.id));
const MCP_OPS_STUDIO_TAB_IDS = new Set<string>(MCP_OPS_STUDIO_TABS.map((row) => row.id));

export function appsToolsPrimaryFromPathname(pathname: string): AppsToolsPrimarySection {
  const normalized = pathname.split("#")[0]?.replace(/\/$/, "") ?? pathname;
  if (normalized === APPS_TOOLS_SKILL_FACTORY_HREF) {
    return "skill_factory";
  }
  if (normalized === APPS_TOOLS_CONTENT_FACTORY_HREF) {
    return "content_factory";
  }
  if (normalized === APPS_TOOLS_MCP_OPS_STUDIO_HREF) {
    return "mcp_ops_studio";
  }
  return "module_index";
}

export function skillFactoryTabFromHash(hash: string): SkillFactoryTab | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key || !SKILL_FACTORY_TAB_IDS.has(key)) {
    return null;
  }
  return key as SkillFactoryTab;
}

export function skillFactoryTabHref(tab: SkillFactoryTab): string {
  return `${APPS_TOOLS_SKILL_FACTORY_HREF}#${tab}`;
}

/** Hash tab switch — App Router ignores hash-only router.push; use history + hashchange. */
export function navigateSkillFactoryTab(tab: SkillFactoryTab): void {
  if (typeof window === "undefined") {
    return;
  }
  const href = skillFactoryTabHref(tab);
  window.history.replaceState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function resolveSkillFactoryTab(options: {
  hash?: string;
  fallback?: SkillFactoryTab;
  personalOsMode?: boolean;
}): SkillFactoryTab {
  const key = (options.hash ?? "").replace(/^#/, "").trim().toLowerCase();
  if (SKILL_FACTORY_LIBRARY_ANCHOR_HASHES.has(key)) {
    return "library";
  }
  /** Legacy `#launch` (removed Launch tab) — land on Library where verified skills ship. */
  if (key === "launch") {
    return "library";
  }
  const fromHash = skillFactoryTabFromHash(options.hash ?? "");
  if (fromHash) {
    return fromHash;
  }
  return options.fallback ?? "research";
}

export function contentPackFactoryTabFromHash(hash: string): ContentPackFactoryTab | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "pack-factory" || key === "pipeline") {
    return "research";
  }
  if (!key || !CONTENT_PACK_FACTORY_TAB_IDS.has(key)) {
    return null;
  }
  return key as ContentPackFactoryTab;
}

export function contentPackFactoryTabHref(tab: ContentPackFactoryTab): string {
  return `${APPS_TOOLS_CONTENT_FACTORY_HREF}#${tab}`;
}

/** Hash tab switch — App Router ignores hash-only router.push; use history + hashchange. */
export function navigateContentPackFactoryTab(tab: ContentPackFactoryTab): void {
  if (typeof window === "undefined") {
    return;
  }
  const href = contentPackFactoryTabHref(tab);
  window.history.replaceState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function resolveContentPackFactoryTab(options: {
  hash?: string;
  fallback?: ContentPackFactoryTab;
}): ContentPackFactoryTab {
  const fromHash = contentPackFactoryTabFromHash(options.hash ?? "");
  if (fromHash) {
    return fromHash;
  }
  return options.fallback ?? "research";
}

export function mcpOpsStudioTabFromHash(hash: string): McpOpsStudioTab | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "mcp-catalog") {
    return "catalog";
  }
  if (key === "mcp-install") {
    return "install";
  }
  if (key === "mcp-health") {
    return "health";
  }
  if (!key || !MCP_OPS_STUDIO_TAB_IDS.has(key)) {
    return null;
  }
  return key as McpOpsStudioTab;
}

export function mcpOpsStudioTabHref(tab: McpOpsStudioTab): string {
  return `${APPS_TOOLS_MCP_OPS_STUDIO_HREF}#${tab}`;
}

/** Hash tab switch — App Router ignores hash-only router.push; use history + hashchange. */
export function navigateMcpOpsStudioTab(tab: McpOpsStudioTab): void {
  if (typeof window === "undefined") {
    return;
  }
  const href = mcpOpsStudioTabHref(tab);
  window.history.replaceState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function resolveMcpOpsStudioTab(options: {
  hash?: string;
  fallback?: McpOpsStudioTab;
}): McpOpsStudioTab {
  const fromHash = mcpOpsStudioTabFromHash(options.hash ?? "");
  if (fromHash) {
    return fromHash;
  }
  return options.fallback ?? "catalog";
}

/** True when pathname should use the Apps & Tools shell (index + integrated modules). */
export function appsToolsShellActiveForPathname(pathname: string): boolean {
  const normalized = pathname.split("#")[0]?.replace(/\/$/, "") ?? pathname;
  return (
    normalized === APPS_TOOLS_MODULE_INDEX_HREF ||
    normalized === APPS_TOOLS_SKILL_FACTORY_HREF ||
    normalized === APPS_TOOLS_CONTENT_FACTORY_HREF ||
    normalized === APPS_TOOLS_MCP_OPS_STUDIO_HREF
  );
}
