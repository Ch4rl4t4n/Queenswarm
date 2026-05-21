import { describe, expect, it } from "vitest";

import { shouldVirtualizeAgentList } from "@/lib/agents-list-presenters";

describe("shouldVirtualizeAgentList", () => {
  it("returns false on dashboard when virtualizeList is off", () => {
    expect(shouldVirtualizeAgentList(200, false)).toBe(false);
  });

  it("returns true on agents page when roster is non-empty", () => {
    expect(shouldVirtualizeAgentList(120, true)).toBe(true);
  });

  it("returns false when roster is empty", () => {
    expect(shouldVirtualizeAgentList(0, true)).toBe(false);
  });
});
