/** Rules & skills sub-sections inside Settings → Harness → Rules tab. */

import type { LucideIcon } from "lucide-react";
import { Activity, BookOpen, Cpu, Layers, Sparkles, Wrench } from "lucide-react";

import {
  resolvePrimarySubnavFromUrl,
  SUBNAV_MENU_KEYS,
} from "@/lib/subnav-order-preferences";

export type HarnessRulesSection = "overview" | "monitoring" | "files" | "tools" | "skills" | "loops";

export const HARNESS_RULES_SECTIONS: {
  id: HarnessRulesSection;
  label: string;
  icon: LucideIcon;
}[] = [
  { id: "overview", label: "Overview", icon: Sparkles },
  { id: "monitoring", label: "Monitoring", icon: Activity },
  { id: "files", label: "Rule files", icon: Layers },
  { id: "tools", label: "MCP tools", icon: Wrench },
  { id: "skills", label: "Skills & memory", icon: BookOpen },
  { id: "loops", label: "Operator loops", icon: Cpu },
];

const RULES_SECTION_IDS: HarnessRulesSection[] = HARNESS_RULES_SECTIONS.map((row) => row.id);

const RULES_HASH_PREFIX = "rules";

/** Canonical hash for a Rules & skills sub-section. */
export function harnessRulesSectionHref(section: HarnessRulesSection): string {
  if (section === "overview") {
    return `/settings/harness#${RULES_HASH_PREFIX}`;
  }
  return `/settings/harness#${RULES_HASH_PREFIX}-${section}`;
}

/** Parse `#rules`, `#rules-monitoring`, etc. */
export function harnessRulesSectionFromHash(hash: string): HarnessRulesSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === RULES_HASH_PREFIX) {
    return "overview";
  }
  if (key.startsWith(`${RULES_HASH_PREFIX}-`)) {
    const sub = key.slice(RULES_HASH_PREFIX.length + 1) as HarnessRulesSection;
    return HARNESS_RULES_SECTIONS.some((row) => row.id === sub) ? sub : null;
  }
  return null;
}

/** Prefer hash section; Rules tab without hash → first in saved menu order. */
export function resolveHarnessRulesSection(params: {
  hash?: string;
  fallback?: HarnessRulesSection;
}): HarnessRulesSection {
  const legacy = params.fallback ?? RULES_SECTION_IDS[0] ?? "overview";
  const fromHash = harnessRulesSectionFromHash(params.hash ?? "");
  return resolvePrimarySubnavFromUrl({
    menuKey: SUBNAV_MENU_KEYS.settingsHarnessRules,
    visibleIds: RULES_SECTION_IDS,
    fromUrl: fromHash && RULES_SECTION_IDS.includes(fromHash) ? fromHash : null,
    legacyDefaultId: legacy,
  });
}
