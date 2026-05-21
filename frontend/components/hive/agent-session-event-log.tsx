"use client";

import type { JSX } from "react";

import type { SupervisorSessionEventRow } from "@/lib/hive-types";

interface AgentSessionEventLogProps {
  events: SupervisorSessionEventRow[];
  loading: boolean;
}

export function AgentSessionEventLog({ events, loading }: AgentSessionEventLogProps): JSX.Element {
  const rows = Array.isArray(events) ? events : [];
  if (loading) {
    return <p className="text-xs text-(--qs-text-3)">Loading session timeline…</p>;
  }
  if (rows.length === 0) {
    return <p className="text-xs text-(--qs-text-3)">No timeline events yet.</p>;
  }
  return (
    <div className="v4-event-log max-h-72 space-y-2 overflow-y-auto p-3">
      {rows.map((event) => (
        <div key={event.id} className="v4-learning-feed-row">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-pollen">
                {event.event_type}
              </span>
              <span className="text-[11px] text-(--qs-text-3)">{new Date(event.occurred_at).toLocaleString()}</span>
            </div>
            <p className="mt-1 text-xs text-(--qs-text-2)">{event.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
