/** Agents → Ecosystem sub-section routing (compact sub-nav on /agents). */

import type { LucideIcon } from "lucide-react";
import { Hexagon, Network, Sparkles, Users, Waypoints, Zap, Radio } from "lucide-react";

import { resolvePrimarySubnavFromUrl, SUBNAV_MENU_KEYS } from "@/lib/subnav-order-preferences";

export type AgentsEcosystemSection =
  | "roles"
  | "runtime"
  | "context"
  | "learning"
  | "sessions"
  | "roster"
  | "hierarchy";

const HASH_TO_SECTION: Record<string, AgentsEcosystemSection> = {
  roles: "roles",
  runtime: "runtime",
  context: "context",
  "context-graph": "context",
  learning: "learning",
  sessions: "sessions",
  roster: "roster",
  hierarchy: "hierarchy",
};

export const AGENTS_ECOSYSTEM_SECTIONS: {
  id: AgentsEcosystemSection;
  label: string;
  icon: LucideIcon;
}[] = [
  { id: "roles", label: "Bee roles", icon: Hexagon },
  { id: "runtime", label: "Hybrid runtime", icon: Zap },
  { id: "context", label: "Context graph", icon: Network },
  { id: "learning", label: "Learning loop", icon: Sparkles },
  { id: "sessions", label: "Supervisor", icon: Radio },
  { id: "roster", label: "Active roster", icon: Users },
  { id: "hierarchy", label: "Hierarchy", icon: Waypoints },
];

/** Canonical href for an Ecosystem sub-section (preserves legacy `#sessions` / `#hierarchy`). */
export function agentsEcosystemSectionHref(section: AgentsEcosystemSection): string {
  if (section === "context") {
    return "/agents#context-graph";
  }
  return `/agents#${section}`;
}

/** Map location hash to an Ecosystem sub-section id. */
export function agentsEcosystemSectionFromHash(hash: string): AgentsEcosystemSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  return HASH_TO_SECTION[key] ?? null;
}

/** Prefer hash section; bare `/agents` → first tab in saved menu order. */
export function resolveAgentsEcosystemSection(params: {
  hash?: string;
  visibleIds?: readonly AgentsEcosystemSection[];
  fallback?: AgentsEcosystemSection;
}): AgentsEcosystemSection {
  const visible = params.visibleIds?.length
    ? params.visibleIds
    : AGENTS_ECOSYSTEM_SECTIONS.map((row) => row.id);
  const legacy = params.fallback ?? visible[0] ?? "roles";
  const fromHash = agentsEcosystemSectionFromHash(params.hash ?? "");
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.agentsEcosystem,
    visibleIds: visible,
    fromUrl: fromHash && visible.includes(fromHash) ? fromHash : null,
    legacyDefaultId: legacy,
  });
}
