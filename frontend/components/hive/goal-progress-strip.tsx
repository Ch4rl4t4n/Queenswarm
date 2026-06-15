"use client";

import Link from "next/link";

import { V4Badge } from "@/components/ui/v4";
import type { TaskGoalProgressRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface GoalProgressStripProps {
  progress: TaskGoalProgressRow | null | undefined;
}

function phaseClass(status: TaskGoalProgressRow["phases"][number]["status"]): string {
  if (status === "done") {
    return "bg-[#00FF88]/80";
  }
  if (status === "active") {
    return "bg-cyan animate-pulse";
  }
  return "bg-zinc-700";
}

/** AL3 — Goal progress strip for Mission Kanban lineage drawer. */
export function GoalProgressStrip({ progress }: GoalProgressStripProps): JSX.Element | null {
  if (!progress?.enabled || !progress.visible) {
    return null;
  }

  return (
    <section
      id="goal-progress-strip"
      className="rounded-xl border border-cyan/25 bg-cyan/5 p-3"
      aria-label="Goal progress"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
          Goal progress
        </span>
        <V4Badge tone="info">{progress.loop_chip}</V4Badge>
        <span className="font-mono text-xs text-cyan">{progress.progress_pct}%</span>
        {progress.session_status === "needs_input" ? <V4Badge tone="warn">Needs input</V4Badge> : null}
      </div>

      <p className="mt-1 text-sm font-medium text-(--qs-text)">{progress.headline}</p>
      <p className="mt-1 text-xs text-(--qs-text-2)">{progress.goal_preview}</p>

      {progress.durable_steps_total > 0 ? (
        <p className="mt-1 font-mono text-[10px] text-(--qs-text-3)">
          Durable steps {progress.durable_steps_done}/{progress.durable_steps_total}
        </p>
      ) : null}

      {progress.phases.length > 0 ? (
        <div className="mt-3 space-y-2">
          <div className="flex gap-1">
            {progress.phases.map((phase) => (
              <div
                key={phase.phase_id}
                className={cn("h-1.5 flex-1 rounded-full", phaseClass(phase.status))}
                title={`${phase.label} · ${phase.status}`}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-(--qs-text-3)">
            {progress.phases.map((phase) => (
              <span
                key={`${phase.phase_id}-label`}
                className={cn(phase.phase_id === progress.current_phase ? "text-cyan" : "")}
              >
                {phase.label}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-zinc-800">
          <div className="h-full rounded-full bg-pollen" style={{ width: `${progress.progress_pct}%` }} />
        </div>
      )}

      {progress.session_href ? (
        <Link href={progress.session_href} className="mt-3 inline-flex text-xs text-cyan hover:underline">
          Open supervisor session
        </Link>
      ) : null}
    </section>
  );
}
