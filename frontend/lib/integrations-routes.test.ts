import { describe, expect, it } from "vitest";

import {
  integrationsScrollTargetFromHash,
  integrationsTabFromHash,
  integrationsTabFromQuery,
  integrationsTabHref,
  resolveIntegrationsTab,
} from "@/lib/integrations-routes";

describe("integrationsTabHref", () => {
  it("returns query path for every tab", () => {
    expect(integrationsTabHref("active")).toBe("/integrations?tab=active");
    expect(integrationsTabHref("hub")).toBe("/integrations?tab=hub");
  });

  it("appends scroll hash when requested", () => {
    expect(integrationsTabHref("active", "ecosystem")).toBe("/integrations?tab=active#ecosystem");
    expect(integrationsTabHref("hub", "oauth-consent")).toBe("/integrations?tab=hub#oauth-consent");
  });
});

describe("integrationsTabFromHash", () => {
  it("maps legacy hash aliases", () => {
    expect(integrationsTabFromHash("#hub")).toBe("hub");
    expect(integrationsTabFromHash("#ecosystem")).toBe("active");
    expect(integrationsTabFromHash("#marketplace")).toBe("marketplace");
  });

  it("routes legacy hub sub-section hashes to the hub tab", () => {
    expect(integrationsTabFromHash("#tools")).toBe("hub");
    expect(integrationsTabFromHash("#tool-hub")).toBe("hub");
    expect(integrationsTabFromHash("#vault")).toBe("hub");
    expect(integrationsTabFromHash("#oauth-consent")).toBe("hub");
    expect(integrationsTabFromHash("#templates")).toBe("hub");
  });
});

describe("integrationsScrollTargetFromHash", () => {
  it("returns ecosystem anchor id", () => {
    expect(integrationsScrollTargetFromHash("#ecosystem")).toBe("ecosystem");
    expect(integrationsScrollTargetFromHash("#oauth-consent")).toBe("oauth-consent");
    expect(integrationsScrollTargetFromHash("#social-publish")).toBe("social-publish");
    expect(integrationsScrollTargetFromHash("#publish-queue")).toBe("publish-queue");
    expect(integrationsScrollTargetFromHash("#publish-performance")).toBe("publish-performance");
    expect(integrationsScrollTargetFromHash("#trading-cockpit")).toBe("trading-cockpit");
    expect(integrationsScrollTargetFromHash("#trading-content-hybrid")).toBe("trading-content-hybrid");
    expect(integrationsScrollTargetFromHash("#live-lane")).toBe("live-lane");
    expect(integrationsScrollTargetFromHash("#media-agency")).toBe("media-agency");
    expect(integrationsScrollTargetFromHash("#micro-saas-factory")).toBe("micro-saas-factory");
    expect(integrationsScrollTargetFromHash("#hub")).toBeNull();
  });

  it("maps Tool Hub + templates short hashes to their real DOM ids", () => {
    expect(integrationsScrollTargetFromHash("#tools")).toBe("hub-tools");
    expect(integrationsScrollTargetFromHash("#tool-hub")).toBe("hub-tools");
    expect(integrationsScrollTargetFromHash("#templates")).toBe("hub-templates");
    expect(integrationsScrollTargetFromHash("#phase3-templates")).toBe("hub-templates");
    // vault / roster / obsidian have no in-page anchor — hub sub-section state renders them.
    expect(integrationsScrollTargetFromHash("#vault")).toBeNull();
  });
});

describe("resolveIntegrationsTab", () => {
  it("prefers query over hash", () => {
    expect(resolveIntegrationsTab({ queryTab: "skills", hash: "#hub" })).toBe("skills");
  });

  it("falls back to hash then first visible default", () => {
    expect(resolveIntegrationsTab({ hash: "#plugins" })).toBe("plugins");
    expect(resolveIntegrationsTab({})).toBe("active");
    expect(resolveIntegrationsTab({ visibleTabIds: ["hub", "active"] })).toBe("hub");
  });
});

describe("integrationsTabFromQuery", () => {
  it("rejects unknown tabs", () => {
    expect(integrationsTabFromQuery("unknown")).toBeNull();
    expect(integrationsTabFromQuery("external")).toBe("external");
  });
});
