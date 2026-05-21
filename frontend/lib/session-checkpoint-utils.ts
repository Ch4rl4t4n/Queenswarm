/** Checkpoint resume helpers for long-running supervisor sessions. */

import type { SubAgentSessionRow, SupervisorSessionRow } from "@/lib/hive-types";

export interface SessionCheckpointStepView {
  sub_agent_id: string;
  role: string;
  status: string;
  spawn_order: number;
  is_verified_checkpoint: boolean;
  is_resumable: boolean;
}

export interface SessionCheckpointSnapshotView {
  session_id: string;
  session_status: string;
  runtime_mode: string;
  steps: SessionCheckpointStepView[];
  last_verified_index: number;
  last_verified_role: string | null;
  next_resumable_sub_agent_id: string | null;
  next_resumable_role: string | null;
  can_resume_from_checkpoint: boolean;
  resume_hint: string;
}

const RETRYABLE = new Set(["needs_input", "queued", "pending", "failed"]);
const VERIFIED = "completed";

/** Build a client-side checkpoint snapshot from a session row (matches backend semantics). */
export function buildSessionCheckpointSnapshot(session: SupervisorSessionRow): SessionCheckpointSnapshotView {
  const subs = [...(session.sub_agents ?? [])].sort((a, b) => a.spawn_order - b.spawn_order);
  const sessionStatus = session.status.trim().toLowerCase();
  const runtimeMode = session.runtime_mode.trim().toLowerCase();

  let lastVerifiedIndex = -1;
  const steps: SessionCheckpointStepView[] = subs.map((sub, index) => {
    const status = sub.status.trim().toLowerCase();
    const isVerified = status === VERIFIED;
    if (isVerified) {
      lastVerifiedIndex = index;
    }
    return {
      sub_agent_id: sub.id,
      role: sub.role,
      status,
      spawn_order: sub.spawn_order,
      is_verified_checkpoint: isVerified,
      is_resumable: RETRYABLE.has(status),
    };
  });

  let nextResumableSubAgentId: string | null = null;
  let nextResumableRole: string | null = null;
  for (let index = 0; index < subs.length; index += 1) {
    if (index <= lastVerifiedIndex) {
      continue;
    }
    const status = subs[index].status.trim().toLowerCase();
    if (RETRYABLE.has(status)) {
      nextResumableSubAgentId = subs[index].id;
      nextResumableRole = subs[index].role;
      break;
    }
  }

  const hasVerified = lastVerifiedIndex >= 0;
  const hasResumable = nextResumableSubAgentId !== null;
  const hasQueued = subs.some((sub) => {
    const status = sub.status.trim().toLowerCase();
    return status === "queued" || status === "pending";
  });
  const sessionOpen = sessionStatus !== "stopped" && sessionStatus !== "completed";

  const canResume =
    sessionOpen &&
    ((runtimeMode === "durable" && (hasResumable || (sessionStatus === "paused" && hasQueued))) ||
      (runtimeMode === "inprocess" &&
        ["needs_input", "paused", "running"].includes(sessionStatus) &&
        subs.some((sub) => sub.status.trim().toLowerCase() === "needs_input")));

  let resumeHint = "No retryable steps after the last verified checkpoint.";
  if (!sessionOpen) {
    resumeHint = "Session is closed.";
  } else if (canResume && hasVerified && nextResumableRole) {
    resumeHint = `Resume from verified checkpoint after ${steps[lastVerifiedIndex].role} → ${nextResumableRole}.`;
  } else if (canResume && nextResumableRole) {
    resumeHint = `Resume at first step: ${nextResumableRole}.`;
  } else if (canResume) {
    resumeHint = "Resume queued durable steps.";
  }

  return {
    session_id: session.id,
    session_status: sessionStatus,
    runtime_mode: runtimeMode,
    steps,
    last_verified_index: lastVerifiedIndex,
    last_verified_role: hasVerified ? steps[lastVerifiedIndex].role : null,
    next_resumable_sub_agent_id: nextResumableSubAgentId,
    next_resumable_role: nextResumableRole,
    can_resume_from_checkpoint: canResume,
    resume_hint: resumeHint,
  };
}

/** Whether the session list should show checkpoint resume affordance. */
export function sessionShowsCheckpointResume(session: SupervisorSessionRow): boolean {
  const snapshot = buildSessionCheckpointSnapshot(session);
  return snapshot.can_resume_from_checkpoint && (session.status === "paused" || session.status === "failed");
}

/** Count verified checkpoints in spawn order. */
export function verifiedCheckpointCount(subs: SubAgentSessionRow[]): number {
  return subs.filter((sub) => sub.status.trim().toLowerCase() === VERIFIED).length;
}
