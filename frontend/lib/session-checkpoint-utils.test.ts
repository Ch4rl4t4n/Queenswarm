import { describe, expect, it } from "vitest";

import type { SupervisorSessionRow } from "@/lib/hive-types";
import {
  buildSessionCheckpointSnapshot,
  sessionShowsCheckpointResume,
  verifiedCheckpointCount,
} from "@/lib/session-checkpoint-utils";

function session(overrides: Partial<SupervisorSessionRow> = {}): SupervisorSessionRow {
  return {
    id: "sess-1",
    goal: "Ship",
    status: "paused",
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

describe("session-checkpoint-utils", () => {
  it("buildSessionCheckpointSnapshot marks completed steps as verified", () => {
    const snapshot = buildSessionCheckpointSnapshot(
      session({
        sub_agents: [
          {
            id: "a1",
            role: "researcher",
            status: "completed",
            runtime_mode: "durable",
            toolset: [],
            short_memory: {},
            spawn_order: 0,
            started_at: null,
            completed_at: null,
            last_output: null,
            error_text: null,
          },
          {
            id: "a2",
            role: "coder",
            status: "failed",
            runtime_mode: "durable",
            toolset: [],
            short_memory: {},
            spawn_order: 1,
            started_at: null,
            completed_at: null,
            last_output: null,
            error_text: "timeout",
          },
        ],
      }),
    );

    expect(snapshot.last_verified_role).toBe("researcher");
    expect(snapshot.next_resumable_role).toBe("coder");
    expect(snapshot.can_resume_from_checkpoint).toBe(true);
  });

  it("sessionShowsCheckpointResume is true for paused durable sessions with retryable steps", () => {
    const row = session({
      status: "paused",
      sub_agents: [
        {
          id: "a1",
          role: "researcher",
          status: "completed",
          runtime_mode: "durable",
          toolset: [],
          short_memory: {},
          spawn_order: 0,
          started_at: null,
          completed_at: null,
          last_output: null,
          error_text: null,
        },
        {
          id: "a2",
          role: "coder",
          status: "queued",
          runtime_mode: "durable",
          toolset: [],
          short_memory: {},
          spawn_order: 1,
          started_at: null,
          completed_at: null,
          last_output: null,
          error_text: null,
        },
      ],
    });

    expect(sessionShowsCheckpointResume(row)).toBe(true);
    expect(verifiedCheckpointCount(row.sub_agents)).toBe(1);
  });

  it("sessionShowsCheckpointResume is true for needs_input inprocess sessions", () => {
    const row = session({
      status: "needs_input",
      runtime_mode: "inprocess",
      sub_agents: [
        {
          id: "a1",
          role: "researcher",
          status: "completed",
          runtime_mode: "inprocess",
          toolset: [],
          short_memory: {},
          spawn_order: 0,
          started_at: null,
          completed_at: null,
          last_output: null,
          error_text: null,
        },
        {
          id: "a2",
          role: "publisher",
          status: "needs_input",
          runtime_mode: "inprocess",
          toolset: [],
          short_memory: {},
          spawn_order: 1,
          started_at: null,
          completed_at: null,
          last_output: null,
          error_text: null,
        },
      ],
    });

    expect(sessionShowsCheckpointResume(row)).toBe(true);
  });
});
