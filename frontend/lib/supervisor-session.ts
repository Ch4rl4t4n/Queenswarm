export function runtimeModeLabel(mode: string): string {
  const key = mode.trim().toLowerCase();
  if (key === "durable") return "durable";
  return "in-process";
}

export function isTerminalSessionStatus(status: string): boolean {
  const key = status.trim().toLowerCase();
  return key === "completed" || key === "failed" || key === "stopped";
}

export function sessionStatusTone(status: string): "amber" | "cyan" | "green" | "magenta" | "red" {
  const key = status.trim().toLowerCase();
  if (key === "completed") return "green";
  if (key === "needs_input") return "magenta";
  if (key === "failed" || key === "stopped") return "red";
  if (key === "running") return "cyan";
  return "amber";
}

export interface SubAgentShortMemoryView {
  subGoal: string | null;
  skills: string[];
  skillManifest: Record<string, unknown>[];
  promptPreview: string | null;
}

/** Normalize sub-agent short_memory JSON for dashboard cards. */
import type { SupervisorSessionEventRow } from "@/lib/hive-types";

/** Event types emitted during one sub-agent Celery / in-process step. */
export const SUB_AGENT_STEP_EVENT_TYPES = new Set([
  "sub_agent_spawned",
  "sub_agent_requeued",
  "sub_agent_started",
  "sub_agent_skipped",
  "sub_agent_completed",
  "dynamic_tools_discovered",
  "agent_initiative_proposed",
  "approval_requested",
  "needs_input_requested",
]);

/** Filter session timeline events for one sub-agent step. */
export function filterSubAgentEvents(
  events: SupervisorSessionEventRow[],
  subAgentId: string,
): SupervisorSessionEventRow[] {
  return events
    .filter((event) => event.sub_agent_session_id === subAgentId && SUB_AGENT_STEP_EVENT_TYPES.has(event.event_type))
    .sort((a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime());
}

/** Human label for sub-agent step event types. */
export function subAgentStepEventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    sub_agent_spawned: "spawned",
    sub_agent_requeued: "requeued",
    sub_agent_started: "started",
    sub_agent_skipped: "skipped",
    sub_agent_completed: "completed",
    dynamic_tools_discovered: "tools",
    agent_initiative_proposed: "initiative",
    approval_requested: "approval",
    needs_input_requested: "needs input",
  };
  return labels[eventType] ?? eventType.replace(/_/g, " ");
}

/** Tone for sub-agent step badges in the timeline UI. */
export function subAgentStepEventTone(
  eventType: string,
): "ok" | "warn" | "err" | "info" | "gold" {
  if (eventType === "sub_agent_completed") return "ok";
  if (eventType === "sub_agent_skipped") return "warn";
  if (eventType === "approval_requested" || eventType === "needs_input_requested") return "warn";
  if (eventType === "agent_initiative_proposed") return "gold";
  if (eventType === "sub_agent_started") return "info";
  if (eventType === "sub_agent_requeued") return "gold";
  return "info";
}

/** Whether one sub-agent step can be retried individually. */
export function isSubAgentRetryable(subStatus: string, sessionStatus: string): boolean {
  const sessionKey = sessionStatus.trim().toLowerCase();
  if (sessionKey === "stopped" || sessionKey === "completed" || sessionKey === "paused") {
    return false;
  }
  const subKey = subStatus.trim().toLowerCase();
  return subKey === "needs_input" || subKey === "queued" || subKey === "pending" || subKey === "failed";
}

/** Tone for Celery AsyncResult state badges. */
export function celeryJobStateTone(state: string): "ok" | "warn" | "err" | "info" | "gold" {
  const key = state.trim().toUpperCase();
  if (key === "SUCCESS") return "ok";
  if (key === "FAILURE" || key === "REVOKED") return "err";
  if (key === "STARTED" || key === "RETRY") return "info";
  if (key === "PENDING" || key === "NOT_ENQUEUED") return "gold";
  return "warn";
}

