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

  it("no template is marked comingSoon", () => {
    expect(SWARM_WIZARD_TEMPLATES.every((t) => !t.comingSoon)).toBe(true);
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
