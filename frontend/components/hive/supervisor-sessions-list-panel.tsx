"use client";

import { ExternalLink, Info, Pause, Play, Trash2 } from "lucide-react";
import Link from "next/link";
import { memo, useEffect, useMemo, useState } from "react";

import { ForagerProgressCell } from "@/components/hive/forager-progress-cell";
import { AgentsPanelSkeleton } from "@/components/hive/agents-panel-skeleton";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import type { SupervisorSessionRow, SupervisorSessionsControlRow } from "@/lib/hive-types";
import {
  extractSessionPatternSkills,
} from "@/lib/session-pattern-skills";
import { playbookRecipeIdFromContext } from "@/lib/session-playbook-utils";
import {
  isActiveSupervisorSession,
  runtimeModeLabel,
  sessionGoalPreview,
  supervisorSessionBallroomHref,
  supervisorSessionProgressDetail,
  supervisorSessionProgressPct,
} from "@/lib/supervisor-session";
import { cn } from "@/lib/utils";

const SESSION_PREVIEW_LIMIT = 3;

type SessionStatusFilter = "all" | "running" | "needs_input" | "completed" | "failed" | "queued";

export interface SupervisorSessionsListPanelProps {
  sessions: SupervisorSessionRow[];
  isLoading: boolean;
  sessionsControl: SupervisorSessionsControlRow | undefined;
  policyBusy: boolean;
  reviewBusy: string | null;
  deleteBusy: string | null;
  clearAllBusy: boolean;
  sessionRuntimeLabel: (session: SupervisorSessionRow) => string;
  onPatchAutoApprove: (enabled: boolean) => Promise<void>;
  onReview: (
    sessionId: string,
    decision: "approve" | "reject",
    priorPlaybookRecipeId: string | null,
  ) => Promise<void>;
  onControl: (sessionId: string, action: "pause" | "resume" | "stop") => Promise<void>;
  onDelete: (sessionId: string) => Promise<void>;
  onClearAll: (targets: SupervisorSessionRow[]) => Promise<void>;
  onReport: (sessionId: string) => void;
  onPrepareFirst?: () => void;
}

function shortSessionId(id: string): string {
  const tail = id.replace(/-/g, "").slice(-4).toUpperCase();
  return `S-${tail}`;
}

function sessionStatusBadgeTone(status: string): V4BadgeTone {
  if (status === "running") return "info";
  if (status === "needs_input") return "warn";
  if (status === "completed" || status === "approved") return "ok";
  return "gold";
}

function SessionSkillBadge({ slug }: { slug: string }): JSX.Element {
  return (
    <span className="inline-flex max-w-full items-center rounded-md border border-pollen/45 bg-pollen/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-pollen">
      {slug}
    </span>
  );
}

