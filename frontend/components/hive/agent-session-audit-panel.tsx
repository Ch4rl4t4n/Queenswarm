"use client";

import type { JSX } from "react";

import { Download, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet } from "@/lib/api";
import { AgentSessionPlaybookDialog } from "@/components/hive/agent-session-playbook-dialog";
import type { SupervisorSessionAuditLogRow } from "@/lib/hive-types";
import { useSupervisorSessionAuditLive } from "@/lib/use-supervisor-session-audit-live";

interface AgentSessionAuditPanelProps {
  sessionId: string;
  refreshKey?: string;
  onLiveAudit?: () => void;
}

async function downloadBlob(blob: Blob, filename: string): Promise<void> {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Operator audit trail for session control, review, and retry actions. */
export function AgentSessionAuditPanel({ sessionId, refreshKey, onLiveAudit }: AgentSessionAuditPanelProps): JSX.Element {
  const [rows, setRows] = useState<SupervisorSessionAuditLogRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportBusy, setExportBusy] = useState<"json" | "csv" | null>(null);
  const [playbookOpen, setPlaybookOpen] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await hiveGet<SupervisorSessionAuditLogRow[]>(
        `agents/sessions/${encodeURIComponent(sessionId)}/audit-logs?limit=12`,
      );
      setRows(Array.isArray(payload) ? payload : []);
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Audit log unavailable");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void reload();
  }, [reload, refreshKey]);

  const handleLiveEntry = useCallback(
    (entry: SupervisorSessionAuditLogRow) => {
      setRows((prev) => {
        if (prev.some((row) => row.id === entry.id)) {
          return prev;
        }
        return [entry, ...prev].slice(0, 12);
      });
      onLiveAudit?.();
    },
    [onLiveAudit],
  );

  useSupervisorSessionAuditLive(sessionId, handleLiveEntry);

  async function exportReport(format: "html" | "markdown" | "pdf"): Promise<void> {
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
      toast.success(`Session report downloaded (${format.toUpperCase()})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report export failed");
    }
  }

  async function exportAudit(format: "json" | "csv", includeEvents = false): Promise<void> {
    setExportBusy(format);
    try {
      const params = new URLSearchParams({
        format,
        limit: "200",
      });
      if (includeEvents) {
        params.set("include_events", "true");
      }
      const res = await fetch(
        `/api/proxy/agents/sessions/${encodeURIComponent(sessionId)}/audit-logs/export?${params.toString()}`,
        { cache: "no-store" },
      );
      if (!res.ok) {
        throw new Error("Export failed");
      }
      const blob = await res.blob();
      const tail = sessionId.replace(/-/g, "").slice(-8).toUpperCase();
      const suffix = includeEvents ? `-audit-events` : `-audit`;
      await downloadBlob(blob, `session-${tail}${suffix}.${format}`);
      toast.success(`Audit exported (${format.toUpperCase()}${includeEvents ? " + events" : ""})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExportBusy(null);
    }
  }

  async function savePlaybook(): Promise<void> {
    setPlaybookOpen(true);
  }

  return (
    <>
      <AgentSessionPlaybookDialog
        sessionId={sessionId}
        open={playbookOpen}
        onOpenChange={setPlaybookOpen}
        onSaved={() => void reload()}
      />
    <div className="rounded-xl border border-zinc-800/80 bg-black/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Operator audit</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={exportBusy !== null}
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5 text-pollen"
            onClick={() => void savePlaybook()}
          >
            Save playbook
          </button>
          <button
            type="button"
            disabled={exportBusy !== null}
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            onClick={() => void exportAudit("csv")}
          >
            {exportBusy === "csv" ? (
              <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <Download className="h-3.5 w-3.5" aria-hidden />
            )}
            CSV
          </button>
          <button
            type="button"
            disabled={exportBusy !== null}
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            onClick={() => void exportAudit("json")}
          >
            {exportBusy === "json" ? (
              <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <Download className="h-3.5 w-3.5" aria-hidden />
            )}
            JSON
          </button>
          <button
            type="button"
            disabled={exportBusy !== null}
            className="qs-btn qs-btn--ghost qs-btn--sm"
            onClick={() => void exportReport("html")}
          >
            Report HTML
          </button>
          <button
            type="button"
            disabled={exportBusy !== null}
            className="qs-btn qs-btn--ghost qs-btn--sm"
            onClick={() => void exportReport("markdown")}
          >
            Report MD
          </button>
          <button
            type="button"
            disabled={exportBusy !== null}
            className="qs-btn qs-btn--ghost qs-btn--sm"
            onClick={() => void exportReport("pdf")}
          >
            Report PDF
          </button>
          <button
            type="button"
            disabled={exportBusy !== null}
            className="qs-btn qs-btn--ghost qs-btn--sm"
            onClick={() => void exportAudit("json", true)}
          >
            Full JSON
          </button>
        </div>
      </div>

      {loading ? (
        <p className="mt-2 text-xs text-zinc-500">Loading audit trail…</p>
      ) : rows.length === 0 ? (
        <p className="mt-2 text-xs text-zinc-500">No operator actions logged yet (create, control, review, retry, interact).</p>
      ) : (
        <ul className="mt-2 max-h-36 space-y-1.5 overflow-y-auto">
          {rows.map((row) => (
            <li key={row.id} className="rounded-lg bg-black/25 px-2 py-1.5 text-[10px] text-zinc-400">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-pollen">{row.action}</span>
                <span>{new Date(row.created_at).toLocaleString()}</span>
              </div>
              {typeof row.payload.control_action === "string" ? (
                <p className="mt-0.5">control: {row.payload.control_action}</p>
              ) : null}
              {typeof row.payload.decision === "string" ? (
                <p className="mt-0.5">review: {row.payload.decision}</p>
              ) : null}
              {typeof row.payload.sub_agent_role === "string" ? (
                <p className="mt-0.5">retry: {row.payload.sub_agent_role}</p>
              ) : null}
              {typeof row.payload.goal_preview === "string" ? (
                <p className="mt-0.5 truncate">create: {row.payload.goal_preview}</p>
              ) : null}
              {typeof row.payload.runtime_mode === "string" ? (
                <p className="mt-0.5">mode: {row.payload.runtime_mode}</p>
              ) : null}
              {typeof row.payload.command_preview === "string" ? (
                <p className="mt-0.5 truncate">interact: {row.payload.command_preview}</p>
              ) : null}
              {typeof row.payload.recipe_name === "string" ? (
                <p className="mt-0.5 truncate">playbook: {row.payload.recipe_name}</p>
              ) : null}
              {row.payload.playbook_auto_saved === true ? (
                <p className="mt-0.5 text-verified">auto-saved playbook on approve</p>
              ) : null}
              {row.payload.context_diff && typeof row.payload.context_diff === "object" ? (
                <p className="mt-0.5 text-cyan">context diff recorded</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
    </>
  );
}
