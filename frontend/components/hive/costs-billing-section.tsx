"use client";

import { useEffect } from "react";

import { BillingSettingsPanel } from "@/components/hive/billing-settings-panel";
import { BILLING_PLANS_HASH, COSTS_BILLING_SECTION_ID } from "@/lib/billing-settings-copy";

function scrollToBillingHash(): void {
  const hash = window.location.hash.replace(/^#/, "");
  if (hash !== BILLING_PLANS_HASH) {
    return;
  }
  const target = document.getElementById(BILLING_PLANS_HASH);
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
}

/** Billing limits + plans embedded under Settings → Costs with legacy hash support. */
export function CostsBillingSection() {
  useEffect(() => {
    scrollToBillingHash();
    window.addEventListener("hashchange", scrollToBillingHash);
    return () => window.removeEventListener("hashchange", scrollToBillingHash);
  }, []);

  return (
    <section
      id={COSTS_BILLING_SECTION_ID}
      aria-labelledby="hive-costs-billing-heading"
      className="border-t border-(--qs-border) pt-6"
    >
      <h2 id="hive-costs-billing-heading" className="sr-only">
        Plan, tier limits, and billing
      </h2>
      <BillingSettingsPanel variant="embedded" />
    </section>
  );
}
