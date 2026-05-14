"use client";

import type { JSX } from "react";

import type { SupervisorSessionEventRow } from "@/lib/hive-types";

interface AgentSessionEventLogProps {
  events: SupervisorSessionEventRow[];
  loading: boolean;
}

export function AgentSessionEventLog({ events, loading }: AgentSessionEventLogProps): JSX.Element {
  if (loading) {
    return <p className="text-xs text-zinc-500">Loading session timeline...</p>;
  }
  if (events.length === 0) {
    return <p className="text-xs text-zinc-500">No timeline events yet.</p>;
  }
  return (
    <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-cyan/20 bg-black/20 p-3">
      {events.map((event) => (
        <div key={event.id} className="rounded-lg border border-zinc-800 bg-black/20 px-3 py-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-cyan">
              {event.event_type}
            </span>
            <span className="text-[11px] text-zinc-500">{new Date(event.occurred_at).toLocaleString()}</span>
          </div>
          <p className="mt-1 text-xs text-zinc-200">{event.message}</p>
        </div>
      ))}
    </div>
  );
}

