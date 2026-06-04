/**
 * Whole-App UI Reorder Phase 9 — critical operator journeys (E2E matrix).
 * Keep in sync with `hive-ia-canonical.ts` and `hive-page-zone-spec.ts`.
 */

import { CANONICAL_PRIMARY_CP, CANONICAL_MORE_ONLY_HREFS } from "@/lib/hive-ia-canonical";
import { HIVE_PAGE_ZONE_SPECS } from "@/lib/hive-page-zone-spec";
import { VERIFIED_PRIMARY_ROUTES } from "@/lib/dead-button-audit";

export const HIVE_CRITICAL_JOURNEYS_VERSION = "2026.05-v1";

export type HiveCriticalJourneyViewport = "desktop" | "mobile";

export interface HiveCriticalJourneySpec {
  id: string;
  title: string;
  description: string;
  viewport: HiveCriticalJourneyViewport;
  /** Journey requires operator control plane (Agentic OS primary rail). */
  requiresCp?: boolean;
}

/** End-to-end journeys that must never regress after IA reorder. */
export const HIVE_CRITICAL_JOURNEY_SPECS: HiveCriticalJourneySpec[] = [
  {
    id: "operator-bootstrap",
    title: "Operator bootstrap",
    description: "Authenticated session lands on home shell without duplicate desktop search chrome.",
    viewport: "desktop",
    requiresCp: true,
  },
  {
    id: "agentic-os-sidebar-loop",
    title: "Agentic OS sidebar loop",
    description: "Primary rail navigates Swarms → Tasks → Routines → Agents with unified HivePageShell titles.",
    viewport: "desktop",
    requiresCp: true,
  },
  {
    id: "agentic-os-subnav-command",
    title: "Agentic OS subnav command lane",
    description: "In-page subnav switches overview sections without losing shell context.",
    viewport: "desktop",
    requiresCp: true,
  },
  {
    id: "apps-tools-discovery",
    title: "Apps & Tools discovery",
    description: "Module index deep-links to Skill Factory workspace.",
    viewport: "desktop",
  },
  {
    id: "integrations-tab-switch",
    title: "Integrations tab switch",
    description: "Integrations subnav switches to Skills export tab.",
    viewport: "desktop",
  },
  {
    id: "knowledge-subnav",
    title: "Knowledge subnav",
    description: "Knowledge shell subnav switches to Recipes section.",
    viewport: "desktop",
  },
  {
    id: "settings-progressive",
    title: "Settings progressive disclosure",
    description: "Essentials → expand advanced → API keys panel.",
    viewport: "desktop",
  },
  {
    id: "execution-new-task",
    title: "Execution new task",
    description: "Tasks queue CTA opens new task wizard.",
    viewport: "desktop",
  },
  {
    id: "desktop-sidebar-foragers",
    title: "Desktop sidebar → Foragers",
    description: "Primary rail includes Foragers for social intel data collectors.",
    viewport: "desktop",
    requiresCp: true,
  },
  {
    id: "legacy-cockpit-redirect",
    title: "Legacy cockpit redirect",
    description: "Bookmarked /cockpit preserves hash on Agentic OS.",
    viewport: "desktop",
    requiresCp: true,
  },
];

export function hiveCriticalJourneyCount(): number {
  return HIVE_CRITICAL_JOURNEY_SPECS.length;
}

/** IA coverage — every canonical primary href should appear in at least one journey path. */
export function criticalJourneyPrimaryRouteCoverage(): readonly string[] {
  const fromJourneys = new Set<string>([
    ...HIVE_PAGE_ZONE_SPECS.map((spec) => spec.path),
    "/tasks/new",
    "/settings/api-keys",
    "/apps-tools/marketing-automation",
    "/foragers",
    "/routines",
    "/cockpit",
  ]);
  return VERIFIED_PRIMARY_ROUTES.filter((href) => fromJourneys.has(href));
}

/** More-menu-only routes exercised by mobile overflow journey. */
export function criticalJourneyMoreMenuCoverage(): readonly string[] {
  return CANONICAL_MORE_ONLY_HREFS.filter((href) => href === "/factory");
}

export function canonicalAgenticOsLabels(): readonly string[] {
  return CANONICAL_PRIMARY_CP.filter((row) => row.iaZone === "agentic_os").map((row) => row.label);
}
