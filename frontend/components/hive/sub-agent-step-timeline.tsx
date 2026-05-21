"use client";

import type { JSX } from "react";

import { V4Badge } from "@/components/ui/v4";
import type { SupervisorSessionEventRow } from "@/lib/hive-types";
import {
  filterSubAgentEvents,
  subAgentStepEventLabel,
  subAgentStepEventTone,
} from "@/lib/supervisor-session";

interface SubAgentStepTimelineProps {
  subAgentId: string;
  runtimeMode: string;
  status: string;
  events: SupervisorSessionEventRow[];
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** Per sub-agent Celery / in-process step timeline from session events. */
export function SubAgentStepTimeline({
  subAgentId,
  runtimeMode,
  status,
  events,
}: SubAgentStepTimelineProps): JSX.Element {
  const steps = filterSubAgentEvents(events, subAgentId);
  const isDurable = runtimeMode.trim().toLowerCase() === "durable";
  const isQueued = isDurable && (status === "pending" || status === "queued") && steps.length === 0;

  if (steps.length === 0 && !isQueued) {
    return (
      <p className="mt-2 text-[10px] text-zinc-600">
        No step events yet{isDurable ? " — Celery job may still be queued." : "."}
      </p>
    );
  }

  return (
    <div className="mt-2 space-y-1.5">
      <p className="text-[10px] uppercase tracking-wide text-zinc-600">
        {isDurable ? "Celery step timeline" : "Step timeline"}
      </p>
      {isQueued ? (
        <div className="flex items-center gap-2 rounded-lg border border-pollen/20 bg-pollen/5 px-2 py-1.5">
          <V4Badge tone="gold">queued</V4Badge>
          <span className="text-[10px] text-zinc-400">Waiting for hive.supervisor_sub_agent_step worker</span>
        </div>
      ) : null}
      <ol className="space-y-1">
        {steps.map((step) => (
          <li key={step.id} className="flex items-start gap-2 rounded-lg bg-black/20 px-2 py-1.5">
            <V4Badge tone={subAgentStepEventTone(step.event_type)}>{subAgentStepEventLabel(step.event_type)}</V4Badge>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[10px] text-zinc-400">{step.message}</p>
              {typeof step.payload.runtime_mode === "string" ? (
                <p className="mt-0.5 text-[9px] text-zinc-600">{step.payload.runtime_mode}</p>
              ) : null}
            </div>
            <span className="shrink-0 font-mono text-[9px] text-zinc-600">{formatTime(step.occurred_at)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
