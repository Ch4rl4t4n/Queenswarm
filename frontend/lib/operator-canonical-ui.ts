/**
 * Canonical operator UI — keep / wire / remove decisions.
 * Aligned with manual §0–4 and docs/OPERATOR_CANONICAL_WORKFLOW.md.
 */

import type { CockpitSection } from "@/lib/cockpit-routes";

/** Agentic OS sections hidden in solo mode — none; full subnav always visible. */
export const SOLO_COCKPIT_HIDDEN_SECTIONS: readonly CockpitSection[] = [];

/** Solo-only tabs — hidden outside solo (team mode keeps Operator overview only). */
export const SOLO_COCKPIT_ONLY_SECTIONS: readonly CockpitSection[] = ["business"];

/** Solo primary row — business brief, operator overview, innovation. */
export const SOLO_COCKPIT_PRIMARY_SECTIONS: readonly CockpitSection[] = [
  "business",
  "overview",
  "innovation",
];

/** Solo secondary row — always visible (no accordion). */
export const SOLO_COCKPIT_ADVANCED_SECTIONS: readonly CockpitSection[] = [
  "command",
  "grok",
  "icm",
  "modules",
  "fleet",
  "lanes",
];

/** Solo tab sort order — optional cron digests last. */
export const SOLO_COCKPIT_SECTION_ORDER: readonly CockpitSection[] = [
  "business",
  "overview",
  "innovation",
  "command",
  "grok",
  "icm",
  "modules",
  "fleet",
  "lanes",
];

export interface CockpitNavSplit {
  primary: CockpitSection[];
  advanced: CockpitSection[];
}

export function isCockpitAdvancedSection(section: CockpitSection, soloMode: boolean): boolean {
  return soloMode && (SOLO_COCKPIT_ADVANCED_SECTIONS as readonly string[]).includes(section);
}

export type OperatorUiDisposition = "keep" | "wire" | "remove" | "demote";

export interface OperatorUiControlAudit {
  id: string;
  area: string;
  label: string;
  disposition: OperatorUiDisposition;
  reason: string;
}

/** Registry for CI/docs — nav-only primaries we demoted or removed. */
export const OPERATOR_UI_CONTROL_AUDIT: readonly OperatorUiControlAudit[] = [
  {
    id: "agents-create-first-session",
    area: "Agents",
    label: "Create first session",
    disposition: "wire",
    reason: "Applies solo preset + focuses goal field (manual §2).",
  },
  {
    id: "agents-spawn-primary",
    area: "Agents",
    label: "Spawn agent",
    disposition: "demote",
    reason: "Solo primary path is supervisor sessions, not bee spawn.",
  },
  {
    id: "live-swarm-run-simulation",
    area: "Dashboard",
    label: "Run simulation",
    disposition: "remove",
    reason: "Unused toolbar; simulations optional via nav.",
  },
  {
    id: "recipes-run-mission",
    area: "Knowledge",
    label: "Run mission",
    disposition: "remove",
    reason: "No recipe→task wiring; catalog is browse/export only.",
  },
  {
    id: "vc-setup-card",
    area: "Integrations",
    label: "Virtual Company setup",
    disposition: "remove",
    reason: "Legacy VC bootstrap — hidden in solo (manual §4 ignore Swarm Fleet).",
  },
  {
    id: "cockpit-advanced-accordion",
    area: "Agentic OS",
    label: "Advanced tools accordion",
    disposition: "remove",
    reason: "Full two-row subnav always visible; progressive disclosure only in Settings.",
  },
  {
    id: "pattern-onboarding-cta",
    area: "Knowledge",
    label: "Start supervisor session",
    disposition: "demote",
    reason: "Links to /agents#sessions — not an instant run.",
  },
  {
    id: "first-run-setup-banner",
    area: "Agentic OS",
    label: "First-run setup banner",
    disposition: "wire",
    reason: "OW5 — compact nudge on Overview until LLM → brief → session complete.",
  },
  {
    id: "settings-operator-hub-open",
    area: "Settings",
    label: "Open in app",
    disposition: "demote",
    reason: "Navigation only — ghost link with arrow suffix.",
  },
  {
    id: "billing-preview-links",
    area: "Settings",
    label: "Cost cockpit / Enterprise preview",
    disposition: "demote",
    reason: "Checkout disabled — nav-only ghost links.",
  },
  {
    id: "research-search-keys-inline",
    area: "Settings",
    label: "Tavily / Serper inline keys",
    disposition: "wire",
    reason: "OW9 — vault-backed research keys wired to executor.",
  },
  {
    id: "pattern-nav-primary-demote",
    area: "Knowledge",
    label: "Open session / Tool Hub",
    disposition: "demote",
    reason: "Tier-2 — nav-only CTAs demoted to ghost.",
  },
  {
    id: "grok-panel-en-only",
    area: "Agentic OS",
    label: "Grok Control Plane copy",
    disposition: "wire",
    reason: "OW10 — Slovak UI strings translated to English.",
  },
  {
    id: "swarms-nav-primary-demote",
    area: "Swarms",
    label: "Swarm Builder / View roster",
    disposition: "demote",
    reason: "Tier-3 — nav-only primaries demoted; builder entry hidden in solo.",
  },
  {
    id: "en-cleanup-solo-panels",
    area: "Knowledge",
    label: "Dreaming / Factory / Capabilities EN copy",
    disposition: "wire",
    reason: "OW11 — hardcoded Slovak UI strings replaced with English.",
  },
];

/** Filter and order Agentic OS tabs for solo operator mode. */
export function visibleCockpitSections(
  soloMode: boolean,
  all: readonly CockpitSection[],
): CockpitSection[] {
  const hidden = soloMode ? SOLO_COCKPIT_HIDDEN_SECTIONS : SOLO_COCKPIT_ONLY_SECTIONS;
  const filtered = all.filter((id) => !hidden.includes(id));
  if (!soloMode) {
    return filtered;
  }
  return [...filtered].sort((a, b) => {
    const ia = SOLO_COCKPIT_SECTION_ORDER.indexOf(a);
    const ib = SOLO_COCKPIT_SECTION_ORDER.indexOf(b);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}

/** Split visible Agentic OS tabs into primary vs advanced (solo only). */
export function cockpitNavSections(
  soloMode: boolean,
  all: readonly CockpitSection[],
): CockpitNavSplit {
  const visible = visibleCockpitSections(soloMode, all);
  if (!soloMode) {
    return { primary: visible, advanced: [] };
  }
  return {
    primary: visible.filter((id) => (SOLO_COCKPIT_PRIMARY_SECTIONS as readonly string[]).includes(id)),
    advanced: visible.filter((id) => (SOLO_COCKPIT_ADVANCED_SECTIONS as readonly string[]).includes(id)),
  };
}

/** Scroll to the session goal composer on Agents. */
export function focusSessionGoalComposer(): void {
  document.getElementById("sessions")?.scrollIntoView({ behavior: "smooth", block: "start" });
  requestAnimationFrame(() => {
    document
      .querySelector<HTMLInputElement>('input[placeholder*="Session goal"]')
      ?.focus();
  });
}
