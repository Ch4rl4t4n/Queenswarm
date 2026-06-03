import { describe, expect, it } from "vitest";

import {
  SKILL_FACTORY_GAPS,
  SKILL_FACTORY_PREREQUISITES,
  SKILL_FACTORY_STEPS,
} from "@/lib/skill-factory-manual";

describe("skill-factory-manual", () => {
  it("defines prerequisites and pipeline steps", () => {
    expect(SKILL_FACTORY_PREREQUISITES.length).toBeGreaterThanOrEqual(4);
    expect(SKILL_FACTORY_STEPS.length).toBeGreaterThanOrEqual(8);
    expect(SKILL_FACTORY_GAPS.some((row) => row.status === "operator")).toBe(true);
  });

  it("each step has hint and actions", () => {
    for (const step of SKILL_FACTORY_STEPS) {
      expect(step.hint.length).toBeGreaterThan(10);
      expect(step.actions.length).toBeGreaterThanOrEqual(2);
    }
  });
});
