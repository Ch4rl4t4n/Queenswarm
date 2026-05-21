import { describe, expect, it } from "vitest";

import { swrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";

describe("swrVisiblePollOptions", () => {
  it("returns dedupe and throttle derived from refresh interval", () => {
    const opts = swrVisiblePollOptions(10_000);
    expect(opts.refreshInterval).toBe(10_000);
    expect(opts.revalidateOnFocus).toBe(false);
    expect(opts.dedupingInterval).toBe(6_000);
    expect(opts.focusThrottleInterval).toBe(20_000);
  });

  it("caps dedupe at 6s and floors focus throttle at 15s for fast polls", () => {
    const opts = swrVisiblePollOptions(5_000);
    expect(opts.dedupingInterval).toBe(3_750);
    expect(opts.focusThrottleInterval).toBe(15_000);
  });
});
