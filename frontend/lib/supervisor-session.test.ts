import { describe, expect, it } from "vitest";

import {
  filterSubAgentEvents,
  isTerminalSessionStatus,
  parseSubAgentShortMemory,
  runtimeModeLabel,
  sessionStatusTone,
  supervisorSessionMatchesStatusFilter,
  supervisorSessionProgressPct,
  supervisorSessionManualApproveHint,
  supervisorSessionAgentsHref,
  skillFactoryForgeHref,
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

  it("builds skill factory forge deep link", () => {
    expect(skillFactoryForgeHref()).toBe("/integrations?tab=studio&section=lanes#skill-forge");
  });

  it("builds agents deep link with session id", () => {
    expect(supervisorSessionAgentsHref("abc-123")).toBe("/agents?session=abc-123#sessions");
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

  it("supervisorSessionProgressPct floors running work at 5%", () => {
    expect(
      supervisorSessionProgressPct({
        status: "running",
        sub_agents: [{ status: "running" }, { status: "running" }],
      }),
    ).toBe(5);
    expect(
      supervisorSessionProgressPct({
        status: "running",
        sub_agents: [{ status: "completed" }, { status: "running" }],
      }),
    ).toBe(50);
  });

  it("supervisorSessionProgressPct shows 100 when session completed", () => {
    expect(
      supervisorSessionProgressPct({
        status: "completed",
        sub_agents: [
          { status: "completed" },
          { status: "completed" },
          { status: "completed" },
        ],
      }),
    ).toBe(100);
  });

  it("supervisorSessionMatchesStatusFilter hides archived rows for active", () => {
    expect(supervisorSessionMatchesStatusFilter("running", "active")).toBe(true);
    expect(supervisorSessionMatchesStatusFilter("completed", "active")).toBe(false);
    expect(supervisorSessionMatchesStatusFilter("completed", "completed")).toBe(true);
  });

  it("supervisorSessionManualApproveHint explains critical blocks", () => {
    expect(
      supervisorSessionManualApproveHint(
        {
          status: "needs_input",
          goal: "Digest",
          context_summary: { approval_required: true, approval_reason: "Critical action keyword detected: billing" },
        },
        true,
      ),
    ).toContain("billing");
    expect(
      supervisorSessionManualApproveHint(
        { status: "needs_input", goal: "Forager insights", context_summary: {} },
        true,
      ),
    ).toBeNull();
  });
});

