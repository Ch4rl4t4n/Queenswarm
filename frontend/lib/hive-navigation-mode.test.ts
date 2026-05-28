import { describe, expect, it } from "vitest";

import { hubFallbackTarget } from "./hive-navigation-mode";

describe("hive-navigation-mode", () => {
  it("maps hub fallback targets", () => {
    expect(hubFallbackTarget("overview")).toBe("/");
    expect(hubFallbackTarget("execution")).toBe("/tasks");
    expect(hubFallbackTarget("knowledge")).toBe("/hive-mind");
    expect(hubFallbackTarget("integrations")).toBe("/connectors");
  });
});
