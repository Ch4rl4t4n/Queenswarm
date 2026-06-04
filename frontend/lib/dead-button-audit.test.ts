import { describe, expect, it } from "vitest";

import { contentFactoryPackFactoryHref } from "@/lib/factory-content-factory-routes";
import { JOBS_PATH, TASKS_HUB_PATH, WORKFLOWS_PATH } from "@/lib/execution-lane-routes";
import { integrationsTabHref } from "@/lib/integrations-routes";
import {
  AGENTS_LANE_CROSS_LINKS,
  APPS_INTEGRATIONS_CROSS_LINKS,
  appsIntegrationsCrossLinkTargets,
  agentsLaneCrossLinkTargets,
  EXECUTION_LANE_CROSS_LINKS,
  executionLaneCrossLinkTargets,
  FACTORY_CONTENT_FACTORY_CROSS_LINKS,
  factoryContentFactoryCrossLinkTargets,
  LEGACY_INTEGRATIONS_REDIRECTS,
  LEGACY_KNOWLEDGE_REDIRECTS,
  LEGACY_ROUTE_REDIRECTS,
  legacyRedirectTarget,
  resolveRemovedHashLanding,
  settingsClientLegacyRedirectTarget,
  SETTINGS_CLIENT_LEGACY_REDIRECTS,
  SETTINGS_OPERATOR_CROSS_LINKS,
  settingsCrossLinkTargets,
  urlMatchesLegacyRedirect,
  VERIFIED_PRIMARY_ROUTES,
} from "@/lib/dead-button-audit";

describe("dead-button-audit", () => {
  it("lists verified primary routes including agentic-os", () => {
    expect(VERIFIED_PRIMARY_ROUTES).toContain("/agentic-os");
    expect(VERIFIED_PRIMARY_ROUTES).toContain("/apps-tools");
    expect(VERIFIED_PRIMARY_ROUTES).toContain("/settings/costs");
  });

  it("maps legacy costs route to settings costs", () => {
    expect(LEGACY_ROUTE_REDIRECTS["/costs"]).toBe("/settings/costs");
    expect(legacyRedirectTarget("/costs")).toBe("/settings/costs");
  });

  it("maps legacy billing to costs plan hash (client redirect)", () => {
    expect(SETTINGS_CLIENT_LEGACY_REDIRECTS["/settings/billing"]).toBe("/settings/costs#billing-plans");
    expect(settingsClientLegacyRedirectTarget("/settings/billing")).toBe("/settings/costs#billing-plans");
  });

  it("documents settings cross-links from costs and enterprise", () => {
    expect(settingsCrossLinkTargets("/settings/costs")).toContain("/settings/enterprise");
    expect(settingsCrossLinkTargets("/settings/enterprise")).toContain("/settings/costs");
    expect(settingsCrossLinkTargets("/settings/enterprise")).toContain("/settings/audit");
    expect(SETTINGS_OPERATOR_CROSS_LINKS.length).toBeGreaterThanOrEqual(3);
  });

  it("maps integrations legacy aliases to hub tabs (SSOT with integrations-routes)", () => {
    expect(LEGACY_INTEGRATIONS_REDIRECTS["/connectors"]).toBe(integrationsTabHref("hub"));
    expect(LEGACY_INTEGRATIONS_REDIRECTS["/plugins"]).toBe(integrationsTabHref("plugins"));
    expect(legacyRedirectTarget("/connectors")).toBe(integrationsTabHref("hub"));
  });

  it("maps knowledge legacy aliases with hash deep links", () => {
    expect(LEGACY_KNOWLEDGE_REDIRECTS["/hive-mind"]).toBe("/knowledge#hivemind");
    expect(LEGACY_KNOWLEDGE_REDIRECTS["/recipes"]).toBe("/knowledge#recipes");
  });

  it("documents apps-tools cross-link targets", () => {
    expect(appsIntegrationsCrossLinkTargets("/apps-tools")).toContain("/apps-tools/marketing-automation");
    expect(APPS_INTEGRATIONS_CROSS_LINKS.length).toBeGreaterThanOrEqual(3);
  });

  it("documents factory ↔ content-factory bidirectional cross-links", () => {
    expect(factoryContentFactoryCrossLinkTargets("/apps-tools/content-factory")).toContain("/factory");
    expect(factoryContentFactoryCrossLinkTargets("/factory")).toContain(contentFactoryPackFactoryHref());
    expect(FACTORY_CONTENT_FACTORY_CROSS_LINKS).toHaveLength(2);
  });

  it("documents execution lane cross-links between tasks, workflows, and jobs", () => {
    expect(executionLaneCrossLinkTargets(TASKS_HUB_PATH)).toEqual([WORKFLOWS_PATH, JOBS_PATH]);
    expect(executionLaneCrossLinkTargets(WORKFLOWS_PATH)).toEqual([TASKS_HUB_PATH, JOBS_PATH]);
    expect(executionLaneCrossLinkTargets(JOBS_PATH)).toEqual([TASKS_HUB_PATH, WORKFLOWS_PATH]);
    expect(EXECUTION_LANE_CROSS_LINKS.length).toBe(6);
  });

  it("documents agents lane cross-links for foragers", () => {
    expect(agentsLaneCrossLinkTargets("/foragers")).toContain("/agents");
    expect(agentsLaneCrossLinkTargets("/foragers")).toContain("/knowledge#hivemind");
    expect(agentsLaneCrossLinkTargets("/agents")).toContain("/foragers");
    expect(AGENTS_LANE_CROSS_LINKS).toHaveLength(3);
  });

  it("matches legacy redirect URLs including query and hash", () => {
    expect(
      urlMatchesLegacyRedirect("http://localhost/integrations?tab=hub", integrationsTabHref("hub")),
    ).toBe(true);
    expect(urlMatchesLegacyRedirect("http://localhost/knowledge#hivemind", "/knowledge#hivemind")).toBe(true);
    expect(urlMatchesLegacyRedirect("http://localhost/knowledge", "/knowledge#hivemind")).toBe(false);
  });

  it("maps legacy cockpit and oracle to agentic-os", () => {
    expect(LEGACY_ROUTE_REDIRECTS["/cockpit"]).toBe("/agentic-os");
    expect(legacyRedirectTarget("/cockpit")).toBe("/agentic-os");
    expect(legacyRedirectTarget("/oracle")).toBe("/agentic-os");
  });

  it("lands removed oracle hashes on overview", () => {
    expect(resolveRemovedHashLanding("#oracle")).toEqual({ path: "/agentic-os", hash: "overview" });
    expect(resolveRemovedHashLanding("hive-oracle")).toEqual({ path: "/agentic-os", hash: "overview" });
  });
});
