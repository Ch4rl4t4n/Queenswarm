import { describe, expect, it } from "vitest";

import { agenticPatternLabel } from "@/lib/agentic-pattern-labels";
import {
  extractSessionPatternSkills,
  parseAgenticPatterns,
  patternPreviewToSnapshot,
} from "@/lib/session-pattern-skills";
import type { SupervisorSessionRow } from "@/lib/hive-types";

function minimalSession(overrides: Partial<SupervisorSessionRow> = {}): SupervisorSessionRow {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    goal: "Research competitors",
    status: "running",
    runtime_mode: "durable",
    created_by_subject: null,
    context_summary: {},
    swarm_id: null,
    task_id: null,
    started_at: null,
    completed_at: null,
    error_text: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    sub_agents: [],
    ...overrides,
  };
}

describe("session-pattern-skills", () => {
  it("parseAgenticPatterns returns null when missing", () => {
    expect(parseAgenticPatterns({})).toBeNull();
    expect(parseAgenticPatterns({ agentic_patterns: "bad" })).toBeNull();
  });

  it("parseAgenticPatterns merges primary and secondary into all", () => {
    const parsed = parseAgenticPatterns({
      agentic_patterns: {
        primary: ["planning", "rag"],
        secondary: ["reflection"],
        forced_reflection: true,
        rationale: ["baseline"],
        router_version: "heuristic-v1",
      },
    });
    expect(parsed?.all).toEqual(["planning", "rag", "reflection"]);
    expect(parsed?.forced_reflection).toBe(true);
  });

  it("extractSessionPatternSkills prefers context_summary resolved skills", () => {
    const session = minimalSession({
      context_summary: {
        agentic_patterns: { primary: ["tool_use"], secondary: [], all: ["tool_use"] },
        resolved_skill_slugs: ["context", "tdd"],
        resolved_skills_by_role: { researcher: ["context"], critic: ["tdd"] },
        pattern_suggested_skills: ["context"],
      },
      sub_agents: [
        {
          id: "sub-1",
          role: "researcher",
          status: "running",
          runtime_mode: "durable",
          toolset: [],
          short_memory: { skills: ["ignored"] },
          spawn_order: 0,
          started_at: null,
          completed_at: null,
          last_output: null,
          error_text: null,
        },
      ],
    });
    const snap = extractSessionPatternSkills(session);
    expect(snap.allSkills).toEqual(["context", "tdd"]);
    expect(snap.skillsByRole.researcher).toEqual(["context"]);
    expect(snap.routerEnabled).toBe(true);
  });

  it("extractSessionPatternSkills falls back to sub_agent short_memory", () => {
    const session = minimalSession({
      context_summary: {
        agentic_patterns: { primary: ["rag"], secondary: [], all: ["rag"] },
      },
      sub_agents: [
        {
          id: "sub-1",
          role: "coder",
          status: "queued",
          runtime_mode: "durable",
          toolset: [],
          short_memory: { skills: ["tdd", "diagnose"] },
          spawn_order: 0,
          started_at: null,
          completed_at: null,
          last_output: null,
          error_text: null,
        },
      ],
    });
    const snap = extractSessionPatternSkills(session);
    expect(snap.allSkills).toEqual(["tdd", "diagnose"]);
  });

  it("patternPreviewToSnapshot maps API payload", () => {
    const snap = patternPreviewToSnapshot({
      router_enabled: true,
      agentic_patterns: { primary: ["planning"], secondary: [], all: ["planning"] },
      suggested_skill_slugs: ["multi-step-reasoning"],
      pattern_prompt_preview: "block",
    });
    expect(snap.suggestedSkills).toEqual(["multi-step-reasoning"]);
    expect(snap.patterns?.primary).toEqual(["planning"]);
  });

  it("agenticPatternLabel humanizes unknown ids", () => {
    expect(agenticPatternLabel("tool_use")).toBe("Tool Use");
    expect(agenticPatternLabel("custom_pattern")).toBe("Custom Pattern");
  });
});
