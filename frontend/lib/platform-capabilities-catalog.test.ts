import { describe, expect, it } from "vitest";

import {
  PLANNED_PLATFORM_CAPABILITIES,
  groupPlannedByRolloutPhase,
} from "@/lib/platform-capabilities-catalog";

describe("platform-capabilities-catalog", () => {
  it("groups planned items by rollout phase with phase0 first", () => {
    const grouped = groupPlannedByRolloutPhase(PLANNED_PLATFORM_CAPABILITIES);
    expect(grouped.length).toBeGreaterThan(0);
    expect(grouped[0]?.phase).toBe("phase0");
    expect(grouped.some((g) => g.items.some((i) => i.id === "stripe-live"))).toBe(true);
    expect(grouped.some((g) => g.items.some((i) => i.id === "stripe-live"))).toBe(true);
  });

  it("phase0 week1 items include stripe and pro tier gates", () => {
    const phase0 = groupPlannedByRolloutPhase(PLANNED_PLATFORM_CAPABILITIES).find((g) => g.phase === "phase0");
    expect(phase0).toBeDefined();
    const week1 = phase0?.items.filter((i) => i.week === 1) ?? [];
    expect(week1.map((i) => i.id)).toContain("stripe-live");
  });

  it("every planned item has rolloutPhase", () => {
    for (const item of PLANNED_PLATFORM_CAPABILITIES) {
      expect(item.rolloutPhase).toBeTruthy();
    }
  });
});
