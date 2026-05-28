/** HiveMind sub-section routing inside Knowledge → HiveMind tab. */

import { resolvePrimarySubnavFromUrl, SUBNAV_MENU_KEYS } from "@/lib/subnav-order-preferences";

export type KnowledgeHivemindSection =
  | "graphify"
  | "shape"
  | "recall"
  | "explorer"
  | "evolution";

const ALL_HIVEMIND_SECTIONS: KnowledgeHivemindSection[] = [
  "graphify",
  "shape",
  "recall",
  "explorer",
  "evolution",
];

const HASH_TO_SECTION: Record<string, KnowledgeHivemindSection> = {
  graphify: "graphify",
  shape: "shape",
  recall: "recall",
  explorer: "explorer",
  evolution: "evolution",
  hivemind: "explorer",
};

/** Canonical href for a HiveMind sub-section. */
export function knowledgeHivemindSectionHref(section: KnowledgeHivemindSection): string {
  return `/knowledge#${section}`;
}

/** Map `#recall` hash links to a HiveMind sub-section id. */
export function knowledgeHivemindSectionFromHash(hash: string): KnowledgeHivemindSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  return HASH_TO_SECTION[key] ?? null;
}

/** Prefer hash section; bare `/knowledge` on HiveMind tab → first in saved hub order. */
export function resolveKnowledgeHivemindSection(params: {
  hash?: string;
  fallback?: KnowledgeHivemindSection;
}): KnowledgeHivemindSection {
  const legacy = params.fallback ?? ALL_HIVEMIND_SECTIONS[0] ?? "explorer";
  const fromHash = knowledgeHivemindSectionFromHash(params.hash ?? "");
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.knowledgeHivemind,
    visibleIds: ALL_HIVEMIND_SECTIONS,
    fromUrl: fromHash && ALL_HIVEMIND_SECTIONS.includes(fromHash) ? fromHash : null,
    legacyDefaultId: legacy,
  });
}
