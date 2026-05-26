"use client";

import type { JSX } from "react";

import { useMemo, useState } from "react";
import { RotateCw } from "lucide-react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { SubAgentJobDetail } from "@/components/hive/sub-agent-job-detail";
import { SubAgentStepTimeline } from "@/components/hive/sub-agent-step-timeline";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { SubAgentSessionRow, SupervisorSessionEventRow } from "@/lib/hive-types";
import { isSubAgentRetryable, parseSubAgentShortMemory } from "@/lib/supervisor-session";
import { cn } from "@/lib/utils";

interface SubAgentSessionCardProps {
  sessionId: string;
  sessionStatus: string;
  sub: SubAgentSessionRow;
  events?: SupervisorSessionEventRow[];
  onSessionRefresh?: () => void;
  showFullOutput?: boolean;
}

function manifestTitle(entry: Record<string, unknown>): string {
  const slug = entry.slug ?? entry.id;
  if (typeof slug === "string" && slug.trim()) {
    return slug;
  }
  const title = entry.title;
  if (typeof title === "string" && title.trim()) {
    return title;
  }
  return "skill";
}

export function SubAgentSessionCard({
  sessionId,
  sessionStatus,
  sub,
  events = [],
  onSessionRefresh,
  showFullOutput = false,
}: SubAgentSessionCardProps): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const [retryBusy, setRetryBusy] = useState(false);
  const memory = useMemo(() => parseSubAgentShortMemory(sub.short_memory ?? {}), [sub.short_memory]);
  const canRetry = isSubAgentRetryable(sub.status, sessionStatus);

  async function retryStep(): Promise<void> {
    setRetryBusy(true);
    try {
      await hivePostJson(
        `agents/sessions/${encodeURIComponent(sessionId)}/sub-agents/${encodeURIComponent(sub.id)}/retry`,
        {},
      );
      toast.success(`${sub.role} step retry queued`);
      onSessionRefresh?.();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Retry failed");
    } finally {
      setRetryBusy(false);
    }
  }

  return (
    <article className="rounded-xl border border-zinc-800 bg-black/30 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-cyan">{sub.role}</p>
        <div className="flex items-center gap-2">
          {canRetry ? (
            <button
              type="button"
              disabled={retryBusy}
              className="qs-btn qs-btn--ghost qs-btn--sm gap-1 text-[10px]"
              onClick={() => void retryStep()}
            >
              <RotateCw className={cn("h-3 w-3", retryBusy && "animate-spin")} aria-hidden />
              Retry
            </button>
          ) : null}
          <V4Badge tone={sub.status === "completed" ? "ok" : sub.status === "failed" ? "err" : "info"}>
            {sub.status}
          </V4Badge>
        </div>
      </div>

      <p className="mt-2 text-[11px] text-zinc-500">
        tools: {(sub.toolset ?? []).length ? (sub.toolset ?? []).join(", ") : "none"} · {sub.runtime_mode}
      </p>

      {memory.subGoal ? (
        <p className="mt-2 text-xs text-zinc-300">
          <span className="text-[10px] uppercase tracking-wide text-zinc-600">sub-goal · </span>
          {memory.subGoal}
        </p>
      ) : null}

      {memory.skills.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {memory.skills.map((skill) => (
            <span
              key={skill}
              className="rounded-full border border-pollen/30 bg-pollen/10 px-2 py-0.5 font-mono text-[10px] text-pollen"
            >
              {skill}
            </span>
          ))}
        </div>
      ) : null}

      {memory.skillManifest.length > 0 ? (
        <ul className="mt-2 space-y-1 text-[10px] text-zinc-500">
          {memory.skillManifest.slice(0, 3).map((entry, index) => (
            <li key={`${manifestTitle(entry)}-${index}`} className="truncate">
              {manifestTitle(entry)}
              {typeof entry.version === "string" ? ` · v${entry.version}` : ""}
            </li>
          ))}
        </ul>
      ) : null}

      {memory.promptPreview ? (
        <div className="mt-2">
          <button
            type="button"
            className="text-[10px] uppercase tracking-wide text-cyan hover:text-pollen"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? "Hide skills prompt" : "Show skills prompt"}
          </button>
          {expanded ? (
            <pre className="mt-1 max-h-36 overflow-auto rounded-lg bg-black/40 p-2 font-mono text-[10px] text-zinc-300">
              {typeof sub.short_memory?.skills_prompt_block === "string"
                ? sub.short_memory.skills_prompt_block
                : memory.promptPreview}
            </pre>
          ) : null}
        </div>
      ) : null}

      {sub.last_output ? (
        <p className={cn("mt-2 whitespace-pre-wrap text-xs text-zinc-200", !showFullOutput && (expanded ? "line-clamp-2" : "line-clamp-4"))}>
          {sub.last_output}
        </p>
      ) : null}

      {sub.error_text ? <p className="mt-2 text-xs text-danger">{sub.error_text}</p> : null}

      {events.length > 0 || sub.runtime_mode === "durable" ? (
        <SubAgentStepTimeline
          subAgentId={sub.id}
          runtimeMode={sub.runtime_mode}
          status={sub.status}
          events={events}
        />
      ) : null}

      {sub.runtime_mode === "durable" ? (
        <SubAgentJobDetail
          sessionId={sessionId}
          subAgentId={sub.id}
          celeryTaskId={sub.celery_task_id}
          runtimeMode={sub.runtime_mode}
          subStatus={sub.status}
          selfHealAttempts={sub.self_heal_attempts}
          requeueCount={sub.requeue_count}
        />
      ) : null}
    </article>
  );
}