export function parseSubAgentShortMemory(raw: Record<string, unknown>): SubAgentShortMemoryView {
  const subGoal = typeof raw.sub_goal === "string" ? raw.sub_goal : null;
  const skills = Array.isArray(raw.skills)
    ? raw.skills.filter((item): item is string => typeof item === "string")
    : [];
  let skillManifest: Record<string, unknown>[] = [];
  if (Array.isArray(raw.skill_manifest)) {
    skillManifest = raw.skill_manifest.filter(
      (item): item is Record<string, unknown> => typeof item === "object" && item !== null && !Array.isArray(item),
    );
  } else if (typeof raw.skill_manifest === "object" && raw.skill_manifest !== null && !Array.isArray(raw.skill_manifest)) {
    skillManifest = [raw.skill_manifest as Record<string, unknown>];
  }
  const block = typeof raw.skills_prompt_block === "string" ? raw.skills_prompt_block.trim() : "";
  const promptPreview = block ? block.slice(0, 280) : null;
  return { subGoal, skills, skillManifest, promptPreview };
}

const SESSION_GOAL_CONTEXT_MARKER = "=== END CONTEXT ===";

/** Compact one-line label for session list rows (strips injected soul/mission blocks). */
export function sessionGoalPreview(goal: string, maxLen = 140): string {
  let text = goal.trim();
  const markerIdx = text.indexOf(SESSION_GOAL_CONTEXT_MARKER);
  if (markerIdx >= 0) {
    text = text.slice(markerIdx + SESSION_GOAL_CONTEXT_MARKER.length).trim();
  }
  text = text.replace(/^=+\s*[^=]+=+\s*/g, "").trim();
  const firstLine = text.split(/\r?\n/).find((line) => line.trim().length > 0)?.trim() ?? text;
  if (firstLine.length <= maxLen) {
    return firstLine;
  }
  return `${firstLine.slice(0, maxLen - 1)}…`;
}

/** Deep-link to read-only supervisor session replay in Ballroom. */
export function supervisorSessionBallroomHref(sessionId: string): string {
  return `/ballroom?supervisor_session=${encodeURIComponent(sessionId)}`;
}

/** Terminal supervisor session — control actions are no-ops. */
export function isTerminalSupervisorSession(status: string): boolean {
  return ["completed", "failed", "stopped", "cancelled", "approved", "rejected"].includes(status);
}

/** Active supervisor session — pause/resume/stop still apply. */
export function isActiveSupervisorSession(status: string): boolean {
  return ["running", "queued", "needs_input", "paused"].includes(status);
}

/** Compact excerpt from the latest supervisor session audit row. */
export function supervisorAuditExcerpt(payload: Record<string, unknown>, maxLen = 120): string | null {
  const parts: string[] = [];
  if (typeof payload.control_action === "string" && payload.control_action.trim()) {
    parts.push(`control: ${payload.control_action.trim()}`);
  }
  if (typeof payload.decision === "string" && payload.decision.trim()) {
    parts.push(`review: ${payload.decision.trim()}`);
  }
  if (typeof payload.sub_agent_role === "string" && payload.sub_agent_role.trim()) {
    parts.push(`retry: ${payload.sub_agent_role.trim()}`);
  }
  if (typeof payload.command_preview === "string" && payload.command_preview.trim()) {
    parts.push(`interact: ${payload.command_preview.trim()}`);
  }
  if (typeof payload.goal_preview === "string" && payload.goal_preview.trim()) {
    parts.push(`create: ${payload.goal_preview.trim()}`);
  }
  if (typeof payload.message === "string" && payload.message.trim()) {
    parts.push(payload.message.trim());
  }
  if (parts.length === 0) {
    return null;
  }
  const joined = parts.join(" · ");
  return joined.length <= maxLen ? joined : `${joined.slice(0, maxLen - 1)}…`;
}

