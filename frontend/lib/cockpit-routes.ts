/** Agentic OS hub section routing — hash anchors for /agentic-os sub-views. */

import { resolvePrimarySubnavFromUrl, SUBNAV_MENU_KEYS } from "@/lib/subnav-order-preferences";

export type CockpitSection = "overview" | "command" | "grok" | "icm" | "fleet" | "modules" | "innovation";

const ALL_COCKPIT_SECTIONS: CockpitSection[] = [
  "overview",
  "command",
  "grok",
  "icm",
  "fleet",
  "modules",
  "innovation",
];

const HASH_TO_SECTION: Record<string, CockpitSection> = {
  overview: "overview",
  command: "command",
  grok: "grok",
  "grok-control-plane": "grok",
  icm: "icm",
  "icm-tools": "icm",
  "link-drop": "icm",
  "dialogue-extract": "icm",
  fleet: "fleet",
  "swarm-fleet": "fleet",
  "swarm-immune-system": "fleet",
  modules: "modules",
  "regret-simulator": "modules",
  "context-teleport": "modules",
  "ambient-forager": "modules",
  "parallel-hive": "modules",
  "evolutionary-recipes": "modules",
  innovation: "innovation",
  "innovation-lab": "innovation",
  "intent-crystallizer": "command",
  "zero-ui": "command",
  "proof-of-hive": "overview",
  /** Legacy — Oracle removed from UI; land on overview priorities. */
  oracle: "overview",
  "hive-oracle": "overview",
};

/** Canonical href for a cockpit section. */
export function cockpitSectionHref(section: CockpitSection): string {
  return `/agentic-os#${section}`;
}

/** Map legacy `#link-drop` / `#dialogue-extract` hashes to a section id. */
export function cockpitSectionFromHash(hash: string): CockpitSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  return HASH_TO_SECTION[key] ?? null;
}

/** Prefer hash section; bare `/cockpit` → first tab in saved menu order. */
export function resolveCockpitSection(params: {
  hash?: string;
  visibleIds?: readonly CockpitSection[];
  fallback?: CockpitSection;
}): CockpitSection {
  const visible =
    params.visibleIds && params.visibleIds.length > 0 ? params.visibleIds : ALL_COCKPIT_SECTIONS;
  const legacy = params.fallback ?? visible[0] ?? "overview";
  const fromHash = cockpitSectionFromHash(params.hash ?? "");
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.cockpitPrimary,
    visibleIds: visible,
    fromUrl: fromHash && visible.includes(fromHash) ? fromHash : null,
    legacyDefaultId: legacy,
  });
}
