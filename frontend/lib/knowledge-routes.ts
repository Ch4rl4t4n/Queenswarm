/** Knowledge hub tab routing — hash anchors for consolidated /knowledge hub. */

import { resolvePrimarySubnavFromUrl, SUBNAV_MENU_KEYS } from "@/lib/subnav-order-preferences";

export type KnowledgeTab = "hivemind" | "outputs" | "recipes" | "dreaming" | "memory" | "wiki" | "goals";

const ALL_KNOWLEDGE_TABS: KnowledgeTab[] = ["hivemind", "outputs", "recipes", "dreaming", "memory", "wiki", "goals"];

const HASH_TO_TAB: Record<string, KnowledgeTab> = {
  hivemind: "hivemind",
  outputs: "outputs",
  archive: "outputs",
  recipes: "recipes",
  learning: "recipes",
  dreaming: "dreaming",
  memory: "memory",
  wiki: "wiki",
  goals: "goals",
};

/** Canonical href for a knowledge hub tab (alias-first consolidated nav). */
export function knowledgeTabHref(tab: KnowledgeTab): string {
  return tab === "hivemind" ? "/knowledge" : `/knowledge#${tab}`;
}

/** Map `#outputs` / legacy `#learning` hash links to a tab id. */
export function knowledgeTabFromHash(hash: string): KnowledgeTab | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  return HASH_TO_TAB[key] ?? null;
}

/** Prefer hash tab; bare `/knowledge` → first tab in saved menu order. */
export function resolveKnowledgeTab(params: {
  hash?: string;
  visibleTabIds?: readonly KnowledgeTab[];
  fallback?: KnowledgeTab;
}): KnowledgeTab {
  const visible =
    params.visibleTabIds && params.visibleTabIds.length > 0 ? params.visibleTabIds : ALL_KNOWLEDGE_TABS;
  const legacy = params.fallback ?? visible[0] ?? "hivemind";
  const fromHash = knowledgeTabFromHash(params.hash ?? "");
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.knowledgePrimary,
    visibleIds: visible,
    fromUrl: fromHash && visible.includes(fromHash) ? fromHash : null,
    legacyDefaultId: legacy,
  });
}
