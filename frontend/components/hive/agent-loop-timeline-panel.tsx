"use client";

import { CheckCircle2, Circle, Loader2, Target } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export type AgentLoopPhaseStatus = "pending" | "active" | "done";
export type AgentLoopPhaseId = "goal" | "plan" | "tool" | "verify";

export interface AgentLoopPhaseState {
  phase_id: AgentLoopPhaseId;
  label: string;
  status: AgentLoopPhaseStatus;
  summary: string;
  event_count: number;
  latest_at: string | null;
  highlights: string[];
}

export interface AgentLoopTimelineState {
  enabled: boolean;
  session_id: string;
  session_status: string;
  current_phase: AgentLoopPhaseId;
  progress_pct: number;
  loop_chip: string;
  phases: AgentLoopPhaseState[];
}

interface AgentLoopTimelinePanelProps {
  sessionId: string;
  sessionStatus?: string;
}

function phaseTone(status: AgentLoopPhaseStatus): string {
  if (status === "done") {
    return "border-[#00FF88]/35 bg-[#00FF88]/5 text-[#00FF88]";
  }
  if (status === "active") {
    return "border-cyan/40 bg-cyan/5 text-cyan";
  }
  return "border-(--qs-border) bg-black/20 text-(--qs-text-3)";
}

function PhaseIcon({ status }: { status: AgentLoopPhaseStatus }): JSX.Element {
  if (status === "done") {
    return <CheckCircle2 className="size-4 shrink-0" aria-hidden />;
  }
  if (status === "active") {
    return <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden />;
  }
  return <Circle className="size-4 shrink-0 opacity-50" aria-hidden />;
}

/** AL1/LOOP3 — Goal → Plan → Tool → Verify strip for session drawer. */
export function AgentLoopTimelinePanel({
  sessionId,
  sessionStatus,
}: AgentLoopTimelinePanelProps): JSX.Element | null {
  const [state, setState] = useState<AgentLoopTimelineState | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await hiveGet<AgentLoopTimelineState>(
        `agents/sessions/${encodeURIComponent(sessionId)}/loop-timeline`,
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
    if (!sessionStatus || !["running", "queued", "needs_input"].includes(sessionStatus)) {
      return;
    }
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load, sessionStatus]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-(--qs-text-3)">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        Loading agent loop timeline…
      </div>
    );
  }

  if (!state?.enabled || state.phases.length === 0) {
    return null;
  }

  return (
    <V4Card className="border-cyan/20 p-3" id="agent-loop-timeline">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Target className="size-4 text-pollen" aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Agent loop</span>
        <V4Badge tone="info">{state.loop_chip}</V4Badge>
        <span className="font-mono text-xs text-cyan">{state.progress_pct}%</span>
      </div>

      <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {state.phases.map((phase) => (
          <li
            key={phase.phase_id}
            className={cn(
              "rounded-lg border px-3 py-2",
              phaseTone(phase.status),
              phase.phase_id === state.current_phase && phase.status !== "done" ? "ring-1 ring-cyan/30" : "",
            )}
          >
            <div className="flex items-center gap-2">
              <PhaseIcon status={phase.status} />
              <span className="text-xs font-semibold uppercase tracking-wide">{phase.label}</span>
              {phase.status === "active" ? <V4Badge tone="info">Now</V4Badge> : null}
            </div>
            <p className="mt-1.5 text-xs text-(--qs-text-2)">{phase.summary}</p>
            {phase.highlights.length > 0 ? (
              <ul className="mt-1.5 space-y-0.5 text-[10px] text-(--qs-text-3)">
                {phase.highlights.slice(0, 2).map((line) => (
                  <li key={line} className="truncate">
                    {line}
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ol>
    </V4Card>
  );
}
