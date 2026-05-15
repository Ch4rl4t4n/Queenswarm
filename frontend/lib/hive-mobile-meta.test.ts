import { describe, expect, it } from "vitest";

import { hiveMobileRouteMeta } from "./hive-mobile-meta";

describe("hiveMobileRouteMeta", () => {
  it("returns dashboard meta for root", () => {
    const m = hiveMobileRouteMeta("/");
    expect(m.kicker).toBe("Overview");
    expect(m.staticSubtitle).toContain("roster");
  });

  it("returns overview hub meta under /overview", () => {
    const m = hiveMobileRouteMeta("/overview");
    expect(m.kicker).toBe("Overview");
    expect(m.pageTitleSuffix).toBe("Overview");
  });

  it("returns ballroom meta with pageTitleSuffix", () => {
    const m = hiveMobileRouteMeta("/ballroom");
    expect(m.kicker).toBe("Ballroom");
    expect(m.pageTitleSuffix).toBe("Ballroom");
  });

  it("returns hive-mind meta under /hive-mind", () => {
    const m = hiveMobileRouteMeta("/hive-mind");
    expect(m.kicker).toBe("HiveMind");
    expect(m.pageTitleSuffix).toBe("HiveMind");
  });

  it("returns outputs meta under /outputs", () => {
    const m = hiveMobileRouteMeta("/outputs");
    expect(m.kicker).toBe("Outputs");
    expect(m.pageTitleSuffix).toBe("Outputs");
  });

  it("returns connectors meta under /connectors", () => {
    const m = hiveMobileRouteMeta("/connectors");
    expect(m.kicker).toBe("Connectors");
    expect(m.pageTitleSuffix).toBe("Connectors");
    expect(m.staticSubtitle).toContain("vault");
  });

  it("returns external-projects meta under /external-projects", () => {
    const m = hiveMobileRouteMeta("/external-projects");
    expect(m.kicker).toBe("External");
    expect(m.pageTitleSuffix).toBe("External projects");
  });

  it("returns learning meta under /learning", () => {
    const m = hiveMobileRouteMeta("/learning");
    expect(m.kicker).toBe("Learning");
    expect(m.pageTitleSuffix).toBe("Learning");
  });

  it("returns jobs meta under /jobs", () => {
    const m = hiveMobileRouteMeta("/jobs");
    expect(m.kicker).toBe("Jobs");
    expect(m.staticSubtitle).toContain("Celery");
  });

  it("prefers longer prefix for /tasks/new", () => {
    const m = hiveMobileRouteMeta("/tasks/new");
    expect(m.kicker).toBe("Tasks");
    expect(m.pageTitleSuffix).toBe("New task");
  });

  it("returns settings meta for nested settings routes", () => {
    expect(hiveMobileRouteMeta("/settings/security").kicker).toBe("Settings");
    expect(hiveMobileRouteMeta("/settings/llm-keys").pageTitleSuffix).toBe("LLM keys");
  });

  it("fallbacks to QueenSwarm for unknown routes", () => {
    expect(hiveMobileRouteMeta("/unknown/route").kicker).toBe("QueenSwarm");
  });

  it("returns execution and integrations hub meta", () => {
    expect(hiveMobileRouteMeta("/execution").kicker).toBe("Execution");
    expect(hiveMobileRouteMeta("/integrations").kicker).toBe("Integrations");
  });
});
