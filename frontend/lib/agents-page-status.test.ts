import { describe, expect, it } from "vitest";

import { formatAgentsFetchError } from "@/lib/agents-page-status";

describe("formatAgentsFetchError", () => {
  it("returns null for empty input", () => {
    expect(formatAgentsFetchError(null)).toBeNull();
  });

  it("maps Error instances to message", () => {
    expect(formatAgentsFetchError(new Error("proxy_upstream_unreachable"))).toBe(
      "proxy_upstream_unreachable",
    );
  });
});
