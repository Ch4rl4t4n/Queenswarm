import { describe, expect, it } from "vitest";

import {
  integrationsHubSectionFromHash,
  integrationsHubSectionFromQuery,
  integrationsHubSectionHref,
  resolveIntegrationsHubSection,
} from "@/lib/integrations-hub-routes";

describe("integrationsHubSectionHref", () => {
  it("returns query path with hubSection", () => {
    expect(integrationsHubSectionHref("tools")).toBe("/integrations?tab=hub&hubSection=tools");
    expect(integrationsHubSectionHref("oauth", "oauth-consent")).toBe(
      "/integrations?tab=hub&hubSection=oauth#oauth-consent",
    );
  });
});

describe("integrationsHubSectionFromHash", () => {
  it("maps legacy oauth anchor", () => {
    expect(integrationsHubSectionFromHash("#oauth-consent")).toBe("oauth");
  });

  it("maps section ids", () => {
    expect(integrationsHubSectionFromHash("#templates")).toBe("templates");
  });
});

describe("resolveIntegrationsHubSection", () => {
  it("prefers query over hash", () => {
    expect(
      resolveIntegrationsHubSection({ querySection: "vault", hash: "#oauth-consent" }),
    ).toBe("vault");
  });

  it("defaults to tools", () => {
    expect(resolveIntegrationsHubSection({})).toBe("tools");
  });

  it("reads query param", () => {
    expect(integrationsHubSectionFromQuery("roster")).toBe("roster");
    expect(integrationsHubSectionFromQuery("invalid")).toBeNull();
  });
});
