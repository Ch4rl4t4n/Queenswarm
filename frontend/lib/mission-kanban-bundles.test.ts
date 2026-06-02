import { describe, expect, it } from "vitest";

import { MISSION_KANBAN_BUNDLES } from "@/lib/mission-kanban-bundles";

describe("MISSION_KANBAN_BUNDLES", () => {
  it("defines at least three one-click packs", () => {
    expect(MISSION_KANBAN_BUNDLES.length).toBeGreaterThanOrEqual(3);
  });

  it("each bundle has task text long enough for triage API", () => {
    for (const bundle of MISSION_KANBAN_BUNDLES) {
      expect(bundle.taskText.trim().length).toBeGreaterThanOrEqual(8);
      expect(bundle.id.length).toBeGreaterThan(0);
    }
  });
});
