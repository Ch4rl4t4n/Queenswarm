import { describe, expect, it } from "vitest";

import {
  HIVE_MODAL_MIGRATED,
  HIVE_MODAL_MIGRATION_VERSION,
  hiveModalMigrationCompleteForPhase114,
  hiveModalMigrationCompleteForPhase121,
  hiveModalMigrationCompleteForPhase122,
  hiveModalMigrationCompleteForPhase124,
  hiveModalMigrationComplete,
} from "@/lib/hive-modal-migration-spec";

describe("hive-modal-migration-spec", () => {
  it("exports version", () => {
    expect(HIVE_MODAL_MIGRATION_VERSION).toMatch(/^2026\./);
  });

  it("marks Phase 11.4 critical modals as migrated", () => {
    expect(hiveModalMigrationCompleteForPhase114()).toBe(true);
  });

  it("marks Phase 12.1 secondary modals as migrated", () => {
    expect(hiveModalMigrationCompleteForPhase121()).toBe(true);
  });

  it("marks Phase 12.2 bottom-sheet modals as migrated", () => {
    expect(hiveModalMigrationCompleteForPhase122()).toBe(true);
  });

  it("marks Phase 12.4 final modal backlog as migrated", () => {
    expect(hiveModalMigrationCompleteForPhase124()).toBe(true);
    expect(hiveModalMigrationComplete()).toBe(true);
  });

  it("lists unique migrated component paths", () => {
    const paths = HIVE_MODAL_MIGRATED.map((entry) => entry.component);
    expect(new Set(paths).size).toBe(paths.length);
    expect(HIVE_MODAL_MIGRATED.every((entry) => entry.migrated)).toBe(true);
  });
});
