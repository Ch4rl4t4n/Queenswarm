/** Agentic pattern stack labels shown in Swarm Builder onboarding copy. */

import type { SwarmWizardTemplateId } from "@/lib/swarm-wizard-templates";

export const SWARM_TEMPLATE_PATTERN_STACKS: Record<SwarmWizardTemplateId, string[]> = {
  "exec-assistant": ["Planning", "RAG", "Reflection", "Goal Monitoring"],
  "lead-waterfall": ["Parallelization", "Tool Use", "Human-in-the-Loop"],
  "content-flywheel": ["Prompt Chaining", "Tool Use", "Guardrails", "Reflection"],
  "life-os": ["Memory", "Prioritization", "Reflection", "Planning"],
  "product-ship": ["Planning", "Tracer Bullets", "Human-in-the-Loop", "Reflection"],
};

export function patternCountLabel(templateId: SwarmWizardTemplateId): string {
  const count = SWARM_TEMPLATE_PATTERN_STACKS[templateId]?.length ?? 0;
  return count > 0 ? `${count} agentic patterns orchestrated automatically` : "Agentic patterns orchestrated automatically";
}
