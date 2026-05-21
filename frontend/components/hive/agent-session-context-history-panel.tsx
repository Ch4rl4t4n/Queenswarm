"use client";

import type { JSX } from "react";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet } from "@/lib/api";
import type { SupervisorSessionContextHistoryRow } from "@/lib/hive-types";
import { flattenContextDiffLines, type SupervisorContextDiffNode } from "@/lib/supervisor-context-diff";

interface AgentSessionContextHistoryPanelProps {
  sessionId: string;
  refreshKey?: string;
}

/** Recent context_summary diffs from control and review operator actions. */
export function AgentSessionContextHistoryPanel({
  sessionId,
  refreshKey,
}: AgentSessionContextHistoryPanelProps): JSX.Element {
  const [rows, setRows] = useState<SupervisorSessionContextHistoryRow[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await hiveGet<SupervisorSessionContextHistoryRow[]>(
        `agents/sessions/${encodeURIComponent(sessionId)}/context-history?limit=8`,
      );
      setRows(Array.isArray(payload) ? payload : []);
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Context history unavailable");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void reload();
  }, [reload, refreshKey]);

  return (
    <div className="rounded-xl border border-zinc-800/80 bg-black/20 p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Context history</p>
      {loading ? (
        <p className="mt-2 text-xs text-zinc-500">Loading context diffs…</p>
      ) : rows.length === 0 ? (
        <p className="mt-2 text-xs text-zinc-500">No control or review context changes logged yet.</p>
      ) : (
        <ul className="mt-2 max-h-32 space-y-1.5 overflow-y-auto">
          {rows.map((row) => {
            const lines = flattenContextDiffLines(row.context_diff as SupervisorContextDiffNode);
            const label = row.control_action ?? row.decision ?? row.action;
            return (
              <li key={row.audit_id} className="rounded-lg bg-black/25 px-2 py-1.5 text-[10px] text-zinc-400">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-cyan">{label}</span>
                  <span>{new Date(row.created_at).toLocaleString()}</span>
                </div>
                {lines.map((line) => (
                  <p key={`${row.audit_id}-${line.key}`} className="mt-0.5 truncate font-mono">
                    {line.key}: {line.text}
                  </p>
                ))}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
