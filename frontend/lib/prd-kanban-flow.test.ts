import { describe, expect, it } from "vitest";

import {
  buildPrdKanbanTasksUrl,
  PRODUCT_SHIP_PRD_PREFILL,
  taskPrefillForWizardTemplate,
} from "@/lib/prd-kanban-flow";

describe("prd-kanban-flow", () => {
  it("buildPrdKanbanTasksUrl includes template and swarm_id", () => {
    const url = buildPrdKanbanTasksUrl({ template: "product-ship", swarmId: "abc-123" });
    expect(url).toContain("template=product-ship");
    expect(url).toContain("swarm_id=abc-123");
    expect(url.startsWith("/tasks/new?")).toBe(true);
  });

  it("taskPrefillForWizardTemplate returns PRD outline for product-ship", () => {
    const prefill = taskPrefillForWizardTemplate("product-ship");
    expect(prefill).toBe(PRODUCT_SHIP_PRD_PREFILL);
    expect(prefill).toMatch(/Vertical slices/i);
  });

  it("taskPrefillForWizardTemplate returns null for unknown templates", () => {
    expect(taskPrefillForWizardTemplate("exec-assistant")).toBeNull();
  });
});
