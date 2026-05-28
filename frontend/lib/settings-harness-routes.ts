/** Settings → Harness primary tab routing. */

import {
  harnessRulesSectionFromHash,
  harnessRulesSectionHref,
  resolveHarnessRulesSection,
  type HarnessRulesSection,
} from "@/lib/settings-harness-rules-routes";
import {
  resolvePrimarySubnavFromUrl,
  SUBNAV_MENU_KEYS,
} from "@/lib/subnav-order-preferences";

export type HarnessSection = "operator" | "rules" | "patterns";

export const HARNESS_SECTION_IDS: HarnessSection[] = ["operator", "rules", "patterns"];

/** Parse `#operator`, `#patterns`, or `#rules*` to a harness tab id. */
export function harnessSectionFromHash(hash: string): HarnessSection | null {
  if (harnessRulesSectionFromHash(hash)) {
    return "rules";
  }
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "patterns") {
    return "patterns";
  }
  if (key === "operator" || key === "operator-hub") {
    return "operator";
  }
  return null;
}

/** Canonical href for a harness primary tab. */
export function harnessSectionHref(
  section: HarnessSection,
  rulesSection: HarnessRulesSection = "overview",
): string {
  if (section === "rules") {
    return harnessRulesSectionHref(rulesSection);
  }
  return `/settings/harness#${section}`;
}

/** Prefer hash tab; bare `/settings/harness` → first tab in saved menu order. */
export function resolveHarnessSection(params: { hash?: string }): HarnessSection {
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.settingsHarness,
    visibleIds: HARNESS_SECTION_IDS,
    fromUrl: harnessSectionFromHash(params.hash ?? ""),
    legacyDefaultId: HARNESS_SECTION_IDS[0] ?? "operator",
  });
}

export function parseHarnessLocation(hash: string): {
  tab: HarnessSection;
  rulesSection: HarnessRulesSection;
} {
  const rulesFromHash = harnessRulesSectionFromHash(hash);
  if (rulesFromHash) {
    return { tab: "rules", rulesSection: rulesFromHash };
  }
  const tab = resolveHarnessSection({ hash });
  if (tab === "rules") {
    return { tab, rulesSection: resolveHarnessRulesSection({ hash }) };
  }
  return { tab, rulesSection: resolveHarnessRulesSection({}) };
}
