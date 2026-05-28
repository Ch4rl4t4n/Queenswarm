import { describe, expect, it } from "vitest";

import { hiveMobileRouteMeta } from "./hive-mobile-meta";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "./feature-flags";

describe("hiveMobileRouteMeta", () => {
  it("returns Agentic OS meta for root when CP enabled", () => {
    const m = hiveMobileRouteMeta("/");
    if (OPERATOR_CONTROL_PLANE_ENABLED) {
      expect(m.kicker).toBe("Agentic OS");
      expect(m.pageTitleSuffix).toBe("Agentic OS");
    } else {
      expect(m.kicker).toBe("Dashboard");
      expect(m.staticSubtitle).toContain("roster");
    }
  });

  it("returns Agentic OS meta under /agentic-os and legacy /cockpit when CP enabled", () => {
    if (!OPERATOR_CONTROL_PLANE_ENABLED) {
      return;
    }
    for (const path of ["/agentic-os", "/cockpit"]) {
      const m = hiveMobileRouteMeta(path);
      expect(m.kicker).toBe("Agentic OS");
      expect(m.pageTitleSuffix).toBe("Agentic OS");
    }
  });

  it("returns dashboard hub meta under /dashboard", () => {
    const m = hiveMobileRouteMeta("/dashboard");
    expect(m.kicker).toBe("Dashboard");
    expect(m.pageTitleSuffix).toBe("Dashboard");
  });

  it("treats /overview as dashboard alias meta", () => {
    const m = hiveMobileRouteMeta("/overview");
    expect(m.kicker).toBe("Dashboard");
    expect(m.pageTitleSuffix).toBe("Dashboard");
  });

  it("returns ballroom meta with pageTitleSuffix", () => {
    const m = hiveMobileRouteMeta("/ballroom");
    expect(m.kicker).toBe("Ballroom");
    expect(m.pageTitleSuffix).toBe("Ballroom");
  });

  it("treats /hive-mind as knowledge alias when consolidated", () => {
    const m = hiveMobileRouteMeta("/hive-mind");
    expect(m.kicker).toBe("Knowledge");
    expect(m.pageTitleSuffix).toBe("Knowledge");
  });

  it("treats /outputs as knowledge alias when consolidated", () => {
    const m = hiveMobileRouteMeta("/outputs");
    expect(m.kicker).toBe("Knowledge");
    expect(m.pageTitleSuffix).toBe("Knowledge");
  });

  it("treats /connectors as integrations alias when consolidated", () => {
    const m = hiveMobileRouteMeta("/connectors");
    expect(m.kicker).toBe("Integrations");
    expect(m.pageTitleSuffix).toBe("Integrations");
  });

  it("treats /external-projects as integrations alias when consolidated", () => {
    const m = hiveMobileRouteMeta("/external-projects");
    expect(m.kicker).toBe("Integrations");
    expect(m.pageTitleSuffix).toBe("Integrations");
  });

  it("returns learning meta under /learning", () => {
    const m = hiveMobileRouteMeta("/learning");
    expect(m.kicker).toBe("Knowledge");
    expect(m.pageTitleSuffix).toBe("Knowledge");
  });

  it("returns jobs meta under /jobs", () => {
    const m = hiveMobileRouteMeta("/jobs");
    expect(m.kicker).toBe("Jobs");
    expect(m.pageTitleSuffix).toBe("Jobs");
    expect(m.staticSubtitle).toContain("Celery");
  });

  it("treats /hierarchy as agents alias metadata", () => {
    const m = hiveMobileRouteMeta("/hierarchy");
    expect(m.kicker).toBe("Agents");
    expect(m.pageTitleSuffix).toBe("Agents");
  });

  it("prefers longer prefix for /tasks/new", () => {
    const m = hiveMobileRouteMeta("/tasks/new");
    expect(m.kicker).toBe("Tasks");
    expect(m.pageTitleSuffix).toBe("New task");
  });

  it("returns settings meta for nested settings routes", () => {
    expect(hiveMobileRouteMeta("/settings/security").kicker).toBe("Settings");
    expect(hiveMobileRouteMeta("/settings/llm-keys").pageTitleSuffix).toBe("LLM & Voice");
  });

  it("returns secondary route mobile titles", () => {
    expect(hiveMobileRouteMeta("/foragers").pageTitleSuffix).toBe("Foragers");
    expect(hiveMobileRouteMeta("/apps-tools/mcp-ops-studio").pageTitleSuffix).toBe("MCP Ops Studio");
    expect(hiveMobileRouteMeta("/settings/team").pageTitleSuffix).toBe("Team");
    expect(hiveMobileRouteMeta("/settings/billing").pageTitleSuffix).toBe("Costs");
  });

  it("returns apps-tools and manual meta when consolidated", () => {
    expect(hiveMobileRouteMeta("/apps-tools").kicker).toBe("Apps & Tools");
    expect(hiveMobileRouteMeta("/manual").kicker).toBe("Manual");
  });

  it("fallbacks to QueenSwarm for unknown routes", () => {
    expect(hiveMobileRouteMeta("/unknown/route").kicker).toBe("QueenSwarm");
  });

  it("returns execution and integrations hub meta", () => {
    expect(hiveMobileRouteMeta("/execution").kicker).toBe("Tasks");
    expect(hiveMobileRouteMeta("/integrations").kicker).toBe("Integrations");
  });

  it("supports legacy mode metadata when consolidated nav is disabled", () => {
    const rootKicker = OPERATOR_CONTROL_PLANE_ENABLED ? "Agentic OS" : "Dashboard";
    expect(hiveMobileRouteMeta("/", false).kicker).toBe(rootKicker);
    expect(hiveMobileRouteMeta("/tasks", false).kicker).toBe("Tasks");
    expect(hiveMobileRouteMeta("/overview", false).kicker).toBe("QueenSwarm");
    expect(hiveMobileRouteMeta("/dashboard", false).kicker).toBe("QueenSwarm");
    expect(hiveMobileRouteMeta("/hive-mind", false).kicker).toBe("HiveMind");
    expect(hiveMobileRouteMeta("/outputs", false).kicker).toBe("Outputs");
    expect(hiveMobileRouteMeta("/learning", false).kicker).toBe("Learning");
    expect(hiveMobileRouteMeta("/connectors", false).kicker).toBe("Connectors");
    expect(hiveMobileRouteMeta("/external-projects", false).kicker).toBe("External");
    expect(hiveMobileRouteMeta("/plugins", false).kicker).toBe("Plugins");
  });
});
