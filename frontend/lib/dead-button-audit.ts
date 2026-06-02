/**
 * Whole-App UI Reorder — dead-button audit registry.
 * Canonical hrefs for operator CTAs; legacy aliases that must redirect (not 404).
 */

import { BILLING_PLANS_HASH } from "@/lib/billing-settings-copy";
import {
  CONTENT_FACTORY_PATH,
  contentFactoryMicroSaasHref,
  FACTORY_BLUEPRINT_PATH,
  FACTORY_CROSS_LINK_LABELS,
} from "@/lib/factory-content-factory-routes";
import {
  AGENTS_HUB_PATH,
  EXECUTION_LANE_CROSS_LINK_LABELS,
  FORAGERS_PATH,
  JOBS_PATH,
  KNOWLEDGE_HIVEMIND_HREF,
  TASKS_HUB_PATH,
  WORKFLOWS_PATH,
} from "@/lib/execution-lane-routes";
import { integrationsTabHref } from "@/lib/integrations-routes";

export const DEAD_BUTTON_AUDIT_VERSION = "2026.05-v6";

/** Primary operator destinations — every sidebar / header CTA should resolve here. */
export const VERIFIED_PRIMARY_ROUTES = [
  "/agentic-os",
  "/swarms",
  "/tasks",
  "/routines",
  "/agents",
  "/apps-tools",
  "/integrations",
  "/knowledge",
  "/ballroom",
  "/settings/security",
  "/settings/costs",
  "/manual",
] as const;

/** Agentic OS + dashboard legacy bookmarks. */
export const LEGACY_AGENTIC_REDIRECTS: Record<string, string> = {
  "/cockpit": "/agentic-os",
  "/oracle": "/agentic-os",
  "/dashboard": "/agentic-os",
};

/** Settings + billing legacy paths. */
export const LEGACY_SETTINGS_REDIRECTS: Record<string, string> = {
  "/costs": "/settings/costs",
};

/** Integrations hub consolidations (Phase 70 IA). */
export const LEGACY_INTEGRATIONS_REDIRECTS: Record<string, string> = {
  "/connectors": integrationsTabHref("hub"),
  "/plugins": integrationsTabHref("plugins"),
  "/external-projects": integrationsTabHref("external"),
};

/** Knowledge hub consolidations — hash preserved for deep links. */
export const LEGACY_KNOWLEDGE_REDIRECTS: Record<string, string> = {
  "/hive-mind": "/knowledge#hivemind",
  "/outputs": "/knowledge#outputs",
  "/recipes": "/knowledge#recipes",
  "/learning": "/knowledge#recipes",
};

/** Execution lane legacy aliases. */
export const LEGACY_EXECUTION_REDIRECTS: Record<string, string> = {
  "/execution": "/tasks",
  "/hierarchy": "/agents",
};

/** Agents sub-route bookmarks. */
export const LEGACY_AGENTS_REDIRECTS: Record<string, string> = {
  "/agents/hierarchy": "/agents#hierarchy",
  "/agents/sessions": "/agents#sessions",
};

/** Legacy paths kept for bookmarks — must redirect, never render empty shells. */
export const LEGACY_ROUTE_REDIRECTS: Record<string, string> = {
  ...LEGACY_AGENTIC_REDIRECTS,
  ...LEGACY_SETTINGS_REDIRECTS,
  ...LEGACY_INTEGRATIONS_REDIRECTS,
  ...LEGACY_KNOWLEDGE_REDIRECTS,
  ...LEGACY_EXECUTION_REDIRECTS,
  ...LEGACY_AGENTS_REDIRECTS,
};

/** Client-side legacy settings routes (Next.js page + hash preservation). */
export const SETTINGS_CLIENT_LEGACY_REDIRECTS: Record<string, string> = {
  "/settings/billing": `/settings/costs#${BILLING_PLANS_HASH}`,
};

/** Verified cross-panel CTAs in Settings — both endpoints must render shell content. */
export const SETTINGS_OPERATOR_CROSS_LINKS = [
  { from: "/settings/costs", to: "/settings/enterprise", label: "Open enterprise settings" },
  { from: "/settings/enterprise", to: "/settings/costs", label: "View spend cockpit" },
  { from: "/settings/enterprise", to: "/settings/audit", label: "Open audit log" },
] as const;

/** Verified Apps & Tools ↔ Integrations cross-links (module discovery). */
export const APPS_INTEGRATIONS_CROSS_LINKS = [
  { from: "/apps-tools", to: "/apps-tools/marketing-automation", label: "Marketing Automation" },
  { from: "/apps-tools", to: CONTENT_FACTORY_PATH, label: "Content Factory" },
  { from: "/integrations", to: "/integrations?tab=skills", label: "Skills export" },
] as const;

