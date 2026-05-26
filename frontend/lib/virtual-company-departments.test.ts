import { describe, expect, it } from "vitest";

import {
  activeVirtualCompanyTemplateIds,
  buildSwarmLocalMemoryForTemplate,
  getDepartmentByTemplateId,
  VIRTUAL_COMPANY_DEPARTMENTS,
} from "@/lib/virtual-company-departments";
import { getVirtualCompanyTemplates } from "@/lib/swarm-wizard-templates";

describe("virtual-company-departments", () => {
  it("defines six active virtual company departments", () => {
    const active = VIRTUAL_COMPANY_DEPARTMENTS.filter((d) => d.status === "active");
    expect(active).toHaveLength(6);
    expect(active.map((d) => d.id)).toEqual(
      expect.arrayContaining(["marketing", "sales", "finance", "digital", "rnd", "product"]),
    );
  });

  it("all active departments use simulate + approval execution wire", () => {
    for (const dept of VIRTUAL_COMPANY_DEPARTMENTS) {
      if (dept.status !== "active" || !dept.execution) {
        continue;
      }
      expect(dept.execution.default_mode).toBe("simulate");
      expect(dept.execution.live_requires_approval).toBe(true);
      expect(dept.execution.free_first_routing).toBe(true);
    }
  });

  it("buildSwarmLocalMemoryForTemplate includes execution_studio for marketing", () => {
    const mem = buildSwarmLocalMemoryForTemplate("marketing-ops");
    expect(mem.virtual_company_department).toBe("marketing");
    expect(mem.manager_slug).toBe("content_creation");
    const es = mem.execution_studio as { suggested_connectors: string[] };
    expect(es.suggested_connectors).toContain("notion_workspace");
  });

  it("active template ids are included in buildable virtual company templates", () => {
    const ids = activeVirtualCompanyTemplateIds();
    const templateIds = getVirtualCompanyTemplates().map((t) => t.id);
    for (const id of ids) {
      expect(templateIds).toContain(id);
    }
  });

  it("department templates include mcp_invoke on every agent", () => {
    const deptIds = new Set(activeVirtualCompanyTemplateIds());
    for (const template of getVirtualCompanyTemplates()) {
      if (!deptIds.has(template.id)) {
        continue;
      }
      for (const agent of template.agents) {
        expect(agent.tools).toContain("mcp_invoke");
      }
    }
  });

  it("getDepartmentByTemplateId resolves sales from lead-waterfall", () => {
    expect(getDepartmentByTemplateId("lead-waterfall")?.id).toBe("sales");
  });
});
