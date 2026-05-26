import { describe, expect, it, vi, afterEach } from "vitest";

import { formatTestedAgo } from "@/lib/format-tested-ago";

describe("formatTestedAgo", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns just now for recent timestamps", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-20T12:00:00Z"));
    expect(formatTestedAgo("2026-05-20T11:59:30Z")).toBe("just now");
  });

  it("returns hours ago for older timestamps", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-20T14:00:00Z"));
    expect(formatTestedAgo("2026-05-20T12:00:00Z")).toBe("2h ago");
  });
});
