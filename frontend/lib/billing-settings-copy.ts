/** Copy + layout rules for BillingSettingsPanel (standalone vs embedded in Costs). */

export type BillingSettingsPanelVariant = "standalone" | "embedded";

/** Primary usage card title — avoids duplicate page-level “Usage & Billing” under Costs h1. */
export function billingUsageSectionTitle(variant: BillingSettingsPanelVariant): string {
  return variant === "embedded" ? "Plan & tier limits" : "Usage & Billing";
}

/** Self-referential cost cockpit CTA is redundant when panel is already on /settings/costs. */
export function billingPanelShowsCostCockpitLink(variant: BillingSettingsPanelVariant): boolean {
  return variant !== "embedded";
}

/** Hash target for legacy /settings/billing deep links. */
export const BILLING_PLANS_HASH = "billing-plans";

export const COSTS_BILLING_SECTION_ID = "hive-costs-billing";

/** In-page href for Costs tier-limits KPI → plan comparison cards. */
export function costsBillingPlansHref(): string {
  return `#${BILLING_PLANS_HASH}`;
}
