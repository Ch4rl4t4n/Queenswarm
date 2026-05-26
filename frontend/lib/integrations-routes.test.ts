import { describe, expect, it } from "vitest";

import {
  integrationsScrollTargetFromHash,
  integrationsTabFromHash,
  integrationsTabFromQuery,
  integrationsTabHref,
  resolveIntegrationsTab,
} from "@/lib/integrations-routes";

describe("integrationsTabHref", () => {
  it("returns bare path for active tab", () => {
    expect(integrationsTabHref("active")).toBe("/integrations");
  });

  it("returns query path for other tabs", () => {
    expect(integrationsTabHref("hub")).toBe("/integrations?tab=hub");
  });

  it("appends scroll hash when requested", () => {
    expect(integrationsTabHref("active", "ecosystem")).toBe("/integrations#ecosystem");
    expect(integrationsTabHref("hub", "oauth-consent")).toBe("/integrations?tab=hub#oauth-consent");
  });
});

describe("integrationsTabFromHash", () => {
  it("maps legacy hash aliases", () => {
    expect(integrationsTabFromHash("#hub")).toBe("hub");
    expect(integrationsTabFromHash("#ecosystem")).toBe("active");
    expect(integrationsTabFromHash("#marketplace")).toBe("marketplace");
  });
});

describe("integrationsScrollTargetFromHash", () => {
  it("returns ecosystem anchor id", () => {
    expect(integrationsScrollTargetFromHash("#ecosystem")).toBe("ecosystem");
    expect(integrationsScrollTargetFromHash("#oauth-consent")).toBe("oauth-consent");
    expect(integrationsScrollTargetFromHash("#social-publish")).toBe("social-publish");
    expect(integrationsScrollTargetFromHash("#publish-queue")).toBe("publish-queue");
    expect(integrationsScrollTargetFromHash("#hub")).toBeNull();
  });
});

describe("resolveIntegrationsTab", () => {
  it("prefers query over hash", () => {
    expect(resolveIntegrationsTab({ queryTab: "skills", hash: "#hub" })).toBe("skills");
  });

  it("falls back to hash then default", () => {
    expect(resolveIntegrationsTab({ hash: "#plugins" })).toBe("plugins");
    expect(resolveIntegrationsTab({})).toBe("active");
  });
});

describe("integrationsTabFromQuery", () => {
  it("rejects unknown tabs", () => {
    expect(integrationsTabFromQuery("unknown")).toBeNull();
    expect(integrationsTabFromQuery("external")).toBe("external");
  });
});
