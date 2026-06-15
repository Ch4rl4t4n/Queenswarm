"use client";

import { Flag, Loader2, Pause, Play, ShieldCheck, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

export type MidFlightActionId =
  | "pause_loop"
  | "approve_continue"
  | "reject_revise"
  | "resume_session"
  | "resume_checkpoint";

export interface MidFlightCheckpointActionState {
  action_id: MidFlightActionId;
  label: string;
  enabled: boolean;
  variant: "primary" | "secondary" | "danger" | "ghost";
  reason_disabled: string | null;
}

export interface MidFlightCheckpointState {
  enabled: boolean;
  visible: boolean;
  session_id: string;
  session_status: string;
  checkpoint_state: "running" | "paused" | "needs_input" | "closed";
  loop_phase: string | null;
  loop_chip: string | null;
  headline: string;
  operator_guidance: string;
  primary_action_id: MidFlightActionId | null;
  pending_approval: boolean;
  approval_reason: string | null;
  checkpoint: {
    can_resume_from_checkpoint: boolean;
    resume_hint: string;
    last_verified_role: string | null;
    next_resumable_role: string | null;
    verified_steps: number;
    total_steps: number;
  };
  actions: MidFlightCheckpointActionState[];
}

interface MidFlightCheckpointPanelProps {
  sessionId: string;
  sessionStatus?: string;
  variant?: "full" | "compact";
  onChanged?: () => void;
}

function actionIcon(actionId: MidFlightActionId): JSX.Element {
  if (actionId === "pause_loop") {
    return <Pause className="size-3.5" aria-hidden />;
  }
  if (actionId === "approve_continue") {
    return <ShieldCheck className="size-3.5" aria-hidden />;
  }
  if (actionId === "reject_revise") {
    return <XCircle className="size-3.5" aria-hidden />;
  }
  return <Play className="size-3.5" aria-hidden />;
}

function buttonClass(action: MidFlightCheckpointActionState, isPrimary: boolean): string {
  if (!action.enabled) {
    return "qs-btn qs-btn--ghost qs-btn--sm opacity-45";
  }
  if (isPrimary || action.variant === "primary") {
    return "qs-btn qs-btn--primary qs-btn--sm gap-1.5";
  }
  if (action.variant === "danger") {
    return "qs-btn qs-btn--danger qs-btn--sm gap-1.5";
  }
  if (action.variant === "secondary") {
    return "qs-btn qs-btn--ghost qs-btn--sm gap-1.5 border border-cyan/30 text-cyan";
  }
  return "qs-btn qs-btn--ghost qs-btn--sm gap-1.5";
}

/** LOOP4 — Mid-flight checkpoint bar: pause → review → approve → continue. */
export function MidFlightCheckpointPanel({
  sessionId,
  sessionStatus,
  variant = "full",
  onChanged,
}: MidFlightCheckpointPanelProps): JSX.Element | null {
  const [state, setState] = useState<MidFlightCheckpointState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<MidFlightActionId | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<MidFlightCheckpointState>(
        `agents/sessions/${encodeURIComponent(sessionId)}/mid-flight-checkpoint`,
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
    if (!sessionStatus || !["running", "queued", "needs_input", "paused"].includes(sessionStatus)) {
      return;
    }
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load, sessionStatus]);

  const runAction = useCallback(
    async (actionId: MidFlightActionId) => {
      setBusy(actionId);
      try {
        if (actionId === "pause_loop") {
          await hivePostJson(`agents/sessions/${encodeURIComponent(sessionId)}/control`, { action: "pause" });
          toast.success("Loop paused — review mid-flight evidence.");
        } else if (actionId === "resume_session") {
          await hivePostJson(`agents/sessions/${encodeURIComponent(sessionId)}/control`, { action: "resume" });
          toast.success("Session resumed.");
        } else if (actionId === "approve_continue") {
          await hivePostJson(`agents/sessions/${encodeURIComponent(sessionId)}/review`, { decision: "approve" });
          toast.success("Approved — loop continues.");
        } else if (actionId === "reject_revise") {
          await hivePostJson(`agents/sessions/${encodeURIComponent(sessionId)}/review`, { decision: "reject" });
          toast.message("Rejected — revise goal or sub-agent output before retry.");
        } else if (actionId === "resume_checkpoint") {
          await hivePostJson(`agents/sessions/${encodeURIComponent(sessionId)}/resume-checkpoint`, {});
          toast.success("Resumed from last verified checkpoint.");
        }
        await load();
        onChanged?.();
      } catch (err) {
        toast.error(err instanceof HiveApiError ? err.message : "Checkpoint action failed");
      } finally {
        setBusy(null);
      }
    },
    [load, onChanged, sessionId],
  );

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-(--qs-text-3)">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Loading mid-flight checkpoint…
      </div>
    );
  }

  if (!state?.enabled || !state.visible) {
    return null;
  }

  const primary = state.actions.find((action) => action.action_id === state.primary_action_id);
  const secondary = state.actions.filter((action) => action.action_id !== state.primary_action_id);

  if (variant === "compact") {
    return (
      <div
        id="mid-flight-checkpoint-compact"
        className="mt-3 rounded-xl border border-[#FF00AA]/35 bg-[#FF00AA]/5 p-3"
      >
        <div className="flex flex-wrap items-center gap-2">
          <Flag className="size-4 text-[#FF00AA]" aria-hidden />
          <span className="text-xs font-semibold text-(--qs-text)">{state.headline}</span>
          {state.loop_chip ? <V4Badge tone="info">{state.loop_chip}</V4Badge> : null}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {primary ? (
            <button
              type="button"
              className={buttonClass(primary, true)}
              disabled={!primary.enabled || busy !== null}
              onClick={() => void runAction(primary.action_id)}
            >
              {busy === primary.action_id ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
              ) : (
                actionIcon(primary.action_id)
              )}
              {primary.label}
            </button>
          ) : null}
          {secondary
            .filter((action) => action.enabled)
            .slice(0, 2)
            .map((action) => (
              <button
                key={action.action_id}
                type="button"
                className={buttonClass(action, false)}
                disabled={busy !== null}
                onClick={() => void runAction(action.action_id)}
              >
                {busy === action.action_id ? (
                  <Loader2 className="size-3.5 animate-spin" aria-hidden />
                ) : (
                  actionIcon(action.action_id)
                )}
                {action.label}
              </button>
            ))}
        </div>
      </div>
    );
  }

  return (
    <V4Card
      className={cn(
        "border-[#FF00AA]/35 bg-[#FF00AA]/5 p-3",
        state.checkpoint_state === "needs_input" ? "ring-1 ring-[#FF00AA]/25" : "",
      )}
      id="mid-flight-checkpoint"
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Flag className="size-4 text-[#FF00AA]" aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Mid-flight checkpoint</span>
        <V4Badge tone="warn">{state.checkpoint_state.replace("_", " ")}</V4Badge>
        {state.loop_chip ? <V4Badge tone="info">{state.loop_chip}</V4Badge> : null}
      </div>

      <h3 className="text-sm font-semibold text-(--qs-text)">{state.headline}</h3>
      <p className="mt-1 text-xs text-(--qs-text-2)">{state.operator_guidance}</p>

      {state.approval_reason ? (
        <p className="mt-2 rounded-lg border border-[#FFB800]/30 bg-[#FFB800]/5 px-3 py-2 text-xs text-[#FFB800]">
          {state.approval_reason}
        </p>
      ) : null}

      {state.checkpoint.total_steps > 0 ? (
        <p className="mt-2 font-mono text-[10px] text-(--qs-text-3)">
          Checkpoints {state.checkpoint.verified_steps}/{state.checkpoint.total_steps}
          {state.checkpoint.last_verified_role ? ` · last verified: ${state.checkpoint.last_verified_role}` : ""}
          {state.checkpoint.next_resumable_role ? ` → next: ${state.checkpoint.next_resumable_role}` : ""}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2">
        {primary ? (
          <button
            type="button"
            className={buttonClass(primary, true)}
            disabled={!primary.enabled || busy !== null}
            onClick={() => void runAction(primary.action_id)}
          >
            {busy === primary.action_id ? (
              <Loader2 className="size-3.5 animate-spin" aria-hidden />
            ) : (
              actionIcon(primary.action_id)
            )}
            {primary.label}
          </button>
        ) : null}
        {secondary.map((action) => (
          <button
            key={action.action_id}
            type="button"
            className={buttonClass(action, false)}
            disabled={!action.enabled || busy !== null}
            title={action.reason_disabled ?? undefined}
            onClick={() => void runAction(action.action_id)}
          >
            {busy === action.action_id ? (
              <Loader2 className="size-3.5 animate-spin" aria-hidden />
            ) : (
              actionIcon(action.action_id)
            )}
            {action.label}
          </button>
        ))}
      </div>
    </V4Card>
  );
}
