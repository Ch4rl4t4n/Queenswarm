"use client";

import Link from "next/link";
import { AlertTriangle, ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { hiveGet } from "@/lib/api";
import type { SubAgentSessionRow, SupervisorSessionAuditLogRow, SupervisorSessionRow } from "@/lib/hive-types";
import { supervisorSessionHref } from "@/lib/operator-pending-events";
import { sessionGoalPreview, supervisorAuditExcerpt } from "@/lib/supervisor-session";
import { useSupervisorAuditLatest } from "@/lib/use-supervisor-audit-latest";
import { reconnectSupervisorSessionAudit } from "@/lib/supervisor-session-audit-subscriber";
import { useSupervisorSessionAuditConnectionState } from "@/lib/use-supervisor-session-audit-connection-state";

interface ExecutionStudioSupervisorContextProps {
  sessionIds: string[];
}

function failedSubAgents(session: SupervisorSessionRow): SubAgentSessionRow[] {
  const subAgents = session.sub_agents ?? [];
  return subAgents.filter(
    (sub) =>
      Boolean(sub.error_text?.trim()) ||
      sub.status === "failed" ||
      sub.status === "error" ||
      sub.status === "blocked",
  );
}

function failureExcerpt(text: string | null | undefined, max = 140): string {
  const cleaned = (text ?? "").trim();
  if (!cleaned) return "Connector or tool execution failed.";
  return cleaned.length <= max ? cleaned : `${cleaned.slice(0, max)}…`;
}

function formatSupervisorAuditAction(action: string): string {
  return action.replace(/^supervisor_/, "").replaceAll("_", " ");
}

interface SupervisorSessionContextRowProps {
  session: SupervisorSessionRow;
  initialAudit: SupervisorSessionAuditLogRow | null;
}

function auditConnectionLabel(state: ReturnType<typeof useSupervisorSessionAuditConnectionState>): string {
  if (state === "live") return "Audit live";
  if (state === "connecting") return "Audit connecting…";
  if (state === "reconnecting") return "Audit reconnecting…";
  return "Audit idle";
}

function auditConnectionTone(state: ReturnType<typeof useSupervisorSessionAuditConnectionState>): string {
  if (state === "live") return "text-verified border-verified/30 bg-verified/10";
  if (state === "reconnecting") return "text-magenta border-magenta/30 bg-magenta/10";
  if (state === "connecting") return "text-cyan border-cyan/30 bg-cyan/10";
  return "text-(--qs-text-4) border-(--qs-border)/40 bg-black/20";
}

function SupervisorSessionContextRow({ session, initialAudit }: SupervisorSessionContextRowProps) {
  const latestAudit = useSupervisorAuditLatest(session.id, initialAudit);
  const auditConnection = useSupervisorSessionAuditConnectionState(session.id);
  const failures = failedSubAgents(session);
  const auditText = latestAudit ? supervisorAuditExcerpt(latestAudit.payload) : null;

  return (
    <li className="rounded-lg border border-(--qs-border)/40 bg-black/25 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-[10px] text-(--qs-text-4)">{session.id.slice(0, 8)}…</span>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] ${auditConnectionTone(auditConnection)}`}
            aria-label={`Supervisor audit connection ${auditConnection}`}
          >
            {auditConnectionLabel(auditConnection)}
          </span>
          {auditConnection === "reconnecting" || auditConnection === "connecting" || auditConnection === "idle" ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1 px-2 py-0.5 text-[10px]"
              aria-label="Retry supervisor audit connection"
              onClick={() => reconnectSupervisorSessionAudit(session.id)}
            >
              <RefreshCw className="h-3 w-3" aria-hidden />
              Retry
            </button>
          ) : null}
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-(--qs-text-3)">
            {session.status}
          </span>
        </div>
      </div>
      <p className="mt-1 text-(--qs-text-2)">{sessionGoalPreview(session.goal, 160)}</p>
      {latestAudit ? (
        <p className="mt-2 rounded-lg border border-cyan/20 bg-cyan/5 px-2 py-1 text-[10px] text-(--qs-text-3)">
          <span className="font-semibold text-cyan">{formatSupervisorAuditAction(latestAudit.action)}</span>
          {auditText ? <span className="mt-0.5 block text-(--qs-text-2)">{auditText}</span> : null}
        </p>
      ) : null}
      {failures.length > 0 ? (
        <ul className="mt-2 space-y-1.5 rounded-lg border border-magenta/25 bg-magenta/5 px-2 py-1.5">
          {failures.slice(0, 2).map((sub) => (
            <li key={sub.id} className="text-[10px] text-(--qs-text-3)">
              <span className="inline-flex items-center gap-1 font-semibold text-magenta">
                <AlertTriangle className="h-3 w-3" aria-hidden />
                {sub.role}
              </span>
              <span className="mt-0.5 block text-(--qs-text-2)">{failureExcerpt(sub.error_text)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <Link
        href={supervisorSessionHref(session.id)}
        className="mt-2 inline-flex items-center gap-1 text-[10px] text-cyan hover:text-pollen"
      >
        <ExternalLink className="h-3 w-3" aria-hidden />
        Open in Ballroom
      </Link>
    </li>
  );
}

/** Inline supervisor goal context for pending Execution Studio approvals. */
export function ExecutionStudioSupervisorContext({ sessionIds }: ExecutionStudioSupervisorContextProps) {
  const uniqueIds = useMemo(() => [...new Set(sessionIds.filter(Boolean))], [sessionIds]);
  const [rows, setRows] = useState<
    Array<{ session: SupervisorSessionRow; initialAudit: SupervisorSessionAuditLogRow | null }>
  >([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (uniqueIds.length === 0) {
      setRows([]);
      return;
    }
    let alive = true;
    setLoading(true);
    void (async () => {
      try {
        const loaded = await Promise.all(
          uniqueIds.slice(0, 3).map(async (id) => {
            const [session, auditRows] = await Promise.all([
              hiveGet<SupervisorSessionRow>(`agents/sessions/${encodeURIComponent(id)}`).catch(() => null),
              hiveGet<SupervisorSessionAuditLogRow[]>(
                `agents/sessions/${encodeURIComponent(id)}/audit-logs?limit=1`,
              ).catch(() => []),
            ]);
            if (session === null || typeof session.id !== "string" || !session.id) {
              return null;
            }
            const initialAudit = Array.isArray(auditRows) && auditRows.length > 0 ? auditRows[0] : null;
            return { session, initialAudit };
          }),
        );
        if (!alive) return;
        setRows(loaded.filter((row): row is NonNullable<typeof row> => row !== null));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [uniqueIds]);

  if (uniqueIds.length === 0) {
    return null;
  }

  return (
    <div className="shrink-0 rounded-2xl border border-cyan/30 bg-cyan/5 p-4">
      <p className="text-sm font-semibold text-cyan">Supervisor session context</p>
      <p className="mt-1 text-xs text-(--qs-text-3)">
        Goal excerpts, sub-agent failures, and live operator audit from pending approval sessions.
      </p>
      {loading ? (
        <p className="mt-3 flex items-center gap-2 text-xs text-(--qs-text-3)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading session context…
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {rows.map(({ session, initialAudit }) => (
            <SupervisorSessionContextRow key={session.id} session={session} initialAudit={initialAudit} />
          ))}
          {rows.length === 0 ? (
            <li className="text-xs text-(--qs-text-4)">Unable to load supervisor session details.</li>
          ) : null}
        </ul>
      )}
    </div>
  );
}
