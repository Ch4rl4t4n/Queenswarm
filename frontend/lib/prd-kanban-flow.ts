/** PRD → Kanban flow helpers (Matt Pocock / Product Ship wizard). */

import type { SwarmWizardTemplateId } from "@/lib/swarm-wizard-templates";

export const PRODUCT_SHIP_PRD_PREFILL = `# Product Ship PRD

## Problem
Describe the user pain in 2–3 sentences.

## Success criteria (measurable)
- Criterion 1
- Criterion 2

## Non-goals
- Out of scope item

## Vertical slices (tracer bullets)
1. Slice 1 — smallest shippable increment
2. Slice 2 — next verified step
3. Slice 3 — integration / polish

## Verification
- Simulation gate required before user-facing output
- Human review on ambiguous requirements
`;

export interface PrdKanbanLaunchParams {
  template: SwarmWizardTemplateId;
  swarmId?: string;
}

/** Build `/tasks/new` query for PRD → breaker → Kanban slice flow. */
export function buildPrdKanbanTasksUrl(params: PrdKanbanLaunchParams): string {
  const q = new URLSearchParams();
  q.set("template", params.template);
  if (params.swarmId) {
    q.set("swarm_id", params.swarmId);
  }
  return `/tasks/new?${q.toString()}`;
}

/** Resolve task textarea prefill for wizard-linked intake. */
export function taskPrefillForWizardTemplate(templateId: string): string | null {
  if (templateId === "product-ship") {
    return PRODUCT_SHIP_PRD_PREFILL;
  }
  return null;
}
