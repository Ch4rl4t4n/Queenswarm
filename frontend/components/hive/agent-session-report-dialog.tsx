"use client";

import type { JSX } from "react";

import { Download, ExternalLink, Info, Loader2Icon, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { AgentSessionEventLog } from "@/components/hive/agent-session-event-log";
import { SubAgentSessionCard } from "@/components/hive/sub-agent-session-card";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { SupervisorSessionEventRow, SupervisorSessionRow } from "@/lib/hive-types";
import { sessionGoalPreview } from "@/lib/supervisor-session";
import { cn } from "@/lib/utils";

interface AgentSessionReportDialogProps {
  sessionId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

async function downloadBlob(blob: Blob, filename: string): Promise<void> {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function shortSessionId(id: string): string {
  return `S-${id.replace(/-/g, "").slice(-4).toUpperCase()}`;
}

/** Operator report — timeline, sub-agent outputs, export bundle. */
export function AgentSessionReportDialog({ sessionId, open, onOpenChange }: AgentSessionReportDialogProps): JSX.Element | null {
  const [session, setSession] = useState<SupervisorSessionRow | null>(null);
  const [events, setEvents] = useState<SupervisorSessionEventRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [exportBusy, setExportBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !sessionId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setSession(null);
    setEvents([]);
    void Promise.all([
      hiveGet<SupervisorSessionRow>(`agents/sessions/${encodeURIComponent(sessionId)}`),
      hiveGet<SupervisorSessionEventRow[]>(`agents/sessions/${encodeURIComponent(sessionId)}/events?limit=200`),
    ])
      .then(([sessionBody, eventBody]) => {
        if (cancelled) {
          return;
        }
        setSession(sessionBody);
        setEvents(Array.isArray(eventBody) ? eventBody : []);
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        toast.error(err instanceof HiveApiError ? err.message : "Session report unavailable");
        onOpenChange(false);
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, onOpenChange, sessionId]);

  const eventsBySubAgent = useMemo(() => {
    const map = new Map<string, SupervisorSessionEventRow[]>();
    for (const event of events) {
      if (!event.sub_agent_session_id) {
        continue;
      }
      const bucket = map.get(event.sub_agent_session_id) ?? [];
      bucket.push(event);
      map.set(event.sub_agent_session_id, bucket);
    }
    return map;
  }, [events]);

  async function exportReport(format: "html" | "markdown" | "pdf"): Promise<void> {
    if (!sessionId) {
      return;
    }
    setExportBusy(format);
    try {
      const res = await fetch(
        `/api/proxy/agents/sessions/${encodeURIComponent(sessionId)}/report/export?format=${format}`,
        { cache: "no-store" },
      );
      if (!res.ok) {
        throw new Error("Report export failed");
      }
      const blob = await res.blob();
      const tail = sessionId.replace(/-/g, "").slice(-8).toUpperCase();
      const ext = format === "markdown" ? "md" : format === "pdf" ? "pdf" : "html";
      await downloadBlob(blob, `session-${tail}-report.${ext}`);
      toast.success(`Report downloaded (${format.toUpperCase()})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report export failed");
    } finally {
      setExportBusy(null);
    }
  }

  if (!open || !sessionId) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-[72] flex items-end justify-center bg-black/75 p-0 sm:items-center sm:p-4"
      onClick={() => onOpenChange(false)}
      role="presentation"
    >
      <div
        className="qs-bubble flex max-h-[min(92dvh,920px)] w-full max-w-3xl flex-col overflow-hidden rounded-t-(--qs-radius-lg) sm:rounded-(--qs-radius-lg)"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-labelledby="session-report-title"
      >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-(--qs-border) px-4 py-4 sm:px-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Info className="h-4 w-4 shrink-0 text-pollen" aria-hidden />
              <h2 id="session-report-title" className="text-lg font-semibold text-(--qs-text)">
                Session report
              </h2>
              <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                {shortSessionId(sessionId)}
              </span>
              {session ? <V4Badge tone={session.status === "completed" ? "ok" : session.status === "failed" ? "err" : "info"}>{session.status}</V4Badge> : null}
            </div>
            {session ? (
              <p className="mt-1 text-sm leading-relaxed text-(--qs-text-2)" title={session.goal}>
                {sessionGoalPreview(session.goal, 240)}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
            aria-label="Close report"
            onClick={() => onOpenChange(false)}
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </header>

        <div className="hive-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-(--qs-text-3)">
              <Loader2Icon className="h-4 w-4 animate-spin text-pollen" aria-hidden />
              Loading session report…
            </div>
          ) : session ? (
            <>
              <section className="qs-bubble-inner space-y-2 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">Summary</p>
                <dl className="grid gap-2 text-xs sm:grid-cols-2">
                  <div>
                    <dt className="text-(--qs-text-4)">Runtime</dt>
                    <dd className="text-(--qs-text)">{session.runtime_mode}</dd>
                  </div>
                  <div>
                    <dt className="text-(--qs-text-4)">Sub-agents</dt>
                    <dd className="text-(--qs-text)">{(session.sub_agents ?? []).length}</dd>
                  </div>
                  <div>
                    <dt className="text-(--qs-text-4)">Started</dt>
                    <dd className="text-(--qs-text)">
                      {session.started_at ? new Date(session.started_at).toLocaleString() : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-(--qs-text-4)">Completed</dt>
                    <dd className="text-(--qs-text)">
                      {session.completed_at ? new Date(session.completed_at).toLocaleString() : "—"}
                    </dd>
                  </div>
                </dl>
                {session.error_text ? (
                  <p className="rounded-(--qs-radius-sm) border border-(--qs-red)/35 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">
                    {session.error_text}
                  </p>
                ) : null}
              </section>

              {(session.sub_agents ?? []).length > 0 ? (
                <section className="space-y-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">Sub-agent outputs</p>
                  <div className="space-y-2">
                    {(session.sub_agents ?? []).map((sub) => (
                      <SubAgentSessionCard
                        key={sub.id}
                        sessionId={session.id}
                        sessionStatus={session.status}
                        sub={sub}
                        events={eventsBySubAgent.get(sub.id) ?? []}
                        showFullOutput
                      />
                    ))}
                  </div>
                </section>
              ) : null}

              <section className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">Timeline</p>
                <AgentSessionEventLog events={events} loading={false} />
              </section>
            </>
          ) : null}
        </div>

        <footer className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-(--qs-border) px-4 py-3 sm:px-5">
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/ballroom?supervisor_session=${encodeURIComponent(sessionId)}`}
              className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              Open replay
            </Link>
            {session?.task_id ? (
              <Link href="/knowledge#outputs" className="qs-btn qs-btn--ghost qs-btn--sm">
                My outputs
              </Link>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            {(["html", "markdown", "pdf"] as const).map((format) => (
              <button
                key={format}
                type="button"
                disabled={exportBusy !== null}
                className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1.5", exportBusy === format && "opacity-60")}
                onClick={() => void exportReport(format)}
              >
                {exportBusy === format ? (
                  <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
                ) : (
                  <Download className="h-3.5 w-3.5" aria-hidden />
                )}
                {format.toUpperCase()}
              </button>
            ))}
          </div>
        </footer>
      </div>
    </div>
  );
}
