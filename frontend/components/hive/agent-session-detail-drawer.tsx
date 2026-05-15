"use client";

import type { JSX } from "react";

import { AgentSessionEventLog } from "@/components/hive/agent-session-event-log";
import { AgentSessionInteractForm } from "@/components/hive/agent-session-interact-form";
import type {
  SubAgentSessionRow,
  SupervisorSessionEventRow,
  SupervisorSessionRow,
} from "@/lib/hive-types";

interface AgentSessionDetailDrawerProps {
  session: SupervisorSessionRow;
  events: SupervisorSessionEventRow[];
  eventsLoading: boolean;
  onClose: () => void;
  onReview: (decision: "approve" | "reject") => Promise<void>;
  onInteractionAppended: (event: SupervisorSessionEventRow) => void;
}

function SubAgentCard({ sub }: { sub: SubAgentSessionRow }): JSX.Element {
  return (
    <div className="rounded-xl border border-zinc-800 bg-black/30 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-cyan">{sub.role}</p>
        <span className="text-[11px] text-zinc-400">{sub.status}</span>
      </div>
      <p className="mt-2 text-[11px] text-zinc-500">
        tools: {sub.toolset.length ? sub.toolset.join(", ") : "none"}
      </p>
      {sub.last_output ? <p className="mt-2 text-xs text-zinc-200">{sub.last_output}</p> : null}
    </div>
  );
}

export function AgentSessionDetailDrawer({
  session,
  events,
  eventsLoading,
  onClose,
  onReview,
  onInteractionAppended,
}: AgentSessionDetailDrawerProps): JSX.Element {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 p-2 md:p-4">
      <div className="flex h-full w-full max-w-3xl flex-col rounded-2xl border border-cyan/30 bg-[#080a12] p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">Session detail</h3>
            <p className="mt-1 text-xs text-zinc-400">
              {session.runtime_mode} · {session.status}
            </p>
            <p className="mt-2 text-sm text-zinc-200">{session.goal}</p>
          </div>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="qs-btn qs-btn--green qs-btn--sm" onClick={() => void onReview("approve")}>
            Approve
          </button>
          <button type="button" className="qs-btn qs-btn--danger qs-btn--sm" onClick={() => void onReview("reject")}>
            Reject
          </button>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
              Sub-agents
            </p>
            <div className="space-y-2">
              {session.sub_agents.map((sub) => (
                <SubAgentCard key={sub.id} sub={sub} />
              ))}
            </div>
          </div>
          <div className="space-y-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
              Session timeline
            </p>
            <AgentSessionEventLog events={events} loading={eventsLoading} />
          </div>
        </div>

        <div className="mt-4">
          <AgentSessionInteractForm
            sessionId={session.id}
            onInteractionAppended={onInteractionAppended}
          />
        </div>
      </div>
    </div>
  );
}

