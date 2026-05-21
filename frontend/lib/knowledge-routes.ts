/** Knowledge hub tab routing — hash anchors for consolidated /knowledge hub. */

export type KnowledgeTab = "hivemind" | "outputs" | "recipes" | "dreaming" | "memory" | "goals";

const HASH_TO_TAB: Record<string, KnowledgeTab> = {
  hivemind: "hivemind",
  outputs: "outputs",
  archive: "outputs",
  recipes: "recipes",
  learning: "recipes",
  dreaming: "dreaming",
  memory: "memory",
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
