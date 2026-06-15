"use client";

import { Loader2, Play, RotateCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface CheckpointResumeCtaState {
  enabled: boolean;
  visible: boolean;
  session_id: string;
  session_status: string;
  runtime_mode: string;
  can_resume_from_checkpoint: boolean;
  resume_hint: string;
  last_verified_role: string | null;
  next_resumable_role: string | null;
  verified_steps: number;
  total_steps: number;
  loop_chip: string;
  primary_label: string;
  operator_guidance: string;
}

interface CheckpointResumeCtaStripProps {
  sessionId: string;
  sessionStatus?: string;
  variant?: "inline" | "banner";
  onChanged?: () => void;
}

/** LR1 — Prominent checkpoint resume CTA on supervisor session list. */
export function CheckpointResumeCtaStrip({
  sessionId,
  sessionStatus,
  variant = "banner",
  onChanged,
}: CheckpointResumeCtaStripProps): JSX.Element | null {
  const [state, setState] = useState<CheckpointResumeCtaState | null>(null);
  const [loading, setLoading] = useState(true);
  const [resumeBusy, setResumeBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<CheckpointResumeCtaState>(
        `agents/sessions/${encodeURIComponent(sessionId)}/checkpoint-resume-cta`,
      );
      setState(data);
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!sessionStatus || !["paused", "failed", "needs_input", "running"].includes(sessionStatus)) {
      return;
    }
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load, sessionStatus]);

  async function resumeFromCheckpoint(): Promise<void> {
    setResumeBusy(true);
    try {
      await hivePostJson(`agents/sessions/${encodeURIComponent(sessionId)}/resume-checkpoint`, {});
      toast.success(
        state?.next_resumable_role
          ? `Resumed from checkpoint → ${state.next_resumable_role}`
          : "Session resumed from last verified checkpoint",
      );
      onChanged?.();
      await load();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Checkpoint resume failed");
    } finally {
      setResumeBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-(--qs-text-3)">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Loading checkpoint…
      </div>
    );
  }

  if (!state?.enabled || !state.visible || !state.can_resume_from_checkpoint) {
    return null;
  }

  if (variant === "inline") {
    return (
      <button
        type="button"
        disabled={resumeBusy}
        className="qs-btn qs-btn--green qs-btn--sm gap-1.5"
        data-testid="checkpoint-resume-inline-cta"
        onClick={() => void resumeFromCheckpoint()}
      >
        {resumeBusy ? (
          <RotateCw className="h-3.5 w-3.5 animate-spin" aria-hidden />
        ) : (
          <Play className="h-3.5 w-3.5" aria-hidden />
        )}
        {state.primary_label}
      </button>
    );
  }

  return (
    <div
      className={cn(
        "mt-2 rounded-xl border border-pollen/35 bg-pollen/10 px-3 py-2.5",
        "flex flex-wrap items-center justify-between gap-3",
      )}
      data-testid="checkpoint-resume-cta-strip"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <V4Badge tone="gold">LR1</V4Badge>
          <V4Badge tone="info">{state.loop_chip}</V4Badge>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-pollen">Checkpoint resume</span>
        </div>
        <p className="mt-1 text-xs text-(--qs-text-2)">{state.operator_guidance}</p>
        {state.last_verified_role ? (
          <p className="mt-1 text-[10px] text-(--qs-text-3)">
            Verified: <span className="text-success">{state.last_verified_role}</span>
            {state.next_resumable_role ? (
              <>
                {" "}
                · Continue: <span className="text-pollen">{state.next_resumable_role}</span>
              </>
            ) : null}
          </p>
        ) : null}
      </div>
      <button
        type="button"
        disabled={resumeBusy}
        className="qs-btn qs-btn--green qs-btn--sm shrink-0 gap-1.5 shadow-[0_0_16px_rgba(0,255,136,0.25)]"
        data-testid="checkpoint-resume-primary-cta"
        onClick={() => void resumeFromCheckpoint()}
      >
        {resumeBusy ? (
          <RotateCw className="h-3.5 w-3.5 animate-spin" aria-hidden />
        ) : (
          <Play className="h-3.5 w-3.5" aria-hidden />
        )}
        {state.primary_label}
      </button>
    </div>
  );
}
