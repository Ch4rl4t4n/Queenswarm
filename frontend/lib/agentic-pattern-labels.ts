/** Human labels for Kashef / Queenswarm agentic design pattern IDs. */

export const AGENTIC_PATTERN_LABELS: Record<string, string> = {
  prompt_chaining: "Prompt Chaining",
  routing: "Routing",
  parallelization: "Parallelization",
  reflection: "Reflection",
  tool_use: "Tool Use",
  planning: "Planning",
  multi_agent: "Multi-Agent",
  memory_management: "Memory",
  learning_adaptation: "Learning",
  goal_monitoring: "Goal Monitoring",
  exception_handling: "Exception Handling",
  human_in_the_loop: "Human-in-the-Loop",
  rag: "RAG",
  inter_agent_communication: "Inter-Agent Comms",
  resource_aware: "Resource-Aware",
  reasoning: "Reasoning",
  guardrails: "Guardrails",
  prioritization: "Prioritization",
  exploration: "Exploration",
};

/** Return display label for one pattern id (falls back to title-cased slug). */
export function agenticPatternLabel(patternId: string): string {
  const norm = patternId.trim();
  if (!norm) {
    return "—";
  }
  return AGENTIC_PATTERN_LABELS[norm] ?? norm.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
