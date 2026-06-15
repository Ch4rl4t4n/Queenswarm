import { describe, expect, it } from "vitest";

import type { AgentLoopPhaseStatus } from "@/components/hive/agent-loop-timeline-panel";

/** Mirror of panel phase tone logic for regression tests. */
export function agentLoopPhaseIsHighlighted(
  phaseId: string,
  currentPhase: string,
  status: AgentLoopPhaseStatus,
): boolean {
  return phaseId === currentPhase && status !== "done";
}

describe("agentLoopPhaseIsHighlighted", () => {
  it("highlights active current phase", () => {
    expect(agentLoopPhaseIsHighlighted("tool", "tool", "active")).toBe(true);
  });

  it("does not highlight done current phase", () => {
    expect(agentLoopPhaseIsHighlighted("verify", "verify", "done")).toBe(false);
  });

  it("does not highlight non-current phase", () => {
    expect(agentLoopPhaseIsHighlighted("plan", "tool", "active")).toBe(false);
  });
});
