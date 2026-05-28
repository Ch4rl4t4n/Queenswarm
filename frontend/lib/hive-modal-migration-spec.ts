/**
 * Whole-App UI Reorder Phase 11.4 + 12 — HiveModalShell migration registry (SSOT).
 */

export const HIVE_MODAL_MIGRATION_VERSION = "2026.05-v3.12.4";

export interface HiveModalMigrationEntry {
  id: string;
  component: string;
  scope: "GLOBAL UI" | "LOCAL PANEL";
  /** true when wrapped in HiveModalShell */
  migrated: boolean;
  notes?: string;
}

/** Popover/flyout surfaces — see `hive-popover-spec.ts` (Phase 12.3). */

/** Hive modals — migrated in Phase 7.3 through 12.4. */
export const HIVE_MODAL_MIGRATED: readonly HiveModalMigrationEntry[] = [
  { id: "colony-console", component: "colony-console.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "swarm-manager", component: "swarm-manager-console.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "security-2fa", component: "security-2fa-settings.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "api-keys-mint", component: "settings-api-keys-panel.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "confirm-modal", component: "ConfirmModal.tsx", scope: "GLOBAL UI", migrated: true },
  { id: "swarms-new-colony", component: "swarms-new-colony-dialog.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "forager-form", component: "forager-form-dialog.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "hive-mind-deliverable", component: "hive-mind-deliverable-modal.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "publish-pack-detail", component: "publish-pack-detail-modal.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "agent-session-playbook", component: "agent-session-playbook-dialog.tsx", scope: "LOCAL PANEL", migrated: true },
  { id: "agents-template-editor", component: "agents/new/page.tsx", scope: "LOCAL PANEL", migrated: true },
  {
    id: "agent-session-report",
    component: "agent-session-report-dialog.tsx",
    scope: "LOCAL PANEL",
    migrated: true,
    notes: "align=bottom-sheet",
  },
  {
    id: "dream-report-info",
    component: "dream-report-info-dialog.tsx",
    scope: "LOCAL PANEL",
    migrated: true,
    notes: "align=bottom-sheet",
  },
  {
    id: "apps-tools-module",
    component: "apps-tools-index-client.tsx",
    scope: "LOCAL PANEL",
    migrated: true,
    notes: "align=bottom-sheet",
  },
  { id: "ballroom-filters", component: "ballroom/filters.tsx", scope: "LOCAL PANEL", migrated: true },
  {
    id: "admin-accounts",
    component: "admin-accounts-settings-panel.tsx",
    scope: "LOCAL PANEL",
    migrated: true,
    notes: "center + drawer-right audit",
  },
] as const;

/** Intentionally not HiveModalShell — see `hive-popover-spec.ts` banner exempt. */
export const HIVE_MODAL_BACKLOG: readonly HiveModalMigrationEntry[] = [] as const;

export function hiveModalMigrationCompleteForPhase114(): boolean {
  const critical = ["confirm-modal", "swarms-new-colony", "forager-form"] as const;
  return critical.every((id) => HIVE_MODAL_MIGRATED.some((entry) => entry.id === id && entry.migrated));
}

export function hiveModalMigrationCompleteForPhase121(): boolean {
  const critical = [
    "hive-mind-deliverable",
    "publish-pack-detail",
    "agent-session-playbook",
    "agents-template-editor",
  ] as const;
  return critical.every((id) => HIVE_MODAL_MIGRATED.some((entry) => entry.id === id && entry.migrated));
}

export function hiveModalMigrationCompleteForPhase122(): boolean {
  const critical = ["agent-session-report", "dream-report-info", "apps-tools-module"] as const;
  return critical.every((id) => HIVE_MODAL_MIGRATED.some((entry) => entry.id === id && entry.migrated));
}

export function hiveModalMigrationCompleteForPhase124(): boolean {
  const critical = ["ballroom-filters", "admin-accounts"] as const;
  const modalsDone = critical.every((id) => HIVE_MODAL_MIGRATED.some((entry) => entry.id === id && entry.migrated));
  return modalsDone && HIVE_MODAL_BACKLOG.length === 0;
}

export function hiveModalMigrationComplete(): boolean {
  return (
    hiveModalMigrationCompleteForPhase114() &&
    hiveModalMigrationCompleteForPhase121() &&
    hiveModalMigrationCompleteForPhase122() &&
    hiveModalMigrationCompleteForPhase124()
  );
}
