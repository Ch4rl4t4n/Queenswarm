/** Integrations hub tab routing — `?tab=` canonical; hash fragments legacy + scroll anchors. */

export type IntegrationsTab = "active" | "hub" | "marketplace" | "skills" | "external" | "plugins";

const HASH_TO_TAB: Record<string, IntegrationsTab> = {
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
  const base = tab === "active" ? "/integrations" : `/integrations?tab=${tab}`;
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
  return null;
}

/** Resolve tab from query string `?tab=` value. */
export function integrationsTabFromQuery(raw: string | null | undefined): IntegrationsTab | null {
  if (!raw) {
    return null;
  }
  const allowed: IntegrationsTab[] = ["active", "hub", "marketplace", "skills", "external", "plugins"];
  return allowed.includes(raw as IntegrationsTab) ? (raw as IntegrationsTab) : null;
}

/** Prefer `?tab=` then legacy hash when hydrating client tab state. */
export function resolveIntegrationsTab(params: {
  queryTab?: string | null;
  hash?: string;
  fallback?: IntegrationsTab;
}): IntegrationsTab {
  return (
    integrationsTabFromQuery(params.queryTab) ??
    integrationsTabFromHash(params.hash ?? "") ??
    params.fallback ??
    "active"
  );
}
