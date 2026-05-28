/**
 * Whole-App UI Reorder — Settings panel density tiers (Phase 3.2).
 * Essentials stay expanded; advanced blocks collapse behind disclosure toggles.
 */

export type SettingsPanelDensityTier = "essential" | "advanced";

export interface SettingsDensitySectionSpec {
  id: string;
  tier: SettingsPanelDensityTier;
  /** Deep-link hash — auto-expands matching CollapsibleLazyPanel. */
  hashKey?: string;
}

/** Capabilities atlas — live catalog first; mission/architecture/roadmap collapsed. */
export const CAPABILITIES_DENSITY_SECTIONS: readonly SettingsDensitySectionSpec[] = [
  { id: "capabilities-atlas-header", tier: "essential" },
  { id: "capabilities-live", tier: "essential" },
  { id: "capabilities-mission", tier: "advanced", hashKey: "capabilities-mission" },
  { id: "capabilities-architecture", tier: "advanced", hashKey: "capabilities-architecture" },
  { id: "capabilities-roadmap", tier: "advanced", hashKey: "capabilities-roadmap" },
];

export interface HarnessLoopsPanelSpec {
  id: string;
  tier: SettingsPanelDensityTier;
  title: string;
  hint: string;
  hashKey?: string;
  /** Open on first visit to Operator loops (only one essential panel). */
  defaultOpen?: boolean;
}

/** Harness → Rules → Operator loops — solo trio essential; power panels collapsed. */
export const HARNESS_LOOPS_PANEL_SPECS: readonly HarnessLoopsPanelSpec[] = [
  {
    id: "harness-loops-trio",
    tier: "essential",
    title: "My 3 Bees trio",
    hint: "Morning cycle · bind lanes",
    defaultOpen: true,
  },
  {
    id: "harness-loops-slack",
    tier: "advanced",
    title: "Slack harness trainer",
    hint: "Teach Queen via feedback",
    hashKey: "harness-loops-slack",
  },
  {
    id: "harness-loops-lsp",
    tier: "advanced",
    title: "LSP MCP bridge",
    hint: "IDE context for supervisor",
    hashKey: "harness-loops-lsp",
  },
  {
    id: "harness-loops-rubric",
    tier: "advanced",
    title: "Rubric templates",
    hint: "Evaluation presets",
    hashKey: "harness-loops-rubric",
  },
  {
    id: "harness-loops-maintainer",
    tier: "advanced",
    title: "Queen Maintainer webhook",
    hint: "PR-only self-maintenance",
    hashKey: "harness-loops-maintainer",
  },
  {
    id: "harness-loops-patterns",
    tier: "advanced",
    title: "Recent agentic patterns",
    hint: "Pattern Router selections",
    hashKey: "harness-loops-patterns",
  },
  {
    id: "harness-loops-forager",
    tier: "advanced",
    title: "Forager intelligence loop",
    hint: "Skill/MCP freshness scan",
    hashKey: "harness-loops-forager",
  },
];

export function settingsDensityEssentialSectionIds(
  sections: readonly SettingsDensitySectionSpec[],
): string[] {
  return sections.filter((row) => row.tier === "essential").map((row) => row.id);
}

export function settingsDensityAdvancedSectionIds(
  sections: readonly SettingsDensitySectionSpec[],
): string[] {
  return sections.filter((row) => row.tier === "advanced").map((row) => row.id);
}

export function harnessLoopsPanelSpec(id: string): HarnessLoopsPanelSpec | undefined {
  return HARNESS_LOOPS_PANEL_SPECS.find((row) => row.id === id);
}
