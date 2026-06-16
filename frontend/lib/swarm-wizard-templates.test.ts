import { describe, expect, it } from "vitest";

import {
  getBuildableSwarmTemplates,
  getSentinelSwarmTemplates,
  getSwarmWizardTemplate,
  getVirtualCompanyTemplates,
  templateRequiresProTier,
} from "@/lib/swarm-wizard-templates";
import { activeVirtualCompanyTemplateIds } from "@/lib/virtual-company-departments";

describe("swarm-wizard-templates", () => {
  it("virtual company department templates include mcp_invoke on every agent", () => {
    const deptIds = new Set(activeVirtualCompanyTemplateIds());
    const vc = getVirtualCompanyTemplates().filter((t) => deptIds.has(t.id));
    expect(vc).toHaveLength(6);
    for (const template of vc) {
      expect(template.category).toBe("virtual_company");
      expect(template.agents.length).toBeGreaterThanOrEqual(3);
      expect(template.agents.every((a) => a.tools.includes("mcp_invoke"))).toBe(true);
    }
  });

  it("virtual company includes extended operator templates beyond six departments", () => {
    const vc = getVirtualCompanyTemplates();
    expect(vc.length).toBeGreaterThanOrEqual(6);
    expect(vc.map((t) => t.id)).toEqual(expect.arrayContaining([...activeVirtualCompanyTemplateIds()]));
  });

  it("sentinel-radar is read-only without mcp_invoke", () => {
    const sentinels = getSentinelSwarmTemplates();
    expect(sentinels).toHaveLength(1);
    expect(sentinels[0]?.id).toBe("sentinel-radar");
    for (const agent of sentinels[0]?.agents ?? []) {
      expect(agent.tools).not.toContain("mcp_invoke");
    }
  });

  it("marketing-ops includes research-content-publish pipeline", () => {
    const template = getSwarmWizardTemplate("marketing-ops");
    expect(template).toBeDefined();
    expect(template?.agents.map((a) => a.name)).toEqual(
      expect.arrayContaining(["Marketing Manager", "Topic Research Bee", "Publish Pack Bee"]),
    );
    expect(template?.routine?.name).toMatch(/marketing/i);
  });

  it("sales ops (lead-waterfall) includes pipeline routine", () => {
    const template = getSwarmWizardTemplate("lead-waterfall");
    expect(template?.name).toBe("Sales Ops");
    expect(template?.routine?.name).toMatch(/sales/i);
  });

  it("finance-ops and digital-ops are buildable scout swarms", () => {
    expect(getSwarmWizardTemplate("finance-ops")?.comingSoon).not.toBe(true);
    expect(getSwarmWizardTemplate("digital-ops")?.comingSoon).not.toBe(true);
    expect(getSwarmWizardTemplate("eshop-ops")?.comingSoon).not.toBe(true);
    expect(getSwarmWizardTemplate("rnd-dev")?.comingSoon).not.toBe(true);
  });

  it("eshop-ops includes Shopify and order monitoring bees", () => {
    const template = getSwarmWizardTemplate("eshop-ops");
    expect(template?.agents.map((a) => a.name)).toEqual(
      expect.arrayContaining(["E-shop Manager", "Order Monitor Bee", "Product Research Bee"]),
    );
    expect(template?.routine?.name).toMatch(/e-shop/i);
  });

  it("life-os template is buildable with overnight routine", () => {
    const template = getSwarmWizardTemplate("life-os");
    expect(template?.comingSoon).not.toBe(true);
    expect(template?.routine?.name).toMatch(/overnight/i);
  });

  it("product-ship includes PRD bees and prdKanban flow", () => {
    const template = getSwarmWizardTemplate("product-ship");
    expect(template?.prdKanban).toBeDefined();
    expect(template?.agents.map((a) => a.name)).toEqual(
      expect.arrayContaining(["PRD Planner Manager", "Tracer Bullet Bee", "Ship Gate Bee"]),
    );
  });

  it("content-flywheel is legacy comingSoon", () => {
    expect(getSwarmWizardTemplate("content-flywheel")?.comingSoon).toBe(true);
  });

  it("buildable templates exclude comingSoon", () => {
    const buildable = getBuildableSwarmTemplates();
    expect(buildable.every((t) => !t.comingSoon)).toBe(true);
    expect(buildable.some((t) => t.id === "content-flywheel")).toBe(false);
  });

  it("templateRequiresProTier when commercial free and three+ agents", () => {
    const template = getSwarmWizardTemplate("marketing-ops");
    expect(template).toBeDefined();
    expect(templateRequiresProTier(template!, "commercial", "free")).toBe(true);
    expect(templateRequiresProTier(template!, "internal", "free")).toBe(false);
  });

  it("every buildable template defines accentHex", () => {
    for (const item of getBuildableSwarmTemplates()) {
      expect(item.accentHex).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });

  it("business-analytics-report includes five-bee Codex pipeline", () => {
    const template = getSwarmWizardTemplate("business-analytics-report");
    expect(template?.comingSoon).not.toBe(true);
    expect(template?.agents).toHaveLength(5);
    expect(template?.agents.map((a) => a.name)).toEqual(
      expect.arrayContaining([
        "Analytics Supervisor",
        "Data Fetch Bee",
        "Analyst Bee",
        "Narrative Bee",
        "Critic Bee",
      ]),
    );
    expect(template?.routine?.goalTemplate).toMatch(/critic rubric/i);
  });
});