/** Factory blueprint lane ↔ Content Factory module (bidirectional operator CTAs). */
export const FACTORY_CONTENT_FACTORY_CROSS_LINKS = [
  { from: CONTENT_FACTORY_PATH, to: FACTORY_BLUEPRINT_PATH, label: FACTORY_CROSS_LINK_LABELS.toBlueprint },
  { from: FACTORY_BLUEPRINT_PATH, to: contentFactoryMicroSaasHref(), label: FACTORY_CROSS_LINK_LABELS.toContentFactoryModule },
] as const;

/** Tasks ↔ Workflows ↔ Jobs — execution lane More-menu triangle. */
export const EXECUTION_LANE_CROSS_LINKS = [
  { from: TASKS_HUB_PATH, to: WORKFLOWS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows },
  { from: TASKS_HUB_PATH, to: JOBS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toAsyncJobs },
  { from: WORKFLOWS_PATH, to: TASKS_HUB_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toTasksHub },
  { from: WORKFLOWS_PATH, to: JOBS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toAsyncJobs },
  { from: JOBS_PATH, to: TASKS_HUB_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toTasksHub },
  { from: JOBS_PATH, to: WORKFLOWS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows },
] as const;

/** Agents hub ↔ Foragers ↔ HiveMind ingest context. */
export const AGENTS_LANE_CROSS_LINKS = [
  { from: FORAGERS_PATH, to: AGENTS_HUB_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toAgentsHub },
  { from: FORAGERS_PATH, to: KNOWLEDGE_HIVEMIND_HREF, label: EXECUTION_LANE_CROSS_LINK_LABELS.toHiveMind },
  { from: AGENTS_HUB_PATH, to: FORAGERS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toForagers },
] as const;

export function legacyRedirectTarget(pathname: string): string | null {
  const normalized = pathname.replace(/\/$/, "") || "/";
  return LEGACY_ROUTE_REDIRECTS[normalized] ?? null;
}

export function settingsClientLegacyRedirectTarget(pathname: string): string | null {
  const normalized = pathname.replace(/\/$/, "") || "/";
  return SETTINGS_CLIENT_LEGACY_REDIRECTS[normalized] ?? null;
}

/** Hash deep-links that were removed from product — map to safe landing sections. */
export const REMOVED_HASH_LANDINGS: Record<string, { path: string; hash: string }> = {
  oracle: { path: "/agentic-os", hash: "overview" },
  "hive-oracle": { path: "/agentic-os", hash: "overview" },
};

export function resolveRemovedHashLanding(hash: string): { path: string; hash: string } | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  return REMOVED_HASH_LANDINGS[key] ?? null;
}

export function settingsCrossLinkTargets(fromPath: string): readonly string[] {
  const normalized = fromPath.replace(/\/$/, "") || "/";
  return SETTINGS_OPERATOR_CROSS_LINKS.filter((row) => row.from === normalized).map((row) => row.to);
}

export function appsIntegrationsCrossLinkTargets(fromPath: string): readonly string[] {
  const normalized = fromPath.replace(/\/$/, "") || "/";
  return APPS_INTEGRATIONS_CROSS_LINKS.filter((row) => row.from === normalized).map((row) => row.to);
}

export function factoryContentFactoryCrossLinkTargets(fromPath: string): readonly string[] {
  const normalized = fromPath.replace(/\/$/, "") || "/";
  return FACTORY_CONTENT_FACTORY_CROSS_LINKS.filter((row) => row.from === normalized).map((row) => row.to);
}

export function executionLaneCrossLinkTargets(fromPath: string): readonly string[] {
  const normalized = fromPath.replace(/\/$/, "") || "/";
  return EXECUTION_LANE_CROSS_LINKS.filter((row) => row.from === normalized).map((row) => row.to);
}

export function agentsLaneCrossLinkTargets(fromPath: string): readonly string[] {
  const normalized = fromPath.replace(/\/$/, "") || "/";
  return AGENTS_LANE_CROSS_LINKS.filter((row) => row.from === normalized).map((row) => row.to);
}

/** Compare full page URL against a legacy redirect target (path + query + hash). */
export function urlMatchesLegacyRedirect(pageUrl: string, target: string): boolean {
  const page = new URL(pageUrl, "http://localhost");
  const expected = new URL(target, "http://localhost");
  const normalizePath = (path: string) => path.replace(/\/$/, "") || "/";
  if (normalizePath(page.pathname) !== normalizePath(expected.pathname)) {
    return false;
  }
  for (const [key, value] of expected.searchParams.entries()) {
    if (page.searchParams.get(key) !== value) {
      return false;
    }
  }
  const expectedHash = expected.hash.replace(/^#/, "");
  if (expectedHash.length > 0 && page.hash.replace(/^#/, "") !== expectedHash) {
    return false;
  }
  return true;
}
