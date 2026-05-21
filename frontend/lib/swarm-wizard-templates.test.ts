import { describe, expect, it } from "vitest";

import {
  SWARM_WIZARD_TEMPLATES,
  getSwarmWizardTemplate,
  templateRequiresProTier,
} from "@/lib/swarm-wizard-templates";

describe("swarm-wizard-templates", () => {
  it("all three phase0 templates are buildable (not comingSoon)", () => {
    for (const id of ["exec-assistant", "lead-waterfall", "content-flywheel"] as const) {
      const template = getSwarmWizardTemplate(id);
      expect(template?.comingSoon).not.toBe(true);
      expect(template?.agents.length).toBeGreaterThanOrEqual(3);
    }
  });

  it("lead-waterfall includes scrape-qualify-outreach manager and routine", () => {
    const template = getSwarmWizardTemplate("lead-waterfall");
    expect(template).toBeDefined();
    expect(template?.swarmPurpose).toBe("action");
    expect(template?.agents.map((a) => a.name)).toEqual(
      expect.arrayContaining(["Pipeline Manager", "Lead Scout Bee", "Outreach Draft Bee"]),
    );
    expect(template?.routine?.name).toMatch(/waterfall/i);
  });

  it("content-flywheel includes research-draft-social pipeline and routine", () => {
    const template = getSwarmWizardTemplate("content-flywheel");
    expect(template).toBeDefined();
    expect(template?.swarmPurpose).toBe("scout");
    expect(template?.agents.map((a) => a.name)).toEqual(
      expect.arrayContaining(["Content Editor Manager", "Topic Research Bee", "Draft & Social Bee"]),
    );
    expect(template?.routine?.name).toMatch(/flywheel/i);
  });

  it("life-os template is phase4 buildable with overnight routine", () => {
    const template = getSwarmWizardTemplate("life-os");
    expect(template).toBeDefined();
    expect(template?.comingSoon).not.toBe(true);
    expect(template?.routine?.name).toMatch(/overnight/i);
    expect(template?.agents.length).toBeGreaterThanOrEqual(3);
  });

  it("product-ship includes PRD → Kanban bees and prdKanban flow", () => {
    const template = getSwarmWizardTemplate("product-ship");
    expect(template).toBeDefined();
    expect(template?.prdKanban).toBeDefined();
    expect(template?.agents.map((a) => a.name)).toEqual(
      expect.arrayContaining(["PRD Planner Manager", "Tracer Bullet Bee", "Kanban Slice Bee", "TDD Gate Bee"]),
    );
    expect(template?.routine?.name).toMatch(/ship review/i);
  });

  it("no templates are marked comingSoon", () => {
    const soon = SWARM_WIZARD_TEMPLATES.filter((t) => t.comingSoon);
    expect(soon).toEqual([]);
  });

  it("templateRequiresProTier when commercial free and three agents", () => {
    const template = getSwarmWizardTemplate("exec-assistant");
    expect(template).toBeDefined();
    expect(templateRequiresProTier(template!, "commercial", "free")).toBe(true);
    expect(templateRequiresProTier(template!, "commercial", "pro")).toBe(false);
    expect(templateRequiresProTier(template!, "internal", "free")).toBe(false);
  });

  it("every template defines accentHex", () => {
    for (const item of SWARM_WIZARD_TEMPLATES) {
      expect(item.accentHex).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });
});
