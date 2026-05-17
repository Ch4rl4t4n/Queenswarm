import { describe, expect, it } from "vitest";

import { hubFallbackTarget, keyboardLegendText, shortcutTargets } from "./hive-navigation-mode";

describe("hive-navigation-mode", () => {
  it("maps desktop shortcut targets for consolidated mode", () => {
    const targets = shortcutTargets(true);
    expect(targets.home).toBe("/dashboard");
    expect(targets.tasks).toBe("/tasks");
    expect(targets.knowledge).toBe("/knowledge");
    expect(targets.integrations).toBe("/integrations");
  });

  it("maps desktop shortcut targets for legacy mode", () => {
    const targets = shortcutTargets(false);
    expect(targets.home).toBe("/");
    expect(targets.tasks).toBe("/tasks");
    expect(targets.knowledge).toBe("/hive-mind");
    expect(targets.integrations).toBe("/connectors");
  });

  it("renders mode-specific keyboard legend text", () => {
    expect(keyboardLegendText(true)).toContain("dashboard");
    expect(keyboardLegendText(true)).toContain("tasks");
    expect(keyboardLegendText(false)).toContain("dashboard");
    expect(keyboardLegendText(false)).toContain("tasks");
  });

  it("maps hub sections to legacy fallback routes", () => {
    expect(hubFallbackTarget("overview")).toBe("/");
    expect(hubFallbackTarget("execution")).toBe("/tasks");
    expect(hubFallbackTarget("knowledge")).toBe("/hive-mind");
    expect(hubFallbackTarget("integrations")).toBe("/connectors");
  });
});
