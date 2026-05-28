/** Integrations hub tab routing — `?tab=` canonical; hash fragments legacy + scroll anchors. */

import {
  resolvePrimarySubnavFromUrl,
  SUBNAV_MENU_KEYS,
} from "@/lib/subnav-order-preferences";

export type IntegrationsTab = "active" | "studio" | "hub" | "marketplace" | "skills" | "external" | "plugins";

const ALL_INTEGRATIONS_TABS: IntegrationsTab[] = [
  "active",
  "studio",
  "hub",
  "marketplace",
  "skills",
  "external",
  "plugins",
];

const HASH_TO_TAB: Record<string, IntegrationsTab> = {
  studio: "studio",
  execution: "studio",
  "execution-studio": "studio",
  hub: "hub",
  connectors: "hub",
  marketplace: "marketplace",
  skills: "skills",
  external: "external",
  plugins: "plugins",
  active: "active",
  ecosystem: "active",
};

/** Canonical href for an integrations hub tab. */
export function integrationsTabHref(tab: IntegrationsTab, scrollTarget?: string): string {
  const base = `/integrations?tab=${tab}`;
  if (scrollTarget) {
    return `${base}#${scrollTarget}`;
  }
  return base;
}

/** Map legacy `#hub` / `#ecosystem` hash links to a tab id. */
export function integrationsTabFromHash(hash: string): IntegrationsTab | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  return HASH_TO_TAB[key] ?? null;
}

/** Section id to scroll when hash is a within-page anchor (e.g. `#ecosystem`). */
export function integrationsScrollTargetFromHash(hash: string): string | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "ecosystem") {
    return "ecosystem";
  }
  if (key === "oauth-consent") {
    return "oauth-consent";
  }
  if (key === "tools" || key === "tool-hub" || key === "vault" || key === "templates" || key === "roster" || key === "obsidian") {
    return key;
  }
  if (
    key === "social-publish"
    || key === "publish-queue"
    || key === "publish-performance"
    || key === "trading-cockpit"
    || key === "trading-content-hybrid"
    || key === "live-lane"
    || key === "media-agency"
    || key === "micro-saas-factory"
    || key === "execution-studio"
    || key === "innovation-lab"
  ) {
    return key;
  }
  return null;
}

/** Connector hub tab scrolled to hosted OAuth consent rail (X · Meta · TikTok). */
export function integrationsHubOAuthHref(): string {
  return `/integrations?tab=hub&hubSection=oauth#oauth-consent`;
}

/** Resolve tab from query string `?tab=` value. */
export function integrationsTabFromQuery(raw: string | null | undefined): IntegrationsTab | null {
  if (!raw) {
    return null;
  }
  const allowed: IntegrationsTab[] = ["active", "studio", "hub", "marketplace", "skills", "external", "plugins"];
  return allowed.includes(raw as IntegrationsTab) ? (raw as IntegrationsTab) : null;
}

export type ExecutionStudioWorkspaceSection =
  | "overview"
  | "publish"
  | "lanes"
  | "stack"
  | "analytics"
  | "innovation";

const EXECUTION_STUDIO_SECTIONS: ExecutionStudioWorkspaceSection[] = [
  "overview",
  "publish",
  "lanes",
  "stack",
  "analytics",
  "innovation",
];

/** Map Execution Studio in-page anchors to workspace sub-nav section. */
export function executionStudioWorkspaceFromHash(hash: string): ExecutionStudioWorkspaceSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  if (key === "innovation-lab") {
    return "innovation";
  }
  if (
    key === "publish-queue"
    || key === "social-publish"
    || key === "publish-performance"
    || key === "trading-cockpit"
    || key === "trading-content-hybrid"
  ) {
    return "publish";
  }
  if (key === "live-lane" || key === "media-agency" || key === "micro-saas-factory") {
    return "lanes";
  }
  if (key === "execution-studio") {
    return "overview";
  }
  return null;
}

/** Deep link into Execution Studio workspace section with optional scroll anchor. */
export function executionStudioSectionHref(
  section: ExecutionStudioWorkspaceSection,
  scrollTarget?: string,
): string {
  const base = `/integrations?tab=studio&section=${section}`;
  if (scrollTarget) {
    return `${base}#${scrollTarget}`;
  }
  if (section === "innovation") {
    return `${base}#innovation-lab`;
  }
  return base;
}

export function executionStudioSectionFromQuery(raw: string | null | undefined): ExecutionStudioWorkspaceSection | null {
  if (!raw) {
    return null;
  }
  return EXECUTION_STUDIO_SECTIONS.includes(raw as ExecutionStudioWorkspaceSection)
    ? (raw as ExecutionStudioWorkspaceSection)
    : null;
}

/** True when URL names a tab explicitly (`?tab=` or legacy section hash). */
export function integrationsTabExplicitInLocation(params: {
  queryTab?: string | null;
  hash?: string;
}): boolean {
  return (
    integrationsTabFromQuery(params.queryTab) !== null ||
    integrationsTabFromHash(params.hash ?? "") !== null
  );
}

/** Prefer `?tab=` then legacy hash; bare `/integrations` → first tab in saved menu order. */
export function resolveIntegrationsTab(params: {
  queryTab?: string | null;
  hash?: string;
  visibleTabIds?: readonly IntegrationsTab[];
  fallback?: IntegrationsTab;
}): IntegrationsTab {
  const visible =
    params.visibleTabIds && params.visibleTabIds.length > 0
      ? params.visibleTabIds
      : ALL_INTEGRATIONS_TABS;
  const legacy = params.fallback ?? visible[0] ?? "active";
  const fromUrl =
    integrationsTabFromQuery(params.queryTab) ?? integrationsTabFromHash(params.hash ?? "");
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.integrationsPrimary,
    visibleIds: visible,
    fromUrl: fromUrl && visible.includes(fromUrl) ? fromUrl : null,
    legacyDefaultId: legacy,
  });
}
