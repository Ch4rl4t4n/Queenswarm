/**
 * Whole-App UI Reorder Phase 10 — release gate matrix (SSOT for CI + operator scripts).
 */

import { WHOLE_APP_IA_VERSION } from "@/lib/hive-ia-canonical";
import { HIVE_CRITICAL_JOURNEYS_VERSION } from "@/lib/hive-critical-journeys-spec";
import { HIVE_PAGE_SHELL_VERSION } from "@/lib/hive-page-zone-spec";

export const HIVE_RELEASE_GATE_VERSION = "2026.05-v5";

/** Annotated git tag for Whole-App UI Reorder shippable release (Phase 13.3). */
export const WHOLE_APP_UI_RELEASE_TAG = "v2026.05-whole-app-ui";

/** CI job identifiers — keep in sync with `.github/workflows/ci.yml`. */
export const WHOLE_APP_CI_JOBS = {
  coreGate: "whole_app_ui_gate",
  extendedGate: "whole_app_ui_extended",
  prodJourneys: "whole_app_prod_journeys",
} as const;

/** Playwright specs that must pass before Whole-App UI Reorder is considered shippable. */
export const WHOLE_APP_E2E_SPECS: readonly string[] = [
  "whole-app-ia.spec.ts",
  "whole-app-page-shell.spec.ts",
  "whole-app-settings-disclosure.spec.ts",
  "whole-app-settings-density.spec.ts",
  "whole-app-dead-buttons.spec.ts",
  "whole-app-cross-route-naming.spec.ts",
  "whole-app-mobile-tablet.spec.ts",
  "whole-app-a11y.spec.ts",
  "whole-app-performance.spec.ts",
  "whole-app-critical-journeys.spec.ts",
  "whole-app-release-gate.spec.ts",
] as const;

/** Vitest files covering IA, shell, settings, mobile, a11y, performance contracts. */
export const WHOLE_APP_UNIT_TEST_FILES: readonly string[] = [
  "lib/hive-ia-canonical.test.ts",
  "lib/hive-page-zone-spec.test.ts",
  "lib/hive-critical-journeys-spec.test.ts",
  "lib/hive-release-gate-spec.test.ts",
  "lib/hive-page-error.test.ts",
  "lib/hive-page-performance-spec.test.ts",
  "lib/hive-a11y.test.ts",
  "lib/hive-mobile-meta.test.ts",
  "lib/mobile-tablet-zone-spec.test.ts",
  "lib/mobile-tablet-chrome.test.ts",
  "lib/dead-button-audit.test.ts",
  "lib/execution-lane-routes.test.ts",
  "lib/factory-content-factory-routes.test.ts",
  "lib/settings-nav.test.ts",
  "lib/settings-nav-tiers.test.ts",
  "lib/hive-prod-journey-spec.test.ts",
  "lib/hive-modal-migration-spec.test.ts",
  "lib/hive-modal-shell.test.ts",
  "lib/hive-popover-position.test.ts",
  "lib/hive-popover-spec.test.ts",
  "lib/billing-settings-copy.test.ts",
] as const;

/** Production-authenticated E2E (requires OPERATOR_USER_BEARER_TOKEN). */
export const WHOLE_APP_PROD_E2E_SPECS: readonly string[] = [
  "whole-app-prod-journeys.spec.ts",
  "prod-authenticated-walkthrough.spec.ts",
] as const;

/** Optional extended gate — full responsive shell regression (slower). */
export const WHOLE_APP_EXTENDED_E2E_SPECS: readonly string[] = [
  "responsive-shell.spec.ts",
  "responsive-visual.spec.ts",
] as const;

/** Harness self-improvement smoke (Four Cs + Innovation viability) — set E2E_HARNESS_SELF_IMPROVE=1. */
export const HARNESS_SELF_IMPROVE_E2E_SPECS: readonly string[] = [
  "harness-self-improve-smoke.spec.ts",
] as const;

export const HARNESS_SELF_IMPROVE_E2E_ENV = "E2E_HARNESS_SELF_IMPROVE" as const;

export interface HiveReleaseGateInvariant {
  id: string;
  description: string;
}

/** Structural invariants enforced by `whole-app-release-gate.spec.ts`. */
export const HIVE_RELEASE_GATE_INVARIANTS: HiveReleaseGateInvariant[] = [
  {
    id: "desktop-no-duplicate-search",
    description: "Desktop zone routes must not mount #hive-search (sidebar + canvas only).",
  },
  {
    id: "zone-shell-present",
    description: "Every canonical zone index route renders HivePageShell with matching h1.",
  },
  {
    id: "desktop-sidebar-mobile-hidden",
    description: "Desktop shows sidebar rail; mobile header and bottom nav stay hidden at ≥1024px.",
  },
  {
    id: "no-cockpit-primary-label",
    description: "Primary shell headings must not regress to legacy “Cockpit” naming.",
  },
  {
    id: "ia-version-aligned",
    description: "IA, page shell, journeys, and release gate versions are present and aligned.",
  },
  {
    id: "modal-migration-complete",
    description: "All centered/bottom-sheet modals use HiveModalShell; modal backlog is empty.",
  },
  {
    id: "popover-migration-complete",
    description: "Anchor/flyout popovers use HivePopoverShell; surface exempt list documented.",
  },
];

export interface HiveReleaseGateVersionBundle {
  ia: string;
  pageShell: string;
  journeys: string;
  releaseGate: string;
}

export function hiveReleaseGateVersionBundle(): HiveReleaseGateVersionBundle {
  return {
    ia: WHOLE_APP_IA_VERSION,
    pageShell: HIVE_PAGE_SHELL_VERSION,
    journeys: HIVE_CRITICAL_JOURNEYS_VERSION,
    releaseGate: HIVE_RELEASE_GATE_VERSION,
  };
}

export function wholeAppE2eSpecCount(): number {
  return WHOLE_APP_E2E_SPECS.length;
}

export function wholeAppUnitTestFileCount(): number {
  return WHOLE_APP_UNIT_TEST_FILES.length;
}

export function wholeAppExtendedE2eSpecCount(): number {
  return WHOLE_APP_EXTENDED_E2E_SPECS.length;
}

export function harnessSelfImproveE2eSpecCount(): number {
  return HARNESS_SELF_IMPROVE_E2E_SPECS.length;
}
