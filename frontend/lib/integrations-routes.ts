/** Integrations hub tab routing — always use `?tab=` (hash fragments are legacy). */

export type IntegrationsTab = "active" | "hub" | "marketplace" | "skills" | "external" | "plugins";

const HASH_TO_TAB: Record<string, IntegrationsTab> = {
  hub: "hub",
  ecosystem: "hub",
  connectors: "hub",
  marketplace: "marketplace",
  skills: "skills",
  external: "external",
  plugins: "plugins",
  active: "active",
};

export function integrationsTabHref(tab: IntegrationsTab): string {
  return tab === "active" ? "/integrations" : `/integrations?tab=${tab}`;
}

/** Map legacy `#hub` / `#ecosystem` links to a tab id. */
export function integrationsTabFromHash(hash: string): IntegrationsTab | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (!key) {
    return null;
  }
  return HASH_TO_TAB[key] ?? null;
}
