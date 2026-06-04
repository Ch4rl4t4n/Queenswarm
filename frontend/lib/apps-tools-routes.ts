/** Apps & Tools section routing — primary areas + factory hash tabs. */

export type AppsToolsPrimarySection = "module_index" | "skill_factory" | "content_factory";

export type SkillFactoryTab = "research" | "queue" | "library" | "launch" | "settings" | "guide";

export type ContentPackFactoryTab = "research" | "queue" | "library" | "settings" | "guide";

export const APPS_TOOLS_MODULE_INDEX_HREF = "/apps-tools";

export const APPS_TOOLS_SKILL_FACTORY_HREF = "/apps-tools/skill-factory";

export const APPS_TOOLS_CONTENT_FACTORY_HREF = "/apps-tools/content-factory";

export const SKILL_FACTORY_TABS: { id: SkillFactoryTab; label: string }[] = [
  { id: "research", label: "Research" },
  { id: "queue", label: "Queue" },
  { id: "library", label: "Library" },
  { id: "launch", label: "Launch" },
  { id: "settings", label: "Settings" },
  { id: "guide", label: "Guide" },
];

export const CONTENT_PACK_FACTORY_TABS: { id: ContentPackFactoryTab; label: string }[] = [
  { id: "research", label: "Research" },
  { id: "queue", label: "Queue" },
  { id: "library", label: "Library" },
  { id: "settings", label: "Settings" },
  { id: "guide", label: "Guide" },
];

const SKILL_FACTORY_TAB_IDS = new Set<string>(SKILL_FACTORY_TABS.map((row) => row.id));
const CONTENT_PACK_FACTORY_TAB_IDS = new Set<string>(CONTENT_PACK_FACTORY_TABS.map((row) => row.id));

export function appsToolsPrimaryFromPathname(pathname: string): AppsToolsPrimarySection {
  const normalized = pathname.split("#")[0]?.replace(/\/$/, "") ?? pathname;
  if (normalized === APPS_TOOLS_SKILL_FACTORY_HREF) {
    return "skill_factory";
  }
  if (normalized === APPS_TOOLS_CONTENT_FACTORY_HREF) {
    return "content_factory";
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

export function resolveSkillFactoryTab(options: { hash?: string; fallback?: SkillFactoryTab }): SkillFactoryTab {
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

/** True when pathname should use the Apps & Tools shell (index + factory modules). */
export function appsToolsShellActiveForPathname(pathname: string): boolean {
  const normalized = pathname.split("#")[0]?.replace(/\/$/, "") ?? pathname;
  return (
    normalized === APPS_TOOLS_MODULE_INDEX_HREF ||
    normalized === APPS_TOOLS_SKILL_FACTORY_HREF ||
    normalized === APPS_TOOLS_CONTENT_FACTORY_HREF
  );
}
