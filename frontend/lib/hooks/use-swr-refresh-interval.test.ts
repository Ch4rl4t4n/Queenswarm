import { describe, expect, it } from "vitest";

import { swrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";

describe("swrVisiblePollOptions", () => {
  it("returns dedupe and throttle derived from refresh interval", () => {
    const opts = swrVisiblePollOptions(10_000);
    expect(opts.refreshInterval).toBe(10_000);
    expect(opts.revalidateOnFocus).toBe(true);
    expect(opts.dedupingInterval).toBe(4_000);
    expect(opts.focusThrottleInterval).toBe(10_000);
  });

  it("caps dedupe at 4s for fast polls", () => {
    const opts = swrVisiblePollOptions(5_000);
    expect(opts.dedupingInterval).toBe(3_000);
    expect(opts.focusThrottleInterval).toBe(5_000);
  });
});
