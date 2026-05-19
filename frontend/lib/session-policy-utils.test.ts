import { describe, expect, it } from "vitest";

import {
  formatAccessTtl,
  formatOAuthStateTtl,
  formatRateLimit,
  formatRefreshTtl,
  nearestSelectValue,
} from "@/lib/session-policy-utils";

describe("session policy utils", () => {
  it("formatAccessTtl pluralizes minutes", () => {
    expect(formatAccessTtl(15)).toBe("15 minutes");
    expect(formatAccessTtl(1)).toBe("1 minute");
  });

  it("formatRefreshTtl pluralizes days", () => {
    expect(formatRefreshTtl(30)).toBe("30 days");
    expect(formatRefreshTtl(1)).toBe("1 day");
  });

  it("formatRateLimit normalizes minute windows", () => {
    expect(formatRateLimit({ rate_limit_requests: 100, rate_limit_window_sec: 60 })).toBe(
      "100 req/min sliding window",
    );
  });

  it("formatOAuthStateTtl converts seconds to minutes", () => {
    expect(formatOAuthStateTtl(300)).toBe("Redis state TTL 5 min");
  });

  it("nearestSelectValue picks closest option", () => {
    expect(nearestSelectValue(14, [5, 15, 60])).toBe(15);
    expect(nearestSelectValue(8, [7, 30, 90])).toBe(7);
  });
});
