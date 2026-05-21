"use client";

import type { JSX } from "react";

import Link from "next/link";
import { useState } from "react";

import { AgentSessionAuditPanel } from "@/components/hive/agent-session-audit-panel";
import { AgentSessionContextHistoryPanel } from "@/components/hive/agent-session-context-history-panel";
import { AgentSessionEventLog } from "@/components/hive/agent-session-event-log";
import { AgentSessionInteractForm } from "@/components/hive/agent-session-interact-form";
import { AgentSessionSharedContextPanel } from "@/components/hive/agent-session-shared-context-panel";
import { SubAgentSessionCard } from "@/components/hive/sub-agent-session-card";
import type {
  SupervisorSessionEventRow,
  SupervisorSessionRow,
} from "@/lib/hive-types";
import { playbookRecipeIdFromContext } from "@/lib/session-playbook-utils";

interface AgentSessionDetailDrawerProps {
  session: SupervisorSessionRow;
  events: SupervisorSessionEventRow[];
  eventsLoading: boolean;
  onClose: () => void;
  onReview: (decision: "approve" | "reject", priorPlaybookRecipeId?: string | null) => Promise<void>;
  onInteractionAppended: (event: SupervisorSessionEventRow) => void;
  onSessionRefresh?: () => void;
}

export function AgentSessionDetailDrawer({
  session,
  events,
  eventsLoading,
  onClose,
  onReview,
  onInteractionAppended,
  onSessionRefresh,
}: AgentSessionDetailDrawerProps): JSX.Element {
  const [auditRefreshNonce, setAuditRefreshNonce] = useState(0);
  const auditRefreshKey = `${session.updated_at}:${auditRefreshNonce}`;
  const playbookRecipeId = playbookRecipeIdFromContext(session.context_summary);

  async function handleReview(decision: "approve" | "reject"): Promise<void> {
    await onReview(decision, playbookRecipeId);
    setAuditRefreshNonce((value) => value + 1);
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 p-2 md:p-4">
      <div className="flex h-full w-full max-w-3xl flex-col rounded-2xl border border-[color:var(--qs-border-2)] bg-[#080a12] p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">Session detail</h3>
            <p className="mt-1 text-xs text-zinc-400">
              {session.runtime_mode} · {session.status}
            </p>
            <p className="mt-2 text-sm text-zinc-200">{session.goal}</p>
            {playbookRecipeId ? (
              <Link href="/recipes" className="mt-2 inline-flex text-xs text-pollen underline">
                Saved as operator playbook
              </Link>
            ) : null}
          </div>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="qs-btn qs-btn--green qs-btn--sm" onClick={() => void handleReview("approve")}>
            Approve
          </button>
          <button type="button" className="qs-btn qs-btn--danger qs-btn--sm" onClick={() => void handleReview("reject")}>
            Reject
          </button>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <AgentSessionSharedContextPanel sessionId={session.id} />
            <AgentSessionContextHistoryPanel sessionId={session.id} refreshKey={auditRefreshKey} />
            <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
              Sub-agents
            </p>
            <div className="space-y-2">
              {(session.sub_agents ?? []).map((sub) => (
                <SubAgentSessionCard
                  key={sub.id}
                  sessionId={session.id}
                  sessionStatus={session.status}
                  sub={sub}
                  events={events}
                  onSessionRefresh={onSessionRefresh}
                />
              ))}
            </div>
          </div>
          <div className="space-y-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
              Session timeline
            </p>
            <AgentSessionEventLog events={events} loading={eventsLoading} />
            <AgentSessionAuditPanel
              sessionId={session.id}
              refreshKey={auditRefreshKey}
              onLiveAudit={() => setAuditRefreshNonce((value) => value + 1)}
            />
          </div>
        </div>

        <div className="mt-4">
          <AgentSessionInteractForm
            sessionId={session.id}
            onInteractionAppended={(event) => {
              onInteractionAppended(event);
              setAuditRefreshNonce((value) => value + 1);
            }}
          />
        </div>
      </div>
    </div>
  );
}

