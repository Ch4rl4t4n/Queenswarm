import { describe, expect, it } from "vitest";

import {
  filterSubAgentEvents,
  isTerminalSessionStatus,
  parseSubAgentShortMemory,
  runtimeModeLabel,
  sessionStatusTone,
  subAgentStepEventLabel,
  subAgentStepEventTone,
  celeryJobStateTone,
  isSubAgentRetryable,
} from "./supervisor-session";

describe("supervisor-session helpers", () => {
  it("maps runtime mode labels", () => {
    expect(runtimeModeLabel("durable")).toBe("durable");
    expect(runtimeModeLabel("inprocess")).toBe("in-process");
    expect(runtimeModeLabel("unknown")).toBe("in-process");
  });

  it("detects terminal statuses", () => {
    expect(isTerminalSessionStatus("completed")).toBe(true);
    expect(isTerminalSessionStatus("stopped")).toBe(true);
    expect(isTerminalSessionStatus("running")).toBe(false);
  });

  it("maps session status tones", () => {
    expect(sessionStatusTone("running")).toBe("cyan");
    expect(sessionStatusTone("needs_input")).toBe("magenta");
    expect(sessionStatusTone("completed")).toBe("green");
  });

  it("parses sub-agent short_memory fields", () => {
    const parsed = parseSubAgentShortMemory({
      sub_goal: "Audit pricing page",
      skills: ["context", "tdd"],
      skill_manifest: [{ slug: "tdd", version: "1.0.0" }],
      skills_prompt_block: "Skill: TDD\nred-green-refactor",
    });
    expect(parsed.subGoal).toBe("Audit pricing page");
    expect(parsed.skills).toEqual(["context", "tdd"]);
    expect(parsed.skillManifest).toHaveLength(1);
    expect(parsed.promptPreview).toContain("Skill: TDD");
  });

  it("filters sub-agent step events in chronological order", () => {
    const events = [
      {
        id: "2",
        supervisor_session_id: "s1",
        sub_agent_session_id: "a1",
        event_type: "sub_agent_completed",
        level: "info",
        message: "done",
        payload: {},
        occurred_at: "2026-05-19T12:00:02Z",
        created_at: "2026-05-19T12:00:02Z",
      },
      {
        id: "1",
        supervisor_session_id: "s1",
        sub_agent_session_id: "a1",
        event_type: "sub_agent_started",
        level: "info",
        message: "start",
        payload: {},
        occurred_at: "2026-05-19T12:00:01Z",
        created_at: "2026-05-19T12:00:01Z",
      },
      {
        id: "3",
        supervisor_session_id: "s1",
        sub_agent_session_id: "a2",
        event_type: "sub_agent_started",
        level: "info",
        message: "other",
        payload: {},
        occurred_at: "2026-05-19T12:00:03Z",
        created_at: "2026-05-19T12:00:03Z",
      },
    ];
    const filtered = filterSubAgentEvents(events, "a1");
    expect(filtered.map((row) => row.event_type)).toEqual(["sub_agent_started", "sub_agent_completed"]);
    expect(subAgentStepEventLabel("sub_agent_started")).toBe("started");
    expect(subAgentStepEventTone("sub_agent_completed")).toBe("ok");
    expect(subAgentStepEventTone("needs_input_requested")).toBe("warn");
    expect(celeryJobStateTone("SUCCESS")).toBe("ok");
    expect(celeryJobStateTone("NOT_ENQUEUED")).toBe("gold");
  });

  it("detects retryable sub-agent statuses", () => {
    expect(isSubAgentRetryable("needs_input", "running")).toBe(true);
    expect(isSubAgentRetryable("queued", "running")).toBe(true);
    expect(isSubAgentRetryable("completed", "running")).toBe(false);
    expect(isSubAgentRetryable("needs_input", "paused")).toBe(false);
  });
});

