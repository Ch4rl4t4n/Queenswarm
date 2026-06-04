/**
 * Factory ↔ Content Factory routing SSOT (Whole-App UI Reorder Phase 17).
 *
 * `/factory` — standalone blueprint lane (More menu + spawn CTA).
 * `/apps-tools/content-factory` — module workspace (media agency + embedded micro-SaaS panel).
 */

export const FACTORY_BLUEPRINT_PATH = "/factory";
export const CONTENT_FACTORY_PATH = "/apps-tools/content-factory";

export type ContentFactorySection = "agency" | "micro-saas" | "pack-factory";

const SECTION_HASH: Record<ContentFactorySection, string> = {
  agency: "media-agency",
  "micro-saas": "micro-saas-factory",
  "pack-factory": "pack-factory",
};

/** Canonical href for a Content Factory sub-section (`?section=` + scroll hash). */
export function contentFactorySectionHref(section: ContentFactorySection): string {
  return `${CONTENT_FACTORY_PATH}?section=${section}#${SECTION_HASH[section]}`;
}

/** Deep link into the Micro-SaaS lane inside Content Factory. */
export function contentFactoryMicroSaasHref(): string {
  return contentFactorySectionHref("micro-saas");
}

/** Deep link into Media agency lane inside Content Factory. */
export function contentFactoryAgencyHref(): string {
  return contentFactorySectionHref("agency");
}

/** Deep link into Content Pack Factory lane inside Content Factory. */
export function contentFactoryPackFactoryHref(): string {
  return `${CONTENT_FACTORY_PATH}#pipeline`;
}

/** Operator-facing cross-link labels — keep UI + E2E in sync. */
export const FACTORY_CROSS_LINK_LABELS = {
  toBlueprint: "Micro-SaaS Factory blueprint",
  toContentFactoryModule: "Content Factory module",
} as const;
