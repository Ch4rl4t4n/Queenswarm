import { describe, expect, it } from "vitest";

import { hivePopoverMigrationCompleteForPhase123, HIVE_POPOVER_SPEC_VERSION } from "@/lib/hive-popover-spec";

describe("hive-popover-spec", () => {
  it("exports version", () => {
    expect(HIVE_POPOVER_SPEC_VERSION).toMatch(/^2026\./);
  });

  it("marks Phase 12.3 popover surfaces as migrated", () => {
    expect(hivePopoverMigrationCompleteForPhase123()).toBe(true);
  });
});
