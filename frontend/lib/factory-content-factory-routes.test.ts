import { describe, expect, it } from "vitest";

import {
  contentFactoryAgencyHref,
  contentFactoryMicroSaasHref,
  contentFactoryPackFactoryHref,
  contentFactorySectionHref,
  FACTORY_BLUEPRINT_PATH,
  FACTORY_CROSS_LINK_LABELS,
} from "@/lib/factory-content-factory-routes";

describe("factory-content-factory-routes", () => {
  it("builds pack factory deep link with hash tab", () => {
    expect(contentFactoryPackFactoryHref()).toBe("/apps-tools/content-factory#research");
  });

  it("builds micro-saas deep link with query and hash", () => {
    expect(contentFactoryMicroSaasHref()).toBe(
      "/apps-tools/content-factory?section=micro-saas#micro-saas-factory",
    );
    expect(contentFactorySectionHref("micro-saas")).toBe(contentFactoryMicroSaasHref());
  });

  it("builds agency deep link", () => {
    expect(contentFactoryAgencyHref()).toBe("/apps-tools/content-factory?section=agency#media-agency");
  });

  it("exposes stable blueprint path and cross-link labels", () => {
    expect(FACTORY_BLUEPRINT_PATH).toBe("/factory");
    expect(FACTORY_CROSS_LINK_LABELS.toBlueprint).toBe("Micro-SaaS Factory blueprint");
    expect(FACTORY_CROSS_LINK_LABELS.toContentFactoryModule).toBe("Content Factory module");
  });
});
