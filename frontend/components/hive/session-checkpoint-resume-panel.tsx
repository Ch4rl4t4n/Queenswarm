"use client";

import type { JSX } from "react";

import { CheckCircle2, Play, RotateCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { SupervisorSessionRow } from "@/lib/hive-types";
import {
  buildSessionCheckpointSnapshot,
  type SessionCheckpointSnapshotView,
} from "@/lib/session-checkpoint-utils";
import { cn } from "@/lib/utils";

interface SessionCheckpointResumePanelProps {
  session: SupervisorSessionRow;
  onSessionUpdated?: () => void;
  compact?: boolean;
}

export function SessionCheckpointResumePanel({
  session,
  onSessionUpdated,
  compact = false,
}: SessionCheckpointResumePanelProps): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<SessionCheckpointSnapshotView | null>(null);
  const [loading, setLoading] = useState(false);
  const [resumeBusy, setResumeBusy] = useState(false);

  const localSnapshot = useMemo(() => buildSessionCheckpointSnapshot(session), [session]);

  const refreshSnapshot = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const remote = await hiveGet<SessionCheckpointSnapshotView>(
        `agents/sessions/${encodeURIComponent(session.id)}/checkpoints`,
      );
      setSnapshot(remote);
    } catch {
      setSnapshot(localSnapshot);
    } finally {
      setLoading(false);
    }
  }, [localSnapshot, session.id]);

  useEffect(() => {
    void refreshSnapshot();
  }, [refreshSnapshot, session.updated_at]);

  const view = snapshot ?? localSnapshot;
  if (!view.steps.length && !view.can_resume_from_checkpoint) {
    return null;
  }

  async function resumeFromCheckpoint(): Promise<void> {
    setResumeBusy(true);
    try {
      await hivePostJson(`agents/sessions/${encodeURIComponent(session.id)}/resume-checkpoint`, {});
      toast.success(
        view.next_resumable_role
          ? `Resumed from checkpoint → ${view.next_resumable_role}`
          : "Session resumed from last verified checkpoint",
      );
      onSessionUpdated?.();
      await refreshSnapshot();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Checkpoint resume failed");
    } finally {
      setResumeBusy(false);
    }
  }

  return (
    <section
      className={cn(
        "rounded-xl border border-cyan/25 bg-cyan/5",
        compact ? "p-3" : "p-4",
      )}
      data-testid="session-checkpoint-resume-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-cyan">Checkpoint resume</p>
          <p className="mt-1 text-xs text-(--qs-text-2)">{view.resume_hint}</p>
          {view.last_verified_role ? (
            <p className="mt-1 text-[10px] text-(--qs-text-3)">
              Last verified: <span className="text-success">{view.last_verified_role}</span>
              {view.next_resumable_role ? (
                <>
                  {" "}
                  · Next: <span className="text-pollen">{view.next_resumable_role}</span>
                </>
              ) : null}
            </p>
          ) : null}
        </div>
        {view.can_resume_from_checkpoint ? (
          <button
            type="button"
            disabled={resumeBusy || loading}
            className="qs-btn qs-btn--green qs-btn--sm gap-1.5"
            onClick={() => void resumeFromCheckpoint()}
          >
            {resumeBusy ? (
              <RotateCw className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <Play className="h-3.5 w-3.5" aria-hidden />
            )}
            Resume from checkpoint
          </button>
        ) : null}
      </div>

      {view.steps.length > 0 ? (
        <ol className="mt-3 space-y-2">
          {view.steps.map((step, index) => (
            <li
              key={step.sub_agent_id}
              className={cn(
                "flex items-center justify-between gap-2 rounded-lg border px-2.5 py-2 text-xs",
                step.is_verified_checkpoint
                  ? "border-success/30 bg-success/5"
                  : index === view.last_verified_index + 1 && step.is_resumable
                    ? "border-pollen/40 bg-pollen/5"
                    : "border-zinc-800 bg-black/20",
              )}
            >
              <div className="flex min-w-0 items-center gap-2">
                {step.is_verified_checkpoint ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" aria-hidden />
                ) : (
                  <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center font-mono text-[9px] text-zinc-500">
                    {index + 1}
                  </span>
                )}
                <span className="truncate font-medium text-(--qs-text)">{step.role}</span>
              </div>
              <V4Badge tone={step.is_verified_checkpoint ? "ok" : step.status === "failed" ? "err" : "info"}>
                {step.status.replaceAll("_", " ")}
              </V4Badge>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
