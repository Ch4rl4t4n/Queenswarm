import { describe, expect, it } from "vitest";

import {
  billingPanelShowsCostCockpitLink,
  billingUsageSectionTitle,
  BILLING_PLANS_HASH,
  costsBillingPlansHref,
  COSTS_BILLING_SECTION_ID,
} from "@/lib/billing-settings-copy";

describe("billing-settings-copy", () => {
  it("uses subsection title when embedded in Costs", () => {
    expect(billingUsageSectionTitle("embedded")).toBe("Plan & tier limits");
    expect(billingUsageSectionTitle("standalone")).toBe("Usage & Billing");
  });

  it("hides cost cockpit self-link when embedded", () => {
    expect(billingPanelShowsCostCockpitLink("embedded")).toBe(false);
    expect(billingPanelShowsCostCockpitLink("standalone")).toBe(true);
  });

  it("exports stable hash anchors for legacy billing URLs", () => {
    expect(BILLING_PLANS_HASH).toBe("billing-plans");
    expect(COSTS_BILLING_SECTION_ID).toBe("hive-costs-billing");
    expect(costsBillingPlansHref()).toBe("#billing-plans");
  });
});
