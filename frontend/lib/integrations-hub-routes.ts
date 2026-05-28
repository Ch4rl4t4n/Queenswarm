/** Connector hub sub-section routing inside Integrations → hub tab. */

import type { LucideIcon } from "lucide-react";
import { BookOpen, KeyRound, Link2, Plug, Sparkles, Wrench } from "lucide-react";

import { resolvePrimarySubnavFromUrl, SUBNAV_MENU_KEYS } from "@/lib/subnav-order-preferences";

export type IntegrationsHubSection = "tools" | "oauth" | "vault" | "templates" | "roster" | "obsidian";

const HASH_TO_HUB_SECTION: Record<string, IntegrationsHubSection> = {
  tools: "tools",
  "tool-hub": "tools",
  oauth: "oauth",
  "oauth-consent": "oauth",
  vault: "vault",
  templates: "templates",
  "phase3-templates": "templates",
  roster: "roster",
  obsidian: "obsidian",
};

const HUB_SECTION_QUERY_VALUES: IntegrationsHubSection[] = [
  "tools",
  "oauth",
  "vault",
  "templates",
  "roster",
  "obsidian",
];

export const INTEGRATIONS_HUB_SECTIONS: {
  id: IntegrationsHubSection;
  label: string;
  icon: LucideIcon;
}[] = [
  { id: "tools", label: "Tool registry", icon: Wrench },
  { id: "oauth", label: "OAuth connect", icon: Link2 },
  { id: "vault", label: "Vault secrets", icon: KeyRound },
  { id: "templates", label: "Phase 3 templates", icon: Sparkles },
  { id: "roster", label: "Roster & add", icon: Plug },
  { id: "obsidian", label: "Obsidian vault", icon: BookOpen },
];

/** Canonical href for a connector hub sub-section. */
export function integrationsHubSectionHref(
  section: IntegrationsHubSection,
  scrollTarget?: string,
): string {
  const base = `/integrations?tab=hub&hubSection=${section}`;
  if (scrollTarget) {
    return `${base}#${scrollTarget}`;
  }
  return base;
}

/** Resolve `?hubSection=` query value. */
export function integrationsHubSectionFromQuery(raw: string | null | undefined): IntegrationsHubSection | null {
  if (!raw) {
    return null;
  }
  return HUB_SECTION_QUERY_VALUES.includes(raw as IntegrationsHubSection)
    ? (raw as IntegrationsHubSection)
    : null;
}

/** Map legacy `#oauth-consent` and section hashes to hub sub-section id. */
export function integrationsHubSectionFromHash(hash: string): IntegrationsHubSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  return HASH_TO_HUB_SECTION[key] ?? null;
}

/** Prefer query param, then hash, then first tab in saved hub menu order. */
export function resolveIntegrationsHubSection(params: {
  querySection?: string | null;
  hash?: string;
  fallback?: IntegrationsHubSection;
}): IntegrationsHubSection {
  const visible = HUB_SECTION_QUERY_VALUES;
  const legacy = params.fallback ?? visible[0] ?? "tools";
  const fromUrl =
    integrationsHubSectionFromQuery(params.querySection) ??
    integrationsHubSectionFromHash(params.hash ?? "");
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.integrationsHub,
    visibleIds: visible,
    fromUrl: fromUrl && visible.includes(fromUrl) ? fromUrl : null,
    legacyDefaultId: legacy,
  });
}