function SupervisorSessionsListPanelInner({
  sessions,
  isLoading,
  sessionsControl,
  policyBusy,
  reviewBusy,
  deleteBusy,
  clearAllBusy,
  sessionRuntimeLabel,
  onPatchAutoApprove,
  onReview,
  onControl,
  onDelete,
  onClearAll,
  onReport,
  onPrepareFirst,
}: SupervisorSessionsListPanelProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<SessionStatusFilter>("all");
  const [showAllSessions, setShowAllSessions] = useState(false);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sessions.filter((session) => {
      if (statusFilter !== "all" && session.status !== statusFilter) {
        return false;
      }
      if (!q) return true;
      return (
        session.goal.toLowerCase().includes(q) ||
        session.status.toLowerCase().includes(q) ||
        session.runtime_mode.toLowerCase().includes(q)
      );
    });
  }, [query, sessions, statusFilter]);

  const visibleRows = useMemo(() => {
    if (showAllSessions) {
      return filteredRows;
    }
    return filteredRows.slice(0, SESSION_PREVIEW_LIMIT);
  }, [filteredRows, showAllSessions]);

  const hiddenRowCount = Math.max(0, filteredRows.length - SESSION_PREVIEW_LIMIT);
  const needsInputCount = sessions.filter((row) => row.status === "needs_input").length;
  const runningCount = sessions.filter((row) => row.status === "running").length;

  useEffect(() => {
    setShowAllSessions(false);
  }, [query, statusFilter, sessions.length]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
        <input
          className="qs-input min-w-0 flex-1"
          placeholder="Filter sessions by goal / status / runtime…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label
          className="flex shrink-0 items-center justify-between gap-2 rounded-lg border border-pollen/35 bg-black/25 px-3 py-2 text-xs text-(--qs-text-2) md:min-w-[11.5rem]"
          title="Auto approve approves needs_input sessions automatically. Critical actions stay manual."
        >
          <span className="whitespace-nowrap font-medium lowercase">
            {sessionsControl?.auto_approve_enabled ? "auto approve" : "manual"}
          </span>
          <HiveSwitch
            checked={Boolean(sessionsControl?.auto_approve_enabled)}
            disabled={policyBusy}
            aria-label="Toggle auto approve for supervisor sessions"
            onCheckedChange={(checked) => void onPatchAutoApprove(checked)}
          />
        </label>
        <QsSelect
          className="w-full min-w-0 md:w-40 md:shrink-0"
          value={statusFilter}
          onValueChange={(next) => setStatusFilter(next as SessionStatusFilter)}
          options={[
            { value: "all", label: "all statuses" },
            { value: "running", label: "running" },
            { value: "needs_input", label: "needs_input" },
            { value: "queued", label: "queued" },
            { value: "completed", label: "completed" },
            { value: "failed", label: "failed" },
          ]}
        />
      </div>

      {sessionsControl?.auto_approve_enabled ? (
        <p className="text-xs text-pollen">
          Auto approve is ON — eligible sessions leave the queue automatically. Billing and live PR stay manual.
        </p>
      ) : null}

      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
            Sessions
            {!isLoading && filteredRows.length > 0 ? (
              <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                ({filteredRows.length})
              </span>
            ) : null}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {runningCount > 0 ? <V4Badge tone="info">{runningCount} running</V4Badge> : null}
            {needsInputCount > 0 ? <V4Badge tone="gold">{needsInputCount} needs input</V4Badge> : null}
          </div>
        </div>

        <div className="v4-sessions-list-scroll hive-scrollbar">
          {isLoading ? (
            <AgentsPanelSkeleton rows={3} />
          ) : filteredRows.length === 0 ? (
            <div
              className="rounded-xl border border-dashed border-pollen/35 bg-black/20 px-4 py-6 text-center"
              data-testid="agents-sessions-empty"
            >
              <p className="text-sm text-(--qs-text-2)">
                {sessions.length === 0
                  ? "No supervisor sessions yet."
                  : "No sessions match this filter."}
              </p>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                {sessions.length === 0
                  ? "Describe a goal above and spawn your first dynamic session."
                  : "Clear the filter or pick another status."}
              </p>
              {sessions.length === 0 && onPrepareFirst ? (
                <button type="button" className="qs-btn qs-btn--primary qs-btn--sm mt-4" onClick={onPrepareFirst}>
                  Prepare first session
                </button>
              ) : sessions.length > 0 ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm mt-4"
                  onClick={() => {
                    setQuery("");
                    setStatusFilter("all");
                  }}
                >
                  Reset filters
                </button>
              ) : null}
            </div>
          ) : (
            visibleRows.map((session) => {
              const patternSnapshot = extractSessionPatternSkills(session);
              const skills = patternSnapshot.allSkills.slice(0, 8);
              const roles = [...new Set((session.sub_agents ?? []).map((row) => row.role))].slice(0, 6);
              const routeTags = [
                runtimeModeLabel(session.runtime_mode),
                session.status.replaceAll("_", " "),
                ...(sessionsControl?.auto_approve_enabled ? ["auto-approve"] : ["manual-approve"]),
              ];
              const progressPct = supervisorSessionProgressPct(session);
              const playbookId = playbookRecipeIdFromContext(session.context_summary);

              return (
                <div key={session.id} className="v4-session-row v4-session-row--pollen">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                        {shortSessionId(session.id)}
                      </span>
                      <V4Badge tone={sessionStatusBadgeTone(session.status)}>
                        {session.status.replaceAll("_", " ")}
                      </V4Badge>
                      <V4Badge tone="purple">{runtimeModeLabel(session.runtime_mode)}</V4Badge>
                      {playbookId ? (
                        <Link href="/recipes">
                          <V4Badge tone="gold">playbook</V4Badge>
                        </Link>
                      ) : null}
                    </div>
                    <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={session.goal}>
                      {sessionGoalPreview(session.goal)}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">
                      {(session.sub_agents ?? []).length} sub-agent
                      {(session.sub_agents ?? []).length === 1 ? "" : "s"}
                      {roles.length > 0 ? ` · ${roles.join(", ")}` : ""}
                    </p>

                    <div className="mt-2 space-y-1.5" data-testid="supervisor-session-pattern-skills">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                          Source routes
                        </p>
                        <V4Badge tone="gold">
                          {patternSnapshot.patterns?.router_version?.includes("llm") ? "llm-router" : "heuristic-v1"}
                        </V4Badge>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {routeTags.map((tag) => (
                          <V4Badge key={`${session.id}-route-${tag}`} tone="info">
                            {tag}
                          </V4Badge>
                        ))}
                      </div>
                      {skills.length > 0 ? (
                        <div className="space-y-1">
                          <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">
                            Node routes
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {skills.map((slug) => (
                              <SessionSkillBadge key={`${session.id}-${slug}`} slug={slug} />
                            ))}
                          </div>
                        </div>
                      ) : null}
                      <ForagerProgressCell
                        pct={progressPct}
                        detail={supervisorSessionProgressDetail(session, sessionRuntimeLabel(session))}
                        href={supervisorSessionBallroomHref(session.id)}
                      />
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <span className="text-xs text-(--qs-text-3)">
                      {sessionRuntimeLabel(session)} · {(session.sub_agents ?? []).length} agents
                    </span>
                    <Link href={supervisorSessionBallroomHref(session.id)} className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5">
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                      Ballroom
                    </Link>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                      onClick={() => onReport(session.id)}
                    >
                      <Info className="h-3.5 w-3.5" aria-hidden />
                      Info
                    </button>
                    {isActiveSupervisorSession(session.status) ? (
                      <>
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                          onClick={() => void onControl(session.id, "pause")}
                        >
                          <Pause className="h-3.5 w-3.5" aria-hidden />
                          Pause
                        </button>
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                          onClick={() => void onControl(session.id, "resume")}
                        >
                          <Play className="h-3.5 w-3.5" aria-hidden />
                          Resume
                        </button>
                        <button
                          type="button"
                          className="qs-btn qs-btn--danger qs-btn--sm"
                          onClick={() => void onControl(session.id, "stop")}
                        >
                          Stop
                        </button>
                      </>
                    ) : null}
                    <button
                      type="button"
                      className={cn(
                        "qs-btn qs-btn--danger qs-btn--sm gap-1.5",
                        deleteBusy === session.id && "opacity-60",
                      )}
                      disabled={deleteBusy === session.id}
                      onClick={() => void onDelete(session.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      Delete
                    </button>
                    {session.status === "needs_input" ? (
                      <>
                        <button
                          type="button"
                          className="qs-btn qs-btn--green qs-btn--sm"
                          disabled={reviewBusy === session.id}
                          onClick={() => void onReview(session.id, "approve", playbookId)}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          className="qs-btn qs-btn--danger qs-btn--sm"
                          disabled={reviewBusy === session.id}
                          onClick={() => void onReview(session.id, "reject", playbookId)}
                        >
                          Reject
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {hiddenRowCount > 0 && !showAllSessions ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            disabled={clearAllBusy || deleteBusy !== null}
            onClick={() => setShowAllSessions(true)}
          >
            Show all ({filteredRows.length})
          </button>
        ) : null}
        {showAllSessions && filteredRows.length > SESSION_PREVIEW_LIMIT ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            onClick={() => setShowAllSessions(false)}
          >
            Show less
          </button>
        ) : null}

        {filteredRows.length > 0 ? (
          <button
            type="button"
            className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
            disabled={clearAllBusy || isLoading}
            onClick={() => void onClearAll(filteredRows)}
          >
            {clearAllBusy
              ? "Clearing…"
              : query.trim() || statusFilter !== "all"
                ? `Clear filtered (${filteredRows.length})`
                : `Clear all (${filteredRows.length})`}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export const SupervisorSessionsListPanel = memo(SupervisorSessionsListPanelInner);
