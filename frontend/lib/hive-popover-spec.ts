/**
 * Whole-App UI Reorder Phase 12.3 — popover / flyout surface registry (SSOT).
 */

export const HIVE_POPOVER_SPEC_VERSION = "2026.05-v3.12.4";

export type HiveSurfaceKind = "modal" | "popover-anchor" | "popover-flyout" | "drawer" | "sheet" | "banner";

export interface HiveSurfaceEntry {
  id: string;
  component: string;
  kind: HiveSurfaceKind;
  shell: "HiveModalShell" | "HivePopoverShell" | "useModalA11y" | "bespoke";
  scope: "GLOBAL UI" | "LOCAL PANEL";
}

/** Surfaces standardized on HivePopoverShell (Phase 12.3). */
export const HIVE_POPOVER_MIGRATED: readonly HiveSurfaceEntry[] = [
  {
    id: "info-hint",
    component: "info-hint.tsx",
    kind: "popover-anchor",
    shell: "HivePopoverShell",
    scope: "GLOBAL UI",
  },
  {
    id: "dashboard-settings",
    component: "dashboard-settings-panel.tsx",
    kind: "popover-flyout",
    shell: "HivePopoverShell",
    scope: "LOCAL PANEL",
  },
] as const;

/** Intentionally bespoke — not anchor/flyout popovers or centered modals. */
export const HIVE_SURFACE_EXEMPT: readonly HiveSurfaceEntry[] = [
  {
    id: "hive-install-prompt",
    component: "hive-install-prompt.tsx",
    kind: "banner",
    shell: "useModalA11y",
    scope: "GLOBAL UI",
  },
  { id: "hive-more-sheet", component: "hive-more-sheet.tsx", kind: "sheet", shell: "bespoke", scope: "GLOBAL UI" },
  { id: "hive-sidebar-mobile", component: "hive-sidebar.tsx", kind: "drawer", shell: "bespoke", scope: "GLOBAL UI" },
  { id: "task-result-drawer", component: "task-result-drawer.tsx", kind: "drawer", shell: "bespoke", scope: "LOCAL PANEL" },
] as const;

export function hivePopoverMigrationCompleteForPhase123(): boolean {
  return HIVE_POPOVER_MIGRATED.every((entry) => entry.shell === "HivePopoverShell");
}
