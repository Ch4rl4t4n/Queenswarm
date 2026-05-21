"use client";

import type { JSX } from "react";

import { Loader2Icon } from "lucide-react";
import useSWR from "swr";

import { V4Badge } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import type { SubAgentJobStatusRow } from "@/lib/hive-types";
import { celeryJobStateTone } from "@/lib/supervisor-session";

interface SubAgentJobDetailProps {
  sessionId: string;
  subAgentId: string;
  celeryTaskId?: string | null;
  runtimeMode: string;
  subStatus: string;
  selfHealAttempts?: number | null;
  requeueCount?: number | null;
}

function shortTaskId(taskId: string): string {
  const trimmed = taskId.trim();
  if (trimmed.length <= 14) return trimmed;
  return `${trimmed.slice(0, 8)}…${trimmed.slice(-4)}`;
}

function formatEnqueuedAt(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString();
}

/** Poll Celery AsyncResult for one durable sub-agent step. */
export function SubAgentJobDetail({
  sessionId,
  subAgentId,
  celeryTaskId,
  runtimeMode,
  subStatus,
  selfHealAttempts,
  requeueCount,
}: SubAgentJobDetailProps): JSX.Element | null {
  const isDurable = runtimeMode.trim().toLowerCase() === "durable";
  const pollOptions = useSwrVisiblePollOptions(4_000);
  const activeSub =
    subStatus === "pending" || subStatus === "queued" || subStatus === "running";

  const { data, error, isLoading } = useSWR<SubAgentJobStatusRow>(
    isDurable ? `hive/sub-agent-job:${sessionId}:${subAgentId}` : null,
    () =>
      hiveGet<SubAgentJobStatusRow>(
        `agents/sessions/${encodeURIComponent(sessionId)}/sub-agents/${encodeURIComponent(subAgentId)}/job`,
      ),
    {
      ...pollOptions,
      refreshInterval: isDurable && activeSub ? pollOptions.refreshInterval : 0,
    },
  );

  if (!isDurable) return null;

  const state = data?.state ?? (celeryTaskId ? "PENDING" : "NOT_ENQUEUED");
  const taskId = data?.celery_task_id ?? celeryTaskId ?? null;
  const healAttempts = data?.self_heal_attempts ?? selfHealAttempts ?? null;

  return (
    <div className="mt-2 rounded-lg border border-zinc-800/80 bg-black/25 p-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[10px] uppercase tracking-wide text-zinc-600">Celery job</p>
        <V4Badge tone={celeryJobStateTone(state)}>{state}</V4Badge>
      </div>

      {isLoading && !data ? (
        <div className="mt-2 flex items-center gap-2 text-[10px] text-zinc-500">
          <Loader2Icon className="h-3 w-3 animate-spin text-pollen" aria-hidden />
          Resolving job status…
        </div>
      ) : null}

      {taskId ? (
        <p className="mt-2 font-mono text-[10px] text-cyan" title={taskId}>
          {shortTaskId(taskId)}
        </p>
      ) : (
        <p className="mt-2 text-[10px] text-zinc-500">No Celery task id yet — job may still be enqueueing.</p>
      )}

      <p className="mt-1 text-[10px] text-zinc-600">hive.supervisor_sub_agent_step</p>

      {formatEnqueuedAt(data?.enqueued_at ?? null) ? (
        <p className="mt-1 text-[10px] text-zinc-500">enqueued {formatEnqueuedAt(data?.enqueued_at ?? null)}</p>
      ) : null}

      {typeof healAttempts === "number" ? (
        <p className="mt-1 text-[10px] text-zinc-500">self-heal attempts {healAttempts}</p>
      ) : null}

      {typeof requeueCount === "number" && requeueCount > 0 ? (
        <p className="mt-1 text-[10px] text-pollen">operator requeues {requeueCount}</p>
      ) : null}

      {data?.result && typeof data.result.reason === "string" ? (
        <p className="mt-2 text-[10px] text-zinc-400">result: {data.result.reason}</p>
      ) : null}

      {data?.error ? <p className="mt-2 text-[10px] text-danger">{data.error}</p> : null}
      {error ? <p className="mt-2 text-[10px] text-danger">Job poll failed</p> : null}
    </div>
  );
}
