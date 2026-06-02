import { describe, expect, it } from "vitest";

import { AUTOMATION_LADDER_LEVELS, AUTOMATION_HYBRID_RULE } from "@/lib/automation-ladder";

describe("automation-ladder", () => {
  it("defines five levels L1–L5", () => {
    expect(AUTOMATION_LADDER_LEVELS).toHaveLength(5);
    expect(AUTOMATION_LADDER_LEVELS.map((row) => row.level)).toEqual([1, 2, 3, 4, 5]);
  });

  it("includes webhook and goal levels", () => {
    const ids = AUTOMATION_LADDER_LEVELS.map((row) => row.id);
    expect(ids).toContain("webhook");
    expect(ids).toContain("goal-mode");
  });

  it("hybrid rule mentions n8n", () => {
    expect(AUTOMATION_HYBRID_RULE.toLowerCase()).toContain("n8n");
  });
});
