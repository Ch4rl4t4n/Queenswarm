/** Agentic pattern stack labels shown in Swarm Builder onboarding copy. */

import type { SwarmWizardTemplateId } from "@/lib/swarm-wizard-templates";

export const SWARM_TEMPLATE_PATTERN_STACKS: Record<SwarmWizardTemplateId, string[]> = {
  "marketing-ops": ["Prompt Chaining", "Tool Use", "Guardrails", "Human-in-the-Loop"],
  "lead-waterfall": ["Parallelization", "Tool Use", "Human-in-the-Loop"],
  "finance-ops": ["Reflection", "Guardrails", "Goal Monitoring"],
  "digital-ops": ["RAG", "Tool Use", "Reflection"],
  "eshop-ops": ["RAG", "Tool Use", "Guardrails", "Human-in-the-Loop", "Reflection"],
  "rnd-dev": ["Planning", "Tool Use", "Learning Adaptation"],
  "product-ship": ["Planning", "Tracer Bullets", "Human-in-the-Loop", "Reflection"],
  "sentinel-radar": ["RAG", "Goal Monitoring", "Reflection"],
  "exec-assistant": ["Planning", "RAG", "Reflection", "Goal Monitoring"],
  "content-flywheel": ["Prompt Chaining", "Tool Use", "Guardrails"],
  "content-flywheel-v2": ["RAG", "Prompt Chaining", "Learning Adaptation", "Human-in-the-Loop"],
  "polymarket-prediction-evaluator": ["RAG", "Parallelization", "Reflection", "Guardrails"],
  "polymarket-trading": ["Planning", "Guardrails", "Human-in-the-Loop", "Tool Use"],
  "trading-content-hybrid": ["Planning", "Prompt Chaining", "Guardrails", "Learning Adaptation", "Human-in-the-Loop"],
  "life-business-os": ["Memory", "Planning", "Parallelization", "Reflection", "Goal Monitoring"],
  "faceless-media-agency": ["Prompt Chaining", "Human-in-the-Loop", "Guardrails", "Tool Use", "Learning Adaptation"],
  "micro-saas-factory": ["Planning", "Tool Use", "Guardrails", "Human-in-the-Loop", "Tracer Bullets"],
  "life-os": ["Memory", "Prioritization", "Reflection", "Planning"],
  "business-analytics-report": ["RAG", "Tool Use", "Reflection", "Guardrails", "Human-in-the-Loop"],
};

export function patternCountLabel(templateId: SwarmWizardTemplateId): string {
  const count = SWARM_TEMPLATE_PATTERN_STACKS[templateId]?.length ?? 0;
  return count > 0 ? `${count} agentic patterns orchestrated automatically` : "Agentic patterns orchestrated automatically";
}
