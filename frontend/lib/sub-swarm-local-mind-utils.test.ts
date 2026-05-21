import { describe, expect, it } from "vitest";

import { formatSyncDue, memberCapacityTone, syncTone } from "@/lib/sub-swarm-local-mind-utils";

describe("sub-swarm-local-mind-utils", () => {
  it("formats sync countdown", () => {
    expect(formatSyncDue(0)).toBe("due now");
    expect(formatSyncDue(90)).toBe("1m 30s");
  });

  it("returns warn tone when sync overdue", () => {
    expect(syncTone(true)).toBe("warn");
    expect(syncTone(false)).toBe("ok");
  });

  it("flags empty colonies", () => {
    expect(memberCapacityTone(0, 8)).toBe("warn");
    expect(memberCapacityTone(5, 8)).toBe("ok");
  });
});
